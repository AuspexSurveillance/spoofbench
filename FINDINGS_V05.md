# spoofbench v0.5: a learned detector that starts from the cancel

## What is new

The procedures in `spoofbench/detect.py` start from a fill: an execution on one side, then a cancel on the other. Two things follow. An attempt in which the genuine order never trades cannot be found, and the result depends on the order sequence each procedure was written for. In the v0.3 test sessions 45% of seeded attempts never trade on the simulated market and 73% on ZN.

`spoofbench/learned.py` starts from the cancel instead.

- **Unit.** A pull group: the orders of one account on one side of one instrument that are cancelled together (within 50 ms), with cancel/replace chains followed back to the first generation.
- **Features.** 43 per group, in six families: size against the displayed book; time at rest; executions on the group's own orders; the account's interest and executions on the other side; what the account did on the same side afterwards; the account's session as a whole. All are computed from the firm's own orders and fills and the depth captured at order entry.
- **No feature names a pattern.** There is no "flip" column and no "cross-instrument" column. Opposite-side interest and executions are summed over the instrument and its correlated instrument, and over the time before and after the cancel. `tests/test_learned.py` checks that no pattern-specific feature is in the model.
- **Model.** The average of a randomized-tree ensemble (extra-trees) and gradient boosting, trained on the seeded baseline sessions.
- **Cases.** An account-session becomes a case when at least two of its groups score above the threshold of the account's class. Thresholds are set on out-of-fold baseline scores (each baseline session is scored by a model that was not trained on it) under the budget the procedures use, 2 false cases per 100 legitimate account-sessions of a class, and are never set below a score of 0.2.
- **Explanations.** `Detector.explain` reports how far the score falls when each feature family is replaced by the typical legitimate value.

`spoofbench/stress.py` adds a stress tier: three legitimate account types that produce the same sequence as spoofing for honest reasons (Scalper, LeggedHedger, BlockWorker) and an "adaptive" manipulation family that is not taken from any document (sizes that are not round, orders entered and cancelled one at a time, a small order put back after the cancel, sometimes the spoof entered first). The adaptive accounts are never used in training.

Run: `python run_learned.py --tier std|eq|stress`, `python run_real_learned.py prep|sim|eval ...`, then `python report_v05.py`. Earlier results files are not changed and `run_benchmark.py` gives the same output as before.

## How it was developed

Design choices were made on development sessions generated from other seeds (seed + 20000 for the baseline, seed + 30000 for the test), not on the v0.3 test sessions and not on the recorded test days. There is one exception, item 5.

1. **Start from cancels.** Nearly every seeded attempt, with or without a fill, leaves a pull group.
2. **Pattern-neutral features.** With separate columns for the flip and for the correlated instrument, a boosting model that had never seen the Oystacher pattern found 320 of 481 completed faithful episodes on the development sessions. With the neutral summaries it found 464 of 481.
3. **Model family.** At one false case per 100 legitimate account-sessions on the development sessions, mean recall over the five patterns, each held out in turn: boosting alone 87.8% (standard roster) and 84.2% (stress roster); extra-trees averaged with boosting 93.8% and 91.3%. Monotonic constraints, heavier regularisation, an isolation-forest novelty feature, a small neural network and logistic regression did no better on held-out patterns and were dropped.
4. **Two groups per case**, against three instances for the procedures. One and two gave similar development results; two was steadier on held-out patterns.
5. **The threshold floor (chosen after a first look at test data).** The first run on the v0.3 test sessions and on ZN used the budget thresholds alone, which came out between 0.03 and 0.11. Results for patterns seen in training were as shown under "no floor" below. In the ZN run with the Chen pattern held out, 61 of 480 legitimate account-sessions were flagged. A floor of 0.2 was then picked on the development sessions (standard roster: false cases fell from 2.04 to 0 per 100 and recall of all attempts from 97.5% to 96.9%) and every run was repeated. Both settings are reported for every run. On held-out patterns the floor costs recall.

## Clean test on days bought afterwards

The detector was frozen and published (commit `d7af04b`) before any October data existed in the project. ESZ6 and ZNZ6 order-by-order data for October 5 to 30, 2026 (20 trading days) was then bought and replayed with the same roster, with session ids offset by 2000 so the simulated accounts draw fresh seeds. Two splits were fixed before any result was read: the first ten October days as baseline with the last ten as test, and all ten November days as baseline with all twenty October days as test. Features, model, the two-group rule, the budget and the 0.2 floor are unchanged. The results are in the four "Clean test" sections below. ES uses the same two windows a day as before.

## Limits

