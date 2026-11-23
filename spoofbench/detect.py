"""Reference implementation of the spoofing (5.1), layering (5.2) and cross-product (5.8)
procedures of the Auspex design specification v1.0, with the Appendix C defaults.

The detectors read only what a firm's surveillance system has: the firm's own orders and
fills and the market-data features captured at each order entry. Ground-truth fields
(Order.ep, Order.role) are read only by score().

Two extensions that the benchmark shows are needed are implemented behind flags and are
off by default, so the literal procedures can be measured on their own:
  flip        the opposite-side execution may follow the cancel by a few milliseconds
              (the "flip" in CFTC v. Oystacher), instead of preceding it
  persistent  layers that rest away from the touch for a long time and are not cancelled
              in response to a fill (the layering algorithm in CFTC v. Sarao)
"""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass, replace

CORRELATES = {"CASH": ("FUT",), "FUT": ("CASH",)}
LOOSE_LAT = 20.0      # candidate pairing looks this far past the fill; Params.t_cancel filters later
LOOSE_PRE = 0.05


@dataclass(frozen=True)
class Params:
    W: float = 30.0          # window: spoof entry to opposite-side fill
    k: float = 2.0           # imbalance multiple of displayed depth within d ticks
    d: int = 3
    t_cancel: float = 5.0    # cancel no later than this after the fill
    f_max: float = 0.05      # fill ratio of the non-bona-fide orders
    n: int = 3               # repetitions required ...
    P_sessions: int = 1      # ... within this many consecutive sessions
    L: int = 3               # distinct price levels that make it layering
    q_min: int = 5
    lag: float = 1.0         # extra tolerance when the two legs are in different instruments
    cross: bool = True       # align correlated instruments (4.3 / 5.8)
    exclusions: bool = True  # two-sided quoting and re-quote exclusions of 5.1
    sym: float = 0.5
    requote: float = 0.5
    flip: bool = False
    persistent: bool = False
    kP: float = 1.0
    T_min: float = 20.0
    k_by_acct: tuple = None  # ((account, k), ...) per-account calibrated multiples



class Index:
    """Per-session lookup tables built once and reused by every configuration."""

    def __init__(self, s):
        self.s = s
        self.by = defaultdict(list)                  # (acct, inst, side) -> orders by entry time
        for o in s.orders:
            self.by[(o.acct, o.inst, o.side)].append(o)
        self.tin = {k: [o.t_in for o in v] for k, v in self.by.items()}
        self.fills = defaultdict(list)               # acct -> (t, order, qty)
        for t, oid, q, px, ag in s.fills:
            o = s.by_oid[oid]
            self.fills[o.acct].append((t, o, q))
        self.fill_t = {}                             # (acct, inst, side) -> fill times, fill qty
        tmp = defaultdict(list)
        for a, fl in self.fills.items():
            for t, o, q in fl:
                tmp[(a, o.inst, o.side)].append((t, q))
        self.fill_t = {k: ([t for t, _ in v], [q for _, q in v]) for k, v in tmp.items()}
        self.cands = self._candidates()

    def _candidates(self):
        """Pair each fill with the account's opposite-side orders that were entered before it and
        cancelled around it. Each order is paired once, with the first fill that follows its entry."""
        out, used = [], set()
        for acct, fl in self.fills.items():
            for t, og, q in fl:
                g = og.side
                for inst in (og.inst,) + CORRELATES.get(og.inst, ()):
                    key = (acct, inst, -g)
                    lst = self.by.get(key)
                    if not lst:
                        continue
                    tin = self.tin[key]
                    grp = []
                    for o in lst[bisect_left(tin, t - 30.0):bisect_right(tin, t + 1e-9)]:
                        if o.status == "C" and o.px is not None and o.oid not in used \
                                and t - LOOSE_PRE <= o.t_out <= t + LOOSE_LAT and o.oid != og.oid:
                            grp.append(o)
                    if grp:
                        used.update(o.oid for o in grp)
                        out.append(dict(acct=acct, sid=self.s.sid, inst=inst, cross=inst != og.inst, t=t,
                                        g=g, gen=og, orders=grp))
        return out

    def entered_after(self, acct, inst, side, t0, t1):
        """Quantity the account entered or executed on (inst, side) in [t0, t1]. The window is closed
        at t0 because a re-quote often carries the same timestamp as the cancel it replaces."""
        key = (acct, inst, side)
        lst = self.by.get(key)
        if not lst:
            return 0
        tin = self.tin[key]
        return sum(o.qty for o in lst[bisect_left(tin, t0):bisect_right(tin, t1)])

    def had_fill(self, acct, inst, side, t0, t1):
        ft = self.fill_t.get((acct, inst, side))
        if not ft:
            return False
        return bisect_right(ft[0], t1) > bisect_left(ft[0], t0)


