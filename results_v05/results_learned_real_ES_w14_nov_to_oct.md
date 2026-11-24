# Learned detector (v0.5), tier: real

Seed 20261123. 20 baseline and 40 test sessions, recorded ES order book (CME Globex MBO via Databento, replayed). 22 accounts, 16 legitimate. 4,698 seeded attempts in the test sessions, 1,552 of them without a fill. All numbers below are on the test sessions.

## Thresholds set on the baseline, applied to the test sessions

```
procedures, per-class multiple   completed faithful 1763/2253 (78.3%) | completed evasive 381/893 (42.7%) | no fill 47/1552 (3.0%) | all attempts 2191/4698 (46.6%)
                                 false cases per 100 legitimate account-sessions 4.53 (29 cases: {'prop': 29, 'manip-acct': 2}); flagged groups 2953, of which not seeded 753
learned detector                 completed faithful 2125/2253 (94.3%) | completed evasive 673/893 (75.4%) | no fill 1347/1552 (86.8%) | all attempts 4145/4698 (88.2%)
                                 false cases per 100 legitimate account-sessions 0.31 (2 cases: {'exec': 1, 'prop': 1}); flagged groups 4475, of which not seeded 51
learned, no threshold floor      completed faithful 2129/2253 (94.5%) | completed evasive 692/893 (77.5%) | no fill 1357/1552 (87.4%) | all attempts 4178/4698 (88.9%)
                                 false cases per 100 legitimate account-sessions 6.41 (41 cases: {'mm': 34, 'exec': 2, 'prop': 5}); flagged groups 5825, of which not seeded 1357
```

## By pattern (all attempts; completed faithful in brackets)

```
chen       learned    1113/1336 (83.3%) [622/676 (92.0%)] | procedures     417/1336 (31.2%) [362/676 (53.6%)]
coscia     learned    2235/2316 (96.5%) [883/884 (99.9%)] | procedures    1112/2316 (48.0%) [867/884 (98.1%)]
oystacher  learned      721/963 (74.9%) [565/634 (89.1%)] | procedures      601/963 (62.4%) [475/634 (74.9%)]
sarao      learned        76/83 (91.6%) [55/59 (93.2%)] | procedures        61/83 (73.5%) [59/59 (100.0%)]
```

## Equal false-case load (one threshold read off the test sessions; comparison only)

```
at most 0.5 per 100: learned all attempts 4155/4698 (88.4%), completed 2806/3146 (89.2%) | procedures (k=0.3, 0.16 per 100) all attempts 1076/4698 (22.9%), completed 1065/3146 (33.9%)
at most 1.0 per 100: learned all attempts 4165/4698 (88.7%), completed 2813/3146 (89.4%) | procedures (k=0.3, 0.16 per 100) all attempts 1076/4698 (22.9%), completed 1065/3146 (33.9%)
at most 2.0 per 100: learned all attempts 4168/4698 (88.7%), completed 2814/3146 (89.4%) | procedures (k=0.2, 1.88 per 100) all attempts 1583/4698 (33.7%), completed 1553/3146 (49.4%)
```

## A pattern the detector was never shown

Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.

```
chen       learned: all attempts 767/1336 (57.4%), completed faithful 446/676 (66.0%) | procedures: completed faithful 362/676 (53.6%) | false cases per 100: 0.0 (without the floor: 985/1336 (73.7%), 3.59 per 100)
coscia     learned: all attempts 2235/2316 (96.5%), completed faithful 883/884 (99.9%) | procedures: completed faithful 867/884 (98.1%) | false cases per 100: 0.0 (without the floor: 2235/2316 (96.5%), 4.22 per 100)
oystacher  learned: all attempts 492/963 (51.1%), completed faithful 389/634 (61.4%) | procedures: completed faithful 475/634 (74.9%) | false cases per 100: 0.16 (without the floor: 594/963 (61.7%), 6.25 per 100)
sarao      learned: all attempts 76/83 (91.6%), completed faithful 55/59 (93.2%) | procedures: completed faithful 59/59 (100.0%) | false cases per 100: 0.16 (without the floor: 79/83 (95.2%), 8.91 per 100)
```

## What the highest-scoring alert in each account rests on

Drop in the score when one part of the evidence is replaced by the typical legitimate value.

```
M_COSCIA       score 1.000 seeded | the account's session as a whole +0.67, size against the displayed book +0.11, what the account did on this side afterwards +0.01
M_CHEN_HI      score 1.000 seeded | the account's session as a whole +0.62, size against the displayed book +0.12, what the account did on this side afterwards +0.01
M_SARAO        score 1.000 seeded | the account's session as a whole +0.58, size against the displayed book +0.16, time at rest +0.00
M_OYST         score 0.998 seeded | the account's session as a whole +0.77, the account's interest and executions on the other side +0.07, size against the displayed book +0.06
M_CHEN_LO      score 0.992 seeded | the account's session as a whole +0.62, size against the displayed book +0.08, what the account did on this side afterwards +0.00
M_MM_CHEN      score 0.961 seeded | size against the displayed book +0.85, the account's session as a whole +0.58, what the account did on this side afterwards +0.05
DISC_6         score 0.758 NOT seeded | the account's session as a whole +0.67, what the account did on this side afterwards +0.01, the account's interest and executions on the other side +0.01
DISC_2         score 0.625 NOT seeded | the account's session as a whole +0.55, what the account did on this side afterwards +0.01, the account's interest and executions on the other side +0.01
DISC_7         score 0.620 NOT seeded | the account's session as a whole +0.51, what the account did on this side afterwards +0.01, executions on these orders +0.00
EXEC_3         score 0.512 NOT seeded | size against the displayed book +0.39, the account's session as a whole +0.39, what the account did on this side afterwards +0.09
DISC_5         score 0.436 NOT seeded | the account's session as a whole +0.25, executions on these orders +0.14, what the account did on this side afterwards +0.04
MM_SKEW_SLOW_1 score 0.249 NOT seeded | size against the displayed book +0.18, the account's session as a whole +0.05, what the account did on this side afterwards +0.02
```