- The firm's accounts are simulated, on the simulated market and on the recorded books. Firm orders do not move the recorded market. Seeded episodes are more regular than real manipulation, so results for patterns seen in training are flattering for any trained model. The held-out-pattern results and the stress tier are the better guide, and they are synthetic too.
- Nothing here has been run on records of real manipulation.
- A legitimate account type that was not in the baseline is flagged in most or all of its sessions (stress tier, below). New account types have to be reviewed once and added to the baseline.
- For a pattern never seen in training the calibration is not settled: budget thresholds keep recall high but did not hold the false-case rate in one of four ZN runs, and the 0.2 floor holds the false-case rate and loses about a third of the attempts on two of the four ZN patterns.
- Class thresholds rest on at most a few hundred legitimate account-sessions per class. False-case rates on the test sessions rest on a handful of cases, or none.
- Thirty recorded days, two contracts, the cross-instrument pattern not run on recorded data. The model is trained per instrument; carrying a model from one instrument to another is not tested.
- The adaptive family was written by the same author as the detector.

## Results

Every number below is on test sessions and is generated from `results_v05/*.json` by `report_v05.py`. "All attempts" counts every seeded episode, including those in which the genuine order never traded. "Completed faithful" is the denominator the v0.3 paper uses.

### Simulated market, the v0.3 sessions

30 baseline and 30 test sessions; 4,106 seeded attempts in the test sessions, 1,840 of them without a fill; 540 legitimate account-sessions.

```
procedures        all attempts   1,595/4,106 (38.8%) | completed faithful 1,235/1,618 (76.3%) | completed evasive   261/648 (40.3%) | no fill     99/1,840 (5.4%) | false cases 5 of 540 (0.93 per 100)
learned detector  all attempts   3,989/4,106 (97.2%) | completed faithful 1,581/1,618 (97.7%) | completed evasive   581/648 (89.7%) | no fill 1,827/1,840 (99.3%) | false cases 2 of 540 (0.37 per 100)
learned, no floor all attempts   4,010/4,106 (97.7%) | completed faithful 1,586/1,618 (98.0%) | completed evasive   588/648 (90.7%) | no fill 1,836/1,840 (99.8%) | false cases 16 of 540 (2.96 per 100)
```

Flagged groups that contain no seeded order: 40 of 4,463 (learned), 80 of 1,687 (procedures).

At an equal false-case load (one threshold read off the test sessions, comparison only):

```
at most 0.5 per 100: learned 3,998/4,106 (97.4%) | procedures 1,082/4,106 (26.4%) (k=0.3, 0.0 per 100)
at most 1.0 per 100: learned 4,008/4,106 (97.6%) | procedures 1,082/4,106 (26.4%) (k=0.3, 0.0 per 100)
at most 2.0 per 100: learned 4,010/4,106 (97.7%) | procedures 1,423/4,106 (34.7%) (k=0.2, 1.11 per 100)
```

By pattern, all attempts (completed faithful in brackets):

```
chen       learned 1,194/1,246 (95.8%) [607/618 (98.2%)] | procedures   381/1,246 (30.6%) [340/618 (55.0%)]
coscia     learned 1,907/1,907 (100.0%) [333/333 (100.0%)] | procedures   480/1,907 (25.2%) [325/333 (97.6%)]
oystacher  learned     654/680 (96.2%) [483/489 (98.8%)] | procedures     630/680 (92.6%) [476/489 (97.3%)]
sarao      learned       65/73 (89.0%) [45/48 (93.8%)] | procedures       51/73 (69.9%) [48/48 (100.0%)]
lebental   learned     169/200 (84.5%) [113/130 (86.9%)] | procedures      53/200 (26.5%) [46/130 (35.4%)]
```

A pattern the detector was never shown (every account that runs it is left out of training and calibration). Recall is over all attempts of that pattern:

```
chen       with the floor 1,059/1,246 (85.0%) at 0.0 false cases per 100 | without 1,165/1,246 (93.5%) at 1.85 | threshold read off the test sessions at 1 per 100: 1,153/1,246 (92.5%) | procedures 381/1,246 (30.6%)
coscia     with the floor 1,907/1,907 (100.0%) at 0.19 false cases per 100 | without 1,907/1,907 (100.0%) at 2.96 | threshold read off the test sessions at 1 per 100: 1,907/1,907 (100.0%) | procedures 480/1,907 (25.2%)
oystacher  with the floor     599/680 (88.1%) at 0.19 false cases per 100 | without     647/680 (95.1%) at 1.48 | threshold read off the test sessions at 1 per 100: 643/680 (94.6%) | procedures 630/680 (92.6%)
sarao      with the floor       66/73 (90.4%) at 0.0 false cases per 100 | without       70/73 (95.9%) at 2.04 | threshold read off the test sessions at 1 per 100: 70/73 (95.9%) | procedures 51/73 (69.9%)
lebental   with the floor     132/200 (66.0%) at 0.19 false cases per 100 | without     179/200 (89.5%) at 2.96 | threshold read off the test sessions at 1 per 100: 172/200 (86.0%) | procedures 53/200 (26.5%)
```

### ZN, recorded order book

30 baseline and 30 test sessions; 3,794 seeded attempts in the test sessions, 2,763 of them without a fill; 480 legitimate account-sessions.

