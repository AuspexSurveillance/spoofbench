"""Why the Hold Brothers template is missed: which test removes its episodes (extension set, v0.4).

    python tools/diag_hold.py [--test 30] [--seed 20261123]
"""
import argparse, json, os, statistics, sys
from dataclasses import replace
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from spoofbench.detect import Index, Params, detect
from spoofbench.equities import make_session_eq
from run_equities import hits

ap = argparse.ArgumentParser()
ap.add_argument("--test", type=int, default=30)
ap.add_argument("--base", type=int, default=30)
ap.add_argument("--seed", type=int, default=20261123)
ap.add_argument("--res", default="results_ext/results_equities.json")
ap.add_argument("--out", default="results_ext/diag_hold.json")
a = ap.parse_args()
test = [Index(make_session_eq(a.base + i, a.seed + 10000 + i)) for i in range(a.test)]
chosen = json.load(open(a.res))["class_k"]["k_by_class"]
accts = test[0].s.accounts
C = Params(flip=True, persistent=True, k_by_acct=tuple(sorted((x, chosen[v["kind"]]) for x, v in accts.items())))
es = [(ix.s.sid, e["id"]) for ix in test for e in ix.s.episodes
      if e["template"] == "hold" and e["spoof"] and e["filled"] and not e["evasive"]]
N = replace(C, k_by_acct=None, k=0.0)                      # no size test beyond q_min
cfg = {"reference": C, "no exclusions": replace(C, exclusions=False), "no size test": N,
       "no size test, no exclusions": replace(N, exclusions=False),
       "no size test, no exclusions, d=4": replace(N, exclusions=False, d=4),
       "no size test, d=4": replace(N, d=4)}
found = {}
for name, P in cfg.items():
    h = hits(test, detect(test, P))
    found[name] = sum(x in h for x in es)
out = dict(episodes=len(es), found=found)
qty, need = [], []
for ix in test:
    for e in ix.s.episodes:
        if e["template"] == "hold" and e["spoof"] and e["filled"] and not e["evasive"]:
            os_ = [ix.s.by_oid[o] for o in e["spoof"]]
            keep = [o for o in os_ if o.dist <= 3]
            if keep:
                first = min(keep, key=lambda o: o.t_in)
                qty.append(sum(o.qty for o in keep))
                need.append(chosen["prop"] * sum(first.depth[:4]))
out["median_layer_lots_within_3_ticks"] = statistics.median(qty)
out["median_lots_required_by_class_threshold"] = round(statistics.median(need), 1)
out["share_meeting_size_test"] = round(sum(q >= n for q, n in zip(qty, need)) / len(qty), 3)
json.dump(out, open(a.out, "w"), indent=1)
print(json.dumps(out, indent=1))
