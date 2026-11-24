# spoofbench v0.4 extension set: equities layering templates

Seed 20261123. 30 baseline and 30 test sessions of 30 minutes on the simulated market. Roster: the v0.3 accounts plus four accounts that run the three new templates. Synthetic data.

## Recall by template on the test sessions (completed episodes, detected/total)

Fixed defaults (false cases per 100 legitimate account-sessions: 0.0)
```
chen                 0/570 (0.0%)
chen/evasive         0/243 (0.0%)
coscia               0/283 (0.0%)
coscia/evasive       0/115 (0.0%)
hold                 0/291 (0.0%)
hold/evasive         0/120 (0.0%)
lebental             0/117 (0.0%)
lebental/evasive     0/63 (0.0%)
milrud               0/333 (0.0%)
milrud/evasive       0/141 (0.0%)
oystacher            0/499 (0.0%)
oystacher/evasive    0/200 (0.0%)
sarao                0/64 (0.0%)
sarao/evasive        0/20 (0.0%)
trillium             37/349 (10.6%)
trillium/evasive     0/153 (0.0%)
```

Own 99.5th percentile (false cases per 100 legitimate account-sessions: 0.0)
```
chen                 9/570 (1.6%)
chen/evasive         0/243 (0.0%)
coscia               0/283 (0.0%)
coscia/evasive       0/115 (0.0%)
hold                 0/291 (0.0%)
hold/evasive         0/120 (0.0%)
lebental             3/117 (2.6%)
lebental/evasive     0/63 (0.0%)
milrud               0/333 (0.0%)
milrud/evasive       0/141 (0.0%)
oystacher            5/499 (1.0%)
oystacher/evasive    0/200 (0.0%)
sarao                59/64 (92.2%)
sarao/evasive        5/20 (25.0%)
trillium             3/349 (0.9%)
trillium/evasive     0/153 (0.0%)
```

v0.3 class thresholds, not re-chosen (false cases per 100 legitimate account-sessions: 0.56)
```
chen                 333/570 (58.4%)
chen/evasive         9/243 (3.7%)
coscia               279/283 (98.6%)
coscia/evasive       78/115 (67.8%)
hold                 2/291 (0.7%)
hold/evasive         0/120 (0.0%)
lebental             50/117 (42.7%)
lebental/evasive     2/63 (3.2%)
milrud               4/333 (1.2%)
milrud/evasive       0/141 (0.0%)
oystacher            486/499 (97.4%)
oystacher/evasive    161/200 (80.5%)
sarao                59/64 (92.2%)
sarao/evasive        5/20 (25.0%)
trillium             341/349 (97.7%)
trillium/evasive     22/153 (14.4%)
```

Class thresholds re-chosen on these sessions (false cases per 100 legitimate account-sessions: 0.74)
```
chen                 377/570 (66.1%)
chen/evasive         11/243 (4.5%)
coscia               279/283 (98.6%)
coscia/evasive       78/115 (67.8%)
hold                 2/291 (0.7%)
hold/evasive         0/120 (0.0%)
lebental             59/117 (50.4%)
lebental/evasive     6/63 (9.5%)
milrud               4/333 (1.2%)
milrud/evasive       0/141 (0.0%)
oystacher            486/499 (97.4%)
oystacher/evasive    161/200 (80.5%)
sarao                59/64 (92.2%)
sarao/evasive        5/20 (25.0%)
trillium             341/349 (97.7%)
trillium/evasive     22/153 (14.4%)
```

Re-chosen thresholds, the two accounts linked (false cases per 100 legitimate account-sessions: 0.74)
```
chen                 377/570 (66.1%)
chen/evasive         11/243 (4.5%)
coscia               279/283 (98.6%)
coscia/evasive       78/115 (67.8%)
hold                 2/291 (0.7%)
hold/evasive         0/120 (0.0%)
lebental             59/117 (50.4%)
lebental/evasive     6/63 (9.5%)
milrud               168/333 (50.5%)
milrud/evasive       1/141 (0.7%)
oystacher            486/499 (97.4%)
oystacher/evasive    161/200 (80.5%)
sarao                59/64 (92.2%)
sarao/evasive        5/20 (25.0%)
trillium             341/349 (97.7%)
trillium/evasive     22/153 (14.4%)
```

Class thresholds: v0.3 {'basis': 0.02, 'exec': 0.2, 'mm': 0.3, 'prop': 0.1}; re-chosen {'basis': 0.02, 'exec': 0.2, 'mm': 0.2, 'prop': 0.1}

## Two-sided quoting exclusion and the Hold Brothers pattern

Completed episodes found, by the ratio of layered quantity to the genuine order (faithful and evasive together):
```
ratio 1.0-1.5  n=45   with exclusions    0 | without exclusions    0
ratio 1.5-2.0  n=61   with exclusions    0 | without exclusions    0
ratio 2.0-2.5  n=100  with exclusions    0 | without exclusions    6
ratio 2.5-3.1  n=205  with exclusions    2 | without exclusions   25
```

## Ranking model on a template it was never shown (top-N per session at the rule's volume)

```
trillium   n=349  never shown 92.3% | trained on all 93.4% | rule 97.7%
hold       n=291  never shown 79.7% | trained on all 94.5% | rule 0.7%
milrud     n=333  never shown 2.4% | trained on all 8.1% | rule 1.2%
oystacher  n=499  never shown 23.8% | trained on all 89.8% | rule 97.4%
```
