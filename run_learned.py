"""Learned detector (v0.5) against the procedures, on the same sessions and the same false-case budget.

    python run_learned.py --tier std      the v0.3 sessions (five futures templates)
    python run_learned.py --tier stress   harder legitimate accounts and adaptive manipulation (spoofbench/stress.py)
    python run_learned.py --tier eq       the v0.4 equities sessions; the three equities templates are never trained on

Options: [--base 30] [--test 30] [--seed 20261123] [--out results_v05] [--jobs 2]

Writes results_learned_<tier>.json and .md. Earlier results files are not touched.
"""
import argparse, json, os, time
from collections import defaultdict
from dataclasses import replace
from multiprocessing import Pool

import numpy as np

from spoofbench.bench import make_session
from spoofbench.detect import Index, Params, evaluate as rule_evaluate, persistent
from spoofbench.learned import Detector, featurize, evaluate, matched, pooled, recall_table, USE

GRID = (0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0)
BUDGET = 2.0
FUTURES = ("chen", "coscia", "oystacher", "sarao", "lebental")
EQUITIES = ("trillium", "hold", "milrud")
ADAPTIVE = ("ada_same", "ada_flip", "ada_cross")
LEGIT_TYPES = {"Scalper": ("SCALP_1", "SCALP_2"), "LeggedHedger": ("LEG_1", "LEG_2"), "BlockWorker": ("BLOCK_1", "BLOCK_2")}


def _rule(s):
    """The procedures (flip and persistent variants on) at every multiple of the grid, one session."""
    ix = Index(s)
    out = {}
    for k in GRID:
        P = replace(Params(), flip=True, persistent=True, k=k)
        inst = [i for i in (rule_evaluate(c, ix, P, None) for c in ix.cands) if i]
        cnt = defaultdict(int)
        for i in inst:
            cnt[i["acct"]] += 1
        fl = [i for i in inst if cnt[i["acct"]] >= P.n] + persistent(ix, P)
        out[k] = [(i["acct"], tuple(sorted({s.by_oid[o].ep for o in i["oids"] if s.by_oid[o].role == "spoof"}))) for i in fl]
    return out


def _one(a):
    tier, sid, seed = a
    if tier == "stress":
        from spoofbench.stress import make_session_stress as mk
    elif tier == "eq":
        from spoofbench.equities import make_session_eq as mk
    else:
        mk = make_session
    s = mk(sid, seed)
    rec = featurize(s)
    rec["rule"] = _rule(s)
    if tier == "eq":
        from spoofbench.equities import link_accounts
        rec["linked"] = featurize(link_accounts(s))
    return rec


def build(tier, n, sid0, seed0, jobs):
    args = [(tier, sid0 + i, seed0 + i) for i in range(n)]
    if jobs > 1:
        with Pool(jobs) as p:
            return p.map(_one, args)
    return [_one(a) for a in args]


def rule_instances(recs, kmap):
    kind = {a: v["kind"] for a, v in recs[0]["accounts"].items()}
    return [dict(acct=a, sid=r["sid"], eps=set(eps)) for r in recs for k in set(kmap.values())
            for a, eps in r["rule"][k] if kmap[kind[a]] == k]


def rule_class_k(base, exclude=()):
    """Per-class multiple chosen on the baseline as in run_benchmark.py (smallest k within budget)."""
    acc = base[0]["accounts"]
    chosen = {}
    for kd in sorted({v["kind"] for v in acc.values()}):
        members = {a for a, v in acc.items() if v["kind"] == kd and v["truth"] == "legit" and a not in exclude}
        chosen[kd] = GRID[-1]
        for k in GRID:
            cases = defaultdict(lambda: [0, 0])
            for r in base:
                for a, eps in r["rule"][k]:
                    cases[(a, r["sid"])][0 if eps else 1] += 1
            fc = sum(1 for (a, sid), v in cases.items() if a in members and v[0] == 0)
            if 100.0 * fc / max(1, len(members) * len(base)) <= BUDGET:
                chosen[kd] = k
                break
    return chosen


def frac(v):
    return round(v[0] / v[1], 4) if v[1] else None


def by_pattern(rec, t):
    return dict(completed_faithful=list(pooled(rec, t, False, True)), completed_evasive=list(pooled(rec, t, True, True)),
                unfilled=list(pooled(rec, t, None, False)), all_attempts=list(pooled(rec, t)))


