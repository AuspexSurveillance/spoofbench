# Learned detector (v0.5), tier: stress

Seed 20261123. 30 baseline and 30 test sessions, simulated market. 35 accounts, 24 legitimate. 5,276 seeded attempts in the test sessions, 2,127 of them without a fill. All numbers below are on the test sessions.

Never used in training (accounts that run them are left out of the baseline): ada_cross, ada_flip, ada_same.

## Thresholds set on the baseline, applied to the test sessions

```
procedures, per-class multiple   completed faithful 1829/2255 (81.1%) | completed evasive 453/894 (50.7%) | no fill 100/2127 (4.7%) | all attempts 2382/5276 (45.1%)
                                 false cases per 100 legitimate account-sessions 1.81 (13 cases: {'exec': 10, 'prop': 3}); flagged groups 2562, of which not seeded 138
learned detector                 completed faithful 2233/2255 (99.0%) | completed evasive 836/894 (93.5%) | no fill 2111/2127 (99.2%) | all attempts 5180/5276 (98.2%)
                                 false cases per 100 legitimate account-sessions 0.0 (0 cases: {}); flagged groups 6787, of which not seeded 327
learned, no threshold floor      completed faithful 2237/2255 (99.2%) | completed evasive 843/894 (94.3%) | no fill 2118/2127 (99.6%) | all attempts 5198/5276 (98.5%)
                                 false cases per 100 legitimate account-sessions 1.81 (13 cases: {'basis': 3, 'prop': 9, 'mm': 1}); flagged groups 8063, of which not seeded 1403
```

## By pattern (all attempts; completed faithful in brackets)

```
chen       learned    1156/1190 (97.1%) [494/496 (99.6%)] | procedures     295/1190 (24.8%) [262/496 (52.8%)]
coscia     learned   1843/1843 (100.0%) [243/243 (100.0%)] | procedures     329/1843 (17.9%) [231/243 (95.1%)]
oystacher  learned      705/719 (98.1%) [500/502 (99.6%)] | procedures      673/719 (93.6%) [490/502 (97.6%)]
sarao      learned        62/72 (86.1%) [46/53 (86.8%)] | procedures        53/72 (73.6%) [47/53 (88.7%)]
lebental   learned      172/200 (86.0%) [117/126 (92.9%)] | procedures       57/200 (28.5%) [51/126 (40.5%)]
ada_same   learned      572/580 (98.6%) [366/368 (99.5%)] | procedures      363/580 (62.6%) [302/368 (82.1%)]
ada_flip   learned      436/437 (99.8%) [309/309 (100.0%)] | procedures      432/437 (98.9%) [307/309 (99.4%)]
ada_cross  learned      234/235 (99.6%) [158/158 (100.0%)] | procedures      180/235 (76.6%) [139/158 (88.0%)]
```

## Equal false-case load (one threshold read off the test sessions; comparison only)

```
at most 0.5 per 100: learned all attempts 5189/5276 (98.4%), completed 3074/3149 (97.6%) | procedures: no fixed multiple stays under this rate
at most 1.0 per 100: learned all attempts 5194/5276 (98.4%), completed 3078/3149 (97.7%) | procedures: no fixed multiple stays under this rate
at most 2.0 per 100: learned all attempts 5198/5276 (98.5%), completed 3081/3149 (97.8%) | procedures (k=0.5, 1.53 per 100) all attempts 1151/5276 (21.8%), completed 1126/3149 (35.8%)
```

## A pattern the detector was never shown

Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.

```
chen       learned: all attempts 556/1190 (46.7%), completed faithful 308/496 (62.1%) | procedures: completed faithful 262/496 (52.8%) | false cases per 100: 0.0 (without the floor: 1045/1190 (87.8%), 1.11 per 100)
coscia     learned: all attempts 1843/1843 (100.0%), completed faithful 243/243 (100.0%) | procedures: completed faithful 231/243 (95.1%) | false cases per 100: 0.0 (without the floor: 1843/1843 (100.0%), 1.39 per 100)
oystacher  learned: all attempts 651/719 (90.5%), completed faithful 482/502 (96.0%) | procedures: completed faithful 490/502 (97.6%) | false cases per 100: 0.0 (without the floor: 690/719 (96.0%), 1.39 per 100)
sarao      learned: all attempts 53/72 (73.6%), completed faithful 43/53 (81.1%) | procedures: completed faithful 47/53 (88.7%) | false cases per 100: 0.0 (without the floor: 67/72 (93.1%), 1.67 per 100)
lebental   learned: all attempts 135/200 (67.5%), completed faithful 94/126 (74.6%) | procedures: completed faithful 51/126 (40.5%) | false cases per 100: 0.0 (without the floor: 171/200 (85.5%), 0.83 per 100)
```

## A legitimate account type the detector was never shown

```
Scalper        learned: 60 of 60 account-sessions flagged | procedures: 1 of 60
LeggedHedger   learned: 56 of 60 account-sessions flagged | procedures: 60 of 60
BlockWorker    learned: 60 of 60 account-sessions flagged | procedures: 15 of 60
```

## What the highest-scoring alert in each account rests on

Drop in the score when one part of the evidence is replaced by the typical legitimate value.

```
M_COSCIA       score 1.000 seeded | size against the displayed book +0.18, the account's session as a whole +0.18, what the account did on this side afterwards +0.00
M_OYST         score 1.000 seeded | size against the displayed book +0.16, the account's session as a whole +0.08, the account's interest and executions on the other side +0.06
M_CHEN_HI      score 1.000 seeded | the account's session as a whole +0.36, size against the displayed book +0.06, the account's interest and executions on the other side +0.01
M_MM_CHEN      score 1.000 seeded | size against the displayed book +0.39, the account's session as a whole +0.12, the account's interest and executions on the other side +0.02
M_MM_LEB       score 0.999 seeded | size against the displayed book +0.44, the account's session as a whole +0.08, the account's interest and executions on the other side +0.04
M_ADA_FLIP     score 0.994 seeded | the account's session as a whole +0.32, size against the displayed book +0.17, the account's interest and executions on the other side +0.07
M_SARAO        score 0.992 seeded | size against the displayed book +0.74, the account's session as a whole +0.17, the account's interest and executions on the other side +0.03
M_CHEN_LO      score 0.991 seeded | the account's session as a whole +0.21, size against the displayed book +0.11, time at rest +0.00
M_LEB          score 0.978 seeded | size against the displayed book +0.16, the account's session as a whole +0.06, the account's interest and executions on the other side +0.01
M_ADA_SAME     score 0.973 seeded | size against the displayed book +0.19, the account's session as a whole +0.13, executions on these orders +0.00
M_ADA_X        score 0.971 seeded | size against the displayed book +0.19, the account's session as a whole +0.08, time at rest +0.00
EXEC_2         score 0.565 NOT seeded | size against the displayed book +0.38, what the account did on this side afterwards +0.01, the account's session as a whole +0.01
```
