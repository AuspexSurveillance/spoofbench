"""Why flip (Oystacher) episodes are missed on a thin book (paper Section 6.5).

    python tools/diag_flip.py LOGDIR SYM [--windows 1,4]

For every completed faithful Oystacher episode in the test sessions, reports whether the flip order
executed on entry and whether any spoof order passes the 5% fill test. Reads ground truth, so it is
a diagnostic, not a detector. Loads one session at a time.
"""
import collections, glob, os, pickle, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def main(logdir, sym, windows=None, f_max=0.05):
    files = sorted(glob.glob(os.path.join(logdir, f"{sym}_*.pkl")))
    sid = lambda f: int(os.path.basename(f)[:-4].split("_")[1])
    days = sorted({sid(f) // 100 for f in files})
    test_days = set(days[len(days) // 2:])
    C = collections.Counter()
    for f in files:
        if sid(f) // 100 not in test_days or (windows is not None and sid(f) % 100 not in windows):
            continue
        s = pickle.load(open(f, "rb"))
        by = s.by_oid
        for e in s.episodes:
            if e["template"] != "oystacher" or e["evasive"] or not e["spoof"] or not e["filled"]:
                continue
            sp = [by[i] for i in e["spoof"]]
            gen = [by[i] for i in e["genuine"]]
            aggr = any(o.aggr for o in gen)
            clean = any(o.status == "C" and o.filled <= f_max * o.qty for o in sp)
            C["episodes"] += 1
            C["flip_executed_on_entry"] += aggr
            C["no_spoof_order_passes_fill_test"] += not clean
            C["some_spoof_order_had_a_fill"] += any(o.filled > 0 for o in sp)
            C["both_conditions_met"] += aggr and clean
            C["spoof_qty"] += sum(o.qty for o in sp)
            C["spoof_filled_qty"] += sum(o.filled for o in sp)
        del s
    for k, v in C.items():
        print(k, v)


if __name__ == "__main__":
    w = {int(x) for x in sys.argv[sys.argv.index("--windows") + 1].split(",")} if "--windows" in sys.argv else None
    main(sys.argv[1], sys.argv[2], w)
