# Extension set (v0.4): equities layering templates

Three order sequences from SEC and FINRA documents, added as a separate set. The five futures
templates, the v0.3 sessions and every number in the paper are unchanged: `run_benchmark.py`
reproduces `results/results.json` exactly with this code.

Sources (quoted facts and assumptions are in `SOURCES_EQ` in `spoofbench/equities.py`):

- trillium: FINRA action against Trillium Brokerage Services, LLC (Sept. 13, 2010). Numerous layered
  orders, large next to the stock's pending order volume, cancelled once the resting order filled.
- hold: In re Hold Brothers On-Line Investment Services, LLC, SEC Admin. Proc. File No. 3-15046
  (Sept. 25, 2012). The order's example: a 1,000-share order, eleven opposite orders totaling 2,600
  shares within about 160 ms, cancelled 0.6 s after the fill, then the same on the other side.
- milrud: SEC v. Milrud, No. 15-cv-00237 (D.N.J., Jan. 13, 2015). One account does the layering and a
  second account takes the fill.

Setup: the v0.3 roster plus four accounts, 30 baseline and 30 test sessions of 30 minutes on the
simulated market, seed 20261123. Numbers below are completed faithful episodes on the test
sessions. Full output: `results_ext/results_equities.md`.

## 1. Thresholds chosen before a pattern existed still found it, when the pattern is large

The class thresholds chosen in v0.3 were applied without re-choosing them. They found 341 of 349
Trillium episodes (97.7%) at 0.56 false cases per 100 legitimate account-sessions. The fixed
defaults found 37 of 349 (10.6%) and nothing else.

## 2. A layering sequence made of small orders passed under two tests at once

The rules found 2 of 291 Hold Brothers episodes (0.7%). `tools/diag_hold.py` shows why
(`results_ext/diag_hold.json`):

```
reference configuration                          2 of 291
two-sided quoting exclusion off                 31
size test off                                   77
both off                                       290
size test off, layers counted to 4 ticks       220
```

- Size test. The layers counted within three ticks total 19 lots at the median. The class
  threshold asks for 26.5. Only 22% of episodes meet it.
- Two-sided quoting exclusion. The genuine order rests on the other side and is more than half
  the counted layers, so the account looks like a market maker quoting both sides. With the size
  test off, this exclusion alone removes 213 of 290 episodes. Counting layers out to four ticks
  cuts that to 70.

The ranking model found 79.7% of these episodes without having been shown the pattern, and 94.5%
when trained on it. This is the reverse of the cancel-then-flip result in the paper, where the
rule finds the pattern and the model does not (here 97.4% against 23.8%). Neither covers both.

## 3. Splitting the scheme across two accounts hides it from account-level surveillance

With detection run per account, the rules found 4 of 333 Milrud episodes (1.2%). The ranking model
found 2.4% without having been shown the pattern and 8.1% when trained on it, because its candidates
are also built per account. After the two accounts are merged into one, as a firm would do if it
knew they were under common control, the rules found 168 of 333 (50.5%). The remaining half was
not diagnosed.

## Limits

- Simulated market only. No recorded equities data has been used.
- The book is the same one-tick-spread book as in v0.3, and sizes are taken literally at 100
  shares per lot. In the Hold Brothers example the layers sat inside a ten-cent spread and raised
  the best bid, and the stock's book was far thinner than this one. Finding 2 shows what a
  depth-relative size test and a quoting exclusion do to small layers in a deep book. It does not
  show how that pattern would score in the stock where it occurred.
- The Milrud release does not describe the order sequence. The sequence here is assumed.
- Linking accounts assumes the firm knows they are under common control. Across firms only a
  regulator or a consolidated audit trail can do it.
- Rates per session, the share of evasive episodes and the parameters marked "assumed" are choices.
