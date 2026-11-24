# Learned detector (v0.5), tier: std

Seed 20261123. 30 baseline and 30 test sessions, simulated market. 26 accounts, 18 legitimate. 4,106 seeded attempts in the test sessions, 1,840 of them without a fill. All numbers below are on the test sessions.

## Thresholds set on the baseline, applied to the test sessions

```
procedures, per-class multiple   completed faithful 1235/1618 (76.3%) | completed evasive 261/648 (40.3%) | no fill 99/1840 (5.4%) | all attempts 1595/4106 (38.8%)
                                 false cases per 100 legitimate account-sessions 0.93 (5 cases: {'prop': 5}); flagged groups 1687, of which not seeded 80
learned detector                 completed faithful 1581/1618 (97.7%) | completed evasive 581/648 (89.7%) | no fill 1827/1840 (99.3%) | all attempts 3989/4106 (97.2%)
                                 false cases per 100 legitimate account-sessions 0.37 (2 cases: {'mm': 1, 'prop': 1}); flagged groups 4463, of which not seeded 40
learned, no threshold floor      completed faithful 1586/1618 (98.0%) | completed evasive 588/648 (90.7%) | no fill 1836/1840 (99.8%) | all attempts 4010/4106 (97.7%)
                                 false cases per 100 legitimate account-sessions 2.96 (16 cases: {'prop': 8, 'mm': 3, 'basis': 5}); flagged groups 4831, of which not seeded 385
```

## By pattern (all attempts; completed faithful in brackets)

```
chen       learned    1194/1246 (95.8%) [607/618 (98.2%)] | procedures     381/1246 (30.6%) [340/618 (55.0%)]
coscia     learned   1907/1907 (100.0%) [333/333 (100.0%)] | procedures     480/1907 (25.2%) [325/333 (97.6%)]
oystacher  learned      654/680 (96.2%) [483/489 (98.8%)] | procedures      630/680 (92.6%) [476/489 (97.3%)]
sarao      learned        65/73 (89.0%) [45/48 (93.8%)] | procedures        51/73 (69.9%) [48/48 (100.0%)]
lebental   learned      169/200 (84.5%) [113/130 (86.9%)] | procedures       53/200 (26.5%) [46/130 (35.4%)]
```

## Equal false-case load (one threshold read off the test sessions; comparison only)

```
at most 0.5 per 100: learned all attempts 3998/4106 (97.4%), completed 2169/2266 (95.7%) | procedures (k=0.3, 0.0 per 100) all attempts 1082/4106 (26.4%), completed 1013/2266 (44.7%)
at most 1.0 per 100: learned all attempts 4008/4106 (97.6%), completed 2172/2266 (95.9%) | procedures (k=0.3, 0.0 per 100) all attempts 1082/4106 (26.4%), completed 1013/2266 (44.7%)
at most 2.0 per 100: learned all attempts 4010/4106 (97.7%), completed 2174/2266 (95.9%) | procedures (k=0.2, 1.11 per 100) all attempts 1423/4106 (34.7%), completed 1331/2266 (58.7%)
```

## A pattern the detector was never shown

Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.

```
chen       learned: all attempts 1059/1246 (85.0%), completed faithful 581/618 (94.0%) | procedures: completed faithful 340/618 (55.0%) | false cases per 100: 0.0 (without the floor: 1165/1246 (93.5%), 1.85 per 100)
coscia     learned: all attempts 1907/1907 (100.0%), completed faithful 333/333 (100.0%) | procedures: completed faithful 325/333 (97.6%) | false cases per 100: 0.19 (without the floor: 1907/1907 (100.0%), 2.96 per 100)
oystacher  learned: all attempts 599/680 (88.1%), completed faithful 463/489 (94.7%) | procedures: completed faithful 476/489 (97.3%) | false cases per 100: 0.19 (without the floor: 647/680 (95.1%), 1.48 per 100)
sarao      learned: all attempts 66/73 (90.4%), completed faithful 45/48 (93.8%) | procedures: completed faithful 48/48 (100.0%) | false cases per 100: 0.0 (without the floor: 70/73 (95.9%), 2.04 per 100)
lebental   learned: all attempts 132/200 (66.0%), completed faithful 91/130 (70.0%) | procedures: completed faithful 46/130 (35.4%) | false cases per 100: 0.19 (without the floor: 179/200 (89.5%), 2.96 per 100)
```

## What the highest-scoring alert in each account rests on

Drop in the score when one part of the evidence is replaced by the typical legitimate value.

```
M_COSCIA       score 1.000 seeded | size against the displayed book +0.20, the account's session as a whole +0.11, what the account did on this side afterwards +0.02
M_CHEN_HI      score 1.000 seeded | the account's session as a whole +0.07, size against the displayed book +0.05, what the account did on this side afterwards +0.01
M_OYST         score 1.000 seeded | size against the displayed book +0.10, the account's session as a whole +0.06, the account's interest and executions on the other side +0.03
M_MM_CHEN      score 1.000 seeded | size against the displayed book +0.36, the account's session as a whole +0.07, what the account did on this side afterwards +0.03
M_SARAO        score 0.999 seeded | size against the displayed book +0.44, the account's session as a whole +0.15, what the account did on this side afterwards +0.02
M_CHEN_LO      score 0.998 seeded | the account's session as a whole +0.12, size against the displayed book +0.09, the account's interest and executions on the other side +0.01
M_LEB          score 0.993 seeded | size against the displayed book +0.09, the account's session as a whole +0.07, what the account did on this side afterwards +0.02
M_MM_LEB       score 0.989 seeded | size against the displayed book +0.37, the account's session as a whole +0.05, what the account did on this side afterwards +0.05
DISC_2         score 0.782 NOT seeded | size against the displayed book +0.39, the account's session as a whole +0.02, the account's interest and executions on the other side +0.01
DISC_7         score 0.677 NOT seeded | size against the displayed book +0.36, the account's session as a whole +0.12, executions on these orders +0.00
DISC_3         score 0.634 NOT seeded | the account's interest and executions on the other side +0.21, size against the displayed book +0.18, what the account did on this side afterwards +0.04
DISC_8         score 0.596 NOT seeded | size against the displayed book +0.30, the account's session as a whole +0.21, executions on these orders +0.05
```
