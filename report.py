"""Turn results/results.json into results/results.md (plain text blocks, no tables)."""
import json, sys
R = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "results/results.json"))
M = R["meta"]
pct = lambda x: "n/a" if x is None else f"{100 * x:.1f}%"
L = []
def row(r):
    return f"{r['name']:<40} recall {pct(r['recall_faithful']):>6} | evasive {pct(r['recall_evasive']):>6} | cases/session {r['cases_per_session']:>5} | false cases per 100 legit account-sessions {r['false_cases_per_100_legit_account_sessions']:>5}"
REAL = "instrument" in M
L += [f"# spoofbench results: {M['instrument']} replay" if REAL else "# spoofbench v0.1 results", "",
      f"Seed {M['seed']}. {M['base_sessions']} baseline sessions and {M['test_sessions']} test sessions of {int(M['session_seconds'] / 60)} minutes; "
      f"{M['accounts']} firm accounts, {M['legit_accounts']} of them legitimate. All numbers below are on the test sessions.",
      f"Test set: {M['firm_orders_test']:,} firm orders, {M['candidates_test']:,} fill-then-cancel candidates, {M['episodes_test']:,} seeded episodes, "
      f"of which {M['episodes_with_fill']:,} got a fill on the genuine order and {M['attempts_without_fill']:,} did not. "
      "Recall is measured on episodes with a fill; attempts without a fill are invisible to any fill-triggered procedure.",
      "", (f"Market: recorded {M['instrument']} order-by-order data ({M['source']}), baseline days {M['baseline_days'][0]} to {M['baseline_days'][-1]}, "
           f"test days {M['test_days'][0]} to {M['test_days'][-1]}, windows per day: {M['windows_per_day']}; {M['market_events_test']:,} market events in the test sessions. "
           f"Median displayed size at the touch {M['median_touch_size']:,} lots, within 3 ticks {M['median_size_within_3_ticks']:,} lots. "
           "The firm's accounts and the seeded episodes are simulated on top of the recorded book: their orders do not move the market and nobody reacts to them."
           if REAL else "Synthetic data. Nothing here is a result on real market data."), "",
      "## 1. Literal procedures and calibration", "", "```", row(R["literal_defaults"]), row(R["self_quantile"]), row(R["class_k"]), "```",
      f"Per-class k chosen on the baseline sessions: {R['class_k']['k_by_class']}", "",
      "## 2. Fixed imbalance multiple k (both extensions on)", "", "```"] + [row(r) + "  " + json.dumps(r["false_cases"]) for r in R["fixed_k"]] + ["```", "",
      "## 3. Ablations around the per-class configuration", "", "```"] + [row(r) for r in R["ablations"]] + ["```", "",
      "## 4. Recall by template, per-class configuration (detected/total)", "", "```"] + [f"{k:<20} {v[0]:>4}/{v[1]:<4} {pct(v[0] / v[1]) if v[1] else ''}" for k, v in R["class_k"]["recall"].items()] + ["```", ""]
K = R.get("ranking", {})
if "average_precision" in K:
    L += ["## 5. Ranking model on loose candidates (trained on the seeded baseline sessions)", "",
          f"Training pool {K['train_candidates']:,} candidates ({K['train_true']:,} true); test pool {K['test_candidates']:,} ({K['test_true']:,} true).",
          f"Average precision: model {K['average_precision']['model']}, ranking by imbalance ratio {K['average_precision']['by_imbalance_ratio']}, by size asymmetry {K['average_precision']['by_size_asymmetry']}.", "",
          "Top-N alerts per session (fill-triggered templates only):", "```"]
    for name, d in K["top_n_per_session"].items():
        for N, v in d.items():
            L.append(f"{name:<20} N={int(N):<3} recall {pct(v['recall_faithful']):>6} | all incl. evasive {pct(v['recall_all']):>6} | precision {pct(v['precision']):>6}")
    v, w = K["rule_at_its_own_volume"], K["model_at_rule_volume"]
    L += ["```", f"At the rule's own volume ({K['rule_instances_per_session']} instances per session): rule recall {pct(v['recall_faithful'])}, precision {pct(v['precision'])}; "
          f"model top-{w['N']} recall {pct(w['recall_faithful'])}, precision {pct(w['precision'])}.", ""]
if "leave_one_template_out" in R:
    L += ["## 6. Held-out template: can the model find a pattern it was never shown?", "", "```"]
    for k, v in R["leave_one_template_out"].items():
        L.append(f"{k:<10} n={v['n']:<4} model never shown it {pct(v['model_never_shown_this_template']):>6} | model trained on all {pct(v['model_trained_on_all']):>6} | rule {pct(v['rule']):>6}")
    L += ["```", ""]
if "degradation_chen" in R:
    L += ["## 7. Where detection degrades (Chen-type episodes, faithful and evasive together)", "", "```"]
    for feat, rows in R["degradation_chen"].items():
        for b in rows:
            L.append(f"{feat:<10} {b['bin']:<8} n={b['n']:<4} rule {pct(b['rule']):>6} | model {pct(b['model']):>6}")
    L += ["```", ""]
open((sys.argv[1] if len(sys.argv) > 1 else "results/results.json").replace(".json", ".md"), "w").write("\n".join(L))
print("\n".join(L))
