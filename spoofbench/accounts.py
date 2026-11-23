"""Legitimate account types. Each is built to produce the activity a spoofing detector
is most likely to confuse with manipulation: high cancel rates, one-sided size, and
cancels that happen to follow an opposite-side fill."""
from .sim import BUY, SELL


class Agent:
    kind = "prop"        # account class from the account master
    truth = "legit"

    def __init__(self, name):
        self.name = name

    def start(self, sim):
        self.sim, self.rng = sim, sim.rng


class MarketMaker(Agent):
    """Two-sided quoting at the touch. skew>0 sizes the quotes by inventory; lag_max is the
    longest gap between pulling quotes after a fill and re-entering them (a slow re-quote
    looks like a cancel-after-fill)."""
    kind = "mm"

    def __init__(self, name, q=15, nlev=2, skew=0.0, lag_max=0.2, inst="FUT"):
        super().__init__(name)
        self.q, self.nlev, self.skew, self.lag_max, self.inst = q, nlev, skew, lag_max, inst
        self.inv, self.quotes, self.busy = 0, [], False

    def start(self, sim):
        super().start(sim)
        sim.after(self.rng.uniform(0, 2), self.tick)

    def sizes(self):
        if not self.skew:
            return self.q, self.q
        f = max(-1.0, min(1.0, self.inv / (4.0 * self.q)))
        qb = max(1, round(self.q * (1 + self.skew * max(0.0, -f)) * (0.4 if f > 0.25 else 1)))
        qa = max(1, round(self.q * (1 + self.skew * max(0.0, f)) * (0.4 if f < -0.25 else 1)))
        return qb, qa

    def target(self):
        s = self.sim
        bb, ba = s.touch(self.inst, BUY), s.touch(self.inst, SELL)
        qb, qa = self.sizes()
        want = {}
        for i in range(self.nlev):
            want[(BUY, bb - i)] = qb
            want[(SELL, ba + i)] = qa
        return want

    def tick(self):
        self.sim.after(self.rng.expovariate(1.0), self.tick)
        if self.busy:
            return
        want = self.target()
        have = {(o.side, o.px) for o in self.quotes if o.status == "L"}
        if have != set(want):
            self.pull()
            self.place()

    def pull(self):
        for o in self.quotes:
            self.sim.cancel(o)
        self.quotes = []

    def place(self):
        self.busy = False
        self.pull()
        self.quotes = [self.sim.submit(self.name, self.inst, s, px, q, cb=self.on_fill)
                       for (s, px), q in self.target().items()]

    def on_fill(self, o, x):
        self.inv += o.side * x
        if self.busy or self.rng.random() > 0.6:
            return
        self.busy = True                      # re-quote: pull everything, then come back
        self.sim.after(self.rng.uniform(0.02, 0.3), self._requote)

    def _requote(self):
        self.pull()
        self.sim.after(self.rng.uniform(0.02, self.lag_max), self.place)


class ExecAlgo(Agent):
    """Works large parent orders passively at the touch, cancelling and re-placing children,
    while small passive orders rest on both sides."""
    kind = "exec"

    def start(self, sim):
        super().start(sim)
        sim.after(self.rng.expovariate(1 / 150.0), self.parent)
        sim.after(self.rng.expovariate(1 / 25.0), self.small)

    def parent(self):
        r = self.rng
        self.sim.after(r.expovariate(1 / 150.0), self.parent)
        self.work(r.choice((BUY, SELL)), r.randint(100, 300), self.sim.t + r.uniform(60, 150))

    def work(self, side, left, deadline):
        s, r = self.sim, self.rng
        if left <= 0 or s.t > deadline:
            return
        o = s.submit(self.name, "FUT", side, s.touch("FUT", side), min(left, r.randint(20, 60)))
        s.after(r.uniform(4, 20), self.review, o, side, left, deadline)

    def review(self, o, side, left, deadline):
        self.sim.cancel(o)
        self.sim.after(self.rng.uniform(0.2, 3.0), self.work, side, left - o.filled, deadline)

    def small(self):
        s, r = self.sim, self.rng
        s.after(r.expovariate(1 / 25.0), self.small)
        side = r.choice((BUY, SELL))
        o = s.submit(self.name, "FUT", side, s.touch("FUT", side), r.randint(1, 5))
        s.after(r.uniform(5, 30), s.cancel, o)


class Discretionary(Agent):
    """Point-and-click style account: small passive and aggressive orders, and the occasional
    large passive order that is pulled a few seconds later."""
    kind = "prop"

    def start(self, sim):
        super().start(sim)
        sim.after(self.rng.expovariate(1 / 15.0), self.small)
        sim.after(self.rng.expovariate(1 / 60.0), self.take)
        sim.after(self.rng.expovariate(1 / 200.0), self.large)

    def small(self):
        s, r = self.sim, self.rng
        s.after(r.expovariate(1 / 15.0), self.small)
        side = r.choice((BUY, SELL))
        o = s.submit(self.name, "FUT", side, s.touch("FUT", side) - side * r.randint(0, 1), r.randint(1, 5))
        s.after(r.uniform(5, 40), s.cancel, o)

    def take(self):
        s, r = self.sim, self.rng
        s.after(r.expovariate(1 / 60.0), self.take)
        s.submit(self.name, "FUT", r.choice((BUY, SELL)), None, r.randint(1, 5))

    def large(self):
        s, r = self.sim, self.rng
        s.after(r.expovariate(1 / 200.0), self.large)
        side = r.choice((BUY, SELL))
        o = s.submit(self.name, "FUT", side, s.touch("FUT", side) - side * r.randint(0, 1), r.randint(20, 60))
        s.after(r.uniform(2, 20), s.cancel, o)


class BasisTrader(Agent):
    """Genuine two-legged trading across the correlated pair: rests a bid in CASH and an offer in
    FUT (or the reverse); when the CASH leg fills it cancels the passive FUT leg and hedges
    with a market order on the same side. Both legs are genuine."""
    kind = "basis"

    def start(self, sim):
        super().start(sim)
        sim.after(self.rng.expovariate(1 / 60.0), self.package)

    def package(self):
        s, r = self.sim, self.rng
        s.after(r.expovariate(1 / 60.0), self.package)
        g = r.choice((BUY, SELL))
        q = r.randint(20, 50)
        st = {"done": False}
        fut = s.submit(self.name, "FUT", -g, s.touch("FUT", -g), q)

        def on_fill(o, x):
            if st["done"]:
                return
            st["done"] = True
            left = fut.rem
            s.cancel(fut)
            if left > 0:
                s.submit(self.name, "FUT", -g, None, left)

        cash = s.submit(self.name, "CASH", g, s.touch("CASH", g), q, cb=on_fill)

        def timeout():
            if not st["done"]:
                st["done"] = True
                s.cancel(fut)
            s.cancel(cash)

        s.after(r.uniform(10, 40), timeout)