def run(tier, base, test, log=print, family=False):
    acc = test[0]["accounts"]
    tmpl = {a: v.get("template") for a, v in acc.items()}
    fut = tuple(t for t in FUTURES if t in set(tmpl.values()))
    patterns = fut + (ADAPTIVE if tier == "stress" else ()) + (EQUITIES if tier == "eq" else ())
    unseen = set(ADAPTIVE) if tier == "stress" else (set(EQUITIES) if tier == "eq" else set())
    ex0 = {a for a, t in tmpl.items() if t in unseen}
    R = dict(meta=dict(tier=tier, base_sessions=len(base), test_sessions=len(test), accounts=len(acc),
                       legit_accounts=sum(v["truth"] == "legit" for v in acc.values()),
                       groups_base=sum(len(r["meta"]) for r in base), groups_test=sum(len(r["meta"]) for r in test),
                       seeded_groups_base=sum(m["true"] for r in base for m in r["meta"]),
                       episodes_test=sum(1 for r in test for e in r["episodes"] if e["n_spoof"]),
                       episodes_test_without_fill=sum(1 for r in test for e in r["episodes"] if e["n_spoof"] and not e["filled"]),
                       features=USE, n=2, budget=BUDGET, floor=Detector().floor, never_trained_on=sorted(unseen)))

    # 1. the procedures, per-class multiple chosen on the baseline (the v0.3 reference)
    kc = rule_class_k(base)
    R["rule"], rule_hit = evaluate(test, rule_instances(test, kc), "procedures, per-class multiple")
    R["rule"]["k_by_class"] = kc
    rule_rec = recall_table(test, rule_hit)
    log(f"rule     completed faithful {frac(R['rule']['completed_faithful'])} all attempts {frac(R['rule']['all_attempts'])} false/100 {R['rule']['false_cases_per_100_legit_account_sessions']}")

    # 2. the learned detector, thresholds set on out-of-fold baseline scores
    det = Detector(budget=BUDGET).fit(base, exclude=ex0)
    p, rows = det.score(test)
    flagged = det.flag(rows, p)
    R["learned"], hit = evaluate(test, flagged, "learned detector")
    R["learned"]["thresholds"] = {k: round(v, 4) for k, v in det.thr.items()}
    R["learned_budget_only"] = evaluate(test, det.flag(rows, p, budget_only=True), "learned detector, budget thresholds without the floor")[0]
    R["learned_budget_only"]["thresholds"] = {k: round(v, 4) for k, v in det.thr_budget.items()}
    bflag = det.flag(det.oof_rows, det.oof)
    R["learned"]["baseline_out_of_fold"] = {k: v for k, v in evaluate(base, bflag)[0].items()
                                            if k in ("all_attempts", "false_cases_per_100_legit_account_sessions", "false_cases")}
    log(f"learned  completed faithful {frac(R['learned']['completed_faithful'])} all attempts {frac(R['learned']['all_attempts'])} false/100 {R['learned']['false_cases_per_100_legit_account_sessions']} "
        f"(no floor: all {frac(R['learned_budget_only']['all_attempts'])}, false/100 {R['learned_budget_only']['false_cases_per_100_legit_account_sessions']})")
    lrec = recall_table(test, hit)
    R["by_pattern"] = {t: dict(learned=by_pattern(lrec, t), rule=by_pattern(rule_rec, t)) for t in patterns}

    # 3. equal false-case load: one threshold read off the test sessions (comparison only)
    kinds = sorted({v["kind"] for v in acc.values()})
    n_ls = R["meta"]["legit_accounts"] * len(test)
    pts = []
    for k in GRID:
        ev, h = evaluate(test, rule_instances(test, {kd: k for kd in kinds}))
        pts.append((ev["false_cases_per_100_legit_account_sessions"], k, ev))
    M = matched(test, rows, p, det.n)
    R["matched"] = {}
    for f, rec in M.items():
        ok = [x for x in pts if x[0] <= f]
        best = max(ok, key=lambda x: x[2]["all_attempts"][0]) if ok else None
        R["matched"][str(f)] = dict(
            learned=dict(all_attempts=list(pooled(rec)), completed=list(pooled(rec, filled=True)), unfilled=list(pooled(rec, filled=False))),
            rule_fixed_k=None if best is None else dict(k=best[1], false_per_100=best[0], all_attempts=best[2]["all_attempts"],
                                                        completed=[best[2]["completed_faithful"][0] + best[2]["completed_evasive"][0],
                                                                   best[2]["completed_faithful"][1] + best[2]["completed_evasive"][1]]))

    # 4. a pattern the detector was never shown: every account that runs it is left out of training
    def held_out(extra_train=()):
        out = {}
        for t in fut:
            ex = {a for a, tt in tmpl.items() if tt == t} | (ex0 - set(extra_train))
            d = Detector(budget=BUDGET).fit(base, exclude=ex)
            pp, rr = d.score(test)
            ev, h = evaluate(test, d.flag(rr, pp))
            rec = recall_table(test, h)
            m1 = matched(test, rr, pp, d.n, rates=(1.0,))[1.0]
            ev0, h0 = evaluate(test, d.flag(rr, pp, budget_only=True))
            out[t] = dict(learned=by_pattern(rec, t), rule=by_pattern(rule_rec, t),
                          learned_at_1_false_case_per_100=by_pattern(m1, t),
                          false_cases_per_100_legit_account_sessions=ev["false_cases_per_100_legit_account_sessions"],
                          budget_only=dict(all_attempts=by_pattern(recall_table(test, h0), t)["all_attempts"],
                                           false_cases_per_100_legit_account_sessions=ev0["false_cases_per_100_legit_account_sessions"]))
            log(f"held out {t:10s} learned all {frac(out[t]['learned']['all_attempts'])} completed faithful {frac(out[t]['learned']['completed_faithful'])} "
                f"| rule completed faithful {frac(out[t]['rule']['completed_faithful'])} | false/100 {out[t]['false_cases_per_100_legit_account_sessions']} "
                f"(no floor: {out[t]['budget_only']['false_cases_per_100_legit_account_sessions']})")
        return out

    R["held_out_pattern"] = held_out()
    if tier == "stress" and family:
        log("with the adaptive family in training:")
        fam = {a for a, t in tmpl.items() if t in ADAPTIVE}
        R["held_out_pattern_family_in_training"] = held_out(extra_train=fam)
    if tier == "stress":
        # 5. a legitimate account type the detector was never shown
        R["held_out_legitimate_type"] = {}
        for name, accts in LEGIT_TYPES.items():
            d = Detector(budget=BUDGET).fit(base, exclude=ex0 | set(accts))
            pp, rr = d.score(test)
            fl = d.flag(rr, pp)
            ev, h = evaluate(test, fl)
            bad = {(i["acct"], i["sid"]) for i in fl if i["acct"] in accts}
            rbad = {(i["acct"], i["sid"]) for i in rule_instances(test, rule_class_k(base, exclude=accts)) if i["acct"] in accts}
            R["held_out_legitimate_type"][name] = dict(account_sessions=len(accts) * len(test), flagged=len(bad), flagged_by_procedures=len(rbad),
                                                       all_attempts=ev["all_attempts"],
                                                       false_cases_per_100_legit_account_sessions=ev["false_cases_per_100_legit_account_sessions"])
            log(f"legit type never shown {name}: {len(bad)} of {len(accts) * len(test)} account-sessions flagged (procedures: {len(rbad)})")
    if tier == "eq":
        linked = [r["linked"] for r in test]
        pp, rr = det.score(linked)
        ev, h = evaluate(linked, det.flag(rr, pp))
        R["linked_accounts"] = dict(milrud=by_pattern(recall_table(linked, h), "milrud"),
                                    false_cases_per_100_legit_account_sessions=ev["false_cases_per_100_legit_account_sessions"])

    # 6. what the highest-scoring alerts rest on
    X = np.vstack([r["X"] for r in test])[:, det.cols]
    order = np.argsort(-p)
    seen, ex = set(), []
    for i in order:
        sid, m = rows[i]
        if m["acct"] in seen or p[i] <= det.thr.get(det.kind.get(m["acct"]), det.thr_default):
            continue
        seen.add(m["acct"])
        e = det.explain(X[i].astype(float))
        ex.append(dict(account=m["acct"], session=sid, time=round(m["t"], 3), orders=len(m["oids"]), seeded=bool(m["true"]), **e))
        if len(ex) >= 12:
            break
    R["examples"] = ex
    return R