def evaluate(c, ix, P, kmap=None):
    """Apply one parameter set to one candidate. Returns an instance dict or None."""
    if c["cross"] and not P.cross:
        return None
    t, gen = c["t"], c["gen"]
    hi = P.t_cancel + (P.lag if c["cross"] else 0.0)
    keep = []
    for o in c["orders"]:
        lat = o.t_out - t
        if o.dist > P.d or o.filled > P.f_max * o.qty or o.t_in < t - P.W:
            continue
        if 0.0 <= lat <= hi or (P.flip and lat < 0.0 and gen.aggr):
            keep.append(o)
    if not keep:
        return None
    first = min(keep, key=lambda o: o.t_in)
    Q = sum(o.qty for o in keep)
    depth = max(0, sum(first.depth[:P.d + 1]))
    k = kmap.get(c["acct"], P.k) if kmap else P.k
    if Q < max(P.q_min, k * depth):
        return None
    tc = max(o.t_out for o in keep)
    sym = first.own_opp >= P.sym * (first.own_same + Q)
    again = ix.entered_after(c["acct"], c["inst"], first.side, tc, tc + P.requote) >= 0.5 * Q
    if P.exclusions and (sym or again):
        return None
    levels = len({o.px for o in keep})
    proc = "5.8" if c["cross"] else ("5.2" if levels >= P.L else "5.1")
    lats = [o.t_out - t for o in keep]
    return dict(acct=c["acct"], sid=c["sid"], proc=proc, t=t, oids=[o.oid for o in keep], Q=Q, depth=depth,
                ratio=Q / max(1, depth), asym=Q / max(1, gen.qty), lat=max(lats), lat_min=min(lats),
                levels=levels, n_orders=len(keep), life=tc - first.t_in, cross=int(c["cross"]),
                gen_aggr=int(gen.aggr), sym=int(sym), again=int(again),
                own_ratio=first.own_opp / max(1, first.own_same + Q))


def persistent(ix, P):
    """5.2 extension: L or more of the account's orders resting on one side at distinct levels beyond
    the first two ticks, together at least kP times the displayed size at those levels, held for
    T_min or longer with no fills, while the account executes on the other side."""
    out = []
    for (acct, inst, side), lst in ix.by.items():
        far = [o for o in lst if o.px is not None and o.dist >= 2 and o.status in ("C", "R") and o.filled == 0
               and o.t_out - o.t_in > 0.0]
        if len(far) < P.L:
            continue
        # at equal timestamps entries are applied before exits, so a cancel/replace does not break the run
        ev = sorted([(o.t_in, 1, o) for o in far] + [(o.t_out, 0, o) for o in far], key=lambda e: (e[0], -e[1]))
        live, on, start, oids = {}, False, 0.0, set()
        for t, kind, o in ev:
            if kind:
                live[o.oid] = o
            else:
                live.pop(o.oid, None)
            ok = False
            if len({x.px for x in live.values()}) >= P.L:
                newest = max(live.values(), key=lambda x: x.t_in)
                ref = sum(newest.depth[2:])
                ok = sum(x.qty for x in live.values()) >= max(P.q_min, P.kP * ref)
            if ok and not on:
                on, start, oids = True, t, set()
            if on:
                oids.update(live)
            if on and not ok:
                on = False
                if t - start >= P.T_min and ix.had_fill(acct, inst, -side, start, t + P.W):
                    out.append(dict(acct=acct, sid=ix.s.sid, proc="5.2P", t=start, oids=sorted(oids),
                                    Q=0, depth=0, ratio=0.0, asym=0.0, lat=t - start, lat_min=0.0, levels=P.L,
                                    n_orders=len(oids), life=t - start, cross=0, gen_aggr=0, sym=0, again=0,
                                    own_ratio=0.0))
    return out


