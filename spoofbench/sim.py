"""Limit order book simulator for the seeded-manipulation benchmark.

Two correlated instruments (FUT, CASH) each run a price-time-priority book driven by
anonymous background flow. A set of firm accounts trades on top of it: legitimate
account types that produce hard negatives, and manipulator accounts that run the
enforcement-order templates in templates.py. Only the firm's own orders and fills,
plus market-data features captured at each order entry, are written to the log. That
is the view a firm's surveillance system has.
"""
import heapq
import random
from collections import defaultdict, deque

BUY, SELL = 1, -1
STREET = "STREET"
NLEV = 9          # book levels captured in each entry snapshot
D_REF = 3         # "within d ticks of the touch" used for the own-presence snapshot


class Order:
    __slots__ = ("oid", "acct", "inst", "side", "px", "qty", "rem", "t_in", "t_out", "status",
                 "dist", "depth", "own_same", "own_opp", "aggr", "ep", "role", "cb", "_filled", "ahead")

    def __init__(self, oid, acct, inst, side, px, qty, t):
        self.oid, self.acct, self.inst, self.side, self.px = oid, acct, inst, side, px
        self.qty = self.rem = qty
        self.t_in, self.t_out, self.status = t, None, "L"   # L live, F filled, C cancelled, R replaced
        self.dist = 0            # ticks behind the same-side touch at entry (negative = improved it)
        self.depth = None        # same-side displayed qty at levels 0..NLEV-1 at entry, own orders excluded
        self.own_same = 0        # own resting qty within D_REF ticks, same side, at entry
        self.own_opp = 0         # own resting qty within D_REF ticks, opposite side, at entry
        self.aggr = False        # executed on entry
        self.ep = None           # episode id (ground truth; never read by the detectors)
        self.role = None         # "spoof" | "genuine"
        self.cb = None           # fill callback
        self._filled = 0
        self.ahead = 0           # replay only: displayed quantity queued ahead of this order

    @property
    def filled(self):
        return self.qty - self.rem if self.status in ("L", "F") else self._filled


class Book:
    def __init__(self, mid):
        self.q = {BUY: {}, SELL: {}}
        self.sz = {BUY: {}, SELL: {}}
        self.best = {BUY: mid - 1, SELL: mid}
        self.last = mid

    def best_px(self, side):
        sz = self.sz[side]
        p = self.best[side]
        if sz.get(p, 0) > 0:
            return p
        step = -1 if side == BUY else 1
        for i in range(1, 600):
            p2 = p + step * i
            if sz.get(p2, 0) > 0:
                self.best[side] = p2
                return p2
        return None

    def depth(self, side, d):
        b = self.best_px(side)
        if b is None:
            return 0
        sz = self.sz[side]
        step = -1 if side == BUY else 1
        return sum(sz.get(b + step * i, 0) for i in range(d + 1))

    def levels(self, side, n=NLEV):
        b = self.best_px(side)
        if b is None:
            return [0] * n
        sz = self.sz[side]
        step = -1 if side == BUY else 1
        return [sz.get(b + step * i, 0) for i in range(n)]


