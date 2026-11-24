"""Learned detector (v0.5) on recorded market data.

    python run_real_learned.py prep DATADIR WINDIR SYM     cut every day file of SYM into 30-minute windows (tools/prep_dbn.py)
    python run_real_learned.py sim  WINDIR RECDIR SYM      replay each window; keep features, labels and the procedures' flags
    python run_real_learned.py eval RECDIR SYM OUTDIR [--windows 0,3]

Sessions and seeds are the ones run_real.py uses, so the procedures' numbers can be checked against
results_real/. One session is in memory at a time. RECDIR holds features of the firm's hypothetical
orders only; the recorded market data stays in DATADIR and WINDIR.
"""
import glob, json, os, pickle, sys, time

import run_learned
from run_real import sid_map, SEED, REAL_GRID
from spoofbench.bench import roster, Session
from spoofbench.learned import featurize
from spoofbench.replay import ReplaySim


def prep(datadir, windir, sym):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools"))
    from prep_dbn import prep as cut
    for f in sorted(glob.glob(os.path.join(datadir, f"*.mbo.{sym}*.dbn.zst"))):
        day = os.path.basename(f).split(".")[0].split("-")[-1]
        if glob.glob(os.path.join(windir, f"{sym[:2]}_{day}_*.npz")):
            continue
        t0 = time.time()
        cut(f, windir)
        print(f"   {time.time() - t0:.0f}s", flush=True)


def sim(windir, recdir, sym):
    import numpy as np
    os.makedirs(recdir, exist_ok=True)
    sids, days = sid_map(windir, sym)
    run_learned.GRID = REAL_GRID
    for f, sid in sorted(sids.items(), key=lambda x: x[1]):
        out = os.path.join(recdir, f"{sym}_{sid:04d}.pkl")
        if os.path.exists(out):
            continue
        t0 = time.time()
        s = ReplaySim(SEED + sid, np.load(f))
        agents = roster(real=True)
        s.agents = agents
        s.run()
        ses = Session(sid, s, agents)
        d = [o for o in s.orders if o.acct.startswith("DISC")]
        rec = featurize(ses)
        rec["rule"] = run_learned._rule(ses)
        rec.update(day=os.path.basename(f).split("_")[1], window=sid % 100, events=len(s.ev[0]), orders=len(s.orders),
                   touch=float(np.median([o.depth[0] for o in d])), within3=float(np.median([sum(o.depth[:4]) for o in d])))
        pickle.dump(rec, open(out + ".tmp", "wb"), protocol=4)
        os.replace(out + ".tmp", out)
        ep = [e for e in rec["episodes"] if e["n_spoof"]]
        print(f"{os.path.basename(f)} sid {sid}: {rec['events']:,} market events, {rec['orders']:,} firm orders, {len(rec['meta']):,} groups, "
              f"{len(ep)} attempts ({sum(e['filled'] for e in ep)} with a fill), {time.time() - t0:.0f}s", flush=True)


def evaluate(recdir, sym, outdir, windows=None):
    import statistics as st
    recs = [pickle.load(open(f, "rb")) for f in sorted(glob.glob(os.path.join(recdir, f"{sym}_*.pkl")))]
    if windows is not None:
        recs = [r for r in recs if r["window"] in windows]
    days = sorted({r["day"] for r in recs})
    half = days[:len(days) // 2]
    base, test = [r for r in recs if r["day"] in half], [r for r in recs if r["day"] not in half]
    run_learned.GRID = REAL_GRID
    t0 = time.time()
    R = run_learned.run("real", base, test, log=lambda s: print(s, flush=True))
    R["meta"].update(seed=SEED, instrument=sym, market=f"recorded {sym} order book (CME Globex MBO via Databento, replayed)",
                     baseline_days=half, test_days=[d for d in days if d not in half],
                     windows_per_day=sorted(windows) if windows is not None else "all",
                     median_touch_size=st.median(r["touch"] for r in test), median_size_within_3_ticks=st.median(r["within3"] for r in test),
                     runtime_seconds=round(time.time() - t0, 1))
    os.makedirs(outdir, exist_ok=True)
    tag = sym if windows is None else f"{sym}_w{''.join(str(w) for w in sorted(windows))}"
    json.dump(R, open(os.path.join(outdir, f"results_learned_real_{tag}.json"), "w"), indent=1, default=str)
    run_learned.write_md(R, os.path.join(outdir, f"results_learned_real_{tag}.md"))
    print("done", tag)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prep":
        prep(*sys.argv[2:5])
    elif cmd == "sim":
        sim(*sys.argv[2:5])
    else:
        w = {int(x) for x in sys.argv[sys.argv.index("--windows") + 1].split(",")} if "--windows" in sys.argv else None
        evaluate(sys.argv[2], sys.argv[3], sys.argv[4], w)
