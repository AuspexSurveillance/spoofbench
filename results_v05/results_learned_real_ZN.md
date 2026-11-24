# Learned detector (v0.5), tier: real

Seed 20261123. 30 baseline and 30 test sessions, recorded ZN order book (CME Globex MBO via Databento, replayed). 22 accounts, 16 legitimate. 3,794 seeded attempts in the test sessions, 2,763 of them without a fill. All numbers below are on the test sessions.

## Thresholds set on the baseline, applied to the test sessions

```
procedures, per-class multiple   completed faithful 654/740 (88.4%) | completed evasive 208/291 (71.5%) | no fill 60/2763 (2.2%) | all attempts 922/3794 (24.3%)
                                 false cases per 100 legitimate account-sessions 0.62 (3 cases: {'prop': 2, 'exec': 1, 'manip-acct': 1}); flagged groups 968, of which not seeded 45
learned detector                 completed faithful 737/740 (99.6%) | completed evasive 282/291 (96.9%) | no fill 2751/2763 (99.6%) | all attempts 3770/3794 (99.4%)
                                 false cases per 100 legitimate account-sessions 0.0 (0 cases: {}); flagged groups 4733, of which not seeded 15
learned, no threshold floor      completed faithful 737/740 (99.6%) | completed evasive 283/291 (97.3%) | no fill 2755/2763 (99.7%) | all attempts 3775/3794 (99.5%)
                                 false cases per 100 legitimate account-sessions 1.04 (5 cases: {'exec': 2, 'mm': 3}); flagged groups 4895, of which not seeded 170
```

## By pattern (all attempts; completed faithful in brackets)

```
chen       learned    1179/1191 (99.0%) [125/125 (100.0%)] | procedures       84/1191 (7.1%) [57/125 (45.6%)]
coscia     learned   1855/1855 (100.0%) [89/89 (100.0%)] | procedures      131/1855 (7.1%) [80/89 (89.9%)]
oystacher  learned      671/679 (98.8%) [481/483 (99.6%)] | procedures      657/679 (96.8%) [474/483 (98.1%)]
sarao      learned        65/69 (94.2%) [42/43 (97.7%)] | procedures        50/69 (72.5%) [43/43 (100.0%)]
```

## Equal false-case load (one threshold read off the test sessions; comparison only)

```
at most 0.5 per 100: learned all attempts 3774/3794 (99.5%), completed 1020/1031 (98.9%) | procedures (k=0.005, 0.21 per 100) all attempts 838/3794 (22.1%), completed 802/1031 (77.8%)
at most 1.0 per 100: learned all attempts 3775/3794 (99.5%), completed 1020/1031 (98.9%) | procedures (k=0.005, 0.21 per 100) all attempts 838/3794 (22.1%), completed 802/1031 (77.8%)
at most 2.0 per 100: learned all attempts 3777/3794 (99.6%), completed 1020/1031 (98.9%) | procedures (k=0.005, 0.21 per 100) all attempts 838/3794 (22.1%), completed 802/1031 (77.8%)
```

## A pattern the detector was never shown

Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.

```
chen       learned: all attempts 781/1191 (65.6%), completed faithful 81/125 (64.8%) | procedures: completed faithful 57/125 (45.6%) | false cases per 100: 0.0 (without the floor: 1128/1191 (94.7%), 12.71 per 100)
coscia     learned: all attempts 1855/1855 (100.0%), completed faithful 89/89 (100.0%) | procedures: completed faithful 80/89 (89.9%) | false cases per 100: 0.0 (without the floor: 1855/1855 (100.0%), 0.62 per 100)
oystacher  learned: all attempts 458/679 (67.5%), completed faithful 325/483 (67.3%) | procedures: completed faithful 474/483 (98.1%) | false cases per 100: 0.0 (without the floor: 671/679 (98.8%), 1.04 per 100)
sarao      learned: all attempts 65/69 (94.2%), completed faithful 42/43 (97.7%) | procedures: completed faithful 43/43 (100.0%) | false cases per 100: 0.0 (without the floor: 65/69 (94.2%), 1.04 per 100)
```

## What the highest-scoring alert in each account rests on

Drop in the score when one part of the evidence is replaced by the typical legitimate value.

```
M_COSCIA       score 1.000 seeded | size against the displayed book +0.84, the account's session as a whole +0.29, time at rest +0.01
M_CHEN_HI      score 1.000 seeded | size against the displayed book +0.30, the account's session as a whole +0.19, time at rest +0.00
M_CHEN_LO      score 1.000 seeded | size against the displayed book +0.32, the account's session as a whole +0.23, time at rest +0.00
M_OYST         score 1.000 seeded | size against the displayed book +0.68, the account's session as a whole +0.10, the account's interest and executions on the other side +0.05
M_MM_CHEN      score 1.000 seeded | size against the displayed book +0.36, the account's session as a whole +0.13, the account's interest and executions on the other side +0.01
M_SARAO        score 1.000 seeded | size against the displayed book +0.89, the account's session as a whole +0.35, the account's interest and executions on the other side +0.01
DISC_4         score 0.278 NOT seeded | size against the displayed book +0.23, executions on these orders +0.00, what the account did on this side afterwards -0.04
```
