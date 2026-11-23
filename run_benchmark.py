"""Run the benchmark end to end and write results/results.json and results/results.md.

    python run_benchmark.py [--base 30] [--test 30] [--seed 20261123] [--dump DIR]
"""
import argparse, json, os, time
from collections import defaultdict
from dataclasses import replace

from spoofbench.bench import make_session, dump
from spoofbench.detect import Index, Params, detect, score, calibrate, evaluate, persistent, LOOSE_LAT

FEATS = ["Q", "depth", "ratio", "asym", "lat", "lat_min", "levels", "n_orders", "life", "cross", "gen_aggr",
         "sym", "again", "own_ratio", "rep"]
GRID = (0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0)


def pooled(rec, evasive=False):
    d = sum(v[0] for k, v in rec.items() if k.endswith("/evasive") == evasive)
    n = sum(v[1] for k, v in rec.items() if k.endswith("/evasive") == evasive)
    return d, n


def summarize(name, idx, P, n_legit):
    r = score(idx, detect(idx, P))
    r["name"] = name
    r["false_cases_per_100_legit_account_sessions"] = round(100.0 * sum(
        v for k, v in r["false_cases"].items() if k != "manip-acct") / (n_legit * len(idx)), 2)
    r["cases_per_session"] = round(r["cases"] / len(idx), 2)
    d, n = pooled(r["recall"])
    r["recall_faithful"] = round(d / n, 3) if n else None
    d, n = pooled(r["recall"], True)
    r["recall_evasive"] = round(d / n, 3) if n else None
    return r


def loose_instances(idx):
    """Every fill-then-cancel candidate with almost no thresholds: the pool the ranking model scores."""
    P = Params(k=0.0, q_min=5, d=8, t_cancel=LOOSE_LAT, f_max=0.5, n=1, exclusions=False, flip=True)
    rows = []
    for ix in idx:
        inst = [i for i in (evaluate(c, ix, P) for c in ix.cands) if i]
        rep = defaultdict(int)
        for i in inst:
            rep[i["acct"]] += 1
        for i in inst:
            i["rep"] = rep[i["acct"]]
            eps = {ix.s.by_oid[o].ep for o in i["oids"] if ix.s.by_oid[o].role == "spoof"}
            i["true"], i["eps"] = int(bool(eps)), eps
            rows.append(i)
    return rows


def budget_eval(idx, rows, key, budgets):
    """Take the top-N instances per session by `key`; report episode recall (fill-triggered templates) and precision."""
    by_s = defaultdict(list)
    for r in rows:
        by_s[r["sid"]].append(r)
    total = {(ix.s.sid, e["id"]): e for ix in idx for e in ix.s.episodes
             if e["spoof"] and e["filled"] and e["template"] != "sarao"}
    out = {}
    for N in budgets:
        hit, tp, n = set(), 0, 0
        for sid, rs in by_s.items():
            for r in sorted(rs, key=key, reverse=True)[:N]:
                n += 1
                tp += r["true"]
                hit.update((sid, e) for e in r["eps"])
        fa = [k for k in total if not total[k]["evasive"]]
        out[N] = dict(recall_faithful=round(sum(k in hit for k in fa) / max(1, len(fa)), 3),
                      recall_all=round(sum(k in hit for k in total) / max(1, len(total)), 3), precision=round(tp / max(1, n), 3))
    return out