```
procedures        all attempts     922/3,794 (24.3%) | completed faithful     654/740 (88.4%) | completed evasive   208/291 (71.5%) | no fill     60/2,763 (2.2%) | false cases 3 of 480 (0.62 per 100)
learned detector  all attempts   3,770/3,794 (99.4%) | completed faithful     737/740 (99.6%) | completed evasive   282/291 (96.9%) | no fill 2,751/2,763 (99.6%) | false cases 0 of 480 (0.0 per 100)
learned, no floor all attempts   3,775/3,794 (99.5%) | completed faithful     737/740 (99.6%) | completed evasive   283/291 (97.3%) | no fill 2,755/2,763 (99.7%) | false cases 5 of 480 (1.04 per 100)
```

Flagged groups that contain no seeded order: 15 of 4,733 (learned), 45 of 968 (procedures).

At an equal false-case load (one threshold read off the test sessions, comparison only):

```
at most 0.5 per 100: learned 3,774/3,794 (99.5%) | procedures 838/3,794 (22.1%) (k=0.005, 0.21 per 100)
at most 1.0 per 100: learned 3,775/3,794 (99.5%) | procedures 838/3,794 (22.1%) (k=0.005, 0.21 per 100)
at most 2.0 per 100: learned 3,777/3,794 (99.6%) | procedures 838/3,794 (22.1%) (k=0.005, 0.21 per 100)
```

By pattern, all attempts (completed faithful in brackets):

```
chen       learned 1,179/1,191 (99.0%) [125/125 (100.0%)] | procedures     84/1,191 (7.1%) [57/125 (45.6%)]
coscia     learned 1,855/1,855 (100.0%) [89/89 (100.0%)] | procedures    131/1,855 (7.1%) [80/89 (89.9%)]
oystacher  learned     671/679 (98.8%) [481/483 (99.6%)] | procedures     657/679 (96.8%) [474/483 (98.1%)]
sarao      learned       65/69 (94.2%) [42/43 (97.7%)] | procedures       50/69 (72.5%) [43/43 (100.0%)]
```

A pattern the detector was never shown (every account that runs it is left out of training and calibration). Recall is over all attempts of that pattern:

```
chen       with the floor   781/1,191 (65.6%) at 0.0 false cases per 100 | without 1,128/1,191 (94.7%) at 12.71 | threshold read off the test sessions at 1 per 100: 1,134/1,191 (95.2%) | procedures 84/1,191 (7.1%)
coscia     with the floor 1,855/1,855 (100.0%) at 0.0 false cases per 100 | without 1,855/1,855 (100.0%) at 0.62 | threshold read off the test sessions at 1 per 100: 1,855/1,855 (100.0%) | procedures 131/1,855 (7.1%)
oystacher  with the floor     458/679 (67.5%) at 0.0 false cases per 100 | without     671/679 (98.8%) at 1.04 | threshold read off the test sessions at 1 per 100: 671/679 (98.8%) | procedures 657/679 (96.8%)
sarao      with the floor       65/69 (94.2%) at 0.0 false cases per 100 | without       65/69 (94.2%) at 1.04 | threshold read off the test sessions at 1 per 100: 65/69 (94.2%) | procedures 50/69 (72.5%)
```

### ES, recorded order book, the two windows a day used in v0.3

10 baseline and 10 test sessions; 1,101 seeded attempts in the test sessions, 266 of them without a fill; 160 legitimate account-sessions.

```
procedures        all attempts     521/1,101 (47.3%) | completed faithful     430/577 (74.5%) | completed evasive    87/258 (33.7%) | no fill        4/266 (1.5%) | false cases 2 of 160 (1.25 per 100)
learned detector  all attempts     844/1,101 (76.7%) | completed faithful     512/577 (88.7%) | completed evasive   166/258 (64.3%) | no fill     166/266 (62.4%) | false cases 0 of 160 (0.0 per 100)
learned, no floor all attempts     857/1,101 (77.8%) | completed faithful     516/577 (89.4%) | completed evasive   172/258 (66.7%) | no fill     169/266 (63.5%) | false cases 0 of 160 (0.0 per 100)
```

Flagged groups that contain no seeded order: 12 of 886 (learned), 137 of 663 (procedures).

At an equal false-case load (one threshold read off the test sessions, comparison only):

```
at most 0.5 per 100: learned 857/1,101 (77.8%) | procedures 278/1,101 (25.2%) (k=0.5, 0.0 per 100)
at most 1.0 per 100: learned 857/1,101 (77.8%) | procedures 278/1,101 (25.2%) (k=0.5, 0.0 per 100)
at most 2.0 per 100: learned 858/1,101 (77.9%) | procedures 278/1,101 (25.2%) (k=0.5, 0.0 per 100)
```

By pattern, all attempts (completed faithful in brackets):

