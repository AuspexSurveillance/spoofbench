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