def experiments(base, test, grid=GRID):
    """All experiments on a list of baseline Index objects and a list of test Index objects."""
    accts = test[0].s.accounts
    n_legit = sum(v["truth"] == "legit" for v in accts.values())
    kinds = {k: v["kind"] for k, v in accts.items()}
    R = dict(meta=dict(base_sessions=len(base), test_sessions=len(test), session_seconds=test[0].s.T,
                       accounts=len(accts), legit_accounts=n_legit,
                       firm_orders_test=sum(len(ix.s.orders) for ix in test),
                       candidates_test=sum(len(ix.cands) for ix in test)))
    eps = [e for ix in test for e in ix.s.episodes]
    R["meta"]["episodes_test"] = len(eps)
    R["meta"]["episodes_with_fill"] = sum(1 for e in eps if e["spoof"] and e["filled"])
    R["meta"]["attempts_without_fill"] = sum(1 for e in eps if e["spoof"] and not e["filled"])

    D = Params()
    X = replace(D, flip=True, persistent=True)
    S = lambda name, P: summarize(name, test, P, n_legit)

    # 1. the literal procedures at the Appendix C defaults
    R["literal_defaults"] = S("5.1/5.2/5.8 literal, Appendix C defaults", D)

    # 2. fixed imbalance multiple, both extensions on
    R["fixed_k"] = [S(f"fixed k={k}", replace(X, k=k)) for k in grid]

    # 3. Section 6.1 read literally: 99.5th percentile of the account's own entry imbalance
    ks = calibrate(base)
    R["self_quantile"] = S("self-quantile 99.5%", replace(X, k_by_acct=ks))
    R["self_quantile"]["k"] = {k: round(v, 3) for k, v in ks}

    # 4. Sections 6.2/6.3: per-class multiple chosen on the baseline sessions as the smallest k whose
    #    false cases stay within budget (2 per 100 account-sessions of that class)
    chosen, cache = {}, {}
    for k in grid:
        fl = detect(base, replace(X, k=k))
        score(base, fl)
        bad = defaultdict(lambda: [0, 0])
        for i in fl:
            bad[(i["acct"], i["sid"])][i["true"]] += 1
        cache[k] = bad
    for kd in sorted(set(kinds.values())):
        members = [x for x in accts if kinds[x] == kd and accts[x]["truth"] == "legit"]
        for k in grid:
            fc = sum(1 for (ac, sid), v in cache[k].items() if ac in members and v[1] == 0)
            if 100.0 * fc / max(1, len(members) * len(base)) <= 2.0:
                chosen[kd] = k
                break
        else:
            chosen[kd] = grid[-1]
    kc = tuple(sorted((x, chosen[kinds[x]]) for x in accts))
    C = replace(X, k_by_acct=kc)
    R["class_k"] = S("per-class k from seeded baseline", C)
    R["class_k"]["k_by_class"] = chosen

    # 5. ablations around the per-class configuration
    R["ablations"] = [S("per-class k (reference)", C), S("no flip extension", replace(C, flip=False)),
                      S("no persistent-layering extension", replace(C, persistent=False)),
                      S("no cross-instrument alignment", replace(C, cross=False)),
                      S("no exclusions", replace(C, exclusions=False)),
                      S("fixed k=0.05 (for comparison)", replace(X, k=0.05)),
                      S("fixed k=0.05, no exclusions", replace(X, k=0.05, exclusions=False)),
                      S("repetition n=1", replace(C, n=1)),
                      S("repetition 3 within 5 sessions", replace(C, P_sessions=5))]

    # 6. supervised ranking of loose candidates, trained on the seeded baseline sessions
    try:
        import numpy as np
        from sklearn.ensemble import HistGradientBoostingClassifier
        from sklearn.metrics import average_precision_score
        tr, te = loose_instances(base), loose_instances(test)
        f = lambda rows: np.array([[r[c] for c in FEATS] for r in rows], dtype=float)
        m = HistGradientBoostingClassifier(max_depth=4, max_iter=200, learning_rate=0.1, random_state=0)
        m.fit(f(tr), np.array([r["true"] for r in tr]))
        p = m.predict_proba(f(te))[:, 1]
        for r, s in zip(te, p):
            r["score"] = float(s)
        y = np.array([r["true"] for r in te])
        budgets = (5, 10, 20, 40)
        rule = [i for i in detect(test, replace(C, persistent=False))]
        score(test, rule)
        for i in rule:
            i["eps"] = {next(ix.s for ix in test if ix.s.sid == i["sid"]).by_oid[o].ep for o in i["oids"]
                        if next(ix.s for ix in test if ix.s.sid == i["sid"]).by_oid[o].role == "spoof"}
        R["ranking"] = dict(train_candidates=len(tr), train_true=int(sum(r["true"] for r in tr)),
                            test_candidates=len(te), test_true=int(y.sum()),
                            average_precision=dict(model=round(float(average_precision_score(y, p)), 3),
                                                   by_imbalance_ratio=round(float(average_precision_score(y, [r["ratio"] for r in te])), 3),
                                                   by_size_asymmetry=round(float(average_precision_score(y, [r["asym"] for r in te])), 3)),
                            top_n_per_session=dict(model=budget_eval(test, te, lambda r: r["score"], budgets),
                                                   by_imbalance_ratio=budget_eval(test, te, lambda r: r["ratio"], budgets),
                                                   by_size_asymmetry=budget_eval(test, te, lambda r: r["asym"], budgets)),
                            rule_instances_per_session=round(len(rule) / len(test), 1),
                            rule_at_its_own_volume=budget_eval(test, rule, lambda r: r["ratio"], (10 ** 6,))[10 ** 6])
        N = max(1, round(len(rule) / len(test)))
        R["ranking"]["model_at_rule_volume"] = dict(N=N, **budget_eval(test, te, lambda r: r["score"], (N,))[N])
        # 7. where detection degrades: chen episodes by cancel latency and by spoof size, rule vs model at N
        hit_rule = {(i["sid"], e) for i in rule for e in i["eps"]}
        by_s = defaultdict(list)
        for r in te:
            by_s[r["sid"]].append(r)
        hit_model = {(sid, e) for sid, rs in by_s.items() for r in sorted(rs, key=lambda r: r["score"], reverse=True)[:N] for e in r["eps"]}
        bins = dict(latency=((0, 1), (1, 2.5), (2.5, 5), (5, 10), (10, 20)), spoof_qty=((0, 15), (15, 30), (30, 50), (50, 80), (80, 200)))
        deg = {}
        for feat, bb in bins.items():
            deg[feat] = []
            for lo, hi in bb:
                es = [(ix.s.sid, e["id"]) for ix in test for e in ix.s.episodes if e["template"] == "chen" and e["spoof"]
                      and e["filled"] and lo <= e["params"].get(feat, -1) < hi]
                if es:
                    deg[feat].append(dict(bin=f"{lo}-{hi}", n=len(es), rule=round(sum(x in hit_rule for x in es) / len(es), 3),
                                          model=round(sum(x in hit_model for x in es) / len(es), 3)))
        R["degradation_chen"] = deg
        tpl = lambda ix_list: {(ix.s.sid, e["id"]): e["template"] for ix in ix_list for e in ix.s.episodes}
        tb, tt = tpl(base), tpl(test)
        loo = {}
        for held in ("chen", "coscia", "oystacher", "lebental"):
            keep = [r for r in tr if not any(tb[(r["sid"], e)] == held for e in r["eps"])]
            m2 = HistGradientBoostingClassifier(max_depth=4, max_iter=200, learning_rate=0.1, random_state=0)
            m2.fit(f(keep), np.array([r["true"] for r in keep]))
            for r, sc in zip(te, m2.predict_proba(f(te))[:, 1]):
                r["s2"] = float(sc)
            hit = {(sid, e) for sid, rs in by_s.items() for r in sorted(rs, key=lambda r: r["s2"], reverse=True)[:N] for e in r["eps"]}
            es = [(ix.s.sid, e["id"]) for ix in test for e in ix.s.episodes if e["template"] == held and e["spoof"]
                  and e["filled"] and not e["evasive"]]
            if not es:
                continue
            loo[held] = dict(n=len(es), model_never_shown_this_template=round(sum(x in hit for x in es) / len(es), 3),
                             model_trained_on_all=round(sum(x in hit_model for x in es) / len(es), 3),
                             rule=round(sum(x in hit_rule for x in es) / len(es), 3))
        R["leave_one_template_out"] = loo
    except ImportError as e:                                  # scikit-learn not installed
        R["ranking"] = dict(skipped=str(e))

    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=int, default=30)
    ap.add_argument("--test", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--dump", default=None)
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    t0 = time.time()
    base = [Index(make_session(i, a.seed + i)) for i in range(a.base)]
    test = [Index(make_session(a.base + i, a.seed + 10000 + i)) for i in range(a.test)]
    if a.dump:
        for ix in base + test:
            dump(ix.s, a.dump)
    R = experiments(base, test)
    R["meta"]["seed"] = a.seed
    R["meta"]["runtime_seconds"] = round(time.time() - t0, 1)
    os.makedirs(a.out, exist_ok=True)
    json.dump(R, open(os.path.join(a.out, "results.json"), "w"), indent=1, default=str)
    print(json.dumps(R["meta"]))
    for key in ("literal_defaults", "self_quantile", "class_k"):
        r = R[key]
        print(f"{r['name']:42s} recall faithful {r['recall_faithful']} evasive {r['recall_evasive']} | cases/session {r['cases_per_session']} | false/100 {r['false_cases_per_100_legit_account_sessions']}")
    for r in R["fixed_k"] + R["ablations"]:
        print(f"{r['name']:42s} recall faithful {r['recall_faithful']} evasive {r['recall_evasive']} | cases/session {r['cases_per_session']} | false/100 {r['false_cases_per_100_legit_account_sessions']} {r['false_cases']}")
    print("class k:", R["class_k"].get("k_by_class"))
    print("per-template (class k):", {k: f"{v[0]}/{v[1]}" for k, v in R["class_k"]["recall"].items()})
    print("done; see", os.path.join(a.out, "results.json"))


if __name__ == "__main__":
    main()
