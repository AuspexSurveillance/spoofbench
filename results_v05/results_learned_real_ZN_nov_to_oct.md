# Learned detector (v0.5), tier: real

Seed 20261123. 60 baseline and 120 test sessions, recorded ZN order book (CME Globex MBO via Databento, replayed). 22 accounts, 16 legitimate. 15,159 seeded attempts in the test sessions, 11,142 of them without a fill. All numbers below are on the test sessions.

## Thresholds set on the baseline, applied to the test sessions

```
procedures, per-class multiple   completed faithful 2474/2828 (87.5%) | completed evasive 832/1189 (70.0%) | no fill 199/11142 (1.8%) | all attempts 3505/15159 (23.1%)
                                 false cases per 100 legitimate account-sessions 0.31 (6 cases: {'mm': 5, 'prop': 1, 'manip-acct': 1}); flagged groups 3628, of which not seeded 116
learned detector                 completed faithful 2811/2828 (99.4%) | completed evasive 1165/1189 (98.0%) | no fill 11097/11142 (99.6%) | all attempts 15073/15159 (99.4%)
                                 false cases per 100 legitimate account-sessions 0.0 (0 cases: {}); flagged groups 19351, of which not seeded 121
learned, no threshold floor      completed faithful 2816/2828 (99.6%) | completed evasive 1168/1189 (98.2%) | no fill 11108/11142 (99.7%) | all attempts 15092/15159 (99.6%)
                                 false cases per 100 legitimate account-sessions 2.55 (49 cases: {'mm': 11, 'prop': 27, 'exec': 11}); flagged groups 21139, of which not seeded 1877
```

## By pattern (all attempts; completed faithful in brackets)

```
chen       learned    4954/4982 (99.4%) [468/470 (99.6%)] | procedures      240/4982 (4.8%) [162/470 (34.5%)]
coscia     learned   7103/7103 (100.0%) [268/268 (100.0%)] | procedures      358/7103 (5.0%) [233/268 (86.9%)]
oystacher  learned    2769/2793 (99.1%) [1949/1950 (99.9%)] | procedures    2723/2793 (97.5%) [1939/1950 (99.4%)]
sarao      learned      247/281 (87.9%) [126/140 (90.0%)] | procedures      184/281 (65.5%) [140/140 (100.0%)]
```

## Equal false-case load (one threshold read off the test sessions; comparison only)

```
at most 0.5 per 100: learned all attempts 15078/15159 (99.5%), completed 3976/4017 (99.0%) | procedures (k=0.005, 0.26 per 100) all attempts 3035/15159 (20.0%), completed 2967/4017 (73.9%)
at most 1.0 per 100: learned all attempts 15082/15159 (99.5%), completed 3979/4017 (99.1%) | procedures (k=0.005, 0.26 per 100) all attempts 3035/15159 (20.0%), completed 2967/4017 (73.9%)
at most 2.0 per 100: learned all attempts 15088/15159 (99.5%), completed 3984/4017 (99.2%) | procedures (k=0.002, 1.35 per 100) all attempts 3551/15159 (23.4%), completed 3344/4017 (83.2%)
```

## A pattern the detector was never shown

Every account that runs the pattern is left out of training and calibration. Thresholds are set on the baseline as above.

```
chen       learned: all attempts 3095/4982 (62.1%), completed faithful 268/470 (57.0%) | procedures: completed faithful 162/470 (34.5%) | false cases per 100: 0.0 (without the floor: 4742/4982 (95.2%), 2.5 per 100)
coscia     learned: all attempts 7103/7103 (100.0%), completed faithful 268/268 (100.0%) | procedures: completed faithful 233/268 (86.9%) | false cases per 100: 0.0 (without the floor: 7103/7103 (100.0%), 2.24 per 100)
oystacher  learned: all attempts 1845/2793 (66.1%), completed faithful 1298/1950 (66.6%) | procedures: completed faithful 1939/1950 (99.4%) | false cases per 100: 0.0 (without the floor: 2772/2793 (99.2%), 2.55 per 100)
sarao      learned: all attempts 247/281 (87.9%), completed faithful 126/140 (90.0%) | procedures: completed faithful 140/140 (100.0%) | false cases per 100: 0.0 (without the floor: 274/281 (97.5%), 3.44 per 100)
```

## What the highest-scoring alert in each account rests on

Drop in the score when one part of the evidence is replaced by the typical legitimate value.

```
M_CHEN_HI      score 1.000 seeded | the account's session as a whole +0.28, size against the displayed book +0.15, time at rest +0.00
M_COSCIA       score 1.000 seeded | size against the displayed book +0.49, the account's session as a whole +0.11, time at rest +0.00
M_OYST         score 1.000 seeded | size against the displayed book +0.69, the account's session as a whole +0.07, the account's interest and executions on the other side +0.04
M_CHEN_LO      score 1.000 seeded | size against the displayed book +0.32, the account's session as a whole +0.09, time at rest +0.01
M_MM_CHEN      score 1.000 seeded | size against the displayed book +0.31, the account's session as a whole +0.08, the account's interest and executions on the other side +0.01
M_SARAO        score 1.000 seeded | size against the displayed book +0.87, the account's session as a whole +0.15, what the account did on this side afterwards +0.00
DISC_7         score 0.347 NOT seeded | size against the displayed book +0.29, the account's session as a whole +0.05, executions on these orders +0.00
DISC_5         score 0.325 NOT seeded | time at rest +0.28, size against the displayed book +0.11, the account's session as a whole +0.09
MM_LADDER      score 0.244 NOT seeded | size against the displayed book +0.17, executions on these orders +0.00, time at rest -0.01
DISC_1         score 0.230 NOT seeded | size against the displayed book +0.18, executions on these orders +0.00, what the account did on this side afterwards -0.01
```