```
chen       learned     188/291 (64.6%) [118/155 (76.1%)] | procedures      76/291 (26.1%) [69/155 (44.5%)]
coscia     learned     493/549 (89.8%) [276/276 (100.0%)] | procedures     325/549 (59.2%) [268/276 (97.1%)]
oystacher  learned     142/235 (60.4%) [104/128 (81.2%)] | procedures     102/235 (43.4%) [75/128 (58.6%)]
sarao      learned       21/26 (80.8%) [14/18 (77.8%)] | procedures       18/26 (69.2%) [18/18 (100.0%)]
```

A pattern the detector was never shown (every account that runs it is left out of training and calibration). Recall is over all attempts of that pattern:

```
chen       with the floor     124/291 (42.6%) at 0.0 false cases per 100 | without     159/291 (54.6%) at 0.0 | threshold read off the test sessions at 1 per 100: 163/291 (56.0%) | procedures 76/291 (26.1%)
coscia     with the floor     489/549 (89.1%) at 0.0 false cases per 100 | without     493/549 (89.8%) at 2.5 | threshold read off the test sessions at 1 per 100: 493/549 (89.8%) | procedures 325/549 (59.2%)
oystacher  with the floor     100/235 (42.6%) at 0.62 false cases per 100 | without     104/235 (44.3%) at 0.62 | threshold read off the test sessions at 1 per 100: 104/235 (44.3%) | procedures 102/235 (43.4%)
sarao      with the floor       21/26 (80.8%) at 0.62 false cases per 100 | without       22/26 (84.6%) at 1.25 | threshold read off the test sessions at 1 per 100: 25/26 (96.2%) | procedures 18/26 (69.2%)
```

### Clean test, ZN: first ten October days as baseline, last ten as test

60 baseline and 60 test sessions; 7,546 seeded attempts in the test sessions, 5,499 of them without a fill; 960 legitimate account-sessions.

```
procedures        all attempts   1,792/7,546 (23.7%) | completed faithful 1,258/1,420 (88.6%) | completed evasive   440/627 (70.2%) | no fill     94/5,499 (1.7%) | false cases 8 of 960 (0.83 per 100)
learned detector  all attempts   7,503/7,546 (99.4%) | completed faithful 1,413/1,420 (99.5%) | completed evasive   612/627 (97.6%) | no fill 5,478/5,499 (99.6%) | false cases 0 of 960 (0.0 per 100)
learned, no floor all attempts   7,508/7,546 (99.5%) | completed faithful 1,414/1,420 (99.6%) | completed evasive   614/627 (97.9%) | no fill 5,480/5,499 (99.7%) | false cases 20 of 960 (2.08 per 100)
```

Flagged groups that contain no seeded order: 52 of 9,549 (learned), 110 of 1,905 (procedures).

At an equal false-case load (one threshold read off the test sessions, comparison only):

```
at most 0.5 per 100: learned 7,505/7,546 (99.5%) | procedures 1,529/7,546 (20.3%) (k=0.005, 0.31 per 100)
at most 1.0 per 100: learned 7,506/7,546 (99.5%) | procedures 1,529/7,546 (20.3%) (k=0.005, 0.31 per 100)
at most 2.0 per 100: learned 7,508/7,546 (99.5%) | procedures 1,792/7,546 (23.7%) (k=0.002, 1.98 per 100)
```

By pattern, all attempts (completed faithful in brackets):

```
chen       learned 2,444/2,458 (99.4%) [257/257 (100.0%)] | procedures    156/2,458 (6.3%) [117/257 (45.5%)]
coscia     learned 3,538/3,538 (100.0%) [132/132 (100.0%)] | procedures    176/3,538 (5.0%) [114/132 (86.4%)]
oystacher  learned 1,390/1,404 (99.0%) [957/957 (100.0%)] | procedures 1,367/1,404 (97.4%) [953/957 (99.6%)]
sarao      learned     131/146 (89.7%) [67/74 (90.5%)] | procedures      93/146 (63.7%) [74/74 (100.0%)]
```

A pattern the detector was never shown (every account that runs it is left out of training and calibration). Recall is over all attempts of that pattern:

```
chen       with the floor 1,407/2,458 (57.2%) at 0.0 false cases per 100 | without 2,364/2,458 (96.2%) at 2.81 | threshold read off the test sessions at 1 per 100: 2,329/2,458 (94.8%) | procedures 156/2,458 (6.3%)
coscia     with the floor 3,538/3,538 (100.0%) at 0.0 false cases per 100 | without 3,538/3,538 (100.0%) at 2.19 | threshold read off the test sessions at 1 per 100: 3,538/3,538 (100.0%) | procedures 176/3,538 (5.0%)
oystacher  with the floor   938/1,404 (66.8%) at 0.0 false cases per 100 | without 1,391/1,404 (99.1%) at 2.08 | threshold read off the test sessions at 1 per 100: 1,389/1,404 (98.9%) | procedures 1,367/1,404 (97.4%)
sarao      with the floor     131/146 (89.7%) at 0.0 false cases per 100 | without     144/146 (98.6%) at 2.81 | threshold read off the test sessions at 1 per 100: 133/146 (91.1%) | procedures 93/146 (63.7%)
```