def detect(indexes, P):
    """Run one parameter set over a list of sessions (in time order). Returns flagged instances:
    those in an account-window where the repetition requirement is met."""
    per = []
    kmap = dict(P.k_by_acct) if P.k_by_acct else None
    for ix in indexes:
        inst = [i for i in (evaluate(c, ix, P, kmap) for c in ix.cands) if i]
        per.append(inst)
    flagged = []
    counts = [defaultdict(int) for _ in indexes]
    for j, inst in enumerate(per):
        for i in inst:
            counts[j][i["acct"]] += 1
    for j, inst in enumerate(per):
        lo = max(0, j - P.P_sessions + 1)
        for i in inst:
            if sum(counts[m][i["acct"]] for m in range(lo, j + 1)) >= P.n:
                flagged.append(i)
    if P.persistent:
        for ix in indexes:
            flagged.extend(persistent(ix, P))
    return flagged


def score(indexes, flagged):
    """Episode recall and false-alert load against ground truth."""
    hit_eps, cases = set(), defaultdict(lambda: [0, 0])     # (acct, sid) -> [true instances, false instances]
    sess = {ix.s.sid: ix.s for ix in indexes}
    for i in flagged:
        s = sess[i["sid"]]
        eps = {s.by_oid[o].ep for o in i["oids"] if s.by_oid[o].role == "spoof"}
        i["true"] = int(bool(eps))
        cases[(i["acct"], i["sid"])][0 if eps else 1] += 1
        hit_eps.update((i["sid"], e) for e in eps)
    rec = defaultdict(lambda: [0, 0])                       # (template, evasive) -> [detected, total]
    for ix in indexes:
        for e in ix.s.episodes:
            if not e["spoof"] or not e["filled"]:
                continue                                    # attempts that never got a fill are reported separately
            r = rec[(e["template"], e["evasive"])]
            r[1] += 1
            r[0] += (ix.s.sid, e["id"]) in hit_eps
    kinds = {a: v for ix in indexes for a, v in ix.s.accounts.items()}
    false_cases = defaultdict(int)
    for (acct, sid), (tp, fp) in cases.items():
        if tp == 0:
            false_cases[kinds[acct]["kind"] if kinds[acct]["truth"] == "legit" else "manip-acct"] += 1
    return dict(recall={f"{k[0]}{'/evasive' if k[1] else ''}": v for k, v in sorted(rec.items())},
                cases=len(cases), false_cases=dict(false_cases), false_cases_total=sum(false_cases.values()),
                instances=len(flagged), false_instances=sum(1 - i["true"] for i in flagged),
                sessions=len(indexes))


def calibrate(indexes, q=0.995, d=3, cap=None, floor=0.02):
    """Section 6.1: per-account imbalance threshold as a quantile of the account's own history.
    An entry group is the account's passive orders on one side entered within one second of each
    other; its imbalance is group size over displayed depth within d ticks.
    cap: if set, an account's threshold may not exceed cap times the median threshold of its class."""
    groups = defaultdict(list)
    kinds = {}
    for ix in indexes:
        kinds.update({a: v["kind"] for a, v in ix.s.accounts.items()})
        for (acct, inst, side), lst in ix.by.items():
            cur, last_t = None, -1e9
            for o in lst:
                if o.px is None or o.aggr or o.dist > d or o.dist < 0:
                    continue
                if o.t_in - last_t > 1.0:
                    if cur:
                        groups[acct].append(cur[0] / max(1, cur[1]))
                    cur = [0, sum(o.depth[:d + 1])]
                cur[0] += o.qty
                last_t = o.t_in
            if cur:
                groups[acct].append(cur[0] / max(1, cur[1]))
    k = {}
    for a, g in groups.items():
        if len(g) >= 50:
            g = sorted(g)
            k[a] = max(floor, g[min(len(g) - 1, int(q * len(g)))])
    if cap:
        by_kind = defaultdict(list)
        for a, v in k.items():
            by_kind[kinds[a]].append(v)
        med = {kd: sorted(v)[len(v) // 2] for kd, v in by_kind.items()}
        k = {a: min(v, cap * med[kinds[a]]) for a, v in k.items()}
    return tuple(sorted(k.items()))
