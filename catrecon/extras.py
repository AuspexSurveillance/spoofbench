"""Further measurements for the paper: sampled review, clock offsets under latency spikes, and
the share of seeded errors that the CAT error rate would show. Writes results/extras.json."""
import json, random, statistics
from collections import defaultdict
import catrecon as C
from spoofbench.bench import make_session

SEED = 20261123
rng = random.Random(SEED)
s = make_session(0, SEED)
oms, master, cat, acks, cxl = C.build(s, rng)
fdids = {m["fdid"] for m in master.values()}
R = {}

# 1. share of erroneous orders that the CAT feedback would count
c2, o2, m2, lab = C.inject(oms, master, cat, rng, 200)
f = C.detect_cat(c2, acks, fdids)
R["error_rate"] = dict(orders=len(oms), erroneous_orders=len(lab), flagged_by_cat=sum(o in f for o in lab),
                       true_rate_pct=round(100 * len(lab) / len(oms), 2), cat_rate_pct=round(100 * sum(o in f for o in lab) / len(oms), 2))

# 2. sampled review against the firm's records: chance that a kind of error is seen at least once
report_kinds = [n for n, v in C.ERRORS.items() if v[0] == "report"]
samp = {}
for k in (5, 50, 200):
    c3, o3, m3, l3 = C.inject(oms, master, cat, rng, k, only=report_kinds)
    full = C.detect_oms(c3, o3, m3)
    by_kind = defaultdict(list)
    for oid, n in l3.items(): by_kind[n].append(oid)
    row = {}
    for frac in (0.001, 0.005, 0.01, 0.05, 0.10, 0.25, 1.0):
        seen = tot = 0
        for trial in range(200):
            pick = set(rng.sample([r["oid"] for r in o3], max(1, int(frac * len(o3))))) if frac < 1 else None
            for n, oids in by_kind.items():
                tot += 1
                seen += any((pick is None or o in pick) and o in full for o in oids)
        row[f"{100 * frac:g}%"] = round(seen / tot, 3)
    samp[str(k)] = row
R["sampled_review"] = samp

# 3. clock offsets when exchange latency has spikes: 3% of acknowledgements take 2 to 20 ms
def spiky(acks_, rng_):
    out = []
    for a in acks_:
        a = dict(a); base = next(r for r in [by[a["_oid"]]])
        a["t"] = base["t_in"] + (rng_.uniform(0.002, 0.020) if rng_.random() < 0.03 else rng_.uniform(0.0002, 0.002))
        out.append(a)
    return out
by = {r["oid"]: r for r in oms}
acks_s = spiky(acks, rng)
lat0 = [a["t"] - by[a["_oid"]]["t_in"] for a in acks_s]
base_med = statistics.median(lat0)
clock = {}
for upper in (0.0035, 0.010, 0.025):
    C.WIN = (-0.0010, upper)
    false_flags = len(C.detect_exch(cat, acks_s, cxl))
    row = {"false_flags_per_10000_orders": round(1e4 * false_flags / len(oms), 1)}
    for d in (-0.050, -0.020, -0.005, -0.002, 0.002, 0.005, 0.020, 0.050):
        c4, o4, m4, l4 = C.inject(oms, master, cat, rng, 300, drift=d, only=("clock_drift",))
        ff = C.detect_exch(c4, acks_s, cxl)
        row[f"{1000 * d:+g} ms"] = round(sum(o in ff for o in l4) / len(l4), 3)
    clock[f"window to +{1000 * upper:g} ms"] = row
C.WIN = (-0.0010, 0.0035)
R["clock_per_event"] = clock
# host-level test: median acknowledgement delay of a host's events against the clean median
host = {}
for n_ev in (20, 100, 500):
    row = {}
    for d in (0.0001, 0.0002, 0.0005, 0.001):
        hit = 0
        for trial in range(300):
            samp_l = rng.sample(lat0, n_ev)
            hit += abs(statistics.median(x - d for x in samp_l) - base_med) > 0.00015
        row[f"{1000 * d:g} ms"] = round(hit / 300, 3)
    fa = sum(abs(statistics.median(rng.sample(lat0, n_ev)) - base_med) > 0.00015 for _ in range(300)) / 300
    row["false alarm"] = round(fa, 3)
    host[str(n_ev)] = row
R["clock_host_median"] = dict(clean_median_ms=round(1000 * base_med, 3), threshold_ms=0.15, by_events=host)
json.dump(R, open("results/extras.json", "w"), indent=1)
print(json.dumps(R, indent=1))