class Sim:
    def __init__(self, seed, T=1800.0, mids=None, bg=None):
        self.rng = random.Random(seed)
        self.T = T
        self.t = 0.0
        self.heap, self.seq, self.noid = [], 0, 0
        mids = mids or {"FUT": 10000, "CASH": 20000}
        self.books = {k: Book(v) for k, v in mids.items()}
        self.bg = dict(lam_l=4.0, life=8.0, lam_m=1.6, beta=0.35, gamma=3.0, qmax=10, mmax=15)
        self.bg.update(bg or {})
        self.orders, self.fills, self.episodes = [], [], []
        self.live = defaultdict(dict)
        self.agents = []

    # ---------------- scheduling
    def at(self, t, fn, *args):
        heapq.heappush(self.heap, (t, self.seq, fn, args))
        self.seq += 1

    def after(self, dt, fn, *args):
        self.at(self.t + dt, fn, *args)

    def run(self):
        for inst in self.books:
            for side in (BUY, SELL):
                self._seed_book(inst, side)
                self.after(self.rng.expovariate(self.bg["lam_l"]), self._bg_limit, inst, side)
            self.after(self.rng.expovariate(self.bg["lam_m"]), self._bg_market, inst)
        for a in self.agents:
            a.start(self)
        heap = self.heap
        while heap:
            t, _, fn, args = heapq.heappop(heap)
            if t > self.T:
                break
            self.t = t
            fn(*args)
        for o in self.orders:                       # close the session
            if o.status == "L":
                o._filled = o.qty - o.rem
                o.status, o.t_out = "X", self.T      # X = still live at the end of the session
        return self

    # ---------------- order entry / cancel
    def submit(self, acct, inst, side, px, qty, ep=None, role=None, cb=None):
        """px=None is a market order. Returns the Order (firm) or the resting Order (street)."""
        book = self.books[inst]
        self.noid += 1
        o = Order(self.noid, acct, inst, side, px, qty, self.t)
        firm = acct != STREET
        if firm:
            o.ep, o.role, o.cb = ep, role, cb
            self._snapshot(o, book)
            self.orders.append(o)
        opp = -side
        osz, oq = book.sz[opp], book.q[opp]
        while o.rem > 0:
            bp = book.best_px(opp)
            if bp is None or (px is not None and (bp - px) * side > 0):
                break
            dq = oq[bp]
            while dq and o.rem > 0:
                r = dq[0]
                if r.rem == 0:
                    dq.popleft()
                    continue
                x = r.rem if r.rem < o.rem else o.rem
                r.rem -= x
                o.rem -= x
                osz[bp] -= x
                book.last = bp
                o.aggr = True
                if r.acct != STREET:
                    self.fills.append((self.t, r.oid, x, bp, False))
                    if r.rem == 0:
                        r.status, r.t_out = "F", self.t
                        self.live[r.acct].pop(r.oid, None)
                    if r.cb:
                        self.at(self.t, r.cb, r, x)
                elif r.rem == 0:
                    r.status = "F"
                if firm:
                    self.fills.append((self.t, o.oid, x, bp, True))
                if r.rem == 0:
                    dq.popleft()
            if osz.get(bp, 0) <= 0:
                osz.pop(bp, None)
                oq.pop(bp, None)
        if o.rem > 0 and px is not None:
            sz = book.sz[side]
            b = book.best_px(side)
            sz[px] = sz.get(px, 0) + o.rem
            q = book.q[side]
            if px not in q:
                q[px] = deque()
            q[px].append(o)
            if b is None or (px - b) * side > 0:
                book.best[side] = px
            if firm:
                self.live[acct][o.oid] = o
        else:
            if o.rem == 0:
                o.status, o.t_out = "F", self.t
            else:                                    # unfilled remainder of a market order
                o._filled = o.qty - o.rem
                o.rem = 0
                o.status, o.t_out = "C", self.t
        if firm and o.aggr and o.cb:
            self.at(self.t, o.cb, o, o.filled)
        return o

    def cancel(self, o, replace=False):
        if o.status != "L" or o.rem <= 0:
            return False
        book = self.books[o.inst]
        sz = book.sz[o.side]
        left = sz.get(o.px, 0) - o.rem
        if left <= 0:
            sz.pop(o.px, None)
            book.q[o.side].pop(o.px, None)
        else:
            sz[o.px] = left
        o._filled = o.qty - o.rem
        o.rem = 0
        o.status, o.t_out = ("R" if replace else "C"), self.t
        if o.acct != STREET:
            self.live[o.acct].pop(o.oid, None)
        return True

    def _snapshot(self, o, book):
        side = o.side
        b = book.best_px(side)
        ob = book.best_px(-side)
        lev = book.levels(side)
        own_same = own_opp = 0
        for x in self.live[o.acct].values():
            if x.inst != o.inst:
                continue
            if x.side == side and b is not None:
                k = (b - x.px) * side
                if 0 <= k < NLEV:
                    lev[k] -= x.rem
                    if k <= D_REF:
                        own_same += x.rem
            elif x.side != side and ob is not None:
                if 0 <= (x.px - ob) * side <= D_REF:
                    own_opp += x.rem
        o.depth = lev
        o.own_same, o.own_opp = own_same, own_opp
        if o.px is None or b is None:
            o.dist = 0
        else:
            o.dist = (b - o.px) * side

    # ---------------- background flow
    _W = (0.34, 0.58, 0.74, 0.84, 0.90, 0.94, 0.97, 0.99, 1.0)

    def _seed_book(self, inst, side):
        book = self.books[inst]
        b = book.best[side]
        for i in range(8):
            for _ in range(3 if i else 8):
                o = self.submit(STREET, inst, side, b - side * i, self.rng.randint(1, self.bg["qmax"]))
                self.after(self.rng.expovariate(1.0 / self.bg["life"]), self.cancel, o)

    def _bg_limit(self, inst, side):
        rng, bg = self.rng, self.bg
        self.after(rng.expovariate(bg["lam_l"]), self._bg_limit, inst, side)
        book = self.books[inst]
        b, ob = book.best_px(side), book.best_px(-side)
        if b is None:
            b = (ob - side) if ob is not None else book.last - side
        r = rng.random()
        if r < 0.04 and ob is not None and (ob - b) * side >= 2:
            px = b + side
        else:
            r = rng.random()
            k = 0
            while r > self._W[k]:
                k += 1
            px = b - side * k
        o = self.submit(STREET, inst, side, px, rng.randint(1, bg["qmax"]))
        if o.status == "L":
            self.after(rng.expovariate(1.0 / bg["life"]), self.cancel, o)

    def imbalance(self, inst):
        bk = self.books[inst]
        db, da = bk.depth(BUY, D_REF), bk.depth(SELL, D_REF)
        return (db - da) / (db + da) if db + da else 0.0

    def _bg_market(self, inst):
        # Background takers react to displayed imbalance in two ways: they trade more often when
        # the book is lopsided, and they trade toward the heavy side. This is the channel through
        # which a spoof order gets the genuine order filled.
        rng, bg = self.rng, self.bg
        g = bg["gamma"]
        self.after(rng.expovariate(bg["lam_m"] * (1 + g)), self._bg_market, inst)
        imb = self.imbalance(inst)
        if inst == "CASH":                          # the cash market follows the futures book
            imb = 0.5 * imb + 0.5 * self.imbalance("FUT")
        if rng.random() > (1 + g * abs(imb)) / (1 + g):
            return
        p = min(0.9, max(0.1, 0.5 + bg["beta"] * imb))
        self.submit(STREET, inst, BUY if rng.random() < p else SELL, None, rng.randint(1, bg["mmax"]))

    # ---------------- helpers for agents
    def touch(self, inst, side):
        b = self.books[inst].best_px(side)
        return b if b is not None else self.books[inst].last
