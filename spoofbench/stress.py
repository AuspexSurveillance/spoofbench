"""Stress tier (v0.5): harder legitimate accounts and manipulation that does not follow a document.

Kept apart from the five futures templates and the equities set so that every earlier number
stays reproducible. Nothing here runs unless run_learned.py --tier stress is used.

Legitimate accounts added (each produces, for honest reasons, the sequence a spoofing detector
looks for: a large resting order pulled soon after a small execution on the other side):

  Scalper       works a large passive entry order while small take-profit orders from earlier
                entries rest on the other side; when a take-profit trades it pulls the entry
                order and comes back later at a new price.
  LeggedHedger  two-legged package across the correlated pair with a hedge ratio, so the futures
                leg is several times the cash leg; when the cash leg trades it pulls the futures
                leg and hedges somewhere the firm's records do not show.
  BlockWorker   scales in with a ladder of large passive orders at several prices, pulls the
                whole ladder when it goes stale and re-enters later, with small orders on both
                sides in the meantime.

Manipulation added ("adaptive", three modes). These are not taken from an enforcement document.
They are what a trader who knows how the procedures work might do: sizes that are not round,
orders entered and cancelled one at a time instead of as a block, a small order put back on the
same side after the cancel, and sometimes the spoof entered before the genuine order.
  ada_same   genuine passive order and spoof orders in the same instrument
  ada_flip   spoof orders pulled, then an aggressive order on the other side
  ada_cross  genuine order in the cash instrument, spoof orders in the future
"""
from .sim import BUY, SELL
from .accounts import Agent
from .bench import Session, roster
from .sim import Sim
from .templates import Episode, Manipulator, TEMPLATES


class Scalper(Agent):
    kind = "prop"

    def start(self, sim):
        super().start(sim)
        self.entry, self.gen = None, 0
        sim.after(self.rng.expovariate(1 / 20.0), self.enter)

    def enter(self):
        s, r = self.sim, self.rng
        if s.t > s.T - 20:
            return
        side = r.choice((BUY, SELL))
        self.gen += 1
        self.entry = s.submit(self.name, "FUT", side, s.touch("FUT", side) - side * r.randint(0, 1), r.randint(20, 80),
                              cb=self.on_entry)
        s.after(r.uniform(10, 60), self.stale, self.gen)

    def on_entry(self, o, x):
        s, r = self.sim, self.rng
        tp_side = -o.side
        tp = s.submit(self.name, "FUT", tp_side, s.touch("FUT", tp_side) - tp_side * r.randint(0, 2), max(1, min(x, 10)),
                      cb=self.on_tp)
        s.after(r.uniform(30, 120), s.cancel, tp)

    def on_tp(self, o, x):
        if self.entry is not None and self.entry.status == "L" and self.rng.random() < 0.7:
            self.sim.after(self.rng.uniform(0.3, 6.0), self.pull, self.gen)

    def stale(self, gen):
        self.pull(gen)

    def pull(self, gen):
        if gen != self.gen or self.entry is None:
            return
        self.sim.cancel(self.entry)
        self.entry = None
        self.sim.after(self.rng.uniform(3, 30), self.enter)


class LeggedHedger(Agent):
    kind = "basis"

    def start(self, sim):
        super().start(sim)
        sim.after(self.rng.expovariate(1 / 50.0), self.package)

    def package(self):
        s, r = self.sim, self.rng
        s.after(r.expovariate(1 / 50.0), self.package)
        g = r.choice((BUY, SELL))
        q = r.randint(10, 30)
        st = {"done": False}

        def close(other):
            if st["done"]:
                return
            st["done"] = True
            s.after(r.uniform(0.05, 2.0), s.cancel, other)

        fut = s.submit(self.name, "FUT", -g, s.touch("FUT", -g) + g * r.randint(0, 1), round(q * r.uniform(1.5, 3.5)),
                       cb=lambda o, x: close(cash))
        cash = s.submit(self.name, "CASH", g, s.touch("CASH", g), q, cb=lambda o, x: close(fut))

        def timeout():
            if not st["done"]:
                st["done"] = True
                s.cancel(fut)
                s.cancel(cash)

        s.after(r.uniform(10, 40), timeout)


class BlockWorker(Agent):
    kind = "exec"

    def start(self, sim):
        super().start(sim)
        sim.after(self.rng.expovariate(1 / 30.0), self.ladder)
        sim.after(self.rng.expovariate(1 / 25.0), self.small)

    def ladder(self):
        s, r = self.sim, self.rng
        if s.t > s.T - 20:
            return
        side = r.choice((BUY, SELL))
        t = s.touch("FUT", side)
        orders = [s.submit(self.name, "FUT", side, t - side * k, r.randint(10, 30)) for k in range(r.randint(3, 5))]
        st = {"on": True}

        def pull():
            if not st["on"]:
                return
            st["on"] = False
            for o in orders:
                s.cancel(o)
            s.after(r.uniform(5, 40), self.ladder)

        def watch():
            if not st["on"]:
                return
            if (s.touch("FUT", side) - t) * side >= 2:      # the market moved away from the ladder
                pull()
            else:
                s.after(r.uniform(0.3, 1.0), watch)

        s.after(r.uniform(0.3, 1.0), watch)
        s.after(r.uniform(3, 30), pull)

    def small(self):
        s, r = self.sim, self.rng
        s.after(r.expovariate(1 / 25.0), self.small)
        side = r.choice((BUY, SELL))
        o = s.submit(self.name, "FUT", side, s.touch("FUT", side), r.randint(1, 5))
        s.after(r.uniform(5, 30), s.cancel, o)


