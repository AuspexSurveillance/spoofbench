"""Write FINDINGS_V05.md from results_v05/*.json.    python report_v05.py [results_v05]"""
import json, os, sys

D = sys.argv[1] if len(sys.argv) > 1 else "results_v05"
TIERS = [("std", "Simulated market, the v0.3 sessions"), ("real_ZN", "ZN, recorded order book"),
         ("real_ES_w14", "ES, recorded order book, the two windows a day used in v0.3"),
         ("real_ES", "ES, recorded order book, all six windows a day"),
         ("eq", "Equities templates (v0.4 sessions), never trained on"), ("stress", "Stress tier")]
pc = lambda v: f"{v[0]:,}/{v[1]:,} ({100 * v[0] / v[1]:.1f}%)" if v and v[1] else "0/0"
add = lambda a, b: [a[0] + b[0], a[1] + b[1]]


def block(R):
    m = R["meta"]
    n_ls = m["legit_accounts"] * m["test_sessions"]
    L = [f"{m['base_sessions']} baseline and {m['test_sessions']} test sessions; {m['episodes_test']:,} seeded attempts in the test sessions, "
         f"{m['episodes_test_without_fill']:,} of them without a fill; {n_ls} legitimate account-sessions.", "", "```"]
    for key, title in (("rule", "procedures"), ("learned", "learned detector"), ("learned_budget_only", "learned, no floor")):
        r = R[key]
        L.append(f"{title:<17} all attempts {pc(r['all_attempts']):>21} | completed faithful {pc(r['completed_faithful']):>19} | completed evasive {pc(r['completed_evasive']):>17} | "
                 f"no fill {pc(add(r['unfilled_faithful'], r['unfilled_evasive'])):>19} | false cases {r['false_cases_legit']} of {n_ls} ({r['false_cases_per_100_legit_account_sessions']} per 100)")
    L += ["```", "", "Flagged groups that contain no seeded order: "
          f"{R['learned']['false_instances']} of {R['learned']['instances']:,} (learned), {R['rule']['false_instances']} of {R['rule']['instances']:,} (procedures).", ""]
    L += ["At an equal false-case load (one threshold read off the test sessions, comparison only):", "", "```"]
    for f, v in R["matched"].items():
        rk = v["rule_fixed_k"]
        L.append(f"at most {f} per 100: learned {pc(v['learned']['all_attempts'])} | "
                 + ("procedures: no fixed multiple stays under this rate" if rk is None else f"procedures {pc(rk['all_attempts'])} (k={rk['k']}, {rk['false_per_100']} per 100)"))
    L += ["```", "", "By pattern, all attempts (completed faithful in brackets):", "", "```"]
    for t, v in R["by_pattern"].items():
        L.append(f"{t:<10} learned {pc(v['learned']['all_attempts']):>19} [{pc(v['learned']['completed_faithful'])}] | procedures {pc(v['rule']['all_attempts']):>19} [{pc(v['rule']['completed_faithful'])}]")
    L += ["```", "", "A pattern the detector was never shown (every account that runs it is left out of training and calibration). "
          "Recall is over all attempts of that pattern:", "", "```"]
    for t, v in R["held_out_pattern"].items():
        L.append(f"{t:<10} with the floor {pc(v['learned']['all_attempts']):>19} at {v['false_cases_per_100_legit_account_sessions']} false cases per 100 | "
                 f"without {pc(v['budget_only']['all_attempts']):>19} at {v['budget_only']['false_cases_per_100_legit_account_sessions']} | "
                 f"threshold read off the test sessions at 1 per 100: {pc(v['learned_at_1_false_case_per_100']['all_attempts'])} | procedures {pc(v['rule']['all_attempts'])}")
    L += ["```", ""]
    if "held_out_legitimate_type" in R:
        L += ["A legitimate account type the detector was never shown (left out of training and calibration, present in the test sessions):", "", "```"]
        for t, v in R["held_out_legitimate_type"].items():
            L.append(f"{t:<13} learned: {v['flagged']} of {v['account_sessions']} account-sessions flagged | procedures: {v['flagged_by_procedures']} of {v['account_sessions']}")
        L += ["```", ""]
    if "linked_accounts" in R:
        L += [f"Two-account scheme with the two accounts linked into one: {pc(R['linked_accounts']['milrud']['all_attempts'])} of milrud attempts.", ""]
    return L


def main():
    res = {k: json.load(open(os.path.join(D, f"results_learned_{k}.json"))) for k, _ in TIERS
           if os.path.exists(os.path.join(D, f"results_learned_{k}.json"))}
    L = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "v05_notes.md")).read().rstrip().split("\n")
    L += ["", "## Results", "", "Every number below is on test sessions and is generated from `results_v05/*.json` by `report_v05.py`. "
          "\"All attempts\" counts every seeded episode, including those in which the genuine order never traded. "
          "\"Completed faithful\" is the denominator the v0.3 paper uses.", ""]
    for k, title in TIERS:
        if k in res:
            L += [f"### {title}", ""] + block(res[k])
    open("FINDINGS_V05.md", "w").write("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
