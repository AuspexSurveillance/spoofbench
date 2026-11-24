"""Extension set (v0.4): the three equities layering templates added to the v0.3 roster.

    python run_equities.py [--base 30] [--test 30] [--seed 20261123] [--out results_ext]

Writes results_equities.json and results_equities.md. The v0.3 sessions and results are not touched.
"""
import argparse, json, os, time
from dataclasses import replace

from spoofbench.detect import Index, Params, detect
from spoofbench.equities import make_session_eq, link_accounts, GROUPS, SOURCES_EQ
from run_benchmark import experiments, summarize

NEW = ("trillium", "hold", "milrud")


def hits(idx, flagged):
    """(session, episode) pairs with at least one spoof order in a flagged instance."""
    sess = {ix.s.sid: ix.s for ix in idx}
    return {(i["sid"], sess[i["sid"]].by_oid[o].ep) for i in flagged for o in i["oids"]
            if sess[i["sid"]].by_oid[o].role == "spoof"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=int, default=30)
    ap.add_argument("--test", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--out", default="results_ext")
    ap.add_argument("--v03", default="results/results.json")
    a = ap.parse_args()
    t0 = time.time()
    base = [Index(make_session_eq(i, a.seed + i)) for i in range(a.base)]
    test = [Index(make_session_eq(a.base + i, a.seed + 10000 + i)) for i in range(a.test)]
    R = experiments(base, test, held_out=NEW + ("oystacher",))
    accts = test[0].s.accounts
    n_legit = sum(v["truth"] == "legit" for v in accts.values())
    X = Params(flip=True, persistent=True)

    # A. thresholds chosen in v0.3, before these patterns existed
    v03 = json.load(open(a.v03))["class_k"]["k_by_class"]
    kc = tuple(sorted((x, v03[v["kind"]]) for x, v in accts.items()))
    R["carried_over"] = summarize("v0.3 class thresholds, not re-chosen", test, replace(X, k_by_acct=kc), n_legit)
    R["carried_over"]["k_by_class"] = v03

    # B. the two accounts of the two-account scheme linked into one
    chosen = R["class_k"]["k_by_class"]
    linked = [Index(link_accounts(ix.s, GROUPS)) for ix in test]
    kl = tuple(sorted((x, chosen[v["kind"]]) for x, v in linked[0].s.accounts.items()))
    R["linked"] = summarize("per-class k, the two accounts linked", linked, replace(X, k_by_acct=kl), n_legit)

    # C. the two-sided quoting exclusion against layers that are small next to the genuine order
    C = replace(X, k_by_acct=tuple(sorted((x, chosen[v["kind"]]) for x, v in accts.items())))
    h1, h0 = hits(test, detect(test, C)), hits(test, detect(test, replace(C, exclusions=False)))
    bins = ((1.0, 1.5), (1.5, 2.0), (2.0, 2.5), (2.5, 3.1))
    rows = []
    for lo, hi in bins:
        es = [(ix.s.sid, e["id"]) for ix in test for e in ix.s.episodes if e["template"] == "hold" and e["spoof"]
              and e["filled"] and lo <= e["params"]["ratio"] < hi]
        if es:
            rows.append(dict(ratio=f"{lo}-{hi}", n=len(es), with_exclusions=sum(x in h1 for x in es),
                             without_exclusions=sum(x in h0 for x in es)))
    R["hold_by_ratio"] = rows

    R["meta"].update(seed=a.seed, runtime_seconds=round(time.time() - t0, 1), extension="equities v0.4",
                     sources={k: v["document"] for k, v in SOURCES_EQ.items()})
    os.makedirs(a.out, exist_ok=True)
    json.dump(R, open(os.path.join(a.out, "results_equities.json"), "w"), indent=1, default=str)

    pct = lambda d, n: f"{d}/{n} ({100 * d / n:.1f}%)" if n else "0/0"
    L = ["# spoofbench v0.4 extension set: equities layering templates", "",
         f"Seed {a.seed}. {a.base} baseline and {a.test} test sessions of 30 minutes on the simulated market. "
         f"Roster: the v0.3 accounts plus four accounts that run the three new templates. Synthetic data.", "",
         "## Recall by template on the test sessions (completed episodes, detected/total)", ""]
    for key, title in (("literal_defaults", "Fixed defaults"), ("self_quantile", "Own 99.5th percentile"),
                       ("carried_over", "v0.3 class thresholds, not re-chosen"), ("class_k", "Class thresholds re-chosen on these sessions"),
                       ("linked", "Re-chosen thresholds, the two accounts linked")):
        r = R[key]
        L += [f"{title} (false cases per 100 legitimate account-sessions: {r['false_cases_per_100_legit_account_sessions']})", "```"]
        L += [f"{k:<20} {pct(*v)}" for k, v in r["recall"].items()] + ["```", ""]
    L += [f"Class thresholds: v0.3 {v03}; re-chosen {chosen}", "",
          "## Two-sided quoting exclusion and the Hold Brothers pattern", "",
          "Completed episodes found, by the ratio of layered quantity to the genuine order (faithful and evasive together):", "```"]
    L += [f"ratio {b['ratio']:<8} n={b['n']:<4} with exclusions {b['with_exclusions']:>4} | without exclusions {b['without_exclusions']:>4}" for b in rows]
    L += ["```", ""]
    if "leave_one_template_out" in R:
        L += ["## Ranking model on a template it was never shown (top-N per session at the rule's volume)", "", "```"]
        for k, v in R["leave_one_template_out"].items():
            L.append(f"{k:<10} n={v['n']:<4} never shown {100 * v['model_never_shown_this_template']:.1f}% | trained on all "
                     f"{100 * v['model_trained_on_all']:.1f}% | rule {100 * v['rule']:.1f}%")
        L += ["```", ""]
    open(os.path.join(a.out, "results_equities.md"), "w").write("\n".join(L))
    print("\n".join(L))


if __name__ == "__main__":
    main()
