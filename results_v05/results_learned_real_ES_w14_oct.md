# Learned detector (v0.5), tier: real

Seed 20261123. 20 baseline and 20 test sessions, recorded ES order book (CME Globex MBO via Databento, replayed). 22 accounts, 16 legitimate. 2,313 seeded attempts in the test sessions, 726 of them without a fill. All numbers below are on the test sessions.

## Thresholds set on the baseline, applied to the test sessions

```
procedures, per-class multiple   completed faithful 880/1125 (78.2%) | completed evasive 179/462 (38.7%) | no fill 26/726 (3.6%) | all attempts 1085/2313 (46.9%)
                                 false cases per 100 legitimate account-sessions 0.31 (1 cases: {'prop': 1}); flagged groups 1276, of which not seeded 188
learned detector                 completed faithful 1047/1125 (93.1%) | completed evasive 352/462 (76.2%) | no fill 626/726 (86.2%) | all attempts 2025/2313 (87.5%)
                                 false cases per 100 legitimate account-sessions 0.31 (1 cases: {'prop': 1}); flagged groups 2176, of which not seeded 20
learned, no threshold floor      completed faithful 1051/1125 (93.4%) | completed evasive 356/462 (77.1%) | no fill 631/726 (86.9%) | all attempts 2038/2313 (88.1%)
                                 false cases per 100 legitimate account-sessions 2.81 (9 cases: {'prop': 3, 'exec': 4, 'mm': 2}); flagged groups 2391, of which not seeded 222
```

## By pattern (all attempts; completed faithful in brackets)

```
chen       learned      533/645 (82.6%) [296/329 (90.0%)] | procedures      217/645 (33.6%) [186/329 (56.5%)]
coscia     learned    1111/1154 (96.3%) [453/454 (99.8%)] | procedures     570/1154 (49.4%) [444/454 (97.8%)]
oystacher  learned      344/474 (72.6%) [273/315 (86.7%)] | procedures      271/474 (57.2%) [223/315 (70.8%)]
sarao      learned        37/40 (92.5%) [25/27 (92.6%)] | procedures        27/40 (67.5%) [27/27 (100.0%)]
```

## Equal false-case load (one threshold read off the test sessions; comparison only)

```
at most 0.5 per 100: learned all attempts 2025/2313 (87.5%), completed 1399/1587 (88.2%) | procedures (k=0.3, 0.0 per 100) all attempts 592/2313 (25.6%), completed 585/1587 (36.9%)
at most 1.0 per 100: learned all attempts 2034/2313 (87.9%), completed 1404/1587 (88.5%) | procedures (k=0.3, 0.0 per 100) all attempts 592/2313 (25.6%), completed 585/1587 (36.9%)
at most 2.0 per 100: learned all attempts 2035/2313 (88.0%), completed 1404/1587 (88.5%) | procedures (k=0.3, 0.0 per 100) all attempts 592/2313 (25.6%), completed 585/1587 (36.9%)
```

## A pattern the detector was never shown

Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.

```
chen       learned: all attempts 322/645 (49.9%), completed faithful 194/329 (59.0%) | procedures: completed faithful 186/329 (56.5%) | false cases per 100: 0.0 (without the floor: 492/645 (76.3%), 4.69 per 100)
coscia     learned: all attempts 1111/1154 (96.3%), completed faithful 453/454 (99.8%) | procedures: completed faithful 444/454 (97.8%) | false cases per 100: 0.31 (without the floor: 1111/1154 (96.3%), 2.19 per 100)
oystacher  learned: all attempts 233/474 (49.2%), completed faithful 182/315 (57.8%) | procedures: completed faithful 223/315 (70.8%) | false cases per 100: 0.62 (without the floor: 314/474 (66.2%), 3.12 per 100)
sarao      learned: all attempts 37/40 (92.5%), completed faithful 25/27 (92.6%) | procedures: completed faithful 27/27 (100.0%) | false cases per 100: 0.31 (without the floor: 40/40 (100.0%), 4.06 per 100)
```

## What the highest-scoring alert in each account rests on

Drop in the score when one part of the evidence is replaced by the typical legitimate value.

```
M_COSCIA       score 1.000 seeded | size against the displayed book +0.42, the account's session as a whole +0.24, what the account did on this side afterwards +0.00
M_CHEN_HI      score 0.999 seeded | the account's session as a whole +0.21, size against the displayed book +0.11, the account's interest and executions on the other side +0.01
M_OYST         score 0.999 seeded | the account's session as a whole +0.17, size against the displayed book +0.14, the account's interest and executions on the other side +0.06
M_SARAO        score 0.998 seeded | size against the displayed book +0.49, the account's session as a whole +0.18, what the account did on this side afterwards +0.00
M_CHEN_LO      score 0.996 seeded | size against the displayed book +0.14, the account's session as a whole +0.10, the account's interest and executions on the other side +0.00
M_MM_CHEN      score 0.978 seeded | size against the displayed book +0.92, the account's session as a whole +0.10, time at rest +0.02
MM_SKEW_SLOW_1 score 0.277 NOT seeded | size against the displayed book +0.25, the account's session as a whole +0.06, what the account did on this side afterwards +0.02
DISC_5         score 0.249 NOT seeded | the account's session as a whole +0.23, executions on these orders +0.00, what the account did on this side afterwards -0.00
MM_SKEW_FAST   score 0.239 NOT seeded | size against the displayed book +0.24, the account's interest and executions on the other side +0.01, what the account did on this side afterwards +0.00
```
