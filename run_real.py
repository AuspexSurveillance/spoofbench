"""Run the benchmark on recorded market data (windows written by tools/prep_dbn.py).

    python run_real.py sim  WINDIR LOGDIR SYM [--only FILE ...]   replay sessions, one log per window
    python run_real.py eval LOGDIR SYM OUTDIR [--windows 0,2,4]   all experiments on the logs

Sessions are ordered by day then window. The first half of the days is the baseline set, the
second half the test set. The raw market data never leaves WINDIR; logs hold only the firm's
hypothetical orders and fills.
"""
import glob, json, os, pickle, statistics as st, sys, time

from spoofbench.bench import roster, Session
from spoofbench.detect import Index
from spoofbench.replay import ReplaySim

REAL_GRID = (0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0)
SEED = 20261123


def sid_map(windir, sym):
    files = sorted(glob.glob(os.path.join(windir, f"{sym}_*_*.npz")))
    days = sorted({os.path.basename(f).split("_")[1] for f in files})
    return {f: days.index(os.path.basename(f).split("_")[1]) * 100 + int(os.path.basename(f).split("_")[2][:-4]) for f in files}, days


def sim(windir, logdir, sym, only=None):
    import numpy as np
    os.makedirs(logdir, exist_ok=True)
    sids, days = sid_map(windir, sym)
    for f, sid in sorted(sids.items(), key=lambda x: x[1]):
        out = os.path.join(logdir, f"{sym}_{sid:04d}.pkl")
        if (only and os.path.basename(f) not in only) or os.path.exists(out):
            continue
        t0 = time.time()
        win = np.load(f)
        s = ReplaySim(SEED + sid, win)
        agents = roster(real=True)
        s.agents = agents
        s.run()
        for o in s.orders:
            o.cb = None
        ses = Session(sid, s, agents)
        ses.day, ses.events = os.path.basename(f).split("_")[1], len(s.ev[0])
        pickle.dump(ses, open(out + ".tmp", "wb"), protocol=4)
        os.replace(out + ".tmp", out)
        ep = [e for e in s.episodes if e["spoof"]]
        print(f"{os.path.basename(f)} sid {sid}: {ses.events:,} market events, {len(s.orders):,} firm orders, "
              f"{len(ep)} episodes ({sum(e['filled'] for e in ep)} with a fill), {time.time() - t0:.0f}s", flush=True)


def evaluate(logdir, sym, outdir, windows=None):
    """windows: keep only these 30-minute windows of each day (e.g. {0, 2, 4}) to bound memory."""
    from array import array
    from run_benchmark import experiments
    logs = []
    for f in sorted(glob.glob(os.path.join(logdir, f"{sym}_*.pkl"))):
        if windows is not None and int(os.path.basename(f)[:-4].split("_")[1]) % 100 not in windows:
            continue
        s = pickle.load(open(f, "rb"))
        for o in s.orders:
            o.depth = array("i", o.depth)            # compact; slicing and sum() work the same
        logs.append(s)
    days = sorted({s.day for s in logs})
    half = days[:len(days) // 2]
    base = [Index(s) for s in logs if s.day in half]
    test = [Index(s) for s in logs if s.day not in half]
    R = experiments(base, test, grid=REAL_GRID)
    d = [o for ix in test for o in ix.s.orders if o.acct.startswith("DISC")]
    R["meta"].update(seed=SEED, instrument=sym, source="CME Globex MBO via Databento, replayed", baseline_days=half,
                     test_days=[x for x in days if x not in half], market_events_test=sum(ix.s.events for ix in test),
                     median_touch_size=st.median(o.depth[0] for o in d),
                     median_size_within_3_ticks=st.median(sum(o.depth[:4]) for o in d),
                     windows_per_day=sorted(windows) if windows is not None else "all")
    os.makedirs(outdir, exist_ok=True)
    json.dump(R, open(os.path.join(outdir, f"results_real_{sym}.json"), "w"), indent=1, default=str)
    print(json.dumps(R["meta"]))


if __name__ == "__main__":
    if sys.argv[1] == "sim":
        only = sys.argv[sys.argv.index("--only") + 1:] if "--only" in sys.argv else None
        sim(sys.argv[2], sys.argv[3], sys.argv[4], only)
    else:
        w = {int(x) for x in sys.argv[sys.argv.index("--windows") + 1].split(",")} if "--windows" in sys.argv else None
        evaluate(sys.argv[2], sys.argv[3], sys.argv[4], w)
