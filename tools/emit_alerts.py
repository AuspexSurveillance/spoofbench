"""Write detector output as alert records that follow spec/alert.schema.json.

    python tools/emit_alerts.py [--seed 20261123] [--seconds 1800] [--out alerts.jsonl]

One seeded session is built, the reference configuration is run (class multiples from
results/results.json, both variants on), and one JSON record is written per alert. A record holds
what a reviewer needs to check the alert by hand: the orders, the book at entry, each test with
the value observed and the threshold in force, and the parameters. Ground truth is not written
to the record. validate() checks a record against the schema with the standard library only.
"""
import argparse, json, os, sys
from collections import defaultdict
from dataclasses import asdict, replace

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
from spoofbench.bench import make_session
from spoofbench.detect import Index, Params, detect, evaluate, score

LIBRARY = "0.4"
SCHEMA = os.path.join(ROOT, "spec", "alert.schema.json")
NAMES = {"5.1": "spoofing", "5.2": "layering", "5.2P": "persistent layering", "5.8": "cross-product"}
BASIS = {"5.1": ["Commodity Exchange Act 4c(a)(5)(C)", "CME Rule 575.A"],
         "5.2": ["Commodity Exchange Act 4c(a)(5)(C)", "CME Rule 575.A"],
         "5.2P": ["Commodity Exchange Act 4c(a)(5)(C)", "CME Rule 575.A"],
         "5.8": ["Commodity Exchange Act 4c(a)(5)", "CME Rule 575"]}
CLASS_K = {"basis": 0.02, "exec": 0.2, "mm": 0.3, "prop": 0.1}     # results/results.json, class_k.k_by_class
SIDE = {1: "B", -1: "S"}
WORD = {1: "buy", -1: "sell"}


def _params(P, k):
    d = {key: val for key, val in asdict(P).items() if key != "k_by_acct"}
    d["k"] = k
    return d


def _events(orders, role):
    ev = []
    for o in orders:
        base = dict(order_id=str(o.oid), role=role, side=SIDE[o.side], price=o.px, quantity=o.qty, instrument=o.inst)
        ev.append(dict(base, t=round(o.t_in, 6), action="enter"))
        if role == "flagged":
            ev.append(dict(base, t=round(o.t_out, 6), action="replace" if o.status == "R" else "cancel"))
    return ev


