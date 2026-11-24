"""Test of the fill-test change proposed in the paper (Section 8): on a thin book, spoof orders
resting at the touch are partly executed before they are cancelled, and the 5% fill-ratio test
removes them. Two changes are compared with the reference configuration on recorded-data logs.

    python tools/fill_fix.py LOGDIR SYM OUT.json [--windows 0,3]
"""
import glob, json, os, pickle, sys
from array import array
from collections import defaultdict
from dataclasses import replace
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from spoofbench.detect import Index, Params, detect, score

GRID = (0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0)
logdir, sym, out = sys.argv[1:4]
windows = {int(x) for x in sys.argv[sys.argv.index("--windows") + 1].split(",")} if "--windows" in sys.argv else None
logs = []
for f in sorted(glob.glob(os.path.join(logdir, f"{sym}_*.pkl"))):
    if windows is not None and int(os.path.basename(f)[:-4].split("_")[1]) % 100 not in windows:
        continue
    s = pickle.load(open(f, "rb"))
    for o in s.orders:
        o.depth = array("i", o.depth)
    logs.append(s)
days = sorted({s.day for s in logs})
half = days[:len(days) // 2]
base = [Index(s) for s in logs if s.day in half]
test = [Index(s) for s in logs if s.day not in half]
accts = test[0].s.accounts
kinds = {k: v["kind"] for k, v in accts.items()}
n_legit = sum(v["truth"] == "legit" for v in accts.values())


def run(X):
    """Class thresholds chosen on the baseline days under configuration X (2 false cases per 100
    account-sessions of the class), then scored on the test days."""
    chosen, cache = {}, {}
    for k in GRID:
        fl = detect(base, replace(X, k=k))
        score(base, fl)
        bad = defaultdict(lambda: [0, 0])
        for i in fl:
            bad[(i["acct"], i["sid"])][i["true"]] += 1
        cache[k] = bad
    for kd in sorted(set(kinds.values())):
        members = [x for x in accts if kinds[x] == kd and accts[x]["truth"] == "legit"]
        for k in GRID:
            fc = sum(1 for (ac, sid), v in cache[k].items() if ac in members and v[1] == 0)
            if 100.0 * fc / max(1, len(members) * len(base)) <= 2.0:
                chosen[kd] = k
                break
        else:
            chosen[kd] = GRID[-1]
    C = replace(X, k_by_acct=tuple(sorted((x, chosen[kinds[x]]) for x in accts)))
    r = score(test, detect(test, C))
    fa = {k: v for k, v in r["recall"].items() if not k.endswith("/evasive")}
    legit_false = sum(v for k, v in r["false_cases"].items() if k != "manip-acct")
    return dict(k_by_class=chosen, recall=r["recall"], faithful_found=sum(v[0] for v in fa.values()),
                faithful_total=sum(v[1] for v in fa.values()), false_cases=legit_false,
                legit_account_sessions=n_legit * len(test),
                false_cases_per_100=round(100.0 * legit_false / (n_legit * len(test)), 2))


X = Params(flip=True, persistent=True)
R = dict(instrument=sym, baseline_sessions=len(base), test_sessions=len(test),
         windows="all" if windows is None else sorted(windows))
for name, P in (("reference", X), ("flip variant without the fill test", replace(X, flip_fill=False)),
                ("fill limit 50% at the touch", replace(X, f_touch=0.5)),
                ("no fill limit at the touch", replace(X, f_touch=1.0))):
    R[name] = run(P)
    v = R[name]
    print(f"{name:<38} {v['faithful_found']}/{v['faithful_total']} | oystacher {v['recall'].get('oystacher')} | "
          f"false {v['false_cases']}/{v['legit_account_sessions']} | k {v['k_by_class']}", flush=True)
json.dump(R, open(out, "w"), indent=1)
