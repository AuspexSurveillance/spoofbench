# Recorded-data replay: findings

Same accounts, templates and detectors as the simulated benchmark, run on top of recorded CME order-by-order data (ESZ6 and ZNZ6, 2 to 13 November 2026, 9:00 to 12:00 Central). First five days are the baseline set, last five the test set.
ZN uses all six 30-minute windows per day (30 test sessions). ES uses two windows per day (10 test sessions) because of memory limits on the machine it ran on.
The firm's orders are hypothetical: they do not move the recorded market and nobody reacts to them. The firm's accounts are simulated. The cross-instrument template is not run (one instrument at a time).
Every number is generated from results_real/*.json and results/results.json.

## Market depth (median displayed size at the touch / within 3 ticks, lots)

- Simulated market: about 69 / about 212
- ZN, recorded book: 1580 / 11606
- ES, recorded book: 18 / 113

## Seeded episodes in the test sessions (with a fill / total)

- Simulated market: 2,266 / 4,158
- ZN, recorded book: 1,031 / 3,811
- ES, recorded book: 835 / 1,332

## 1. Literal procedures at the v1.0 defaults

- Simulated market: recall 0.0%, 0 cases
- ZN, recorded book: recall 0.0%, 0 cases
- ES, recorded book: recall 2.6%, 4 cases

## 2. Threshold from the account's own 99.5th percentile

- Simulated market: recall 4.9%
- ZN, recorded book: recall 7.8%
- ES, recorded book: recall 3.1%

## 3. Per-class threshold chosen on seeded baseline sessions

- Simulated market: recall 76.3% (evasive variants 40.3%), 0.93 false cases per 100 legitimate account-sessions; multiples {'basis': 0.02, 'exec': 0.2, 'mm': 0.3, 'prop': 0.1}
- ZN, recorded book: recall 88.4% (evasive variants 71.5%), 0.62 false cases per 100 legitimate account-sessions; multiples {'exec': 0.005, 'mm': 0.005, 'prop': 0.002}
- ES, recorded book: recall 74.5% (evasive variants 33.7%), 1.25 false cases per 100 legitimate account-sessions; multiples {'exec': 0.3, 'mm': 1.0, 'prop': 0.002}

## 4. Flip pattern (Oystacher), detected/total: without the flip variant -> with it

- Simulated market: 1/489 -> 476/489
- ZN, recorded book: 1/483 -> 474/483
- ES, recorded book: 0/128 -> 75/128

## 5. Persistent layering (Sarao), detected/total: without the persistent variant -> with it

- Simulated market: 0/48 -> 48/48
- ZN, recorded book: 0/43 -> 43/43
- ES, recorded book: 0/18 -> 18/18

## 6. False cases per 100 legitimate account-sessions: with exclusions -> without

- Simulated market: 0.93 -> 12.59
- ZN, recorded book: 0.62 -> 0.83
- ES, recorded book: 1.25 -> 1.88

## 7. Ranking model, average precision (model / ranking by imbalance)

- Simulated market: 0.995 / 0.658
- ZN, recorded book: 0.993 / 0.915
- ES, recorded book: 0.779 / 0.587

## 8. Held-out template recall, model never shown the pattern vs procedure

- Simulated market: chen 43.0% vs 55.0%; coscia 61.6% vs 97.6%; oystacher 36.4% vs 97.3%; lebental 13.1% vs 35.4%
- ZN, recorded book: chen 41.6% vs 45.6%; coscia 75.3% vs 89.9%; oystacher 60.5% vs 98.1%
- ES, recorded book: chen 46.5% vs 44.5%; coscia 93.5% vs 97.1%; oystacher 8.6% vs 58.6%

## What carries over from the simulation

- The v1.0 default threshold finds almost nothing on either contract.
- A threshold taken from the account's own history finds almost nothing.
- Thresholds chosen per account class from seeded sessions recover most completed episodes at about one false case per 100 legitimate account-sessions.
- The flip variant and the persistent-layering variant are both needed.
- The ranking model helps on patterns it was trained on and cannot be relied on for a pattern it has not seen (Oystacher on ES).

## What the recorded data adds

- The workable multiple depends on the contract: the market-making class needs about 0.005 on ZN and about 1.0 on ES. One default per procedure cannot serve both.
- On both contracts the exclusions change the false-case count far less than in the simulation.
- On ES, flip episodes are harder to catch than in the simulation (75 of 128).
- Most seeded episodes on ZN never get a fill, which is consistent with a small order waiting behind more than a thousand lots at the touch.

## Diagnostics

- Own-percentile floor. The released experiments floor an account's own-percentile multiple at 0.02, which binds for 20 of 22 accounts on ZN. Without the floor ZN recall is 8.6% (64 of 740) with 3 false cases, so the conclusion does not depend on the floor. Every manipulating discretionary account still gets a higher threshold than every legitimate one (tools/selfq_floor.py, results_real/selfq_floor_ZN.txt).
- Missed flip episodes on ES. Of 128 completed flip episodes, 49 had no spoof order that passed the 5% fill test (the spoof orders, resting at the touch of an 18-lot book, were hit; 1,002 of 5,542 spoof lots traded) and 23 had a flip order that did not execute on entry. 75 met both conditions, which is the number detected. On ZN 475 of 483 met both (tools/diag_flip.py, results_real/diag_flip.json).

## Caveat on comparing multiples across contracts

The firm's accounts use the same lot sizes on every market. Multiplying each class multiple by the median displayed quantity within three ticks gives thresholds of roughly 20 to 110 lots on all three markets (apart from discretionary accounts on ES, where only the 5-lot floor applies). The two-orders-of-magnitude gap in multiples between ZN and ES therefore mirrors the gap in depth. The conclusion that a multiple cannot be carried between instruments stands; the size of the gap is a property of this design.

## Fill-ratio test on a thin book: the change the paper proposed, now tested (ES)

The paper found that on ES the 5% fill-ratio test removed flip episodes whose spoof orders, resting at
the touch of a thin book, were partly executed before they were cancelled. It proposed two changes and
tested neither. `tools/fill_fix.py` tests them on the same ES sessions (10 baseline, 10 test), with class
thresholds re-chosen for each configuration. The thresholds came out the same in all four.

```
configuration                          faithful episodes   flip episodes   false cases (of 160)
reference                              430 / 577           75 / 128        2
flip variant without the fill test     448 / 577           93 / 128        2
fill limit 50% at the touch            447 / 577           92 / 128        4
no fill limit at the touch             451 / 577           95 / 128        6
```

Dropping the fill test from the flip variant alone recovers 18 flip episodes and adds no false case.
Loosening the limit for every order entered at the touch recovers about the same number and doubles or
triples the false cases, because legitimate passive orders at the touch are also partly filled and then
cancelled. Of the 53 flip episodes missed in the reference run, 35 are still missed. In 23 of them the
flip order did not execute on entry, which no change to the fill test can fix. ZN has not been re-run;
8 of its 483 flip episodes had any fill on a spoof order, so little change is expected there.
Results: `results_real/fill_fix_ES.json`.