### Clean test, ZN: November 2 to 13 as baseline, October 5 to 30 as test

60 baseline and 120 test sessions; 15,159 seeded attempts in the test sessions, 11,142 of them without a fill; 1920 legitimate account-sessions.

```
procedures        all attempts  3,505/15,159 (23.1%) | completed faithful 2,474/2,828 (87.5%) | completed evasive 832/1,189 (70.0%) | no fill   199/11,142 (1.8%) | false cases 6 of 1920 (0.31 per 100)
learned detector  all attempts 15,073/15,159 (99.4%) | completed faithful 2,811/2,828 (99.4%) | completed evasive 1,165/1,189 (98.0%) | no fill 11,097/11,142 (99.6%) | false cases 0 of 1920 (0.0 per 100)
learned, no floor all attempts 15,092/15,159 (99.6%) | completed faithful 2,816/2,828 (99.6%) | completed evasive 1,168/1,189 (98.2%) | no fill 11,108/11,142 (99.7%) | false cases 49 of 1920 (2.55 per 100)
```

Flagged groups that contain no seeded order: 121 of 19,351 (learned), 116 of 3,628 (procedures).

At an equal false-case load (one threshold read off the test sessions, comparison only):

```
at most 0.5 per 100: learned 15,078/15,159 (99.5%) | procedures 3,035/15,159 (20.0%) (k=0.005, 0.26 per 100)
at most 1.0 per 100: learned 15,082/15,159 (99.5%) | procedures 3,035/15,159 (20.0%) (k=0.005, 0.26 per 100)
at most 2.0 per 100: learned 15,088/15,159 (99.5%) | procedures 3,551/15,159 (23.4%) (k=0.002, 1.35 per 100)
```

By pattern, all attempts (completed faithful in brackets):

```
chen       learned 4,954/4,982 (99.4%) [468/470 (99.6%)] | procedures    240/4,982 (4.8%) [162/470 (34.5%)]
coscia     learned 7,103/7,103 (100.0%) [268/268 (100.0%)] | procedures    358/7,103 (5.0%) [233/268 (86.9%)]
oystacher  learned 2,769/2,793 (99.1%) [1,949/1,950 (99.9%)] | procedures 2,723/2,793 (97.5%) [1,939/1,950 (99.4%)]
sarao      learned     247/281 (87.9%) [126/140 (90.0%)] | procedures     184/281 (65.5%) [140/140 (100.0%)]
```

A pattern the detector was never shown (every account that runs it is left out of training and calibration). Recall is over all attempts of that pattern:

```
chen       with the floor 3,095/4,982 (62.1%) at 0.0 false cases per 100 | without 4,742/4,982 (95.2%) at 2.5 | threshold read off the test sessions at 1 per 100: 4,724/4,982 (94.8%) | procedures 240/4,982 (4.8%)
coscia     with the floor 7,103/7,103 (100.0%) at 0.0 false cases per 100 | without 7,103/7,103 (100.0%) at 2.24 | threshold read off the test sessions at 1 per 100: 7,103/7,103 (100.0%) | procedures 358/7,103 (5.0%)
oystacher  with the floor 1,845/2,793 (66.1%) at 0.0 false cases per 100 | without 2,772/2,793 (99.2%) at 2.55 | threshold read off the test sessions at 1 per 100: 2,768/2,793 (99.1%) | procedures 2,723/2,793 (97.5%)
sarao      with the floor     247/281 (87.9%) at 0.0 false cases per 100 | without     274/281 (97.5%) at 3.44 | threshold read off the test sessions at 1 per 100: 249/281 (88.6%) | procedures 184/281 (65.5%)
```

### Clean test, ES (two windows a day): first ten October days as baseline, last ten as test

20 baseline and 20 test sessions; 2,313 seeded attempts in the test sessions, 726 of them without a fill; 320 legitimate account-sessions.

```
procedures        all attempts   1,085/2,313 (46.9%) | completed faithful   880/1,125 (78.2%) | completed evasive   179/462 (38.7%) | no fill       26/726 (3.6%) | false cases 1 of 320 (0.31 per 100)
learned detector  all attempts   2,025/2,313 (87.5%) | completed faithful 1,047/1,125 (93.1%) | completed evasive   352/462 (76.2%) | no fill     626/726 (86.2%) | false cases 1 of 320 (0.31 per 100)
learned, no floor all attempts   2,038/2,313 (88.1%) | completed faithful 1,051/1,125 (93.4%) | completed evasive   356/462 (77.1%) | no fill     631/726 (86.9%) | false cases 9 of 320 (2.81 per 100)
```

Flagged groups that contain no seeded order: 20 of 2,176 (learned), 188 of 1,276 (procedures).

At an equal false-case load (one threshold read off the test sessions, comparison only):