def to_alert(i, ix, P, kmap=None, count=None, n_alert=0, budget=2.0):
    """One detector instance (a dict returned by detect) as an alert record."""
    s = ix.s
    orders = [s.by_oid[x] for x in i["oids"]]
    first = min(orders, key=lambda o: o.t_in)
    side, acct, proc = first.side, i["acct"], i["proc"]
    k = (kmap or {}).get(acct, P.k)
    a = dict(schema_version="0.1", alert_id=f"S{s.sid}-{acct}-{n_alert}",
             procedure=dict(id=proc, name=NAMES[proc], variant="base", library_version=LIBRARY),
             basis=BASIS[proc], account=acct, session=str(s.sid), instrument=first.inst,
             time_base="session_seconds")
    ev = _events(orders, "flagged")
    tests = []

    def test(name, observed, comparison, threshold, note=None):
        ok = {">=": observed >= threshold, "<=": observed <= threshold, "==": observed == threshold}[comparison]
        t = dict(name=name, observed=observed, comparison=comparison, threshold=threshold, passed=bool(ok))
        if note:
            t["note"] = note
        tests.append(t)

    if proc == "5.2P":
        a["procedure"]["variant"] = "persistent"
        t0, t1 = i["t"], i["t"] + i["life"]
        test("levels", len({o.px for o in orders}), ">=", P.L, "distinct prices among the orders in the run")
        test("distance", min(o.dist for o in orders), ">=", 2, "ticks beyond the touch at entry")
        test("duration", round(i["life"], 6), ">=", P.T_min, "seconds the layers were held with no fills")
        test("opposite_side_fill", True, "==", True, "the account executed on the other side while the layers rested")
        a["window"] = dict(start=round(t0, 6), end=round(t1, 6))
        text = (f"Between t={t0:.3f} s and t={t1:.3f} s, account {acct} kept {WORD[side]} orders in {first.inst} "
                f"at {P.L} or more price levels at least two ticks beyond the touch for {i['life']:.1f} seconds with "
                f"no fills ({len(orders)} orders in all), while executing on the other side.")
    else:
        t = i["t"]
        gen = next((o for (tf, o, q) in ix.fills[acct] if tf == t and o.side == -side), None)
        if gen is not None:
            g = dict(order_id=str(gen.oid), role="opposite_side", side=SIDE[gen.side], price=gen.px,
                     quantity=gen.qty, instrument=gen.inst)
            ev += [dict(g, t=round(gen.t_in, 6), action="enter"), dict(g, t=round(t, 6), action="fill")]
            a["genuine_instrument"] = gen.inst
        flip = P.flip and i["lat_min"] < 0.0
        if flip:
            a["procedure"]["variant"] = "flip"
        hi = P.t_cancel + (P.lag if i["cross"] else 0.0)
        depth, Q = i["depth"], i["Q"]
        worst = max(orders, key=lambda o: o.filled / o.qty)
        f_max = P.f_touch if (P.f_touch is not None and worst.dist <= 0) else P.f_max
        if flip and not P.flip_fill:
            f_max = 1.0
        test("size", Q, ">=", round(max(P.q_min, k * depth), 6),
             f"the greater of q_min and k times displayed depth within {P.d} ticks (k={k}, depth={depth})")
        test("distance", max(o.dist for o in orders), "<=", P.d, "ticks from the touch at entry")
        test("fill_ratio", round(worst.filled / worst.qty, 6), "<=", f_max, "highest fill ratio among the flagged orders")
        test("cancel_latency", round(i["lat"], 6), "<=", hi,
             "seconds from the opposite-side fill to the last cancel"
             + ("; at least one cancel came before the fill (flip variant)" if flip else ""))
        test("entry_window", round(t - first.t_in, 6), "<=", P.W, "seconds from the first flagged entry to the fill")
        if proc == "5.2":
            test("levels", i["levels"], ">=", P.L, "distinct prices among the flagged orders")
        a["book_at_entry"] = dict(d=P.d, displayed_same_side=depth, own_same_side=first.own_same,
                                  own_opposite_side=first.own_opp)
        t0, t1 = min(e["t"] for e in ev), max(e["t"] for e in ev)
        a["window"] = dict(start=t0, end=t1)
        filled = sum(o.filled for o in orders)
        other = f" in {gen.inst if gen else 'a correlated instrument'}" if i["cross"] else ""
        text = (f"Between t={t0:.3f} s and t={t1:.3f} s, account {acct} entered {len(orders)} {WORD[side]} "
                f"order{'s' if len(orders) != 1 else ''} totalling {Q} lots in {first.inst} at {i['levels']} price "
                f"level{'s' if i['levels'] != 1 else ''} within {P.d} ticks of the touch, against displayed "
                f"{WORD[side]}-side depth of {depth} lots within {P.d} ticks; received a fill on a "
                f"{WORD[-side]} order{other} at t={t:.3f} s; and cancelled the {WORD[side]} orders "
                + (f"within {i['lat']:.3f} seconds of the fill." if not flip else
                   "around the fill, with at least one cancel just before an aggressive order on the other side.")
                + f" Lots filled on the {WORD[side]} orders: {filled} of {Q}.")
    a["events"] = sorted(ev, key=lambda e: (e["t"], e["action"] != "enter"))
    a["tests"] = tests
    a["exclusions"] = [dict(name="two_sided_quoting", applied=P.exclusions, met=bool(i["sym"])),
                       dict(name="requote", applied=P.exclusions, met=bool(i["again"]))]
    if proc == "5.2P":
        a["repetition"] = dict(count=1, required=1, sessions=1)
    else:
        a["repetition"] = dict(count=int(count or 0), required=P.n, sessions=P.P_sessions)
        text += f" The account met the pattern {int(count or 0)} time{'s' if count != 1 else ''} in the session window."
    a["parameters"] = _params(P, k)
    kind = s.accounts[acct]["kind"]
    if kmap and acct in kmap and kind != "unclassified":
        a["calibration"] = dict(k_source="account_class", account_class=kind)
        if budget is not None:
            a["calibration"]["false_case_budget_per_100"] = budget
    else:
        a["calibration"] = dict(k_source="default")
    a["narrative"] = text
    a["disposition"] = dict(status="open")
    return a


