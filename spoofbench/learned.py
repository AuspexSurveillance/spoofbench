"""Learned detector (v0.5).

The procedures in detect.py start from a fill: an opposite-side execution, then a cancel. That
leaves out every attempt in which the genuine order never traded, and it ties the result to the
order sequence the procedure was written for. This module starts from the cancel instead.

Unit of analysis: a *pull group*, the orders of one account on one side of one instrument that
were cancelled together (within EPS seconds), with cancel/replace chains followed back to the
first generation. Every pull group gets a feature vector built only from what the firm's own
records hold: the group's size against displayed depth, how long it rested, how much of it
traded, what the account had and did on the opposite side (same instrument and the correlated
one) before, during and just after, and whether the account came back on the same side.

A gradient-boosted classifier trained on seeded baseline sessions scores each group. Alerts are
raised per account-session when enough groups score above a class threshold; the thresholds are
chosen on out-of-fold scores of the baseline sessions under the same false-case budget the
procedures use. Ground-truth fields (Order.ep, Order.role) are read only to build labels and to
score.
"""
from bisect import bisect_left, bisect_right
from collections import defaultdict

import numpy as np

EPS = 0.05                 # cancels this close together belong to one pull group
LOOK = 1.0                 # "just after" window, seconds
CORRELATES = {"CASH": ("FUT",), "FUT": ("CASH",)}

FEATS = [
    # size and shape
    "Q", "n_ord", "n_lev", "n_gen", "dist_min", "dist_max", "dist_wm", "share_touch",
    "r_d3", "r_d0", "r_lvl", "r_all", "r_med",
    # time
    "dur", "dur_last", "ent_span",
    # executions on the group itself
    "fill_share", "sib_fill",
    # the account's own book around the group
    "own_same", "own_opp", "two_sided", "asym_opp",
    # opposite side, same instrument
    "opp_live_t0", "opp_live_tc", "opp_ent_pre", "opp_ent_life", "opp_pfill", "opp_afill",
    "lat_fill", "first_fill_rel", "opp_afill_post50", "opp_afill_post1", "opp_ent_post50", "flip_px_ok",
    "opp_cxl_sim", "opp_cxl_post",
    # opposite side, correlated instrument
    "x_live_t0", "x_pfill", "x_afill", "x_lat_fill", "x_ent_pre",
    # after the cancel, same side
    "again_05", "again_5", "same_afill_post1", "same_pfill_life",
    # pattern-neutral summaries: opposite-side interest and executions in either instrument,
    # before or after the cancel
    "u_exp", "u_exec", "u_exec_post", "u_lat", "asym_exp", "asym_exec",
    # the pull as part of a wider withdrawal: robust to orders cancelled one at a time
    "r_live", "wave_cxl", "r_wave",
    # the account's session as a whole (quantity-weighted over its pull groups in this instrument)
    "ctx_n", "ctx_fill_w", "ctx_exec_w", "ctx_again_w", "ctx_short_w", "ctx_qshare", "ctx_ofill", "ctx_ofill_big",
]
WAVE = ["r_live", "wave_cxl", "r_wave"]
CTX = ["ctx_n", "ctx_fill_w", "ctx_exec_w", "ctx_again_w", "ctx_short_w", "ctx_qshare", "ctx_ofill", "ctx_ofill_big"]
SPECIFIC = ["opp_live_t0", "opp_live_tc", "opp_ent_pre", "opp_ent_life", "opp_pfill", "opp_afill", "lat_fill",
            "first_fill_rel", "opp_afill_post50", "opp_afill_post1", "opp_ent_post50", "flip_px_ok",
            "x_live_t0", "x_pfill", "x_afill", "x_lat_fill", "x_ent_pre", "own_opp", "asym_opp"]
NEUTRAL = [f for f in FEATS if f not in SPECIFIC]
CORE = [f for f in NEUTRAL if f not in WAVE and f not in CTX]
FI = {f: i for i, f in enumerate(FEATS)}


