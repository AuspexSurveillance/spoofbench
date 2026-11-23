"""Manipulation templates. Each one encodes the order sequence described in a public
enforcement document. SOURCES records where every pattern fact comes from; parameters the
documents do not state are sampled from the ranges noted beside them and are marked
"assumed" in SOURCES. The "stated" entries paraphrase or quote the cited documents; consult the
documents themselves before relying on them.

Every episode has a "faithful" form (parameters inside what the document describes) and an
"evasive" form (smaller size, slower cancel) used to measure where detection degrades.
"""
from .sim import BUY, SELL
from .accounts import Discretionary, MarketMaker

SOURCES = {
    "chen": {
        "document": "In re Tanius Technology, LLC, CFTC Docket No. 22-34 (Sept. 26, 2022)",
        "url": "https://www.cftc.gov/media/7696/enftaniusorder092622/download",
        "stated": ["one or more small orders (often between 1-5 lots) on one side",
                   "followed almost immediately by multiple 20-lot orders on the opposite side",
                   "cancelled most of these 20-lot orders within five seconds",
                   "occasionally repeat the process ... until he had induced a fill",
                   "over 1,000 separate occasions; 12 different futures contracts",
                   "Relevant Period October 1, 2020 to June 30, 2021; trader: Randy Chen, a Tanius employee"],
        "assumed": ["2-5 spoof orders per round, placed 0-2 ticks behind the touch",
                    "85% of cancels within 5 s of the fill, the rest within 12 s"],
    },
    "coscia": {
        "document": "In re Panther Energy Trading LLC and Michael J. Coscia, CFTC Docket No. 13-26 (July 22, 2013)",
        "url": "https://cftc.gov/idc/groups/public/%40lrenforcementactions/documents/legalpleading/enfpantherorder072213.pdf",
        "stated": ["a relatively small order on one side of the market at or near the best price (example: 17 contracts)",
                   "within a fraction of a second, relatively larger orders on the other side at three progressively closer prices",
                   "if the small order filled, the large orders were immediately cancelled",
                   "the algorithm would then enter the reverse sequence",
                   "hundreds of times in an individual futures contract in a single day",
                   "18 futures contracts on four CME Group exchanges, August 8 to October 18, 2011"],
        "assumed": ["each large order is 2-5x the small order", "cancel 5-100 ms after the fill; give up after 1-4 s"],
    },
    "oystacher": {
        "document": "CFTC v. Oystacher and 3Red Trading LLC, No. 1:15-cv-09196 (N.D. Ill.), complaint filed Oct. 19, 2015",
        "url": "https://cftc.gov/idc/groups/public/%40lrenforcementactions/documents/legalpleading/enfigorcomplnt101915.pdf",
        "stated": ["spoof orders at or near the best price that more than doubled the number of contracts offered or bid at those price levels or better",
                   "one to fourteen spoof orders per example",
                   "cancelled simultaneously within one second of entry (average durations about 0.61-0.75 s)",
                   "within 5 milliseconds, an aggressive 'flip' order on the opposite side at the same or a better price",
                   "at least 1,316 flips on at least 51 trading days, December 2011 to January 2014"],
        "assumed": ["spoof total is 1-3x the quantity displayed at the price", "flip order is 30-60% of the spoof quantity"],
    },
    "sarao": {
        "document": "CFTC v. Nav Sarao Futures Limited PLC and Navinder Singh Sarao (N.D. Ill.), complaint filed Apr. 17, 2015; CFTC Release 7156-15",
        "url": "https://www.cftc.gov/PressRoom/PressReleases/7156-15",
        "stated": ["four to six exceptionally large sell orders, each one price level from the other",
                   "modified so they remained at least three or four price levels from the best asking price",
                   "the vast majority were cancelled without resulting in any transactions",
                   "cycled on and off several times during a typical trading day; used on over 400 trading days, April 2010 to April 2015"],
        "assumed": ["each layer is 1.5-4x the average displayed size of a far level", "cycles last 40-240 s",
                    "the account works small passive orders on the opposite side during a cycle"],
    },
    "lebental": {
        "document": "In re Sidney Lebental, CFTC Docket No. 26-01 (May 1, 2026)",
        "url": "https://www.cftc.gov/media/13841/ENFLebentalOrder050126/download",
        "stated": ["a genuine order or orders on BrokerTec for cash Treasuries",
                   "spoof orders in Treasury futures (most frequently the Ultra Bond) on the opposite side of the market",
                   "after the genuine orders were fully or partially filled, the spoof orders were cancelled shortly thereafter",
                   "approximately 50 occasions, January to September 2019"],
        "assumed": ["spoof quantity is 0.5-2x the displayed size at the futures touch", "cancel 0.2-4 s after the cash fill"],
    },
}


