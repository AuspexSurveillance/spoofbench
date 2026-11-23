# spoofbench results: ZN replay

Seed 20261123. 30 baseline sessions and 30 test sessions of 30 minutes; 22 firm accounts, 16 of them legitimate. All numbers below are on the test sessions.
Test set: 240,259 firm orders, 29,089 fill-then-cancel candidates, 3,811 seeded episodes, of which 1,031 got a fill on the genuine order and 2,763 did not. Recall is measured on episodes with a fill; attempts without a fill are invisible to any fill-triggered procedure.

Market: recorded ZN order-by-order data (CME Globex MBO via Databento, replayed), baseline days 20261102 to 20261106, test days 20261109 to 20261113, windows per day: all; 7,600,349 market events in the test sessions. Median displayed size at the touch 1,580 lots, within 3 ticks 11,606 lots. The firm's accounts and the seeded episodes are simulated on top of the recorded book: their orders do not move the market and nobody reacts to them.

## 1. Literal procedures and calibration

```
5.1/5.2/5.8 literal, Appendix C defaults recall   0.0% | evasive   0.0% | cases/session   0.0 | false cases per 100 legit account-sessions   0.0
self-quantile 99.5%                      recall   7.8% | evasive   0.0% | cases/session   1.0 | false cases per 100 legit account-sessions   0.0
per-class k from seeded baseline         recall  88.4% | evasive  71.5% | cases/session  3.47 | false cases per 100 legit account-sessions  0.62
```
Per-class k chosen on the baseline sessions: {'exec': 0.005, 'mm': 0.005, 'prop': 0.002}

## 2. Fixed imbalance multiple k (both extensions on)

```
fixed k=0.002                            recall  91.4% | evasive  71.5% | cases/session   5.3 | false cases per 100 legit account-sessions  7.92  {"exec": 15, "mm": 21, "manip-acct": 5, "prop": 2}
fixed k=0.005                            recall  82.3% | evasive  66.3% | cases/session  2.93 | false cases per 100 legit account-sessions  0.21  {"exec": 1}
fixed k=0.01                             recall  72.7% | evasive  62.5% | cases/session  2.07 | false cases per 100 legit account-sessions   0.0  {}
fixed k=0.02                             recall  69.6% | evasive  61.2% | cases/session  1.87 | false cases per 100 legit account-sessions   0.0  {}
fixed k=0.05                             recall  68.8% | evasive  48.5% | cases/session  1.87 | false cases per 100 legit account-sessions   0.0  {}
fixed k=0.1                              recall  64.5% | evasive  22.3% | cases/session  1.87 | false cases per 100 legit account-sessions   0.0  {}
fixed k=0.2                              recall  48.0% | evasive   0.0% | cases/session  1.87 | false cases per 100 legit account-sessions   0.0  {}
fixed k=0.3                              recall  28.5% | evasive   0.0% | cases/session   1.8 | false cases per 100 legit account-sessions   0.0  {}
fixed k=0.5                              recall   7.0% | evasive   0.0% | cases/session  0.97 | false cases per 100 legit account-sessions   0.0  {}
fixed k=1.0                              recall   5.8% | evasive   0.0% | cases/session  0.87 | false cases per 100 legit account-sessions   0.0  {}
fixed k=2.0                              recall   5.8% | evasive   0.0% | cases/session  0.87 | false cases per 100 legit account-sessions   0.0  {}
```

## 3. Ablations around the per-class configuration

