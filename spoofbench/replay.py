"""Replay recorded order-by-order (MBO) market data as the background market.

The firm's accounts and the seeded episodes are the same code as in the simulated benchmark;
only the market is real. Firm orders are hypothetical: they do not change the recorded book and
nobody reacts to them. A passive firm order queues behind the displayed quantity at its price and
is filled when the recorded flow would have reached it:
  - quantity ahead of it shrinks as orders that were resting before it are cancelled, reduced
    or filled;
  - once nothing is ahead, a recorded fill at its price fills it;
  - a recorded fill at a worse price on its side fills it completely.
An aggressive firm order executes against the displayed quantity at entry.

Input is one window file written by tools/prep_dbn.py: the resting orders at the window start
and the events in the window (add, cancel, modify, fill, trade, clear).
"""
import heapq
from .sim import Sim, Order, BUY, SELL, NLEV, D_REF

A, C, M, R, F, T = (ord(x) for x in "ACMRFT")


class ReplaySim(Sim):
    def __init__(self, seed, win, T=1800.0):
        super().__init__(seed, T=T, mids={"FUT": 0})
        self.book = bk = self.books["FUT"]
        self.real = real = {}                       # order id -> [side, price, size, priority time]
        for oid, s, p, q in zip(win["init_oid"].tolist(), win["init_side"].tolist(), win["init_px"].tolist(),
                                win["init_size"].tolist()):
            d = bk.sz[s]
            d[p] = d.get(p, 0) + q
            real[oid] = [s, p, q, -1.0]
        bk.best[BUY], bk.best[SELL] = max(bk.sz[BUY]), min(bk.sz[SELL])
        bk.last = bk.best[BUY]
        self.ev = tuple(win[k] for k in ("t", "act", "side", "px", "size", "oid"))   # numpy; converted in chunks
        self.virt = {BUY: {}, SELL: {}}             # price -> live firm orders resting there
        self.nvirt = 0

    # ---------------- firm orders
    def submit(self, acct, inst, side, px, qty, ep=None, role=None, cb=None):
        bk = self.book
        self.noid += 1
        o = Order(self.noid, acct, "FUT", side, px, qty, self.t)
        o.ep, o.role, o.cb = ep, role, cb
        self._snapshot(o, bk)
        self.orders.append(o)
        osz = bk.sz[-side]
        bp = bk.best_px(-side)
        if bp is not None:
            for _ in range(60):                     # walk displayed levels; the recorded book is not changed
                if o.rem <= 0 or (px is not None and (bp - px) * side > 0):
                    break
                x = min(o.rem, osz.get(bp, 0))
                if x > 0:
                    o.rem -= x
                    o.aggr = True
                    self.fills.append((self.t, o.oid, x, bp, True))
                bp += side
        if o.rem > 0 and px is not None:
            o.ahead = bk.sz[side].get(px, 0)
            self.virt[side].setdefault(px, []).append(o)
            self.nvirt += 1
            self.live[acct][o.oid] = o
        elif o.rem == 0:
            o.status, o.t_out = "F", self.t
        else:
            o._filled = o.qty - o.rem
            o.rem = 0
            o.status, o.t_out = "C", self.t
        if o.aggr and o.cb:
            self.at(self.t, o.cb, o, o.filled)
        return o

    def _drop(self, o):
        lst = self.virt[o.side].get(o.px)
        if lst and o in lst:
            lst.remove(o)
            if not lst:
                del self.virt[o.side][o.px]
            self.nvirt -= 1
        self.live[o.acct].pop(o.oid, None)

    def cancel(self, o, replace=False):
        if o.status != "L" or o.rem <= 0:
            return False
        self._drop(o)
        o._filled = o.qty - o.rem
        o.rem = 0
        o.status, o.t_out = ("R" if replace else "C"), self.t
        return True

    def _vfill(self, v, x):
        v.rem -= x
        self.fills.append((self.t, v.oid, x, v.px, False))
        if v.rem == 0:
            v.status, v.t_out = "F", self.t
            self._drop(v)
        if v.cb:
            self.at(self.t, v.cb, v, x)

    def _snapshot(self, o, book):
        side = o.side
        b, ob = book.best_px(side), book.best_px(-side)
        o.depth = book.levels(side)                 # recorded depth; firm orders are not in it
        own_same = own_opp = 0
        for x in self.live[o.acct].values():
            if x.side == side and b is not None:
                if 0 <= (b - x.px) * side <= D_REF:
                    own_same += x.rem
            elif x.side != side and ob is not None:
                if 0 <= (x.px - ob) * side <= D_REF:
                    own_opp += x.rem
        o.own_same, o.own_opp = own_same, own_opp
        o.dist = 0 if (o.px is None or b is None) else (b - o.px) * side

    # ---------------- event loop: recorded events merged with the firm's scheduled actions
    def run(self):
        for a in self.agents:
            a.start(self)
        heap, Tend = self.heap, self.T
        ev, total, nxt, CH = self.ev, len(self.ev[0]), 0, 250_000
        tl = al = sl = pl = zl = ol = ()
        n, i = 0, 0
        bk, real, virt = self.book, self.real, self.virt
        sz, best = bk.sz, bk.best
        while True:
            if i >= n and nxt < total:              # next chunk of recorded events as plain lists
                tl, al, sl, pl, zl, ol = (x[nxt:nxt + CH].tolist() for x in ev)
                nxt += CH
                n, i = len(tl), 0
            te = tl[i] if i < n else 1e18
            if heap and heap[0][0] <= te:
                t, _, fn, args = heapq.heappop(heap)
                if t > Tend:
                    break
                self.t = t
                fn(*args)
                continue
            if te > Tend:
                break
            self.t = te
            a, oid = al[i], ol[i]
            if a == A:
                s, p, q = sl[i], pl[i], zl[i]
                d = sz[s]
                d[p] = d.get(p, 0) + q
                real[oid] = [s, p, q, te]
                if (p - best[s]) * s > 0:
                    best[s] = p
            elif a == C:
                o = real.pop(oid, None)
                if o is not None:
                    s, p, q, tp = o
                    d = sz[s]
                    left = d.get(p, 0) - q
                    if left > 0:
                        d[p] = left
                    else:
                        d.pop(p, None)
                    if self.nvirt:
                        vl = virt[s].get(p)
                        if vl:
                            for v in vl:
                                if tp < v.t_in:
                                    v.ahead -= q
            elif a == M:
                o = real.get(oid)
                p, q = pl[i], zl[i]
                if o is None:
                    s = sl[i]
                    d = sz[s]
                    d[p] = d.get(p, 0) + q
                    real[oid] = [s, p, q, te]
                else:
                    s, p0, q0, tp = o
                    d = sz[s]
                    left = d.get(p0, 0) - q0
                    if left > 0:
                        d[p0] = left
                    else:
                        d.pop(p0, None)
                    d[p] = d.get(p, 0) + q
                    keep = p == p0 and q <= q0          # a size reduction keeps queue priority
                    if self.nvirt:
                        vl = virt[s].get(p0)
                        if vl:
                            gone = (q0 - q) if keep else q0
                            for v in vl:
                                if tp < v.t_in:
                                    v.ahead -= gone
                    o[1], o[2] = p, q
                    if not keep:
                        o[3] = te
                if (p - best[s]) * s > 0:
                    best[s] = p
            elif a == F:
                if self.nvirt:
                    o = real.get(oid)
                    s = o[0] if o is not None else sl[i]
                    vs = virt[s]
                    if vs:
                        p, q = pl[i], zl[i]
                        behind_time = o[3] if o is not None else -1.0
                        for pv in list(vs):
                            if pv == p:
                                for v in list(vs[pv]):
                                    if v.ahead <= 0 or behind_time > v.t_in:
                                        self._vfill(v, min(q, v.rem))
                            elif (pv - p) * s > 0:      # the market traded through this order's price
                                for v in list(vs[pv]):
                                    self._vfill(v, v.rem)
                bk.last = pl[i]
            elif a == R:
                sz[BUY].clear()
                sz[SELL].clear()
                real.clear()
            i += 1
        for o in self.orders:
            if o.status == "L":
                o._filled = o.qty - o.rem
                o.status, o.t_out = "X", self.T
        return self