class Episode:
    def __init__(self, sim, acct, template, evasive):
        self.sim, self.acct = sim, acct
        self.rec = dict(id=len(sim.episodes), acct=acct, template=template, evasive=bool(evasive),
                        t0=sim.t, t1=None, spoof=[], genuine=[], filled=False, params={})
        sim.episodes.append(self.rec)

    def spoof(self, inst, side, px, qty):
        o = self.sim.submit(self.acct, inst, side, px, qty, ep=self.rec["id"], role="spoof")
        self.rec["spoof"].append(o.oid)
        return o

    def genuine(self, inst, side, px, qty, cb=None):
        o = self.sim.submit(self.acct, inst, side, px, qty, ep=self.rec["id"], role="genuine", cb=cb)
        self.rec["genuine"].append(o.oid)
        return o

    def close(self):
        self.rec["t1"] = self.sim.t


def chen(sim, acct, done, evasive=False):
    r = sim.rng
    g = r.choice((BUY, SELL))
    ep = Episode(sim, acct, "chen", evasive)
    st = {"filled": False, "closed": False, "round": 0, "spoofs": []}

    def finish():
        if st["closed"]:
            return
        st["closed"] = True
        for s in st["spoofs"]:
            sim.cancel(s)
        sim.cancel(gen)
        ep.close()
        done()

    def on_fill(o, x):
        if st["filled"] or st["closed"]:
            return
        st["filled"] = ep.rec["filled"] = True
        if evasive:
            lat = r.uniform(0.2, 20.0)
        else:
            lat = r.uniform(0.2, 5.0) if r.random() < 0.85 else r.uniform(5.0, 12.0)
        ep.rec["params"]["latency"] = lat
        sim.after(lat, finish)

    def place():
        if st["filled"] or st["closed"]:
            return
        lot = r.choice((5, 10, 20)) if evasive else 20
        m = r.randint(1, 3) if evasive else r.randint(2, 5)
        ep.rec["params"]["spoof_qty"] = lot * m
        for _ in range(m):
            px = sim.touch("FUT", -g) + g * r.randint(0, 2)
            st["spoofs"].append(ep.spoof("FUT", -g, px, lot))
        sim.after(r.uniform(2.0, 6.0), timeout, st["round"])

    def timeout(rnd):
        if st["filled"] or st["closed"] or rnd != st["round"]:
            return
        for s in st["spoofs"]:
            sim.cancel(s)
        st["spoofs"] = []
        st["round"] += 1
        if st["round"] < 3 and r.random() < 0.6:
            sim.after(r.uniform(0.2, 1.0), place)
        else:
            finish()

    gen = ep.genuine("FUT", g, sim.touch("FUT", g), r.randint(1, 5), cb=on_fill)
    sim.after(r.uniform(0.05, 0.6), place)


