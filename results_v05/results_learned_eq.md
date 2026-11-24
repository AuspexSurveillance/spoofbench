# Learned detector (v0.5), tier: eq

Seed 20261123. 30 baseline and 30 test sessions, simulated market. 30 accounts, 18 legitimate. 6,384 seeded attempts in the test sessions, 2,823 of them without a fill. All numbers below are on the test sessions.

Never used in training (accounts that run them are left out of the baseline): hold, milrud, trillium.

## Thresholds set on the baseline, applied to the test sessions

```
procedures, per-class multiple   completed faithful 1607/2506 (64.1%) | completed evasive 283/1055 (26.8%) | no fill 104/2823 (3.7%) | all attempts 1994/6384 (31.2%)
                                 false cases per 100 legitimate account-sessions 0.74 (4 cases: {'prop': 3, 'manip-acct': 1, 'mm': 1}); flagged groups 2175, of which not seeded 138
learned detector                 completed faithful 2488/2506 (99.3%) | completed evasive 938/1055 (88.9%) | no fill 2791/2823 (98.9%) | all attempts 6217/6384 (97.4%)
                                 false cases per 100 legitimate account-sessions 0.0 (0 cases: {}); flagged groups 6788, of which not seeded 110
learned, no threshold floor      completed faithful 2489/2506 (99.3%) | completed evasive 976/1055 (92.5%) | no fill 2800/2823 (99.2%) | all attempts 6265/6384 (98.1%)
                                 false cases per 100 legitimate account-sessions 1.85 (10 cases: {'manip-acct': 10, 'mm': 3, 'prop': 7}); flagged groups 8394, of which not seeded 1665
```

## By pattern (all attempts; completed faithful in brackets)

```
chen       learned    1182/1221 (96.8%) [564/570 (98.9%)] | procedures     418/1221 (34.2%) [377/570 (66.1%)]
coscia     learned   1824/1824 (100.0%) [283/283 (100.0%)] | procedures     424/1824 (23.2%) [279/283 (98.6%)]
oystacher  learned      686/699 (98.1%) [497/499 (99.6%)] | procedures      647/699 (92.6%) [486/499 (97.4%)]
sarao      learned        81/84 (96.4%) [62/64 (96.9%)] | procedures        64/84 (76.2%) [59/64 (92.2%)]
lebental   learned      172/200 (86.0%) [109/117 (93.2%)] | procedures       70/200 (35.0%) [59/117 (50.4%)]
trillium   learned      523/536 (97.6%) [349/349 (100.0%)] | procedures      365/536 (68.1%) [341/349 (97.7%)]
hold       learned    1266/1267 (99.9%) [291/291 (100.0%)] | procedures        2/1267 (0.2%) [2/291 (0.7%)]
milrud     learned      483/553 (87.3%) [333/333 (100.0%)] | procedures         4/553 (0.7%) [4/333 (1.2%)]
```

## Equal false-case load (one threshold read off the test sessions; comparison only)

```
at most 0.5 per 100: learned all attempts 6225/6384 (97.5%), completed 3433/3561 (96.4%) | procedures (k=0.2, 0.19 per 100) all attempts 1699/6384 (26.6%), completed 1608/3561 (45.2%)
at most 1.0 per 100: learned all attempts 6239/6384 (97.7%), completed 3444/3561 (96.7%) | procedures (k=0.2, 0.19 per 100) all attempts 1699/6384 (26.6%), completed 1608/3561 (45.2%)
at most 2.0 per 100: learned all attempts 6246/6384 (97.8%), completed 3450/3561 (96.9%) | procedures (k=0.2, 0.19 per 100) all attempts 1699/6384 (26.6%), completed 1608/3561 (45.2%)
```

## A pattern the detector was never shown

Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.

```
chen       learned: all attempts 1021/1221 (83.6%), completed faithful 546/570 (95.8%) | procedures: completed faithful 377/570 (66.1%) | false cases per 100: 0.0 (without the floor: 1154/1221 (94.5%), 2.22 per 100)
coscia     learned: all attempts 1824/1824 (100.0%), completed faithful 283/283 (100.0%) | procedures: completed faithful 279/283 (98.6%) | false cases per 100: 0.0 (without the floor: 1824/1824 (100.0%), 1.85 per 100)
oystacher  learned: all attempts 642/699 (91.8%), completed faithful 480/499 (96.2%) | procedures: completed faithful 486/499 (97.4%) | false cases per 100: 0.0 (without the floor: 680/699 (97.3%), 1.85 per 100)
sarao      learned: all attempts 81/84 (96.4%), completed faithful 62/64 (96.9%) | procedures: completed faithful 59/64 (92.2%) | false cases per 100: 0.0 (without the floor: 82/84 (97.6%), 1.85 per 100)
lebental   learned: all attempts 135/200 (67.5%), completed faithful 92/117 (78.6%) | procedures: completed faithful 59/117 (50.4%) | false cases per 100: 0.0 (without the floor: 166/200 (83.0%), 1.3 per 100)
```

## Two-account scheme with the accounts linked

```
milrud  all attempts 485/553 (87.7%)
```

## What the highest-scoring alert in each account rests on

Drop in the score when one part of the evidence is replaced by the typical legitimate value.

```
M_COSCIA       score 1.000 seeded | size against the displayed book +0.25, the account's session as a whole +0.06, what the account did on this side afterwards +0.00
M_CHEN_HI      score 1.000 seeded | the account's session as a whole +0.14, size against the displayed book +0.10, the account's interest and executions on the other side +0.01
M_OYST         score 1.000 seeded | size against the displayed book +0.22, the account's session as a whole +0.05, the account's interest and executions on the other side +0.04
M_CHEN_LO      score 1.000 seeded | size against the displayed book +0.13, the account's session as a whole +0.11, the account's interest and executions on the other side +0.00
M_SARAO        score 1.000 seeded | size against the displayed book +0.48, the account's session as a whole +0.12, what the account did on this side afterwards +0.01
M_MM_CHEN      score 0.999 seeded | size against the displayed book +0.60, the account's session as a whole +0.11, the account's interest and executions on the other side +0.04
M_MM_LEB       score 0.999 seeded | size against the displayed book +0.42, the account's session as a whole +0.05, what the account did on this side afterwards +0.04
M_HOLD         score 0.993 seeded | the account's session as a whole +0.85, size against the displayed book +0.13, the account's interest and executions on the other side +0.00
M_LEB          score 0.993 seeded | size against the displayed book +0.16, the account's session as a whole +0.04, the account's interest and executions on the other side +0.01
M_TRIL         score 0.991 seeded | the account's session as a whole +0.38, size against the displayed book +0.34, what the account did on this side afterwards +0.01
M_MIL_DIRTY    score 0.988 seeded | the account's session as a whole +0.75, size against the displayed book +0.49, the account's interest and executions on the other side +0.01
M_MIL_CLEAN    score 0.479 NOT seeded | the account's session as a whole +0.42, the account's interest and executions on the other side +0.10, executions on these orders +0.01
```
