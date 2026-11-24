"""Extension set (v0.4): equities layering sequences from SEC and FINRA documents.

Kept apart from the five futures templates so that the v0.3 sessions, and every number in the
paper, stay reproducible. Nothing here runs unless run_equities.py is used.

Sizes are in round lots of 100 shares. The market is the same single simulated book with a
one-tick spread, so two features of the equities cases are not modelled: orders placed inside a
wide spread that move the national best bid or offer, and orders spread across venues.

SOURCES_EQ follows the convention of templates.SOURCES: "stated" paraphrases or quotes the cited
document, "assumed" lists what the template adds. Consult the documents before relying on them.
"""
import copy

from .sim import Sim, BUY, SELL
from .accounts import Discretionary
from .bench import Session, roster
from .templates import Episode, Manipulator, TEMPLATES

SOURCES_EQ = {
    "trillium": {
        "document": "FINRA news release, 'FINRA Sanctions Trillium Brokerage Services, LLC, Director of Trading, "
                    "Chief Compliance Officer, and Nine Traders $2.26 Million for Illicit Equities Trading Strategy' (Sept. 13, 2010)",
        "url": "https://www.finra.org/media-center/news-releases/2010/finra-sanctions-trillium-brokerage-services-llc-director-trading-chief",
        "stated": ["entered numerous layered, non-bona fide market moving orders to generate selling or buying interest in specific stocks",
                   "often in substantial size relative to a stock's overall legitimate pending order volume",
                   "induced other market participants to enter orders to execute against limit orders previously entered by the Trillium traders",
                   "once their orders were filled, the traders would then immediately cancel the non-bona fide orders",
                   "nine proprietary traders; over 46,000 instances; NASDAQ and NYSE Arca"],
        "assumed": ["the limit order rests at the best price", "3-8 layers entered over 0.5-3 s, stepping toward the best price",
                    "layers total 1-3x the displayed size within three ticks", "cancel 0.1-1 s after the fill"],
    },
    "hold": {
        "document": "In re Hold Brothers On-Line Investment Services, LLC, et al., SEC Admin. Proc. File No. 3-15046, "
                    "Exchange Act Release No. 67924 (Sept. 25, 2012)",
        "url": "https://www.sec.gov/litigation/admin/2012/34-67924.pdf",
        "stated": ["example of June 4, 2010 in W.W. Grainger: an offer to sell 1,000 shares, then within about 160 milliseconds "
                   "eleven buy orders totaling 2,600 shares at rising prices",
                   "the sell order was filled; all open buy orders were cancelled about 0.6 s later",
                   "about five seconds later the same sequence on the opposite side (buy 1,000; eleven sell orders totaling 2,600 at falling prices)",
                   "the round trip took under seven seconds",
                   "more than 325,000 layered transactions and more than 8 million layered orders, January 2009 to September 2010"],
        "assumed": ["layers rise from four ticks behind the best price to the best price (in the example they were inside a ten-cent spread "
                    "and raised the best bid, which a one-tick spread cannot reproduce)",
                    "layers total 2.2-3.0x the genuine order (2.6x in the example); 9-12 layers", "the reverse leg follows in 80% of filled episodes",
                    "an unfilled attempt is abandoned after 2-6 s"],
    },
    "milrud": {
        "document": "SEC v. Aleksandr Milrud, No. 15-cv-00237 (D.N.J.), complaint filed Jan. 13, 2015; SEC Litigation Release No. 23173",
        "url": "https://www.sec.gov/litigation/litreleases/2015/lr23173.htm",
        "stated": ["traders were given at least two accounts: one for the 'dirty work' of layering, the other for 'clean' trades "
                   "at the prices the first account's orders had affected",
                   "they limited the number of trades and price changes to avoid attention",
                   "traders chiefly in China and Korea; since at least January 2013"],
        "assumed": ["the order sequence itself (the release does not describe it): 3-6 layers in the first account totaling 2-4x "
                    "the genuine order in the second, entered over 0.5-2 s, cancelled 0.5-3 s after the fill"],
    },
}

PARTNER = {"M_MIL_DIRTY": "M_MIL_CLEAN"}                 # layering account -> account that takes the fill
GROUPS = {"G_MIL": ("M_MIL_DIRTY", "M_MIL_CLEAN")}       # accounts a firm could link if it knew they were under common control


def _run(sim, ep, gen_acct, g, gq, plan, lat_fn, timeout, after):
    """Common body: genuine order on side g, layers on the other side from `plan`
    (a list of (delay, ticks behind the touch, quantity)), cancel after the fill."""
    r, s = sim.rng, -g
    st = {"filled": False, "closed": False, "spoofs": []}

    def finish():
        if st["closed"]:
            return
        st["closed"] = True
        for o in st["spoofs"]:
            sim.cancel(o)
        sim.cancel(gen)
        ep.close()
        after(st["filled"])

    def on_fill(o, x):
        if st["filled"] or st["closed"]:
            return
        st["filled"] = ep.rec["filled"] = True
        lat = lat_fn()
        ep.rec["params"]["latency"] = lat
        sim.after(lat, finish)

    def layer(k, q, ref):
        if not st["closed"]:
            st["spoofs"].append(ep.spoof("FUT", s, ref - s * k, q))

    def give_up():
        if not st["filled"]:
            finish()

    gen = sim.submit(gen_acct, "FUT", g, sim.touch("FUT", g), gq, ep=ep.rec["id"], role="genuine", cb=on_fill)
    ep.rec["genuine"].append(gen.oid)
    ref = sim.touch("FUT", s)
    for dt, k, q in plan:
        sim.after(dt, layer, k, q, ref)
    sim.after(timeout, give_up)


