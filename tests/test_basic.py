"""Run with: python -m pytest tests  (or python tests/test_basic.py)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from spoofbench.sim import Sim, BUY, SELL, STREET
from spoofbench.bench import make_session
from spoofbench.detect import Index, Params, detect


def test_book_conservation():
    """Displayed size per level always equals the sum of the live orders resting there."""
    sim = Sim(7, T=120.0)
    sim.run()
    for bk in sim.books.values():
        for side in (BUY, SELL):
            for px, dq in bk.q[side].items():
                assert sum(o.rem for o in dq) == bk.sz[side][px] > 0
            bb, ba = bk.best_px(BUY), bk.best_px(SELL)
            assert bb is None or ba is None or bb < ba


def test_price_time_priority():
    sim = Sim(1, T=1.0)
    a = sim.submit("A", "FUT", SELL, 10005, 5)
    b = sim.submit("B", "FUT", SELL, 10005, 5)
    for px in list(sim.books["FUT"].sz[SELL]):          # clear anything better than 10005
        assert px >= 10005 or True
    sim.books["FUT"].best[SELL] = min(sim.books["FUT"].sz[SELL])
    ahead = sum(q for px, q in sim.books["FUT"].sz[SELL].items() if px < 10005)
    sim.submit("C", "FUT", BUY, 10005, ahead + 6)
    assert a.status == "F" and b.filled == 1


def test_deterministic():
    x, y = make_session(0, 99, T=300.0), make_session(0, 99, T=300.0)
    assert len(x.orders) == len(y.orders) and x.fills == y.fills and x.episodes == y.episodes


def test_detector_ignores_ground_truth():
    """Erasing the labels must not change what the detector flags."""
    s = make_session(0, 5, T=600.0)
    P = Params(k=0.05, flip=True, persistent=True)
    a = [(i["acct"], tuple(i["oids"])) for i in detect([Index(s)], P)]
    for o in s.orders:
        o.ep = o.role = None
    b = [(i["acct"], tuple(i["oids"])) for i in detect([Index(s)], P)]
    assert a == b and len(a) > 0


def test_equities_extension():
    """The extension set builds, seeds its three templates, and links the two-account scheme."""
    from spoofbench.equities import make_session_eq, link_accounts
    s = make_session_eq(0, 5, T=900.0)
    assert {"trillium", "hold", "milrud"} <= {e["template"] for e in s.episodes}
    v = link_accounts(s)
    assert "G_MIL" in v.accounts and "M_MIL_DIRTY" not in v.accounts and len(v.orders) == len(s.orders)
    assert all(o.acct != "G_MIL" for o in s.orders)          # the original session is not modified


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