class _Key:
    """Arrays for one (account, instrument, side): entries, resting quantity over time, cancels, fills."""

    def __init__(self):
        self.orders = []
        self.fills = []                              # (t, qty, aggressor, px)

    def build(self, aggfill):
        o = self.orders
        self.tin = np.array([x.t_in for x in o])
        q = np.array([x.qty for x in o], dtype=float)
        pas = np.array([x.px is not None and not x.aggr for x in o])
        self.c_all = np.concatenate(([0.0], np.cumsum(q)))
        self.c_pas = np.concatenate(([0.0], np.cumsum(q * pas)))
        self.px = np.array([np.nan if x.px is None else x.px for x in o])
        ev = []
        for x in o:
            if x.px is None:
                continue
            rest = x.qty - aggfill.get(x.oid, 0)
            if rest > 0 and x.t_out is not None and x.t_out > x.t_in:
                ev.append((x.t_in, rest))
                ev.append((x.t_out, -rest))
        ev.sort()
        self.lv_t = np.array([e[0] for e in ev])
        self.lv_c = np.concatenate(([0.0], np.cumsum([e[1] for e in ev])))
        cx = sorted((x.t_out, x.qty - x.filled) for x in o
                    if x.px is not None and x.status in ("C", "R") and x.t_out > x.t_in)
        self.cx_t = np.array([c[0] for c in cx])
        self.cx_c = np.concatenate(([0.0], np.cumsum([c[1] for c in cx])))
        f = self.fills
        self.f_t = np.array([x[0] for x in f])
        fq = np.array([x[1] for x in f], dtype=float)
        ag = np.array([x[2] for x in f], dtype=bool)
        self.f_cp = np.concatenate(([0.0], np.cumsum(fq * ~ag))) if len(f) else np.zeros(1)
        self.f_ca = np.concatenate(([0.0], np.cumsum(fq * ag))) if len(f) else np.zeros(1)
        self.f_px = np.array([x[3] for x in f], dtype=float)
        self.med = float(np.median([x.qty for x in o if x.px is not None])) if any(x.px is not None for x in o) else 1.0
        return self

    # window sums; lo/hi inclusive flags chosen by the caller through side arguments
    @staticmethod
    def _win(t, c, a, b, left="left", right="right"):
        return c[np.searchsorted(t, b, right)] - c[np.searchsorted(t, a, left)]

    def ent_all(self, a, b, **kw):
        return self._win(self.tin, self.c_all, a, b, **kw)

    def ent_pas(self, a, b, **kw):
        return self._win(self.tin, self.c_pas, a, b, **kw)

    def cxl(self, a, b, **kw):
        return self._win(self.cx_t, self.cx_c, a, b, **kw)

    def pfill(self, a, b, **kw):
        return self._win(self.f_t, self.f_cp, a, b, **kw)

    def afill(self, a, b, **kw):
        return self._win(self.f_t, self.f_ca, a, b, **kw)

    def live(self, t, side):
        return self.lv_c[np.searchsorted(self.lv_t, t, side)]

    def last_fill(self, a, b):
        """Time of the last fill in [a, b], nan if none."""
        j = np.searchsorted(self.f_t, b, "right") - 1
        ok = (j >= 0) & (self.f_t[np.clip(j, 0, None)] >= a) if len(self.f_t) else np.zeros(len(b), bool)
        out = np.full(len(b), np.nan)
        if len(self.f_t):
            out[ok] = self.f_t[j[ok]]
        return out

    def first_fill(self, a, b):
        j = np.searchsorted(self.f_t, a, "left")
        out = np.full(len(a), np.nan)
        if len(self.f_t):
            ok = (j < len(self.f_t))
            ok[ok] &= self.f_t[j[ok]] <= b[ok]
            out[ok] = self.f_t[j[ok]]
        return out


_EMPTY = None


def _empty():
    global _EMPTY
    if _EMPTY is None:
        _EMPTY = _Key().build({})
    return _EMPTY