def coscia(sim, acct, done, evasive=False, g=None, depth=0):
    r = sim.rng
    g = g or r.choice((BUY, SELL))
    ep = Episode(sim, acct, "coscia", evasive)
    st = {"filled": False, "closed": False, "spoofs": []}

    def finish():
        if st["closed"]:
            return
        st["closed"] = True
        for s in st["spoofs"]:
            sim.cancel(s)
        sim.cancel(gen)
        ep.close()
        if depth < 1 and r.random() < 0.7:           # the reverse sequence
            sim.after(r.uniform(0.05, 0.3), coscia, sim, acct, done, evasive, -g, depth + 1)
        else:
            done()

    def on_fill(o, x):
        if st["filled"] or st["closed"]:
            return
        st["filled"] = ep.rec["filled"] = True
        lat = r.uniform(0.5, 10.0) if evasive else r.uniform(0.005, 0.1)
        ep.rec["params"]["latency"] = lat
        sim.after(lat, finish)

    def place():
        if st["filled"] or st["closed"]:
            return
        mult = r.uniform(0.5, 2.0) if evasive else r.uniform(2.0, 5.0)
        t = sim.touch("FUT", -g)
        tot = 0
        for k in (2, 1, 0):                          # three prices, progressively closer to the touch
            q = max(1, round(gq * mult))
            tot += q
            st["spoofs"].append(ep.spoof("FUT", -g, t + g * k, q))
        ep.rec["params"]["spoof_qty"] = tot
        sim.after(r.uniform(1.0, 4.0), finish)

    gq = r.randint(5, 20)
    gen = ep.genuine("FUT", g, sim.touch("FUT", g), gq, cb=on_fill)
    sim.after(r.uniform(0.01, 0.3), place)


def oystacher(sim, acct, done, evasive=False):
    r = sim.rng
    g = r.choice((BUY, SELL))                        # side of the aggressive flip order
    s = -g
    ep = Episode(sim, acct, "oystacher", evasive)
    px = sim.touch("FUT", s)
    there = sim.books["FUT"].sz[s].get(px, 0)
    total = max(10, round(there * (r.uniform(0.3, 1.0) if evasive else r.uniform(1.0, 3.0))))
    n = min(14, 1 + int(r.expovariate(1 / 2.5)))
    base, extra = divmod(total, n)
    spoofs = [ep.spoof("FUT", s, px, base + (1 if i < extra else 0)) for i in range(n) if base + (1 if i < extra else 0) > 0]
    ep.rec["params"]["spoof_qty"] = total

    def on_fill(o, x):
        ep.rec["filled"] = True

    def flip():
        for o in spoofs:
            sim.cancel(o)
        sim.after(r.uniform(0.0005, 0.005), enter)

    def enter():
        o = ep.genuine("FUT", g, px, max(1, round(total * r.uniform(0.3, 0.6))), cb=on_fill)
        sim.after(r.uniform(1.0, 4.0), end, o)

    def end(o):
        sim.cancel(o)
        ep.close()
        done()

    sim.after(r.uniform(1.0, 4.0) if evasive else r.uniform(0.3, 0.9), flip)


def sarao(sim, acct, done, evasive=False):
    r = sim.rng
    s = SELL if r.random() < 0.8 else BUY
    g = -s
    ep = Episode(sim, acct, "sarao", evasive)
    nl, start = r.randint(4, 6), r.choice((3, 4))
    far = sim.books["FUT"].levels(s)[2:8]
    avg = max(5.0, sum(far) / len(far))
    mult = (0.3, 1.0) if evasive else (1.5, 4.0)
    sizes = [max(5, round(avg * r.uniform(*mult))) for _ in range(nl)]
    ep.rec["params"]["spoof_qty"] = sum(sizes)
    st = {"on": True, "ref": None, "orders": [], "gen": []}

    def lay(replace):
        t = sim.touch("FUT", s)
        for o in st["orders"]:
            sim.cancel(o, replace=replace)
        st["orders"] = [ep.spoof("FUT", s, t - s * (start + i), q) for i, q in enumerate(sizes)]
        st["ref"] = t

    def watch():
        if not st["on"]:
            return
        if sim.touch("FUT", s) != st["ref"]:
            lay(True)
        sim.after(r.uniform(0.2, 0.5), watch)

    def on_fill(o, x):
        ep.rec["filled"] = True

    def work():
        if not st["on"]:
            return
        o = ep.genuine("FUT", g, sim.touch("FUT", g), r.randint(5, 20), cb=on_fill)
        st["gen"].append(o)
        sim.after(r.uniform(5, 15), sim.cancel, o)
        sim.after(r.uniform(5, 20), work)

    def end():
        st["on"] = False
        for o in st["orders"] + st["gen"]:
            sim.cancel(o)
        ep.close()
        done()

    lay(False)
    sim.after(r.uniform(0.2, 0.5), watch)
    sim.after(r.uniform(1, 5), work)
    sim.after(r.uniform(40, 240), end)