def _split(total, n):
    base, extra = divmod(total, n)
    return [base + (1 if i < extra else 0) for i in range(n)]


def trillium(sim, acct, done, evasive=False):
    r = sim.rng
    g = r.choice((BUY, SELL))
    ep = Episode(sim, acct, "trillium", evasive)
    depth = sim.books["FUT"].depth(-g, 3)
    total = max(10, round(depth * (r.uniform(0.3, 1.0) if evasive else r.uniform(1.0, 3.0))))
    n = r.randint(2, 4) if evasive else r.randint(3, 8)
    span = r.uniform(0.5, 3.0)
    plan = [(0.05 + span * i / n, min(4, n - 1 - i), q) for i, q in enumerate(_split(total, n))]
    ep.rec["params"]["spoof_qty"] = total
    lat = (lambda: r.uniform(2.0, 15.0)) if evasive else (lambda: r.uniform(0.1, 1.0))
    _run(sim, ep, acct, g, r.randint(5, 20), plan, lat, span + r.uniform(5, 15), lambda filled: done())


def hold(sim, acct, done, evasive=False, g=None, leg=0):
    r = sim.rng
    g = g or r.choice((BUY, SELL))
    ep = Episode(sim, acct, "hold", evasive)
    gq = r.choice((5, 10)) if evasive else 10
    total = max(3, round(gq * (r.uniform(1.2, 2.0) if evasive else r.uniform(2.2, 3.0))))
    n = min(total, r.randint(3, 5) if evasive else r.randint(9, 12))
    span = r.uniform(0.1, 0.3)
    plan = [(0.01 + span * i / n, 4 - (5 * i) // n, q) for i, q in enumerate(_split(total, n))]
    ep.rec["params"].update(spoof_qty=total, ratio=total / gq)
    lat = (lambda: r.uniform(2.0, 10.0)) if evasive else (lambda: r.uniform(0.4, 0.8))

    def after(filled):
        if leg == 0 and filled and r.random() < 0.8:      # the same sequence on the opposite side
            sim.after(r.uniform(3.0, 6.0), hold, sim, acct, done, evasive, -g, 1)
        else:
            done()

    _run(sim, ep, acct, g, gq, plan, lat, r.uniform(2.0, 6.0), after)


def milrud(sim, acct, done, evasive=False):
    r = sim.rng
    g = r.choice((BUY, SELL))
    ep = Episode(sim, acct, "milrud", evasive)
    gq = r.randint(5, 20)
    total = max(3, round(gq * (r.uniform(1.0, 2.0) if evasive else r.uniform(2.0, 4.0))))
    n = min(total, r.randint(2, 3) if evasive else r.randint(3, 6))
    span = r.uniform(0.5, 2.0)
    plan = [(0.05 + span * i / n, min(3, n - 1 - i), q) for i, q in enumerate(_split(total, n))]
    ep.rec["params"].update(spoof_qty=total, clean=PARTNER[acct])
    lat = (lambda: r.uniform(3.0, 15.0)) if evasive else (lambda: r.uniform(0.5, 3.0))
    _run(sim, ep, PARTNER[acct], g, gq, plan, lat, span + r.uniform(5, 15), lambda filled: done())


TEMPLATES.update(trillium=trillium, hold=hold, milrud=milrud)


class CleanAccount(Discretionary):
    """The second account of the two-account scheme: it holds the genuine orders and nothing else unusual."""
    truth = "manip"
    template = "milrud"


def roster_eq():
    return roster() + [Manipulator("M_TRIL", "trillium", 20), Manipulator("M_HOLD", "hold", 40),
                       Manipulator("M_MIL_DIRTY", "milrud", 20), CleanAccount("M_MIL_CLEAN")]


def make_session_eq(sid, seed, T=1800.0):
    sim = Sim(seed, T=T)
    agents = roster_eq()
    sim.agents = agents
    sim.run()
    return Session(sid, sim, agents)


class _View:
    pass


def link_accounts(s, groups=GROUPS):
    """The same session with each group of accounts merged into one, as a firm would see it after
    linking accounts under common control. Orders of other accounts are shared, not copied."""
    alias = {m: grp for grp, ms in groups.items() for m in ms}
    v = _View()
    v.sid, v.T, v.fills, v.episodes = s.sid, s.T, s.fills, s.episodes
    v.orders = []
    for o in s.orders:
        if o.acct in alias:
            o = copy.copy(o)
            o.acct = alias[o.acct]
        v.orders.append(o)
    v.by_oid = {o.oid: o for o in v.orders}
    v.accounts = {k: a for k, a in s.accounts.items() if k not in alias}
    for grp, ms in groups.items():
        v.accounts[grp] = dict(s.accounts[ms[0]])
    return v
