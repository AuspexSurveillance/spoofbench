"""Own-percentile calibration with and without the floor on the multiple (paper Section 6.2).

    python tools/selfq_floor.py LOGDIR SYM [--windows 1,4]

The released experiments floor an account's own-percentile multiple at 0.02. On a deep book
(ZN) the floor binds for almost every account, so this script repeats the experiment with a
lower floor and with none.
"""
import glob, os, pickle, sys
from array import array
from dataclasses import replace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from spoofbench.detect import Index, Params, calibrate          # noqa: E402
from run_benchmark import summarize                               # noqa: E402


def main(logdir, sym, windows=None):
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
    X = replace(Params(), flip=True, persistent=True)
    n_legit = sum(v["truth"] == "legit" for v in test[0].s.accounts.values())
    for floor in (0.02, 0.002, 0.0):
        ks = calibrate(base, floor=floor)
        r = summarize("own percentile", test, replace(X, k_by_acct=ks), n_legit)
        print(f"floor {floor}: recall {r['recall_faithful']}, evasive {r['recall_evasive']}, false cases {r['false_cases']} "
              f"({r['false_cases_per_100_legit_account_sessions']} per 100 legitimate account-sessions)")
        print("   by template:", r["recall"])
        print("   multiples:", {k: round(v, 4) for k, v in ks})


if __name__ == "__main__":
    w = {int(x) for x in sys.argv[sys.argv.index("--windows") + 1].split(",")} if "--windows" in sys.argv else None
    main(sys.argv[1], sys.argv[2], w)