def _pull_groups(lst):
    """Cluster one key's cancelled orders by cancel time and follow replace chains."""
    cand = [o for o in lst if o.px is not None and o.status in ("C", "R") and o.t_out > o.t_in and o.qty - o.filled > 0]
    if not cand:
        return []
    cand.sort(key=lambda o: o.t_out)
    clusters, cur = [], [cand[0]]
    for o in cand[1:]:
        if o.t_out - cur[-1].t_out <= EPS:
            cur.append(o)
        else:
            clusters.append(cur)
            cur = [o]
    clusters.append(cur)
    parent = list(range(len(clusters)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    if any(o.status == "R" for o in cand):
        where = {o.oid: ci for ci, c in enumerate(clusters) for o in c}
        tin = [o.t_in for o in lst]
        for ci, c in enumerate(clusters):
            if any(o.status == "R" for o in c):
                for o in lst[bisect_left(tin, c[0].t_out - 1e-9):bisect_right(tin, c[-1].t_out + EPS)]:
                    cj = where.get(o.oid)
                    if cj is not None and cj != ci:
                        parent[find(ci)] = find(cj)
    groups = defaultdict(list)
    for ci, c in enumerate(clusters):
        groups[find(ci)].append(c)
    return list(groups.values())                    # each group: list of generations, in time order


def features(s):
    """Pull groups of one session. Returns (X float32 [n, len(FEATS)], meta list of dicts)."""
    keys = defaultdict(_Key)
    aggfill = defaultdict(int)
    for o in s.orders:
        keys[(o.acct, o.inst, o.side)].orders.append(o)
    for t, oid, q, px, ag in s.fills:
        o = s.by_oid[oid]
        keys[(o.acct, o.inst, o.side)].fills.append((t, q, ag, px))
        if ag:
            aggfill[oid] += q
    for k in keys.values():
        k.build(aggfill)
    rows, meta = [], []
    for (acct, inst, side), K in keys.items():
        gs = _pull_groups(K.orders)
        if not gs:
            continue
        n = len(gs)
        F = np.zeros((n, len(FEATS)))
        t0 = np.zeros(n); tg = np.zeros(n); tc = np.zeros(n); Qv = np.zeros(n); pxn = np.zeros(n); d3 = np.ones(n)
        tin_list = K.tin
        for gi, gens in enumerate(gs):
            peak = max(gens, key=lambda g: sum(o.qty for o in g))
            last = gens[-1]
            allo = [o for g in gens for o in g]
            first = min(peak, key=lambda o: o.t_in)
            oldest = min(allo, key=lambda o: o.t_in)
            Q = float(sum(o.qty for o in peak))
            d = first.depth
            dists = [o.dist for o in peak]
            lv = {o.dist for o in peak}
            t0[gi], tg[gi], tc[gi], Qv[gi] = oldest.t_in, min(o.t_in for o in last), max(o.t_out for o in last), Q
            pxn[gi] = max(o.px * side for o in peak) * side          # price nearest the touch
            f = F[gi]
            f[FI["Q"]] = Q
            f[FI["n_ord"]] = len(peak)
            f[FI["n_lev"]] = len(lv)
            f[FI["n_gen"]] = len(gens)
            f[FI["dist_min"]] = min(dists)
            f[FI["dist_max"]] = max(dists)
            f[FI["dist_wm"]] = sum(o.dist * o.qty for o in peak) / Q
            f[FI["share_touch"]] = sum(o.qty for o in peak if o.dist <= 0) / Q
            d3[gi] = max(1, sum(d[:4]))
            f[FI["r_d3"]] = Q / d3[gi]
            f[FI["r_d0"]] = Q / max(1, d[0])
            f[FI["r_lvl"]] = Q / max(1, sum(d[k] for k in lv if 0 <= k < len(d)))
            f[FI["r_all"]] = Q / max(1, sum(d))
            f[FI["r_med"]] = Q / max(1.0, K.med)
            f[FI["ent_span"]] = max(o.t_in for o in peak) - first.t_in
            tot = sum(o.qty for o in allo)
            f[FI["fill_share"]] = sum(o.filled for o in allo) / tot
            # orders entered with the peak generation that traded in full and so were never cancelled
            a, b = bisect_left(tin_list, first.t_in - EPS), bisect_right(tin_list, max(o.t_in for o in peak) + EPS)
            f[FI["sib_fill"]] = sum(o.qty for o in K.orders[a:b] if o.status == "F" and o.px is not None and not o.aggr) / Q
            f[FI["own_same"]] = oldest.own_same
            f[FI["own_opp"]] = oldest.own_opp
            f[FI["two_sided"]] = oldest.own_opp / max(1.0, oldest.own_same + Q)
            f[FI["asym_opp"]] = Q / max(1.0, oldest.own_opp)
            eps = {o.ep for o in allo if o.role == "spoof"}
            meta.append(dict(acct=acct, sid=s.sid, inst=inst, side=side, t0=float(t0[gi]), t=float(tc[gi]),
                             oids=[o.oid for o in allo], true=int(bool(eps)), eps=eps))
        dur = tc - t0
        F[:, FI["dur"]] = dur
        F[:, FI["dur_last"]] = tc - tg
        O = keys.get((acct, inst, -side)) or _empty()
        F[:, FI["opp_live_t0"]] = O.live(t0, "right")
        F[:, FI["opp_live_tc"]] = O.live(tc - EPS, "left")
        F[:, FI["opp_ent_pre"]] = O.ent_pas(t0 - LOOK, t0)
        F[:, FI["opp_ent_life"]] = O.ent_pas(t0, tc, left="right")
        F[:, FI["opp_pfill"]] = O.pfill(t0, tc)
        F[:, FI["opp_afill"]] = O.afill(t0, tc)
        lf = O.last_fill(t0, tc)
        F[:, FI["lat_fill"]] = np.where(np.isnan(lf), -1.0, tc - lf)
        ff = O.first_fill(t0, tc)
        F[:, FI["first_fill_rel"]] = np.where(np.isnan(ff), -1.0, (ff - t0) / np.maximum(dur, 1e-3))
        F[:, FI["opp_afill_post50"]] = O.afill(tc, tc + EPS, left="right")
        F[:, FI["opp_afill_post1"]] = O.afill(tc, tc + LOOK, left="right")
        F[:, FI["opp_ent_post50"]] = O.ent_all(tc, tc + EPS, left="right")
        if len(O.tin):
            j = np.searchsorted(O.tin, tc, "right")
            ok = j < len(O.tin)
            ok[ok] &= O.tin[j[ok]] <= tc[ok] + EPS
            p = np.where(ok, O.px[np.clip(j, 0, len(O.tin) - 1)], np.nan)
            reach = np.where(np.isnan(p), 1.0, ((p - pxn) * (-side) >= 0).astype(float))
            F[:, FI["flip_px_ok"]] = np.where(ok, reach, 0.0)
        F[:, FI["opp_cxl_sim"]] = O.cxl(tc - EPS, tc + EPS)
        F[:, FI["opp_cxl_post"]] = O.cxl(tc + EPS, tc + LOOK, left="right")
        xl = np.zeros(n); xp = np.zeros(n); xa = np.zeros(n); xe = np.zeros(n); xlat = np.full(n, -1.0)
        xlife = np.zeros(n); xpost = np.zeros(n); xnear = np.full(n, np.inf)
        near = np.full(n, np.inf)                    # time between the cancel and the nearest opposite execution
        for Kk in (O,):
            a_, b_ = Kk.last_fill(t0, tc), Kk.first_fill(tc + 1e-9, tc + LOOK)
            near = np.fmin(near, np.fmin(np.where(np.isnan(a_), np.inf, tc - a_), np.where(np.isnan(b_), np.inf, b_ - tc)))
        for j in CORRELATES.get(inst, ()):
            Xk = keys.get((acct, j, -side))
            if Xk is None:
                continue
            xl += Xk.live(t0, "right")
            xp += Xk.pfill(t0, tc)
            xa += Xk.afill(t0, tc)
            xe += Xk.ent_all(t0 - LOOK, t0)
            xlife += Xk.ent_pas(t0, tc, left="right")
            xpost += Xk.pfill(tc, tc + LOOK, left="right") + Xk.afill(tc, tc + LOOK, left="right")
            a_, b_ = Xk.last_fill(t0, tc), Xk.first_fill(tc + 1e-9, tc + LOOK)
            near = np.fmin(near, np.fmin(np.where(np.isnan(a_), np.inf, tc - a_), np.where(np.isnan(b_), np.inf, b_ - tc)))
            lf = Xk.last_fill(t0, tc)
            lat = np.where(np.isnan(lf), -1.0, tc - lf)
            xlat = np.where((xlat < 0) | ((lat >= 0) & (lat < xlat)), lat, xlat)
        F[:, FI["x_live_t0"]], F[:, FI["x_pfill"]], F[:, FI["x_afill"]] = xl, xp, xa
        F[:, FI["x_lat_fill"]], F[:, FI["x_ent_pre"]] = xlat, xe
        F[:, FI["again_05"]] = K.ent_all(tc, tc + 0.5) / Qv
        F[:, FI["again_5"]] = K.ent_all(tc, tc + 5.0) / Qv
        F[:, FI["same_afill_post1"]] = K.afill(tc, tc + LOOK, left="right") / Qv
        F[:, FI["same_pfill_life"]] = K.pfill(t0, tc) / Qv
        wave = K.cxl(tc - 2.0, tc + 2.0)
        F[:, FI["r_live"]] = K.live(tc - EPS, "left") / d3
        F[:, FI["wave_cxl"]] = wave / Qv
        F[:, FI["r_wave"]] = wave / d3
        post = O.pfill(tc, tc + LOOK, left="right") + O.afill(tc, tc + LOOK, left="right") + xpost
        pre = F[:, FI["opp_pfill"]] + F[:, FI["opp_afill"]] + xp + xa
        exp = F[:, FI["opp_live_t0"]] + F[:, FI["opp_ent_life"]] + xl + xlife
        F[:, FI["u_exp"]] = exp
        F[:, FI["u_exec"]] = pre + post
        F[:, FI["u_exec_post"]] = post
        F[:, FI["u_lat"]] = np.where(np.isinf(near), -1.0, near)
        F[:, FI["asym_exp"]] = Qv / np.maximum(1.0, exp)
        F[:, FI["asym_exec"]] = Qv / np.maximum(1.0, pre + post)
        rows.append(F)
    if not rows:
        return np.zeros((0, len(FEATS)), np.float32), meta
    X = np.vstack(rows)
    # account-session context
    idx = defaultdict(list)
    for i, m in enumerate(meta):
        idx[(m["acct"], m["inst"])].append(i)
    ofill = {}
    for (acct, inst, side), K in keys.items():
        po = [o for o in K.orders if o.px is not None and not o.aggr]
        a = ofill.setdefault((acct, inst), [0.0, 0.0, []])
        a[2].extend(po)
    for key, (_, _, po) in ofill.items():
        if not po:
            ofill[key] = (0.0, 0.0)
            continue
        q75 = float(np.percentile([o.qty for o in po], 75))
        big = [o for o in po if o.qty >= q75]
        ofill[key] = (sum(o.filled for o in po) / sum(o.qty for o in po), sum(o.filled for o in big) / max(1, sum(o.qty for o in big)))
    for key, ii in idx.items():
        ii = np.array(ii)
        Q = X[ii, FI["Q"]]
        tot = Q.sum()
        X[ii, FI["ctx_n"]] = len(ii)
        X[ii, FI["ctx_fill_w"]] = (X[ii, FI["fill_share"]] * Q).sum() / tot
        X[ii, FI["ctx_exec_w"]] = (((X[ii, FI["u_lat"]] >= 0) & (X[ii, FI["u_lat"]] <= 5.0)) * Q).sum() / tot
        X[ii, FI["ctx_again_w"]] = ((X[ii, FI["again_5"]] >= 0.5) * Q).sum() / tot
        X[ii, FI["ctx_short_w"]] = ((X[ii, FI["dur"]] < 5.0) * Q).sum() / tot
        X[ii, FI["ctx_qshare"]] = Q / tot
        X[ii, FI["ctx_ofill"]], X[ii, FI["ctx_ofill_big"]] = ofill.get(key, (0.0, 0.0))
    return X.astype(np.float32), meta


# ---------------------------------------------------------------------------------------------
# Model, calibration and scoring
# ---------------------------------------------------------------------------------------------
USE = CORE + WAVE + CTX          # pattern-neutral features; SPECIFIC is kept for ablation only
GROUPS = {
    "size against the displayed book": ["Q", "n_ord", "n_lev", "dist_min", "dist_max", "dist_wm", "share_touch",
                                        "r_d3", "r_d0", "r_lvl", "r_all", "r_med", "r_live", "r_wave", "wave_cxl"],
    "time at rest": ["dur", "dur_last", "ent_span", "n_gen"],
    "executions on these orders": ["fill_share", "sib_fill", "same_pfill_life"],
    "the account's interest and executions on the other side": ["own_same", "two_sided", "u_exp", "u_exec", "u_exec_post",
                                                                "u_lat", "asym_exp", "asym_exec", "opp_cxl_sim", "opp_cxl_post"],
    "what the account did on this side afterwards": ["again_05", "again_5", "same_afill_post1"],
    "the account's session as a whole": CTX,
}


def featurize(s):
    """Everything the detector and the scorer need from one session, without the order objects."""
    X, meta = features(s)
    eps = [dict(id=e["id"], template=e["template"], evasive=bool(e["evasive"]), filled=bool(e["filled"]),
                n_spoof=len(e["spoof"]), params=e.get("params", {})) for e in s.episodes]
    return dict(sid=s.sid, X=X, meta=meta, accounts=s.accounts, episodes=eps)


def _stack(recs, cols):
    X = np.vstack([r["X"] for r in recs])[:, cols]
    rows = [(r["sid"], m) for r in recs for m in r["meta"]]
    return X, np.array([m["true"] for _, m in rows]), np.array([sid for sid, _ in rows]), rows


class Detector:
    """Average of a randomized-tree ensemble and gradient boosting over pull-group features.

    n       an account-session becomes a case when at least n of its groups score above the
            threshold of the account's class
    budget  false cases allowed per 100 legitimate account-sessions of a class on the baseline
    floor   a class threshold is never set below this score. Seeded groups score near 1 and
            legitimate ones near 0, so the budget alone puts the threshold a few hundredths above
            zero, where a small shift between baseline and test days turns into false cases.
            0.2 was chosen on development sessions (see FINDINGS_V05.md).
    The thresholds are set on out-of-fold scores: every baseline session is scored by a model
    that was not trained on it.
    """

    def __init__(self, n=2, budget=2.0, folds=5, seed=0, feats=None, trees=150, floor=0.2):
        self.n, self.budget, self.folds, self.seed, self.trees, self.floor = n, budget, folds, seed, trees, floor
        self.feats = list(feats or USE)
        self.cols = [FI[f] for f in self.feats]

    def _fit(self, X, y):
        from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
        et = ExtraTreesClassifier(n_estimators=self.trees, min_samples_leaf=5, max_features=0.4, bootstrap=True,
                                  max_samples=0.5, n_jobs=-1, random_state=self.seed).fit(X, y)
        gb = HistGradientBoostingClassifier(max_depth=6, max_iter=300, learning_rate=0.06, l2_regularization=1.0,
                                            min_samples_leaf=20, random_state=self.seed).fit(X, y)
        return et, gb

    @staticmethod
    def _proba(models, X):
        return np.mean([m.predict_proba(X)[:, 1] for m in models], axis=0)

    def fit(self, recs, exclude=()):
        """recs: featurized baseline sessions. exclude: accounts left out of training and calibration."""
        exclude = set(exclude)
        X, y, sid, rows = _stack(recs, self.cols)
        keep = np.array([m["acct"] not in exclude for _, m in rows])
        u = np.unique(sid)
        oof = np.zeros(len(y))
        for f in range(self.folds):
            te = np.isin(sid, u[f::self.folds])
            oof[te] = self._proba(self._fit(X[~te & keep], y[~te & keep]), X[te])
        self.models = self._fit(X[keep], y[keep])
        acc = recs[0]["accounts"]
        self.kind = {a: v["kind"] for a, v in acc.items()}
        per = defaultdict(list)
        for (s, m), p in zip(rows, oof):
            per[(m["acct"], s)].append(p)
        self.thr, self.thr_budget = {}, {}
        for kd in sorted(set(self.kind.values())):
            members = [a for a, v in acc.items() if v["kind"] == kd and v["truth"] == "legit" and a not in exclude]
            if not members:
                continue
            stat = sorted((self._nth(per.get((a, r["sid"]), ())) for a in members for r in recs), reverse=True)
            allowed = int(self.budget * len(stat) / 100.0)
            self.thr_budget[kd] = float(stat[allowed]) if allowed < len(stat) else 0.0
            self.thr[kd] = max(self.thr_budget[kd], self.floor)
        self.thr_default = max(self.thr.values())
        legit = np.array([acc[m["acct"]]["truth"] == "legit" and m["acct"] not in exclude for _, m in rows])
        self.ref = np.median(X[legit], axis=0)                      # reference point for explanations
        self.oof, self.oof_rows = oof, rows
        return self

    def _nth(self, v):
        v = sorted(v, reverse=True)
        return v[self.n - 1] if len(v) >= self.n else 0.0

    def score(self, recs):
        X, y, sid, rows = _stack(recs, self.cols)
        return self._proba(self.models, X), rows

    def flag(self, rows, p, thr=None, budget_only=False):
        """Flagged groups: those above the class threshold in account-sessions with at least n of them.
        budget_only=True applies the budget thresholds without the floor."""
        per = defaultdict(list)
        table = self.thr_budget if budget_only else self.thr
        default = max(table.values())
        for (sid, m), s in zip(rows, p):
            t = thr if thr is not None else table.get(self.kind.get(m["acct"]), default)
            if s > t:
                per[(m["acct"], sid)].append(dict(m, score=float(s)))
        return [m for ms in per.values() if len(ms) >= self.n for m in ms]

    def explain(self, x):
        """Score drop when each feature group is set to the typical legitimate value: which parts
        of the evidence the score rests on. x: one row in self.feats order."""
        base = self._proba(self.models, x[None, :])[0]
        out = {}
        for name, fs in GROUPS.items():
            z = x.copy()
            for f in fs:
                if f in self.feats:
                    j = self.feats.index(f)
                    z[j] = self.ref[j]
            out[name] = round(float(base - self._proba(self.models, z[None, :])[0]), 4)
        return dict(score=round(float(base), 4), drops=dict(sorted(out.items(), key=lambda kv: -kv[1])))


def recall_table(recs, hit):
    rec = defaultdict(lambda: [0, 0])
    for r in recs:
        for e in r["episodes"]:
            if e["n_spoof"]:
                v = rec[(e["template"], e["evasive"], e["filled"])]
                v[1] += 1
                v[0] += (r["sid"], e["id"]) in hit
    return rec


def pooled(rec, template=None, evasive=None, filled=None):
    d = n = 0
    for (t, ev, fl), v in rec.items():
        if (template is None or t == template) and (evasive is None or ev == evasive) and (filled is None or fl == filled):
            d, n = d + v[0], n + v[1]
    return d, n


def evaluate(recs, flagged, name=""):
    """Episode recall (with and without a fill, faithful and evasive) and false-case load.
    flagged: dicts with acct, sid, true, eps (a group from Detector.flag or a rule instance)."""
    acc = recs[0]["accounts"]
    n_legit = sum(v["truth"] == "legit" for v in acc.values())
    cases, hit = defaultdict(lambda: [0, 0]), set()
    for i in flagged:
        cases[(i["acct"], i["sid"])][0 if i["eps"] else 1] += 1
        hit.update((i["sid"], e) for e in i["eps"])
    fc = defaultdict(int)
    for (a, sid), (tp, fp) in cases.items():
        if tp == 0:
            fc[acc[a]["kind"] if acc[a]["truth"] == "legit" else "manip-acct"] += 1
    rec = recall_table(recs, hit)
    g = lambda **k: list(pooled(rec, **k))
    return dict(name=name, sessions=len(recs),
                completed_faithful=g(evasive=False, filled=True), completed_evasive=g(evasive=True, filled=True),
                unfilled_faithful=g(evasive=False, filled=False), unfilled_evasive=g(evasive=True, filled=False),
                all_attempts=g(),
                false_cases=dict(fc), false_cases_legit=sum(v for k, v in fc.items() if k != "manip-acct"),
                false_cases_per_100_legit_account_sessions=round(100.0 * sum(v for k, v in fc.items() if k != "manip-acct") / (n_legit * len(recs)), 2),
                cases=len(cases), instances=len(flagged), false_instances=sum(1 for i in flagged if not i["eps"]),
                by_template={f"{t}{'/evasive' if ev else ''}{'' if fl else '/unfilled'}": v for (t, ev, fl), v in sorted(rec.items())}), hit


def matched(recs, rows, p, n=2, rates=(0.5, 1.0, 2.0)):
    """Recall when one threshold for all classes is set on these sessions so that false cases per
    100 legitimate account-sessions do not exceed each rate. Used to compare detectors at an equal
    false-case load; it is not an operating point, because the threshold is read off the test sessions."""
    acc = recs[0]["accounts"]
    per = defaultdict(list)
    for (sid, m), s in zip(rows, p):
        per[(m["acct"], sid)].append(s)
    stat = {k: (sorted(v, reverse=True)[n - 1] if len(v) >= n else 0.0) for k, v in per.items()}
    legit = sorted((v for (a, sid), v in stat.items() if acc[a]["truth"] == "legit"), reverse=True)
    n_ls = sum(v["truth"] == "legit" for v in acc.values()) * len(recs)
    eff = defaultdict(float)
    for (sid, m), s in zip(rows, p):
        v = min(s, stat[(m["acct"], sid)])
        for e in m["eps"]:
            if v > eff[(sid, e)]:
                eff[(sid, e)] = v
    out = {}
    for f in rates:
        allowed = int(f * n_ls / 100.0)
        tau = legit[allowed] if allowed < len(legit) else 0.0
        out[f] = recall_table(recs, {k for k, v in eff.items() if v > tau})
    return out
