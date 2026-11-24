"""catrecon: seeded CAT reporting errors and three ways of finding them.

A simulated agency firm receives orders and routes them to an exchange. Its order management
records (OMS) come from a spoofbench session. From them the script writes the CAT events an
Industry Member would report (MENO new order, MEOR order route, MEOC order cancelled), and the
acknowledgements the exchange sends back. It then plants labelled errors of 19 kinds and scores
three controls against them:

  cat    the feedback checks described in the public CAT Industry Member Technical Specifications
         (v4.2.0 r4): data ingestion, duplicate keys, intrafirm linkage, sequence, FDID, route linkage
  oms    reconciliation of the CAT file against the firm's own order records and account master
  exch   reconciliation of the CAT file against the exchange's order and cancel acknowledgements

The "cat" control is a simplified reimplementation from the specification, not the CAT system.
Event and field names follow the specification. Everything else is an assumption stated in ASSUME.
"""
import json, os, random, sys
from collections import defaultdict

sys.path.insert(0, os.environ.get("SPOOFBENCH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
from spoofbench.bench import make_session

ASSUME = {
    "scenario": "agency firm; every order is routed to one exchange; executions are reported by the exchange",
    "route latency": "exchange acknowledgement arrives 0.2 to 2.0 ms after the route, uniform",
    "timestamps": "reported in milliseconds",
    "timing window": "a route or cancel timestamp is accepted if the acknowledgement follows it by -1.0 to +3.5 ms",
    "account holder type": "taken from the account master by account class",
    "one error per order": "each seeded error is on a different order",
}
IMID, EXCH, DATE = "ZZZT", "XNAS", "20261123"
SYM = {"FUT": "AAA", "CASH": "BBB"}
AHT = {"mm": "O", "exec": "A", "prop": "P", "basis": "P"}        # accountHolderType by account class
VALID_AHT = set("AEFIOPVX")
WIN = (-0.0010, 0.0035)


def ms(t):
    return round(t, 3)


def build(session, rng):
    """OMS records, account master, the correct CAT events and the exchange acknowledgements."""
    master = {a: dict(fdid=a, aht=AHT[v["kind"]]) for a, v in session.accounts.items()}
    oms, cat, acks, cxl = [], [], [], []
    for o in session.orders:
        r = dict(oid=o.oid, order_id=f"O{o.oid}", acct=o.acct, sym=SYM[o.inst], side="B" if o.side > 0 else "SL",
                 qty=o.qty * 100, px=None if o.px is None else round(o.px * 0.01, 2), otype="MKT" if o.px is None else "LMT",
                 t_in=o.t_in, t_out=o.t_out, cancelled=o.px is not None and o.status in ("C", "R"),
                 routed_id=f"R{o.oid}", session=f"S{1 + o.oid % 4}")
        oms.append(r)
        key = dict(_oid=o.oid, orderKeyDate=DATE, CATReporterIMID=IMID, symbol=r["sym"], orderID=r["order_id"])
        cat.append(dict(key, type="MENO", firmROEID=f"{DATE}_N{o.oid}", eventTimestamp=ms(r["t_in"]), side=r["side"],
                        quantity=r["qty"], price=r["px"], orderType=r["otype"], firmDesignatedID=master[o.acct]["fdid"],
                        accountHolderType=master[o.acct]["aht"]))
        cat.append(dict(key, type="MEOR", firmROEID=f"{DATE}_R{o.oid}", eventTimestamp=ms(r["t_in"]), senderIMID=IMID,
                        destination=EXCH, routedOrderID=r["routed_id"], session=r["session"], side=r["side"],
                        quantity=r["qty"], price=r["px"]))
        acks.append(dict(_oid=o.oid, routedOrderID=r["routed_id"], session=r["session"], symbol=r["sym"], exchange=EXCH,
                         senderIMID=IMID, side=r["side"], quantity=r["qty"], price=r["px"], t=r["t_in"] + rng.uniform(0.0002, 0.002)))
        if r["cancelled"]:
            cat.append(dict(key, type="MEOC", firmROEID=f"{DATE}_C{o.oid}", eventTimestamp=ms(r["t_out"])))
            cxl.append(dict(_oid=o.oid, routedOrderID=r["routed_id"], session=r["session"], t=r["t_out"] + rng.uniform(0.0002, 0.002)))
    return oms, master, cat, acks, cxl


# ---- seeded errors: name -> (origin, description). Origin "report" = wrong only in the CAT file;
# "upstream" = wrong in the firm's own records too, so the firm's records cannot reveal it.
ERRORS = {
    "omit_new_order": ("report", "MENO not reported"),
    "omit_route": ("report", "MEOR not reported"),
    "omit_cancel": ("report", "MEOC not reported"),
    "dup_order_key": ("report", "orderID reused for a second order on the same day"),
    "dup_roe_id": ("report", "firmROEID reused"),
    "missing_aht": ("report", "accountHolderType missing"),
    "bad_timestamp": ("report", "eventTimestamp not a valid time"),
    "wrong_routed_id": ("report", "routedOrderID does not match what was sent"),
    "wrong_session": ("report", "session does not match what was sent"),
    "out_of_sequence": ("report", "cancel timestamp earlier than the new order"),
    "fdid_unknown": ("report", "firmDesignatedID not in the firm's reference data"),
    "fdid_pending": ("upstream", "firmDesignatedID still PENDING in the account master"),
    "wrong_side": ("report", "side reported as the opposite side"),
    "wrong_qty": ("report", "quantity reported is not the order quantity"),
    "wrong_price": ("report", "price reported is off by a factor of 100"),
    "ts_truncated": ("report", "timestamps truncated to the second"),
    "clock_drift": ("upstream", "order host clock ahead by a fixed offset"),
    "wrong_aht_report": ("report", "accountHolderType differs from the account master"),
    "wrong_aht_master": ("upstream", "accountHolderType wrong in the account master"),
}


def inject(oms, master, cat, rng, per_type=200, drift=0.050, only=None):
    """Returns (cat', oms', master', labels) with labels[oid] = error name. Inputs are not modified."""
    cat = [dict(e) for e in cat]; oms = [dict(r) for r in oms]; master = {k: dict(v) for k, v in master.items()}
    ev = defaultdict(dict)
    for e in cat:
        ev[e["_oid"]][e["type"]] = e
    by = {r["oid"]: r for r in oms}
    pool = [r["oid"] for r in oms if r["cancelled"] and r["px"] is not None and r["t_in"] % 1 > 0.002 and r["t_out"] % 1 > 0.002]
    rng.shuffle(pool)
    labels, drop, names = {}, set(), [n for n in ERRORS if only is None or n in only]
    for name in names:
        for _ in range(per_type):
            oid = pool.pop(); labels[oid] = name
            n, r, c, o = ev[oid]["MENO"], ev[oid]["MEOR"], ev[oid]["MEOC"], by[oid]
            if name == "omit_new_order": drop.add(id(n))
            elif name == "omit_route": drop.add(id(r))
            elif name == "omit_cancel": drop.add(id(c))
            elif name == "dup_order_key":
                other = by[pool.pop()]; labels[other["oid"]] = name
                for e in ev[other["oid"]].values(): e["orderID"] = n["orderID"]; e["symbol"] = n["symbol"]
            elif name == "dup_roe_id": r["firmROEID"] = n["firmROEID"]
            elif name == "missing_aht": n["accountHolderType"] = ""
            elif name == "bad_timestamp": n["eventTimestamp"] = None
            elif name == "wrong_routed_id": r["routedOrderID"] += "X"
            elif name == "wrong_session": r["session"] = "S9"
            elif name == "out_of_sequence": c["eventTimestamp"] = ms(n["eventTimestamp"] - 1.0)
            elif name == "fdid_unknown": n["firmDesignatedID"] = "UNMAPPED"
            elif name == "fdid_pending":
                n["firmDesignatedID"] = "PENDING"; o["fdid_override"] = "PENDING"
            elif name == "wrong_side":
                for e in (n, r): e["side"] = "SL" if e["side"] == "B" else "B"
            elif name == "wrong_qty":
                for e in (n, r): e["quantity"] = e["quantity"] // 2 if e["quantity"] > 100 else e["quantity"] * 2
            elif name == "wrong_price":
                for e in (n, r): e["price"] = round(e["price"] * 100, 2)
            elif name == "ts_truncated":
                for e in (n, r, c): e["eventTimestamp"] = float(int(e["eventTimestamp"]))
            elif name == "clock_drift":
                for e in (n, r, c): e["eventTimestamp"] = ms(e["eventTimestamp"] + drift)
                o["t_in"] += drift; o["t_out"] += drift
            elif name == "wrong_aht_report": n["accountHolderType"] = "I"
            elif name == "wrong_aht_master":
                n["accountHolderType"] = "I"; o["aht_override"] = "I"
    return [e for e in cat if id(e) not in drop], oms, master, labels


# ---- control 1: CAT feedback checks, from the public specification
def detect_cat(cat, acks, fdids):
    flag, ok = set(), []
    for e in cat:                                                   # data ingestion
        bad = not isinstance(e.get("eventTimestamp"), float)
        if e["type"] == "MENO":
            bad |= e.get("accountHolderType") not in VALID_AHT or not e.get("firmDesignatedID")
        (flag.add(e["_oid"]) if bad else ok.append(e))
    roe, okey = defaultdict(list), defaultdict(list)
    for e in ok:
        roe[e["firmROEID"]].append(e)
        if e["type"] == "MENO":
            okey[(e["orderKeyDate"], e["CATReporterIMID"], e["symbol"], e["orderID"])].append(e)
    for v in roe.values():                                          # 3002 duplicate firmROEID
        if len(v) > 1: flag.update(e["_oid"] for e in v)
    dup = {k for k, v in okey.items() if len(v) > 1}                 # 3004 duplicate Order Key
    seen = set()
    for e in ok:
        k = (e["orderKeyDate"], e["CATReporterIMID"], e["symbol"], e["orderID"])
        if k in dup: flag.add(e["_oid"]); continue
        if e["type"] == "MENO":
            if e["firmDesignatedID"] not in fdids or e["firmDesignatedID"] == "PENDING": flag.add(e["_oid"])   # 3701, 3711
        elif k not in okey: flag.add(e["_oid"])                      # 3501 secondary event, key not found
        elif e["eventTimestamp"] < okey[k][0]["eventTimestamp"]: flag.add(e["_oid"])   # 3601 out of sequence
        if e["type"] == "MEOR":
            seen.add((e["senderIMID"], e["destination"], e["symbol"], e["routedOrderID"], e["session"]))
    ak = {(a["senderIMID"], a["exchange"], a["symbol"], a["routedOrderID"], a["session"]): a for a in acks}
    for e in ok:                                                    # route linkage, firm side unlinked
        if e["type"] == "MEOR" and (e["senderIMID"], e["destination"], e["symbol"], e["routedOrderID"], e["session"]) not in ak:
            flag.add(e["_oid"])
    for k, a in ak.items():                                         # exchange side unlinked, named to the firm
        if k not in seen: flag.add(a["_oid"])
    return flag


# ---- control 2: CAT file against the firm's own records
def detect_oms(cat, oms, master):
    flag, idx, roe = set(), defaultdict(list), defaultdict(int)
    for e in cat:
        idx[(e["orderID"], e["type"])].append(e); roe[e["firmROEID"]] += 1
    known = {r["order_id"] for r in oms}
    for e in cat:
        if e["orderID"] not in known or roe[e["firmROEID"]] > 1: flag.add(e["_oid"])
    for r in oms:
        m = master[r["acct"]]
        fd, aht = r.get("fdid_override", m["fdid"]), r.get("aht_override", m["aht"])
        want = {"MENO": dict(eventTimestamp=ms(r["t_in"]), side=r["side"], quantity=r["qty"], price=r["px"], orderType=r["otype"],
                             firmDesignatedID=fd, accountHolderType=aht),
                "MEOR": dict(eventTimestamp=ms(r["t_in"]), routedOrderID=r["routed_id"], session=r["session"], side=r["side"],
                             quantity=r["qty"], price=r["px"])}
        if r["cancelled"]: want["MEOC"] = dict(eventTimestamp=ms(r["t_out"]))
        for t in ("MENO", "MEOR", "MEOC"):
            got = idx.get((r["order_id"], t), [])
            if (t in want) != (len(got) == 1) or (t in want and any(got[0].get(k) != v for k, v in want[t].items())):
                flag.add(r["oid"])
        if fd == "PENDING": flag.add(r["oid"])
    return flag


# ---- control 3: CAT file against the exchange's acknowledgements
def detect_exch(cat, acks, cxl):
    flag = set()
    ak = {(a["routedOrderID"], a["session"]): a for a in acks}
    ck = {(a["routedOrderID"], a["session"]): a for a in cxl}
    route, canc, used = {}, {}, set()
    for e in cat:
        if e["type"] == "MEOR": route[e["orderID"]] = e
        elif e["type"] == "MEOC": canc[e["orderID"]] = e
    inwin = lambda ts, t: isinstance(ts, float) and WIN[0] <= t - ts <= WIN[1]
    for oid_, e in route.items():
        k = (e["routedOrderID"], e["session"]); a = ak.get(k)
        if a is None: flag.add(e["_oid"]); continue
        used.add(k)
        if (e["side"], e["quantity"], e["price"], e["symbol"]) != (a["side"], a["quantity"], a["price"], a["symbol"]) \
                or not inwin(e["eventTimestamp"], a["t"]): flag.add(e["_oid"])
        c, ca = canc.get(oid_), ck.get(k)
        if (c is None) != (ca is None) or (c is not None and not inwin(c["eventTimestamp"], ca["t"])): flag.add(e["_oid"])
    for k, a in ak.items():
        if k not in used: flag.add(a["_oid"])
    return flag


def run(sessions=3, seed=20261123, per_type=200, drifts=(0.001, 0.002, 0.003, 0.005, 0.02, 0.05)):
    rng = random.Random(seed)
    tot = defaultdict(lambda: defaultdict(int)); fp = defaultdict(int); clean = 0; sweep = defaultdict(lambda: [0, 0]); events = 0
    for i in range(sessions):
        s = make_session(i, seed + i)
        oms, master, cat, acks, cxl = build(s, rng)
        fdids = {m["fdid"] for m in master.values()}
        events += len(cat)
        for name, f in (("cat", detect_cat(cat, acks, fdids)), ("oms", detect_oms(cat, oms, master)), ("exch", detect_exch(cat, acks, cxl))):
            fp[name] += len(f)                                      # flags on a file with no seeded error
        clean += len(oms)
        c2, o2, m2, lab = inject(oms, master, cat, rng, per_type)
        F = dict(cat=detect_cat(c2, acks, fdids), oms=detect_oms(c2, o2, m2), exch=detect_exch(c2, acks, cxl))
        for oid, name in lab.items():
            tot[name]["n"] += 1
            for d, f in F.items(): tot[name][d] += oid in f
            tot[name]["any"] += any(oid in f for f in F.values())
        for d, f in F.items(): fp[d + "_seeded_file"] += len(f - set(lab))
        for dr in drifts:                                           # how large must a clock offset be to be seen
            c3, o3, m3, l3 = inject(oms, master, cat, rng, per_type, drift=dr, only=("clock_drift",))
            f = detect_exch(c3, acks, cxl)
            sweep[dr][0] += sum(o in f for o in l3); sweep[dr][1] += len(l3)
    R = dict(meta=dict(sessions=sessions, seed=seed, orders=clean, cat_events=events, per_type_per_session=per_type, assumptions=ASSUME),
             errors={n: dict(origin=ERRORS[n][0], description=ERRORS[n][1], **tot[n]) for n in ERRORS},
             false_flags=dict(fp), drift_sweep={f"{1000 * k:g} ms": v for k, v in sweep.items()})
    return R


if __name__ == "__main__":
    R = run()
    os.makedirs("results", exist_ok=True)
    json.dump(R, open("results/results.json", "w"), indent=1)
    m = R["meta"]
    print(f"{m['sessions']} sessions, {m['orders']:,} orders, {m['cat_events']:,} CAT events; {m['per_type_per_session']} seeded errors of each kind per session\n")
    print(f"{'error':<18}{'origin':<10}{'n':>5}{'CAT':>7}{'OMS':>7}{'exch':>7}{'any':>7}")
    for n, v in R["errors"].items():
        print(f"{n:<18}{v['origin']:<10}{v['n']:>5}{v['cat']:>7}{v['oms']:>7}{v['exch']:>7}{v['any']:>7}")
    print("\nflags on files with no seeded error:", {k: v for k, v in R["false_flags"].items() if "seeded" not in k})
    print("flags on unseeded orders in seeded files:", {k: v for k, v in R["false_flags"].items() if "seeded" in k})
    print("clock offset seen by the exchange reconciliation:", {k: f"{v[0]}/{v[1]}" for k, v in R["drift_sweep"].items()})
