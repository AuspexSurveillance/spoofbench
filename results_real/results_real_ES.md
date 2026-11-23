# spoofbench results: ES replay

Seed 20261123. 10 baseline sessions and 10 test sessions of 30 minutes; 22 firm accounts, 16 of them legitimate. All numbers below are on the test sessions.
Test set: 764,005 firm orders, 114,258 fill-then-cancel candidates, 1,332 seeded episodes, of which 835 got a fill on the genuine order and 266 did not. Recall is measured on episodes with a fill; attempts without a fill are invisible to any fill-triggered procedure.

Market: recorded ES order-by-order data (CME Globex MBO via Databento, replayed), baseline days 20261102 to 20261106, test days 20261109 to 20261113, windows per day: [1, 4]; 11,358,132 market events in the test sessions. Median displayed size at the touch 18 lots, within 3 ticks 113 lots. The firm's accounts and the seeded episodes are simulated on top of the recorded book: their orders do not move the market and nobody reacts to them.

## 1. Literal procedures and calibration

```
5.1/5.2/5.8 literal, Appendix C defaults recall   2.6% | evasive   0.0% | cases/session   0.4 | false cases per 100 legit account-sessions   0.0
self-quantile 99.5%                      recall   3.1% | evasive   0.0% | cases/session   0.9 | false cases per 100 legit account-sessions   0.0
per-class k from seeded baseline         recall  74.5% | evasive  33.7% | cases/session   4.2 | false cases per 100 legit account-sessions  1.25
```
Per-class k chosen on the baseline sessions: {'exec': 0.3, 'mm': 1.0, 'prop': 0.002}

## 2. Fixed imbalance multiple k (both extensions on)

```
fixed k=0.002                            recall  79.7% | evasive  34.9% | cases/session   7.7 | false cases per 100 legit account-sessions 16.88  {"mm": 20, "prop": 2, "exec": 5}
fixed k=0.005                            recall  79.7% | evasive  34.9% | cases/session   7.7 | false cases per 100 legit account-sessions 16.88  {"mm": 20, "prop": 2, "exec": 5}
fixed k=0.01                             recall  79.7% | evasive  34.9% | cases/session   7.7 | false cases per 100 legit account-sessions 16.88  {"mm": 20, "prop": 2, "exec": 5}
fixed k=0.02                             recall  79.7% | evasive  34.9% | cases/session   7.7 | false cases per 100 legit account-sessions 16.88  {"mm": 20, "prop": 2, "exec": 5}
fixed k=0.05                             recall  79.4% | evasive  34.9% | cases/session   7.5 | false cases per 100 legit account-sessions 16.25  {"mm": 20, "prop": 1, "exec": 5}
fixed k=0.1                              recall  78.9% | evasive  31.4% | cases/session   7.4 | false cases per 100 legit account-sessions 15.62  {"mm": 20, "prop": 1, "exec": 4}
fixed k=0.2                              recall  74.5% | evasive  18.2% | cases/session   6.7 | false cases per 100 legit account-sessions 11.88  {"mm": 17, "exec": 2}
fixed k=0.3                              recall  62.7% | evasive  14.0% | cases/session   5.2 | false cases per 100 legit account-sessions  6.25  {"mm": 10}
fixed k=0.5                              recall  44.7% | evasive   7.0% | cases/session   2.5 | false cases per 100 legit account-sessions   0.0  {}
fixed k=1.0                              recall  21.1% | evasive   0.0% | cases/session   1.9 | false cases per 100 legit account-sessions   0.0  {}
fixed k=2.0                              recall   5.7% | evasive   0.0% | cases/session   1.3 | false cases per 100 legit account-sessions   0.0  {}
```

## 3. Ablations around the per-class configuration

