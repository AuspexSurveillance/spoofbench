"""Build benchmark sessions: the firm's account roster, one simulated session per seed,
and the log the detectors read (orders, fills, account master) plus ground truth."""
import csv
import gzip
import json
import os

from .sim import Sim
from .accounts import MarketMaker, ExecAlgo, Discretionary, BasisTrader
from .templates import Manipulator, ManipulatingMM

# name, template, episodes per 30-minute session
MANIPULATORS = [("M_CHEN_LO", "chen", 4), ("M_CHEN_HI", "chen", 30), ("M_COSCIA", "coscia", 40),
                ("M_OYST", "oystacher", 25), ("M_SARAO", "sarao", 3), ("M_LEB", "lebental", 4)]


def roster(real=False):
    """real=True is the single-instrument roster used when replaying recorded market data: the
    two-instrument accounts (basis traders, the cash-futures template) are left out."""
    a = [MarketMaker("MM_FAST_1", q=5, nlev=2), MarketMaker("MM_LADDER", q=3, nlev=7),
         MarketMaker("MM_SKEW_FAST", q=5, nlev=2, skew=2.5, lag_max=0.2),
         MarketMaker("MM_SKEW_SLOW_1", q=5, nlev=2, skew=2.5, lag_max=4.0),
         MarketMaker("MM_SKEW_SLOW_2", q=8, nlev=1, skew=2.5, lag_max=4.0)]
    if not real:
        a += [BasisTrader("BASIS_1"), BasisTrader("BASIS_2")]
    a += [ExecAlgo(f"EXEC_{i}") for i in (1, 2, 3)]
    a += [Discretionary(f"DISC_{i}") for i in range(1, 9)]
    a += [Manipulator(n, t, k) for n, t, k in MANIPULATORS if not (real and t == "lebental")]
    a += [ManipulatingMM("M_MM_CHEN", "chen", 12, q=5, nlev=2, skew=2.5, lag_max=4.0)]
    if not real:
        a += [ManipulatingMM("M_MM_LEB", "lebental", 4, q=5, nlev=2)]
    return a


class Session:
    """What a detector may read: orders, fills, accounts. Ground truth: episodes, order ep/role."""

    def __init__(self, sid, sim, agents):
        self.sid = sid
        self.T = sim.T
        self.orders = sim.orders
        self.fills = sim.fills                      # (t, oid, qty, px, aggressor)
        self.episodes = sim.episodes
        self.accounts = {a.name: dict(kind=a.kind, truth=a.truth,
                                      template=getattr(a, "template", None)) for a in agents}
        self.by_oid = {o.oid: o for o in sim.orders}


def make_session(sid, seed, T=1800.0, bg=None):
    sim = Sim(seed, T=T, bg=bg)
    agents = roster()
    sim.agents = agents
    sim.run()
    return Session(sid, sim, agents)


def dump(session, outdir):
    """Write one session as flat files (the public form of the benchmark)."""
    os.makedirs(outdir, exist_ok=True)
    with gzip.open(os.path.join(outdir, f"orders_{session.sid:03d}.csv.gz"), "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["oid", "acct", "inst", "side", "px", "qty", "filled", "t_in", "t_out", "status", "aggr",
                    "dist", "own_same", "own_opp"] + [f"depth_{i}" for i in range(9)] + ["ep", "role"])
        for o in session.orders:
            w.writerow([o.oid, o.acct, o.inst, o.side, o.px if o.px is not None else "", o.qty, o.filled,
                        f"{o.t_in:.6f}", f"{o.t_out:.6f}", o.status, int(o.aggr), o.dist, o.own_same, o.own_opp]
                       + list(o.depth) + [o.ep if o.ep is not None else "", o.role or ""])
    with gzip.open(os.path.join(outdir, f"fills_{session.sid:03d}.csv.gz"), "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "oid", "qty", "px", "aggressor"])
        for t, oid, q, px, ag in session.fills:
            w.writerow([f"{t:.6f}", oid, q, px, int(ag)])
    with open(os.path.join(outdir, f"episodes_{session.sid:03d}.json"), "w") as f:
        json.dump(dict(accounts=session.accounts, episodes=session.episodes), f)