def _split(r, total, n):
    cuts = sorted(r.random() for _ in range(n - 1))
    return [max(1, round(total * (b - a))) for a, b in zip([0.0] + cuts, cuts + [1.0])]


def _adaptive(mode):
    def run(sim, acct, done, evasive=False):
        r = sim.rng
        g = r.choice((BUY, SELL))
        s = -g
        ep = Episode(sim, acct, "ada_" + mode, evasive)
        st = {"filled": False, "pulled": False, "closed": False, "spoofs": [], "gen": None}
        depth = max(10, sim.books["FUT"].depth(s, 2))
        total = max(8, round(depth * (r.uniform(0.15, 0.5) if evasive else r.uniform(0.4, 2.5))))
        sizes = _split(r, total, r.randint(1, 6))
        span = r.uniform(0.2, 2.5) if r.random() < 0.7 else 0.0          # staggered entry
        ep.rec["params"]["spoof_qty"] = sum(sizes)

        def lay(q):
            if not st["pulled"]:
                st["spoofs"].append(ep.spoof("FUT", s, sim.touch("FUT", s) - s * r.randint(0, 3), q))

        def camo():
            o = sim.submit(acct, "FUT", s, sim.touch("FUT", s), max(1, round(total * r.uniform(0.1, 0.3))))
            sim.after(r.uniform(2, 10), sim.cancel, o)

        def finish():
            if st["closed"]:
                return
            st["closed"] = True
            if st["gen"] is not None:
                sim.cancel(st["gen"])
            ep.close()
            done()

        def pull(then=None):
            if st["pulled"]:
                return
            st["pulled"] = True
            stag = r.uniform(0.1, 1.5) if (r.random() < 0.6 and mode != "flip") else 0.0     # staggered cancel
            live = list(st["spoofs"])
            for i, o in enumerate(live):
                sim.after(stag * i / max(1, len(live)), sim.cancel, o)
            if r.random() < 0.5:
                sim.after(stag + r.uniform(0.01, 0.3), camo)
            if then:
                sim.after(stag + r.uniform(0.001, 0.02), then)
            else:
                sim.after(stag + r.uniform(0.5, 3.0), finish)

        def on_fill(o, x):
            if st["filled"]:
                return
            st["filled"] = ep.rec["filled"] = True
            if mode != "flip":
                lat = r.uniform(0.5, 20.0) if evasive else r.uniform(0.1, 6.0)
                ep.rec["params"]["latency"] = lat
                sim.after(lat, pull)

        def genuine():
            inst = "CASH" if mode == "cross" else "FUT"
            st["gen"] = ep.genuine(inst, g, sim.touch(inst, g), r.randint(10, 40) if mode == "cross" else r.randint(1, 15), cb=on_fill)

        def flip():
            px = sim.touch("FUT", s)
            st["gen"] = ep.genuine("FUT", g, px, max(1, round(total * r.uniform(0.2, 0.6))), cb=on_fill)
            sim.after(r.uniform(1.0, 4.0), finish)

        for i, q in enumerate(sizes):
            sim.after(span * i / len(sizes) + (0.0 if mode == "flip" else 0.02), lay, q)
        if mode == "flip":
            sim.after(span + (r.uniform(1.0, 4.0) if evasive else r.uniform(0.3, 2.0)), pull, flip)
        else:
            if r.random() < 0.3:                      # spoof first, genuine order a moment later
                sim.after(r.uniform(0.1, 1.0), genuine)
            else:
                genuine()
            sim.after(span + r.uniform(3.0, 10.0), pull)

    return run


TEMPLATES.update(ada_same=_adaptive("same"), ada_flip=_adaptive("flip"), ada_cross=_adaptive("cross"))
ADAPTIVE = ("ada_same", "ada_flip", "ada_cross")


def roster_stress():
    return roster() + [Scalper("SCALP_1"), Scalper("SCALP_2"), LeggedHedger("LEG_1"), LeggedHedger("LEG_2"),
                       BlockWorker("BLOCK_1"), BlockWorker("BLOCK_2"),
                       Manipulator("M_ADA_SAME", "ada_same", 20), Manipulator("M_ADA_FLIP", "ada_flip", 15),
                       Manipulator("M_ADA_X", "ada_cross", 8)]


def make_session_stress(sid, seed, T=1800.0):
    sim = Sim(seed, T=T)
    agents = roster_stress()
    sim.agents = agents
    sim.run()
    return Session(sid, sim, agents)