def emit(indexes, P, budget=2.0):
    """Alert records for every instance detect() flags, in detector order. budget is the false-case budget the
    multiples were calibrated under, or None if they were not chosen by the seeded method."""
    kmap = dict(P.k_by_acct) if P.k_by_acct else None
    per = [defaultdict(int) for _ in indexes]
    for j, ix in enumerate(indexes):
        for c in ix.cands:
            inst = evaluate(c, ix, P, kmap)
            if inst:
                per[j][inst["acct"]] += 1
    pos = {ix.s.sid: j for j, ix in enumerate(indexes)}
    out = []
    for n, i in enumerate(detect(indexes, P)):
        j = pos[i["sid"]]
        count = sum(per[m][i["acct"]] for m in range(max(0, j - P.P_sessions + 1), j + 1))
        out.append(to_alert(i, indexes[j], P, kmap, count, n, budget))
    return out


_TYPES = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict,
          "null": type(None)}


def validate(x, schema, path="alert"):
    """Check x against the subset of JSON Schema that alert.schema.json uses. Returns a list of errors."""
    err = []
    types = schema.get("type")
    if types:
        types = [types] if isinstance(types, str) else types
        ok = any(isinstance(x, _TYPES[t]) and not (t in ("number", "integer") and isinstance(x, bool)) for t in types)
        if not ok:
            return [f"{path}: expected {types}, got {type(x).__name__}"]
    if "enum" in schema and x not in schema["enum"]:
        err.append(f"{path}: {x!r} not in {schema['enum']}")
    if isinstance(x, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in x:
                err.append(f"{path}: missing {key}")
        extra = schema.get("additionalProperties", True)
        for key, val in x.items():
            if key in props:
                err += validate(val, props[key], f"{path}.{key}")
            elif extra is False:
                err.append(f"{path}: unexpected {key}")
            elif isinstance(extra, dict):
                err += validate(val, extra, f"{path}.{key}")
    if isinstance(x, list) and "items" in schema:
        for n, val in enumerate(x):
            err += validate(val, schema["items"], f"{path}[{n}]")
    return err


def reference_params(session):
    kc = tuple(sorted((a, CLASS_K[v["kind"]]) for a, v in session.accounts.items()))
    return replace(Params(), flip=True, persistent=True, k_by_acct=kc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--seconds", type=float, default=1800.0)
    ap.add_argument("--out", default="alerts.jsonl")
    args = ap.parse_args()
    s = make_session(0, args.seed, T=args.seconds)
    ix = Index(s)
    P = reference_params(s)
    alerts = emit([ix], P)
    schema = json.load(open(SCHEMA))
    bad = [e for a in alerts for e in validate(a, schema)]
    with open(args.out, "w") as f:
        for a in alerts:
            f.write(json.dumps(a) + "\n")
    by = defaultdict(int)
    for a in alerts:
        by[a["procedure"]["id"] + ("/" + a["procedure"]["variant"] if a["procedure"]["variant"] != "base" else "")] += 1
    flagged = detect([ix], P)
    sc = score([ix], flagged)
    print(f"{len(alerts)} alerts written to {args.out}: {dict(sorted(by.items()))}")
    print(f"schema errors: {len(bad)}")
    print(f"against the labels: {sc['instances'] - sc['false_instances']} true and {sc['false_instances']} false instances")
    for e in bad[:10]:
        print("  ", e)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
