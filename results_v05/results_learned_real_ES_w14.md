# Learned detector (v0.5), tier: real

Seed 20261123. 10 baseline and 10 test sessions, recorded ES order book (CME Globex MBO via Databento, replayed). 22 accounts, 16 legitimate. 1,101 seeded attempts in the test sessions, 266 of them without a fill. All numbers below are on the test sessions.

## Thresholds set on the baseline, applied to the test sessions

```
procedures, per-class multiple   completed faithful 430/577 (74.5%) | completed evasive 87/258 (33.7%) | no fill 4/266 (1.5%) | all attempts 521/1101 (47.3%)
                                 false cases per 100 legitimate account-sessions 1.25 (2 cases: {'prop': 2}); flagged groups 663, of which not seeded 137
learned detector                 completed faithful 512/577 (88.7%) | completed evasive 166/258 (64.3%) | no fill 166/266 (62.4%) | all attempts 844/1101 (76.7%)
                                 false cases per 100 legitimate account-sessions 0.0 (0 cases: {}); flagged groups 886, of which not seeded 12
learned, no threshold floor      completed faithful 516/577 (89.4%) | completed evasive 172/258 (66.7%) | no fill 169/266 (63.5%) | all attempts 857/1101 (77.8%)
                                 false cases per 100 legitimate account-sessions 0.0 (0 cases: {}); flagged groups 980, of which not seeded 90
```

## By pattern (all attempts; completed faithful in brackets)

```
chen       learned      188/291 (64.6%) [118/155 (76.1%)] | procedures       76/291 (26.1%) [69/155 (44.5%)]
coscia     learned      493/549 (89.8%) [276/276 (100.0%)] | procedures      325/549 (59.2%) [268/276 (97.1%)]
oystacher  learned      142/235 (60.4%) [104/128 (81.2%)] | procedures      102/235 (43.4%) [75/128 (58.6%)]
sarao      learned        21/26 (80.8%) [14/18 (77.8%)] | procedures        18/26 (69.2%) [18/18 (100.0%)]
```

## Equal false-case load (one threshold read off the test sessions; comparison only)

```
at most 0.5 per 100: learned all attempts 857/1101 (77.8%), completed 688/835 (82.4%) | procedures (k=0.5, 0.0 per 100) all attempts 278/1101 (25.2%), completed 276/835 (33.1%)
at most 1.0 per 100: learned all attempts 857/1101 (77.8%), completed 688/835 (82.4%) | procedures (k=0.5, 0.0 per 100) all attempts 278/1101 (25.2%), completed 276/835 (33.1%)
at most 2.0 per 100: learned all attempts 858/1101 (77.9%), completed 689/835 (82.5%) | procedures (k=0.5, 0.0 per 100) all attempts 278/1101 (25.2%), completed 276/835 (33.1%)
```

## A pattern the detector was never shown

Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.

```
chen       learned: all attempts 124/291 (42.6%), completed faithful 81/155 (52.3%) | procedures: completed faithful 69/155 (44.5%) | false cases per 100: 0.0 (without the floor: 159/291 (54.6%), 0.0 per 100)
coscia     learned: all attempts 489/549 (89.1%), completed faithful 276/276 (100.0%) | procedures: completed faithful 268/276 (97.1%) | false cases per 100: 0.0 (without the floor: 493/549 (89.8%), 2.5 per 100)
oystacher  learned: all attempts 100/235 (42.6%), completed faithful 74/128 (57.8%) | procedures: completed faithful 75/128 (58.6%) | false cases per 100: 0.62 (without the floor: 104/235 (44.3%), 0.62 per 100)
sarao      learned: all attempts 21/26 (80.8%), completed faithful 14/18 (77.8%) | procedures: completed faithful 18/18 (100.0%) | false cases per 100: 0.62 (without the floor: 22/26 (84.6%), 1.25 per 100)
```

## What the highest-scoring alert in each account rests on

Drop in the score when one part of the evidence is replaced by the typical legitimate value.

```
M_COSCIA       score 1.000 seeded | the account's session as a whole +0.86, size against the displayed book +0.31, what the account did on this side afterwards +0.01
M_OYST         score 0.995 seeded | the account's session as a whole +0.77, size against the displayed book +0.07, the account's interest and executions on the other side +0.06
M_SARAO        score 0.992 seeded | size against the displayed book +0.68, the account's session as a whole +0.54, time at rest +0.01
M_CHEN_HI      score 0.991 seeded | the account's session as a whole +0.70, size against the displayed book +0.10, what the account did on this side afterwards +0.01
M_CHEN_LO      score 0.945 seeded | the account's session as a whole +0.64, size against the displayed book +0.60, what the account did on this side afterwards +0.01
M_MM_CHEN      score 0.875 seeded | size against the displayed book +0.79, the account's session as a whole +0.54, time at rest +0.09
DISC_7         score 0.264 NOT seeded | the account's session as a whole +0.06, executions on these orders -0.00, what the account did on this side afterwards -0.01
DISC_3         score 0.243 NOT seeded | the account's session as a whole +0.10, executions on these orders +0.03, what the account did on this side afterwards -0.00
DISC_4         score 0.238 NOT seeded | the account's session as a whole +0.05, what the account did on this side afterwards +0.00, executions on these orders +0.00
```