```
per-class k (reference)                  recall  88.4% | evasive  71.5% | cases/session  3.47 | false cases per 100 legit account-sessions  0.62
no flip extension                        recall  24.5% | evasive   8.6% | cases/session   2.5 | false cases per 100 legit account-sessions  0.62
no persistent-layering extension         recall  82.6% | evasive  71.5% | cases/session   2.6 | false cases per 100 legit account-sessions  0.62
no cross-instrument alignment            recall  88.4% | evasive  71.5% | cases/session  3.47 | false cases per 100 legit account-sessions  0.62
no exclusions                            recall  89.1% | evasive  72.2% | cases/session  3.63 | false cases per 100 legit account-sessions  0.83
fixed k=0.05 (for comparison)            recall  68.8% | evasive  48.5% | cases/session  1.87 | false cases per 100 legit account-sessions   0.0
fixed k=0.05, no exclusions              recall  68.9% | evasive  48.8% | cases/session  1.87 | false cases per 100 legit account-sessions   0.0
repetition n=1                           recall  93.4% | evasive  71.8% | cases/session  8.23 | false cases per 100 legit account-sessions 19.58
repetition 3 within 5 sessions           recall  93.1% | evasive  71.8% | cases/session  6.23 | false cases per 100 legit account-sessions  7.71
```

## 4. Recall by template, per-class configuration (detected/total)

```
chen                   57/125  45.6%
chen/evasive            2/57   3.5%
coscia                 80/89   89.9%
coscia/evasive         23/31   74.2%
oystacher             474/483  98.1%
oystacher/evasive     183/192  95.3%
sarao                  43/43   100.0%
sarao/evasive           0/11   0.0%
```

## 5. Ranking model on loose candidates (trained on the seeded baseline sessions)

Training pool 33,671 candidates (1,264 true); test pool 22,034 (1,059 true).
Average precision: model 0.993, ranking by imbalance ratio 0.915, by size asymmetry 0.156.

Top-N alerts per session (fill-triggered templates only):
```
model                N=5   recall  15.5% | all incl. evasive  14.9% | precision 100.0%
model                N=10  recall  30.6% | all incl. evasive  29.1% | precision 100.0%
model                N=20  recall  60.8% | all incl. evasive  57.3% | precision 100.0%
model                N=40  recall  97.6% | all incl. evasive  94.4% | precision  85.0%
by_imbalance_ratio   N=5   recall  21.2% | all incl. evasive  15.1% | precision 100.0%
by_imbalance_ratio   N=10  recall  42.0% | all incl. evasive  30.5% | precision 100.0%
by_imbalance_ratio   N=20  recall  68.3% | all incl. evasive  59.8% | precision  99.2%
by_imbalance_ratio   N=40  recall  94.1% | all incl. evasive  87.7% | precision  77.0%
by_size_asymmetry    N=5   recall   5.3% | all incl. evasive   4.9% | precision  45.3%
by_size_asymmetry    N=10  recall   8.6% | all incl. evasive   7.7% | precision  37.7%
by_size_asymmetry    N=20  recall  12.6% | all incl. evasive  11.3% | precision  28.5%
by_size_asymmetry    N=40  recall  17.5% | all incl. evasive  15.0% | precision  18.6%
```
At the rule's own volume (30.6 instances per session): rule recall 87.7%, precision 95.1%; model top-31 recall 88.8%, precision 96.7%.

## 6. Held-out template: can the model find a pattern it was never shown?

```
chen       n=125  model never shown it  41.6% | model trained on all  63.2% | rule  45.6%
coscia     n=89   model never shown it  75.3% | model trained on all  91.0% | rule  89.9%
oystacher  n=483  model never shown it  60.5% | model trained on all  95.0% | rule  98.1%
```

## 7. Where detection degrades (Chen-type episodes, faithful and evasive together)

```
latency    0-1      n=15   rule  33.3% | model  73.3%
latency    1-2.5    n=32   rule  62.5% | model  62.5%
latency    2.5-5    n=67   rule  49.3% | model  61.2%
latency    5-10     n=29   rule   0.0% | model  31.0%
latency    10-20    n=39   rule   2.6% | model  30.8%
spoof_qty  0-15     n=21   rule   0.0% | model   4.8%
spoof_qty  15-30    n=21   rule   0.0% | model  19.0%
spoof_qty  30-50    n=44   rule  27.3% | model  52.3%
spoof_qty  50-80    n=29   rule  48.3% | model  55.2%
spoof_qty  80-200   n=67   rule  49.3% | model  73.1%
```
