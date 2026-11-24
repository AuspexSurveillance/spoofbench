"""Run the procedures on order and fill files in the published CSV format, without the simulator.

    python tools/run_on_csv.py --orders data/sample/orders_030.csv.gz --fills data/sample/fills_030.csv.gz \
        --classes data/sample/episodes_030.json --out alerts.jsonl

A firm that writes its own orders and fills in this format (spec/PROCEDURES.md, section 2) can run
the reference procedures on them and get alert records that follow spec/alert.schema.json.

--classes   account classes: a JSON file {"accounts": {"ACCT": {"kind": "mm"}, ...}} or a CSV with
            the columns acct,class. Only the class is read.
--k-class   size multiple per class, for example mm=0.3,exec=0.2,prop=0.1,basis=0.02 (the default,
            which is what the seeded calibration chose on the simulated market)
--k         size multiple for accounts with no class (default 0.1)

This tool applies multiples you give it. It does not choose them. Choosing them by the seeded
method is done by run_benchmark.py (simulated market) and run_real.py (recorded exchange data).
"""
import argparse, csv, gzip, json, os, sys
from collections import defaultdict
from dataclasses import replace

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from spoofbench.detect import Index, Params
from tools.emit_alerts import emit, validate, CLASS_K, SCHEMA


class Rec:
    """One order as the detectors read it."""
    __slots__ = ("oid", "acct", "inst", "side", "px", "qty", "filled", "t_in", "t_out", "status", "aggr",
                 "dist", "depth", "own_same", "own_opp", "ep", "role")


class Log:
    """One session of a firm's orders and fills."""

    def __init__(self, sid, orders, fills, accounts):
        self.sid, self.orders, self.fills, self.accounts = sid, orders, fills, accounts
        self.by_oid = {o.oid: o for o in orders}
        self.T = max([o.t_out for o in orders] + [0.0])
        self.episodes = []


def _open(path):
    return gzip.open(path, "rt", newline="") if path.endswith(".gz") else open(path, newline="")


def read_orders(path):
    out = []
    with _open(path) as f:
        for r in csv.DictReader(f):
            o = Rec()
            o.oid, o.acct, o.inst, o.side = int(r["oid"]), r["acct"], r["inst"], int(r["side"])
            o.px = int(r["px"]) if r["px"] != "" else None
            o.qty, o.filled = int(r["qty"]), int(r["filled"])
            o.t_in, o.t_out, o.status = float(r["t_in"]), float(r["t_out"]), r["status"]
            o.aggr, o.dist = bool(int(r["aggr"])), int(r["dist"])
            o.own_same, o.own_opp = int(r["own_same"]), int(r["own_opp"])
            o.depth = [int(r[f"depth_{i}"]) for i in range(9)]
            o.ep = o.role = None                     # labels, if the file has them, are not read
            out.append(o)
    out.sort(key=lambda o: (o.t_in, o.oid))
    return out


def read_fills(path):
    with _open(path) as f:
        return [(float(r["t"]), int(r["oid"]), int(r["qty"]), int(r["px"]), bool(int(r["aggressor"])))
                for r in csv.DictReader(f)]


def read_classes(path):
    if not path:
        return {}
    if path.endswith(".json"):
        return {a: v["kind"] for a, v in json.load(open(path))["accounts"].items()}
    with _open(path) as f:
        return {r["acct"]: r["class"] for r in csv.DictReader(f)}


def load(orders, fills, classes=None, sid="1"):
    o = read_orders(orders)
    kinds = read_classes(classes)
    accounts = {a: dict(kind=kinds.get(a, "unclassified")) for a in sorted({x.acct for x in o})}
    return Log(sid, o, read_fills(fills), accounts)


def params_for(log, k_class, k_default):
    kc = tuple(sorted((a, k_class.get(v["kind"], k_default)) for a, v in log.accounts.items()))
    return replace(Params(), flip=True, persistent=True, k_by_acct=kc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", required=True)
    ap.add_argument("--fills", required=True)
    ap.add_argument("--classes", default=None)
    ap.add_argument("--k-class", default=",".join(f"{k}={v}" for k, v in sorted(CLASS_K.items())))
    ap.add_argument("--k", type=float, default=0.1)
    ap.add_argument("--out", default="alerts.jsonl")
    a = ap.parse_args()
    k_class = {kv.split("=")[0]: float(kv.split("=")[1]) for kv in a.k_class.split(",") if kv}
    log = load(a.orders, a.fills, a.classes)
    P = params_for(log, k_class, a.k)
    alerts = emit([Index(log)], P, budget=None)
    schema = json.load(open(SCHEMA))
    bad = [e for x in alerts for e in validate(x, schema)]
    with open(a.out, "w") as f:
        for x in alerts:
            f.write(json.dumps(x) + "\n")
    by = defaultdict(int)
    for x in alerts:
        by[x["account"]] += 1
    print(f"{len(log.orders):,} orders, {len(log.fills):,} fills, {len(log.accounts)} accounts")
    print(f"{len(alerts)} alerts written to {a.out}; schema errors: {len(bad)}")
    for acct, n in sorted(by.items(), key=lambda kv: -kv[1]):
        print(f"  {acct:16s} {n}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