```
at most 0.5 per 100: learned 2,025/2,313 (87.5%) | procedures 592/2,313 (25.6%) (k=0.3, 0.0 per 100)
at most 1.0 per 100: learned 2,034/2,313 (87.9%) | procedures 592/2,313 (25.6%) (k=0.3, 0.0 per 100)
at most 2.0 per 100: learned 2,035/2,313 (88.0%) | procedures 592/2,313 (25.6%) (k=0.3, 0.0 per 100)
```

By pattern, all attempts (completed faithful in brackets):

```
chen       learned     533/645 (82.6%) [296/329 (90.0%)] | procedures     217/645 (33.6%) [186/329 (56.5%)]
coscia     learned 1,111/1,154 (96.3%) [453/454 (99.8%)] | procedures   570/1,154 (49.4%) [444/454 (97.8%)]
oystacher  learned     344/474 (72.6%) [273/315 (86.7%)] | procedures     271/474 (57.2%) [223/315 (70.8%)]
sarao      learned       37/40 (92.5%) [25/27 (92.6%)] | procedures       27/40 (67.5%) [27/27 (100.0%)]
```

A pattern the detector was never shown (every account that runs it is left out of training and calibration). Recall is over all attempts of that pattern:

```
chen       with the floor     322/645 (49.9%) at 0.0 false cases per 100 | without     492/645 (76.3%) at 4.69 | threshold read off the test sessions at 1 per 100: 458/645 (71.0%) | procedures 217/645 (33.6%)
coscia     with the floor 1,111/1,154 (96.3%) at 0.31 false cases per 100 | without 1,111/1,154 (96.3%) at 2.19 | threshold read off the test sessions at 1 per 100: 1,111/1,154 (96.3%) | procedures 570/1,154 (49.4%)
oystacher  with the floor     233/474 (49.2%) at 0.62 false cases per 100 | without     314/474 (66.2%) at 3.12 | threshold read off the test sessions at 1 per 100: 243/474 (51.3%) | procedures 271/474 (57.2%)
sarao      with the floor       37/40 (92.5%) at 0.31 false cases per 100 | without      40/40 (100.0%) at 4.06 | threshold read off the test sessions at 1 per 100: 37/40 (92.5%) | procedures 27/40 (67.5%)
```

### Clean test, ES (two windows a day): November 2 to 13 as baseline, October 5 to 30 as test

20 baseline and 40 test sessions; 4,698 seeded attempts in the test sessions, 1,552 of them without a fill; 640 legitimate account-sessions.

```
procedures        all attempts   2,191/4,698 (46.6%) | completed faithful 1,763/2,253 (78.3%) | completed evasive   381/893 (42.7%) | no fill     47/1,552 (3.0%) | false cases 29 of 640 (4.53 per 100)
learned detector  all attempts   4,145/4,698 (88.2%) | completed faithful 2,125/2,253 (94.3%) | completed evasive   673/893 (75.4%) | no fill 1,347/1,552 (86.8%) | false cases 2 of 640 (0.31 per 100)
learned, no floor all attempts   4,178/4,698 (88.9%) | completed faithful 2,129/2,253 (94.5%) | completed evasive   692/893 (77.5%) | no fill 1,357/1,552 (87.4%) | false cases 41 of 640 (6.41 per 100)
```

Flagged groups that contain no seeded order: 51 of 4,475 (learned), 753 of 2,953 (procedures).

At an equal false-case load (one threshold read off the test sessions, comparison only):

```
at most 0.5 per 100: learned 4,155/4,698 (88.4%) | procedures 1,076/4,698 (22.9%) (k=0.3, 0.16 per 100)
at most 1.0 per 100: learned 4,165/4,698 (88.7%) | procedures 1,076/4,698 (22.9%) (k=0.3, 0.16 per 100)
at most 2.0 per 100: learned 4,168/4,698 (88.7%) | procedures 1,583/4,698 (33.7%) (k=0.2, 1.88 per 100)
```

By pattern, all attempts (completed faithful in brackets):

```
chen       learned 1,113/1,336 (83.3%) [622/676 (92.0%)] | procedures   417/1,336 (31.2%) [362/676 (53.6%)]
coscia     learned 2,235/2,316 (96.5%) [883/884 (99.9%)] | procedures 1,112/2,316 (48.0%) [867/884 (98.1%)]
oystacher  learned     721/963 (74.9%) [565/634 (89.1%)] | procedures     601/963 (62.4%) [475/634 (74.9%)]
sarao      learned       76/83 (91.6%) [55/59 (93.2%)] | procedures       61/83 (73.5%) [59/59 (100.0%)]
```

A pattern the detector was never shown (every account that runs it is left out of training and calibration). Recall is over all attempts of that pattern:

```
chen       with the floor   767/1,336 (57.4%) at 0.0 false cases per 100 | without   985/1,336 (73.7%) at 3.59 | threshold read off the test sessions at 1 per 100: 947/1,336 (70.9%) | procedures 417/1,336 (31.2%)
coscia     with the floor 2,235/2,316 (96.5%) at 0.0 false cases per 100 | without 2,235/2,316 (96.5%) at 4.22 | threshold read off the test sessions at 1 per 100: 2,235/2,316 (96.5%) | procedures 1,112/2,316 (48.0%)
oystacher  with the floor     492/963 (51.1%) at 0.16 false cases per 100 | without     594/963 (61.7%) at 6.25 | threshold read off the test sessions at 1 per 100: 537/963 (55.8%) | procedures 601/963 (62.4%)
sarao      with the floor       76/83 (91.6%) at 0.16 false cases per 100 | without       79/83 (95.2%) at 8.91 | threshold read off the test sessions at 1 per 100: 76/83 (91.6%) | procedures 61/83 (73.5%)
```

### Equities templates (v0.4 sessions), never trained on

30 baseline and 30 test sessions; 6,384 seeded attempts in the test sessions, 2,823 of them without a fill; 540 legitimate account-sessions.

```
procedures        all attempts   1,994/6,384 (31.2%) | completed faithful 1,607/2,506 (64.1%) | completed evasive 283/1,055 (26.8%) | no fill    104/2,823 (3.7%) | false cases 4 of 540 (0.74 per 100)
learned detector  all attempts   6,217/6,384 (97.4%) | completed faithful 2,488/2,506 (99.3%) | completed evasive 938/1,055 (88.9%) | no fill 2,791/2,823 (98.9%) | false cases 0 of 540 (0.0 per 100)
learned, no floor all attempts   6,265/6,384 (98.1%) | completed faithful 2,489/2,506 (99.3%) | completed evasive 976/1,055 (92.5%) | no fill 2,800/2,823 (99.2%) | false cases 10 of 540 (1.85 per 100)
```

Flagged groups that contain no seeded order: 110 of 6,788 (learned), 138 of 2,175 (procedures).

At an equal false-case load (one threshold read off the test sessions, comparison only):

```
at most 0.5 per 100: learned 6,225/6,384 (97.5%) | procedures 1,699/6,384 (26.6%) (k=0.2, 0.19 per 100)
at most 1.0 per 100: learned 6,239/6,384 (97.7%) | procedures 1,699/6,384 (26.6%) (k=0.2, 0.19 per 100)
at most 2.0 per 100: learned 6,246/6,384 (97.8%) | procedures 1,699/6,384 (26.6%) (k=0.2, 0.19 per 100)
```

By pattern, all attempts (completed faithful in brackets):

```
chen       learned 1,182/1,221 (96.8%) [564/570 (98.9%)] | procedures   418/1,221 (34.2%) [377/570 (66.1%)]
coscia     learned 1,824/1,824 (100.0%) [283/283 (100.0%)] | procedures   424/1,824 (23.2%) [279/283 (98.6%)]
oystacher  learned     686/699 (98.1%) [497/499 (99.6%)] | procedures     647/699 (92.6%) [486/499 (97.4%)]
sarao      learned       81/84 (96.4%) [62/64 (96.9%)] | procedures       64/84 (76.2%) [59/64 (92.2%)]
lebental   learned     172/200 (86.0%) [109/117 (93.2%)] | procedures      70/200 (35.0%) [59/117 (50.4%)]
trillium   learned     523/536 (97.6%) [349/349 (100.0%)] | procedures     365/536 (68.1%) [341/349 (97.7%)]
hold       learned 1,266/1,267 (99.9%) [291/291 (100.0%)] | procedures      2/1,267 (0.2%) [2/291 (0.7%)]
milrud     learned     483/553 (87.3%) [333/333 (100.0%)] | procedures        4/553 (0.7%) [4/333 (1.2%)]
```

A pattern the detector was never shown (every account that runs it is left out of training and calibration). Recall is over all attempts of that pattern:

```
chen       with the floor 1,021/1,221 (83.6%) at 0.0 false cases per 100 | without 1,154/1,221 (94.5%) at 2.22 | threshold read off the test sessions at 1 per 100: 1,136/1,221 (93.0%) | procedures 418/1,221 (34.2%)
coscia     with the floor 1,824/1,824 (100.0%) at 0.0 false cases per 100 | without 1,824/1,824 (100.0%) at 1.85 | threshold read off the test sessions at 1 per 100: 1,824/1,824 (100.0%) | procedures 424/1,824 (23.2%)
oystacher  with the floor     642/699 (91.8%) at 0.0 false cases per 100 | without     680/699 (97.3%) at 1.85 | threshold read off the test sessions at 1 per 100: 644/699 (92.1%) | procedures 647/699 (92.6%)
sarao      with the floor       81/84 (96.4%) at 0.0 false cases per 100 | without       82/84 (97.6%) at 1.85 | threshold read off the test sessions at 1 per 100: 82/84 (97.6%) | procedures 64/84 (76.2%)
lebental   with the floor     135/200 (67.5%) at 0.0 false cases per 100 | without     166/200 (83.0%) at 1.3 | threshold read off the test sessions at 1 per 100: 166/200 (83.0%) | procedures 70/200 (35.0%)
```