def lebental(sim, acct, done, evasive=False):
    r = sim.rng
    g = r.choice((BUY, SELL))
    ep = Episode(sim, acct, "lebental", evasive)
    st = {"filled": False, "closed": False, "spoofs": []}

    def finish():
        if st["closed"]:
            return
        st["closed"] = True
        for o in st["spoofs"]:
            sim.cancel(o)
        sim.cancel(gen)
        ep.close()
        done()

    def on_fill(o, x):
        if st["filled"] or st["closed"]:
            return
        st["filled"] = ep.rec["filled"] = True
        lat = r.uniform(0.2, 20.0) if evasive else r.uniform(0.2, 4.0)
        ep.rec["params"]["latency"] = lat
        sim.after(lat, finish)

    def place():
        if st["filled"] or st["closed"]:
            return
        t = sim.touch("FUT", -g)
        there = sim.books["FUT"].sz[-g].get(t, 0)
        total = max(10, round(there * (r.uniform(0.15, 0.5) if evasive else r.uniform(0.5, 2.0))))
        n = r.randint(1, 3)
        base, extra = divmod(total, n)
        for i in range(n):
            q = base + (1 if i < extra else 0)
            if q > 0:
                st["spoofs"].append(ep.spoof("FUT", -g, t + g * r.randint(0, 1), q))
        ep.rec["params"]["spoof_qty"] = total
        sim.after(r.uniform(5, 15), finish)

    gen = ep.genuine("CASH", g, sim.touch("CASH", g), r.randint(10, 40), cb=on_fill)
    sim.after(r.uniform(0.05, 0.5), place)


TEMPLATES = {"chen": chen, "coscia": coscia, "oystacher": oystacher, "sarao": sarao, "lebental": lebental}


class TemplateRunner:
    """Mixin: runs one template at a given rate per session on top of the account's normal activity."""
    truth = "manip"

    def _init_tpl(self, template, per_session, evasive_share=0.3):
        self.template, self.per_session, self.evasive_share = template, per_session, evasive_share

    def start(self, sim):
        super().start(sim)
        self.gap = sim.T / self.per_session
        sim.after(self.rng.expovariate(1.0 / self.gap), self.next)

    def next(self):
        if self.sim.t > self.sim.T - 30:
            return
        TEMPLATES[self.template](self.sim, self.name, self.done, self.rng.random() < self.evasive_share)

    def done(self):
        self.sim.after(self.rng.expovariate(1.0 / self.gap), self.next)


class Manipulator(TemplateRunner, Discretionary):
    """A discretionary account that also manipulates."""

    def __init__(self, name, template, per_session, evasive_share=0.3):
        Discretionary.__init__(self, name)
        self._init_tpl(template, per_session, evasive_share)


class ManipulatingMM(TemplateRunner, MarketMaker):
    """A market-making account that also manipulates: the hard positive, because its legitimate
    two-sided quoting and re-quoting surround every episode."""

    def __init__(self, name, template, per_session, evasive_share=0.3, **mm):
        MarketMaker.__init__(self, name, **mm)
        self._init_tpl(template, per_session, evasive_share)
