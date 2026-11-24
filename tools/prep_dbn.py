"""Cut one Databento MBO day file (one symbol) into 30-minute session windows.

    python tools/prep_dbn.py DAYFILE.dbn.zst OUTDIR [start_hour_utc=15] [sessions=6]

For each session it writes OUTDIR/SYM_YYYYMMDD_k.npz with the orders resting at the session start
(rebuilt from the midnight snapshot onward) and the events inside the session. Bounded memory.
Requires: pip install databento numpy
"""
import sys, os, numpy as np, databento as db

TICK = {"ES": 250_000_000, "ZN": 15_625_000, "UB": 31_250_000}   # price increment in 1e-9 units
A, C, M, R, F, T = (ord(x) for x in "ACMRFT")
EMPTY = (np.zeros(0, np.int64), np.zeros(0, np.int8), np.zeros(0, np.int32), np.zeros(0, np.int32))


def reduce(carry, oid, side, px, size, act):
    """Resting orders (carry) + book events in file order -> resting orders afterwards.
    On CME a cancel always removes the whole order and a modify carries the new price and size."""
    r = np.flatnonzero(act == R)
    if len(r):
        carry = EMPTY
        k = r[-1] + 1
        oid, side, px, size, act = oid[k:], side[k:], px[k:], size[k:], act[k:]
    o = np.concatenate([carry[0], oid])
    s = np.concatenate([carry[1], side])
    p = np.concatenate([carry[2], px])
    z = np.concatenate([carry[3], size])
    alive = np.concatenate([np.ones(len(carry[0]), bool), act != C])
    order = np.argsort(o, kind="stable")
    so = o[order]
    idx = order[np.r_[so[1:] != so[:-1], True]] if len(so) else order
    idx = np.sort(idx[alive[idx] & (z[idx] > 0)])
    return o[idx], s[idx], p[idx], z[idx]


def cols(a, tick):
    side = np.where(a["side"] == b"B", 1, np.where(a["side"] == b"A", -1, 0)).astype(np.int8)
    return a["order_id"].astype(np.int64), side, (a["price"] // tick).astype(np.int32), a["size"].astype(np.int32), a["action"].view(np.uint8).copy()


def prep(path, outdir, start_hour=15, sessions=6, chunk=4_000_000, sess_ns=1800 * 10**9):
    s = db.DBNStore.from_file(path)
    sym = s.symbols[0]
    tick = TICK[sym[:2]]
    day = s.start.strftime("%Y%m%d")
    t0 = int(np.datetime64(s.start.strftime("%Y-%m-%d"), "ns").astype(np.int64)) + start_hour * 3600 * 10**9
    t1 = t0 + sessions * sess_ns
    carry, win, n = EMPTY, [], 0
    for a in s.to_ndarray(count=chunk):
        n += len(a)
        ts = a["ts_recv"].astype(np.int64)
        act = a["action"].view(np.uint8)
        book = (act == A) | (act == M) | (act == C) | (act == R)
        pre = (ts < t0) & book
        if pre.any():
            carry = reduce(carry, *cols(a[pre], tick))
        w = (ts >= t0) & (ts < t1) & (book | (act == F) | (act == T))
        if w.any():
            win.append((ts[w],) + cols(a[w], tick))
        if ts[0] >= t1:
            break
    if not win:
        print(f"{sym} {day}: no events in the window")
        return
    ts, oid, side, px, size, act = (np.concatenate([w[i] for w in win]) for i in range(6))
    os.makedirs(outdir, exist_ok=True)
    out = []
    for k in range(sessions):
        a0 = t0 + k * sess_ns
        m = (ts >= a0) & (ts < a0 + sess_ns)
        bid = carry[2][carry[1] == 1].max()
        ask = carry[2][carry[1] == -1].min()
        np.savez_compressed(os.path.join(outdir, f"{sym[:2]}_{day}_{k}.npz"), sym=sym, day=day, k=k, tick=tick,
                            init_oid=carry[0], init_side=carry[1], init_px=carry[2], init_size=carry[3],
                            t=(ts[m] - a0) / 1e9, act=act[m], side=side[m], px=px[m], size=size[m], oid=oid[m])
        out.append(f"{int(m.sum()) // 1000}k ev, {bid}/{ask}")
        b = m & ((act == A) | (act == M) | (act == C) | (act == R))
        carry = reduce(carry, oid[b], side[b], px[b], size[b], act[b])
    print(f"{sym} {day}: {n:,} records | " + " | ".join(out))


if __name__ == "__main__":
    prep(sys.argv[1], sys.argv[2], *(int(x) for x in sys.argv[3:5]))