Two-account scheme with the two accounts linked into one: 485/553 (87.7%) of milrud attempts.

### Stress tier

30 baseline and 30 test sessions; 5,276 seeded attempts in the test sessions, 2,127 of them without a fill; 720 legitimate account-sessions.

```
procedures        all attempts   2,382/5,276 (45.1%) | completed faithful 1,829/2,255 (81.1%) | completed evasive   453/894 (50.7%) | no fill    100/2,127 (4.7%) | false cases 13 of 720 (1.81 per 100)
learned detector  all attempts   5,180/5,276 (98.2%) | completed faithful 2,233/2,255 (99.0%) | completed evasive   836/894 (93.5%) | no fill 2,111/2,127 (99.2%) | false cases 0 of 720 (0.0 per 100)
learned, no floor all attempts   5,198/5,276 (98.5%) | completed faithful 2,237/2,255 (99.2%) | completed evasive   843/894 (94.3%) | no fill 2,118/2,127 (99.6%) | false cases 13 of 720 (1.81 per 100)
```

Flagged groups that contain no seeded order: 327 of 6,787 (learned), 138 of 2,562 (procedures).

At an equal false-case load (one threshold read off the test sessions, comparison only):

```
at most 0.5 per 100: learned 5,189/5,276 (98.4%) | procedures: no fixed multiple stays under this rate
at most 1.0 per 100: learned 5,194/5,276 (98.4%) | procedures: no fixed multiple stays under this rate
at most 2.0 per 100: learned 5,198/5,276 (98.5%) | procedures 1,151/5,276 (21.8%) (k=0.5, 1.53 per 100)
```

By pattern, all attempts (completed faithful in brackets):

```
chen       learned 1,156/1,190 (97.1%) [494/496 (99.6%)] | procedures   295/1,190 (24.8%) [262/496 (52.8%)]
coscia     learned 1,843/1,843 (100.0%) [243/243 (100.0%)] | procedures   329/1,843 (17.9%) [231/243 (95.1%)]
oystacher  learned     705/719 (98.1%) [500/502 (99.6%)] | procedures     673/719 (93.6%) [490/502 (97.6%)]
sarao      learned       62/72 (86.1%) [46/53 (86.8%)] | procedures       53/72 (73.6%) [47/53 (88.7%)]
lebental   learned     172/200 (86.0%) [117/126 (92.9%)] | procedures      57/200 (28.5%) [51/126 (40.5%)]
ada_same   learned     572/580 (98.6%) [366/368 (99.5%)] | procedures     363/580 (62.6%) [302/368 (82.1%)]
ada_flip   learned     436/437 (99.8%) [309/309 (100.0%)] | procedures     432/437 (98.9%) [307/309 (99.4%)]
ada_cross  learned     234/235 (99.6%) [158/158 (100.0%)] | procedures     180/235 (76.6%) [139/158 (88.0%)]
```

A pattern the detector was never shown (every account that runs it is left out of training and calibration). Recall is over all attempts of that pattern:

```
chen       with the floor   556/1,190 (46.7%) at 0.0 false cases per 100 | without 1,045/1,190 (87.8%) at 1.11 | threshold read off the test sessions at 1 per 100: 1,078/1,190 (90.6%) | procedures 295/1,190 (24.8%)
coscia     with the floor 1,843/1,843 (100.0%) at 0.0 false cases per 100 | without 1,843/1,843 (100.0%) at 1.39 | threshold read off the test sessions at 1 per 100: 1,843/1,843 (100.0%) | procedures 329/1,843 (17.9%)
oystacher  with the floor     651/719 (90.5%) at 0.0 false cases per 100 | without     690/719 (96.0%) at 1.39 | threshold read off the test sessions at 1 per 100: 670/719 (93.2%) | procedures 673/719 (93.6%)
sarao      with the floor       53/72 (73.6%) at 0.0 false cases per 100 | without       67/72 (93.1%) at 1.67 | threshold read off the test sessions at 1 per 100: 64/72 (88.9%) | procedures 53/72 (73.6%)
lebental   with the floor     135/200 (67.5%) at 0.0 false cases per 100 | without     171/200 (85.5%) at 0.83 | threshold read off the test sessions at 1 per 100: 168/200 (84.0%) | procedures 57/200 (28.5%)
```

A legitimate account type the detector was never shown (left out of training and calibration, present in the test sessions):

```
Scalper       learned: 60 of 60 account-sessions flagged | procedures: 1 of 60
LeggedHedger  learned: 56 of 60 account-sessions flagged | procedures: 60 of 60
BlockWorker   learned: 60 of 60 account-sessions flagged | procedures: 15 of 60
```