```
per-class k (reference)                  recall  74.5% | evasive  33.7% | cases/session   4.2 | false cases per 100 legit account-sessions  1.25
no flip extension                        recall  61.5% | evasive  24.0% | cases/session   3.5 | false cases per 100 legit account-sessions  1.25
no persistent-layering extension         recall  71.4% | evasive  33.7% | cases/session   3.4 | false cases per 100 legit account-sessions  1.25
no cross-instrument alignment            recall  74.5% | evasive  33.7% | cases/session   4.2 | false cases per 100 legit account-sessions  1.25
no exclusions                            recall  75.2% | evasive  47.7% | cases/session   4.3 | false cases per 100 legit account-sessions  1.88
fixed k=0.05 (for comparison)            recall  79.4% | evasive  34.9% | cases/session   7.5 | false cases per 100 legit account-sessions 16.25
fixed k=0.05, no exclusions              recall  80.6% | evasive  48.1% | cases/session  10.6 | false cases per 100 legit account-sessions 35.62
repetition n=1                           recall  75.2% | evasive  33.7% | cases/session  10.7 | false cases per 100 legit account-sessions 38.12
repetition 3 within 5 sessions           recall  74.7% | evasive  33.7% | cases/session   8.4 | false cases per 100 legit account-sessions 26.25
```

## 4. Recall by template, per-class configuration (detected/total)

```
chen                   69/155  44.5%
chen/evasive            5/73   6.8%
coscia                268/276  97.1%
coscia/evasive         55/102  53.9%
oystacher              75/128  58.6%
oystacher/evasive      27/75   36.0%
sarao                  18/18   100.0%
sarao/evasive           0/8    0.0%
```

## 5. Ranking model on loose candidates (trained on the seeded baseline sessions)

Training pool 109,794 candidates (596 true); test pool 97,327 (670 true).
Average precision: model 0.779, ranking by imbalance ratio 0.587, by size asymmetry 0.096.

Top-N alerts per session (fill-triggered templates only):
```
model                N=5   recall   6.8% | all incl. evasive   4.9% | precision  82.0%
model                N=10  recall  13.1% | all incl. evasive  10.3% | precision  86.0%
model                N=20  recall  27.4% | all incl. evasive  21.6% | precision  89.0%
model                N=40  recall  54.7% | all incl. evasive  43.5% | precision  89.2%
by_imbalance_ratio   N=5   recall   8.8% | all incl. evasive   6.1% | precision 100.0%
by_imbalance_ratio   N=10  recall  17.7% | all incl. evasive  12.2% | precision 100.0%
by_imbalance_ratio   N=20  recall  33.5% | all incl. evasive  23.9% | precision  97.5%
by_imbalance_ratio   N=40  recall  55.5% | all incl. evasive  41.2% | precision  84.3%
by_size_asymmetry    N=5   recall   4.7% | all incl. evasive   3.2% | precision  54.0%
by_size_asymmetry    N=10  recall   7.7% | all incl. evasive   5.8% | precision  50.0%
by_size_asymmetry    N=20  recall  12.5% | all incl. evasive   9.5% | precision  42.0%
by_size_asymmetry    N=40  recall  12.9% | all incl. evasive   9.8% | precision  21.5%
```
At the rule's own volume (64.0 instances per session): rule recall 73.7%, precision 78.6%; model top-64 recall 78.0%, precision 84.1%.

## 6. Held-out template: can the model find a pattern it was never shown?

```
chen       n=155  model never shown it  46.5% | model trained on all  58.7% | rule  44.5%
coscia     n=276  model never shown it  93.5% | model trained on all  93.5% | rule  97.1%
oystacher  n=128  model never shown it   8.6% | model trained on all  68.0% | rule  58.6%
```

## 7. Where detection degrades (Chen-type episodes, faithful and evasive together)

```
latency    0-1      n=25   rule  56.0% | model  76.0%
latency    1-2.5    n=41   rule  48.8% | model  65.9%
latency    2.5-5    n=80   rule  50.0% | model  53.7%
latency    5-10     n=43   rule   0.0% | model  14.0%
latency    10-20    n=39   rule   0.0% | model  23.1%
spoof_qty  0-15     n=20   rule   0.0% | model  15.0%
spoof_qty  15-30    n=34   rule  11.8% | model  14.7%
spoof_qty  30-50    n=51   rule  31.4% | model  45.1%
spoof_qty  50-80    n=42   rule  42.9% | model  57.1%
spoof_qty  80-200   n=81   rule  44.4% | model  60.5%
```
