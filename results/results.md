# spoofbench v0.1 results

Seed 20261123. 30 baseline sessions and 30 test sessions of 30 minutes; 26 firm accounts, 18 of them legitimate. All numbers below are on the test sessions.
Test set: 687,922 firm orders, 120,701 fill-then-cancel candidates, 4,158 seeded episodes, of which 2,266 got a fill on the genuine order and 1,840 did not. Recall is measured on episodes with a fill; attempts without a fill are invisible to any fill-triggered procedure.

Synthetic data. Nothing here is a result on real market data.

## 1. Literal procedures and calibration

```
5.1/5.2/5.8 literal, Appendix C defaults recall   0.0% | evasive   0.0% | cases/session   0.0 | false cases per 100 legit account-sessions   0.0
self-quantile 99.5%                      recall   4.9% | evasive   0.5% | cases/session  1.17 | false cases per 100 legit account-sessions   0.0
per-class k from seeded baseline         recall  76.3% | evasive  40.3% | cases/session  5.33 | false cases per 100 legit account-sessions  0.93
```
Per-class k chosen on the baseline sessions: {'basis': 0.02, 'exec': 0.2, 'mm': 0.3, 'prop': 0.1}

## 2. Fixed imbalance multiple k (both extensions on)

```
fixed k=0.02                             recall  85.0% | evasive  50.2% | cases/session  9.43 | false cases per 100 legit account-sessions 16.67  {"mm": 60, "exec": 18, "prop": 12}
fixed k=0.05                             recall  83.8% | evasive  48.3% | cases/session  8.73 | false cases per 100 legit account-sessions 15.19  {"mm": 60, "exec": 16, "prop": 6}
fixed k=0.1                              recall  81.4% | evasive  42.7% | cases/session  8.27 | false cases per 100 legit account-sessions 13.52  {"mm": 60, "exec": 8, "prop": 5}
fixed k=0.2                              recall  72.1% | evasive  25.5% | cases/session   5.5 | false cases per 100 legit account-sessions  1.11  {"mm": 6}
fixed k=0.3                              recall  57.4% | evasive  13.1% | cases/session   4.4 | false cases per 100 legit account-sessions   0.0  {}
fixed k=0.5                              recall  34.5% | evasive   1.4% | cases/session  2.97 | false cases per 100 legit account-sessions   0.0  {}
fixed k=1.0                              recall   9.0% | evasive   0.5% | cases/session   1.6 | false cases per 100 legit account-sessions   0.0  {}
fixed k=2.0                              recall   3.0% | evasive   0.5% | cases/session  0.83 | false cases per 100 legit account-sessions   0.0  {}
```

## 3. Ablations around the per-class configuration

```
per-class k (reference)                  recall  76.3% | evasive  40.3% | cases/session  5.33 | false cases per 100 legit account-sessions  0.93
no flip extension                        recall  47.0% | evasive  17.0% | cases/session  4.43 | false cases per 100 legit account-sessions  0.93
no persistent-layering extension         recall  73.4% | evasive  39.8% | cases/session   4.5 | false cases per 100 legit account-sessions  0.93
no cross-instrument alignment            recall  73.5% | evasive  39.5% | cases/session  4.83 | false cases per 100 legit account-sessions  0.93
no exclusions                            recall  77.8% | evasive  43.2% | cases/session   7.5 | false cases per 100 legit account-sessions 12.59
fixed k=0.05 (for comparison)            recall  83.8% | evasive  48.3% | cases/session  8.73 | false cases per 100 legit account-sessions 15.19
fixed k=0.05, no exclusions              recall  87.3% | evasive  55.4% | cases/session 15.13 | false cases per 100 legit account-sessions 47.04
repetition n=1                           recall  80.7% | evasive  40.7% | cases/session 11.77 | false cases per 100 legit account-sessions  25.0
repetition 3 within 5 sessions           recall  80.3% | evasive  40.7% | cases/session  9.53 | false cases per 100 legit account-sessions 13.33
```

## 4. Recall by template, per-class configuration (detected/total)

```
chen                  340/618  55.0%
chen/evasive           17/242  7.0%
coscia                325/333  97.6%
coscia/evasive         82/136  60.3%
lebental               46/130  35.4%
lebental/evasive        5/54   9.3%
oystacher             476/489  97.3%
oystacher/evasive     154/191  80.6%
sarao                  48/48   100.0%
sarao/evasive           3/25   12.0%
```

## 5. Ranking model on loose candidates (trained on the seeded baseline sessions)

Training pool 103,134 candidates (2,253 true); test pool 104,738 (2,280 true).
Average precision: model 0.995, ranking by imbalance ratio 0.658, by size asymmetry 0.22.

Top-N alerts per session (fill-triggered templates only):
```
model                N=5   recall   8.2% | all incl. evasive   6.6% | precision 100.0%
model                N=10  recall  16.5% | all incl. evasive  13.3% | precision 100.0%
model                N=20  recall  31.3% | all incl. evasive  25.7% | precision 100.0%
model                N=40  recall  59.0% | all incl. evasive  50.5% | precision 100.0%
by_imbalance_ratio   N=5   recall   8.0% | all incl. evasive   5.7% | precision  94.7%
by_imbalance_ratio   N=10  recall  16.6% | all incl. evasive  11.9% | precision  96.0%
by_imbalance_ratio   N=20  recall  32.3% | all incl. evasive  23.4% | precision  91.8%
by_imbalance_ratio   N=40  recall  55.5% | all incl. evasive  42.4% | precision  84.3%
by_size_asymmetry    N=5   recall   5.7% | all incl. evasive   4.4% | precision  84.0%
by_size_asymmetry    N=10  recall  10.5% | all incl. evasive   8.1% | precision  74.0%
by_size_asymmetry    N=20  recall  19.0% | all incl. evasive  15.0% | precision  67.5%
by_size_asymmetry    N=40  recall  27.3% | all incl. evasive  21.9% | precision  48.5%
```
At the rule's own volume (54.4 instances per session): rule recall 75.6%, precision 95.1%; model top-54 recall 77.1%, precision 100.0%.

## 6. Held-out template: can the model find a pattern it was never shown?

```
chen       n=618  model never shown it  43.0% | model trained on all  57.4% | rule  55.0%
coscia     n=333  model never shown it  61.6% | model trained on all  91.9% | rule  97.6%
oystacher  n=489  model never shown it  36.4% | model trained on all  96.1% | rule  97.3%
lebental   n=130  model never shown it  13.1% | model trained on all  61.5% | rule  35.4%
```

## 7. Where detection degrades (Chen-type episodes, faithful and evasive together)

```
latency    0-1      n=98   rule  71.4% | model  68.4%
latency    1-2.5    n=174  rule  59.8% | model  59.2%
latency    2.5-5    n=302  rule  58.6% | model  54.3%
latency    5-10     n=142  rule   2.8% | model  28.9%
latency    10-20    n=144  rule   1.4% | model  13.9%
spoof_qty  0-15     n=73   rule   1.4% | model   4.1%
spoof_qty  15-30    n=88   rule   1.1% | model   9.1%
spoof_qty  30-50    n=193  rule  31.6% | model  25.9%
spoof_qty  50-80    n=174  rule  51.1% | model  51.1%
spoof_qty  80-200   n=332  rule  61.7% | model  73.8%
```
