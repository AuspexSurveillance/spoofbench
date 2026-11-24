# Learned detector (v0.5), tier: real

Seed 20261123. 60 baseline and 60 test sessions, recorded ZN order book (CME Globex MBO via Databento, replayed). 22 accounts, 16 legitimate. 7,546 seeded attempts in the test sessions, 5,499 of them without a fill. All numbers below are on the test sessions.

## Thresholds set on the baseline, applied to the test sessions

```
procedures, per-class multiple   completed faithful 1258/1420 (88.6%) | completed evasive 440/627 (70.2%) | no fill 94/5499 (1.7%) | all attempts 1792/7546 (23.7%)
                                 false cases per 100 legitimate account-sessions 0.83 (8 cases: {'mm': 8}); flagged groups 1905, of which not seeded 110
learned detector                 completed faithful 1413/1420 (99.5%) | completed evasive 612/627 (97.6%) | no fill 5478/5499 (99.6%) | all attempts 7503/7546 (99.4%)
                                 false cases per 100 legitimate account-sessions 0.0 (0 cases: {}); flagged groups 9549, of which not seeded 52
learned, no threshold floor      completed faithful 1414/1420 (99.6%) | completed evasive 614/627 (97.9%) | no fill 5480/5499 (99.7%) | all attempts 7508/7546 (99.5%)
                                 false cases per 100 legitimate account-sessions 2.08 (20 cases: {'prop': 14, 'mm': 3, 'exec': 3}); flagged groups 10566, of which not seeded 1059
```

## By pattern (all attempts; completed faithful in brackets)

```
chen       learned    2444/2458 (99.4%) [257/257 (100.0%)] | procedures      156/2458 (6.3%) [117/257 (45.5%)]
coscia     learned   3538/3538 (100.0%) [132/132 (100.0%)] | procedures      176/3538 (5.0%) [114/132 (86.4%)]
oystacher  learned    1390/1404 (99.0%) [957/957 (100.0%)] | procedures    1367/1404 (97.4%) [953/957 (99.6%)]
sarao      learned      131/146 (89.7%) [67/74 (90.5%)] | procedures       93/146 (63.7%) [74/74 (100.0%)]
```

## Equal false-case load (one threshold read off the test sessions; comparison only)

```
at most 0.5 per 100: learned all attempts 7505/7546 (99.5%), completed 2026/2047 (99.0%) | procedures (k=0.005, 0.31 per 100) all attempts 1529/7546 (20.3%), completed 1496/2047 (73.1%)
at most 1.0 per 100: learned all attempts 7506/7546 (99.5%), completed 2027/2047 (99.0%) | procedures (k=0.005, 0.31 per 100) all attempts 1529/7546 (20.3%), completed 1496/2047 (73.1%)
at most 2.0 per 100: learned all attempts 7508/7546 (99.5%), completed 2029/2047 (99.1%) | procedures (k=0.002, 1.98 per 100) all attempts 1792/7546 (23.7%), completed 1698/2047 (83.0%)
```

## A pattern the detector was never shown

Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.

```
chen       learned: all attempts 1407/2458 (57.2%), completed faithful 133/257 (51.8%) | procedures: completed faithful 117/257 (45.5%) | false cases per 100: 0.0 (without the floor: 2364/2458 (96.2%), 2.81 per 100)
coscia     learned: all attempts 3538/3538 (100.0%), completed faithful 132/132 (100.0%) | procedures: completed faithful 114/132 (86.4%) | false cases per 100: 0.0 (without the floor: 3538/3538 (100.0%), 2.19 per 100)
oystacher  learned: all attempts 938/1404 (66.8%), completed faithful 644/957 (67.3%) | procedures: completed faithful 953/957 (99.6%) | false cases per 100: 0.0 (without the floor: 1391/1404 (99.1%), 2.08 per 100)
sarao      learned: all attempts 131/146 (89.7%), completed faithful 67/74 (90.5%) | procedures: completed faithful 74/74 (100.0%) | false cases per 100: 0.0 (without the floor: 144/146 (98.6%), 2.81 per 100)
```

## What the highest-scoring alert in each account rests on

Drop in the score when one part of the evidence is replaced by the typical legitimate value.

```
M_MM_CHEN      score 1.000 seeded | size against the displayed book +0.25, the account's session as a whole +0.07, the account's interest and executions on the other side +0.01
M_COSCIA       score 1.000 seeded | size against the displayed book +0.87, the account's session as a whole +0.10, time at rest +0.02
M_CHEN_HI      score 1.000 seeded | size against the displayed book +0.37, the account's session as a whole +0.08, time at rest +0.01
M_CHEN_LO      score 1.000 seeded | size against the displayed book +0.44, the account's session as a whole +0.08, time at rest +0.01
M_OYST         score 1.000 seeded | size against the displayed book +0.70, the account's session as a whole +0.13, the account's interest and executions on the other side +0.07
M_SARAO        score 1.000 seeded | size against the displayed book +0.89, the account's session as a whole +0.09, the account's interest and executions on the other side +0.01
DISC_3         score 0.232 NOT seeded | size against the displayed book +0.21, the account's interest and executions on the other side +0.02, what the account did on this side afterwards +0.00
```