def write_md(R, path):
    pc = lambda v: f"{v[0]}/{v[1]} ({100 * v[0] / v[1]:.1f}%)" if v and v[1] else "0/0"
    m = R["meta"]
    L = [f"# Learned detector (v0.5), tier: {m['tier']}", "",
         f"Seed {m['seed']}. {m['base_sessions']} baseline and {m['test_sessions']} test sessions, {m.get('market', 'simulated market')}. "
         f"{m['accounts']} accounts, {m['legit_accounts']} legitimate. {m['episodes_test']:,} seeded attempts in the test sessions, "
         f"{m['episodes_test_without_fill']:,} of them without a fill. All numbers below are on the test sessions.", ""]
    if m["never_trained_on"]:
        L += [f"Never used in training (accounts that run them are left out of the baseline): {', '.join(m['never_trained_on'])}.", ""]
    L += ["## Thresholds set on the baseline, applied to the test sessions", "", "```"]
    for key, title in (("rule", "procedures, per-class multiple"), ("learned", "learned detector"),
                       ("learned_budget_only", "learned, no threshold floor")):
        r = R[key]
        L.append(f"{title:<32} completed faithful {pc(r['completed_faithful'])} | completed evasive {pc(r['completed_evasive'])} | "
                 f"no fill {pc([r['unfilled_faithful'][0] + r['unfilled_evasive'][0], r['unfilled_faithful'][1] + r['unfilled_evasive'][1]])} | "
                 f"all attempts {pc(r['all_attempts'])}")
        L.append(f"{'':<32} false cases per 100 legitimate account-sessions {r['false_cases_per_100_legit_account_sessions']} "
                 f"({r['false_cases_legit']} cases: {r['false_cases']}); flagged groups {r['instances']}, of which not seeded {r['false_instances']}")
    L += ["```", "", "## By pattern (all attempts; completed faithful in brackets)", "", "```"]
    for t, v in R["by_pattern"].items():
        L.append(f"{t:<10} learned {pc(v['learned']['all_attempts']):>20} [{pc(v['learned']['completed_faithful'])}] | "
                 f"procedures {pc(v['rule']['all_attempts']):>20} [{pc(v['rule']['completed_faithful'])}]")
    L += ["```", "", "## Equal false-case load (one threshold read off the test sessions; comparison only)", "", "```"]
    for f, v in R["matched"].items():
        rk = v["rule_fixed_k"]
        L.append(f"at most {f} per 100: learned all attempts {pc(v['learned']['all_attempts'])}, completed {pc(v['learned']['completed'])} | "
                 + ("procedures: no fixed multiple stays under this rate" if rk is None else
                    f"procedures (k={rk['k']}, {rk['false_per_100']} per 100) all attempts {pc(rk['all_attempts'])}, completed {pc(rk['completed'])}"))
    L += ["```", ""]
    for key, title in (("held_out_pattern", "A pattern the detector was never shown"),
                       ("held_out_pattern_family_in_training", "The same, with the adaptive family added to training")):
        if key in R:
            L += [f"## {title}", "", "Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.", "", "```"]
            for t, v in R[key].items():
                L.append(f"{t:<10} learned: all attempts {pc(v['learned']['all_attempts'])}, completed faithful {pc(v['learned']['completed_faithful'])} | "
                         f"procedures: completed faithful {pc(v['rule']['completed_faithful'])} | false cases per 100: {v['false_cases_per_100_legit_account_sessions']} "
                         f"(without the floor: {pc(v['budget_only']['all_attempts'])}, {v['budget_only']['false_cases_per_100_legit_account_sessions']} per 100)")
            L += ["```", ""]
    if "held_out_legitimate_type" in R:
        L += ["## A legitimate account type the detector was never shown", "", "```"]
        for t, v in R["held_out_legitimate_type"].items():
            L.append(f"{t:<14} learned: {v['flagged']} of {v['account_sessions']} account-sessions flagged | procedures: {v['flagged_by_procedures']} of {v['account_sessions']}")
        L += ["```", ""]
    if "linked_accounts" in R:
        L += ["## Two-account scheme with the accounts linked", "", "```", f"milrud  all attempts {pc(R['linked_accounts']['milrud']['all_attempts'])}", "```", ""]
    L += ["## What the highest-scoring alert in each account rests on", "",
          "Drop in the score when one part of the evidence is replaced by the typical legitimate value.", "", "```"]
    for e in R["examples"]:
        top = ", ".join(f"{k} {v:+.2f}" for k, v in list(e["drops"].items())[:3])
        L.append(f"{e['account']:<14} score {e['score']:.3f} {'seeded' if e['seeded'] else 'NOT seeded'} | {top}")
    L += ["```", ""]
    open(path, "w").write("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="std", choices=("std", "stress", "eq"))
    ap.add_argument("--base", type=int, default=30)
    ap.add_argument("--test", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20261123)
    ap.add_argument("--out", default="results_v05")
    ap.add_argument("--jobs", type=int, default=2)
    ap.add_argument("--family", action="store_true", help="stress tier: also run held-out patterns with the adaptive family in training")
    a = ap.parse_args()
    t0 = time.time()
    base = build(a.tier, a.base, 0, a.seed, a.jobs)
    test = build(a.tier, a.test, a.base, a.seed + 10000, a.jobs)
    print(f"sessions built in {time.time() - t0:.0f}s", flush=True)
    R = run(a.tier, base, test, log=lambda s: print(s, flush=True), family=a.family)
    R["meta"].update(seed=a.seed, runtime_seconds=round(time.time() - t0, 1))
    os.makedirs(a.out, exist_ok=True)
    json.dump(R, open(os.path.join(a.out, f"results_learned_{a.tier}.json"), "w"), indent=1, default=str)
    write_md(R, os.path.join(a.out, f"results_learned_{a.tier}.md"))
    print("done; see", os.path.join(a.out, f"results_learned_{a.tier}.md"))


if __name__ == "__main__":
    main()
