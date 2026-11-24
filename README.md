# spoofbench

A seeded benchmark for spoofing and layering surveillance. It plants order sequences taken from
public enforcement documents into a simulated market and into replayed exchange order-by-order
data, runs rule-based detection procedures against them, and measures recall and false alerts.
It also contains the calibration method that the measurements support: thresholds chosen per
account class and per instrument on seeded sessions, under a budget on false cases.

Paper: Allen Yilun Li, "Calibrating Spoofing and Layering Surveillance Without Labelled Cases:
A Seeded Benchmark on Simulated and Recorded Futures Order Books" (2026).
SSRN: https://papers.ssrn.com/abstract=7747058

## Main results

Measured on held-out sessions of a simulated market and of recorded CME order-by-order data for
10-Year Treasury Note (ZN) and E-mini S&P 500 (ES) futures (simulated / ZN / ES):

- Fixed default thresholds: 0.0% / 0.0% / 2.6% of completed seeded episodes detected.
- Thresholds from each account's own 99.5th percentile: 4.9% / 7.8% / 3.1%.
- Thresholds chosen per account class on seeded sessions: 76.3% / 88.4% / 74.5%, at
  0.93 / 0.62 / 1.25 false cases per 100 legitimate account-sessions.
- Two documented patterns (cancel-then-flip, persistent layering) are missed until the
  procedures are extended.
- A ranking model trained on seeded labels matches the rules on patterns it has seen and
  does not generalize to a held-out pattern.

Full tables: `FINDINGS.md` (simulated market), `FINDINGS_REAL.md` (all three side by side),
`results/` and `results_real/`. Figure: `docs/fig_sweep.png`.

## Run it

    python tests/test_basic.py          # 5 checks, under a minute
    python run_benchmark.py             # 60 simulated sessions, about 2 minutes; writes results/results.json
    python report.py                    # writes results/results.md
    python run_benchmark.py --dump data # also writes every session as CSV (orders, fills) and JSON (labels)
    python tools/make_figures.py        # docs/fig_sweep.pdf and .png

The simulator, templates and detectors use only the Python standard library (3.9+). The ranking
experiment needs numpy and scikit-learn. A fixed seed (20261123) reproduces every number exactly.

## Layout

    spoofbench/sim.py        price-time-priority order book, two correlated instruments, background flow
    spoofbench/accounts.py   legitimate account types (the hard negatives)
    spoofbench/templates.py  five manipulation templates and where each pattern fact comes from
    spoofbench/bench.py      account roster, session builder, CSV export
    spoofbench/detect.py     candidate pairing, detection procedures, two variants, calibration, scoring
    spoofbench/replay.py     replay of recorded order-by-order data with a queue-position model
    spoofbench/equities.py   extension set: three equities layering templates, account linking
    run_benchmark.py         all experiments on the simulated market
    run_real.py              replay and experiments on recorded data
    run_equities.py          the extension set on the simulated market
    report.py                results JSON -> Markdown
    tools/get_cme_mbo.py     prices, buys and downloads CME MBO files from Databento (asks before buying)
    tools/prep_dbn.py        cuts a Databento MBO day file into 30-minute session windows
    tools/selfq_floor.py     own-percentile calibration with and without a floor
    tools/diag_flip.py       why flip episodes are missed on a thin book
    tools/diag_hold.py       why the Hold Brothers template is missed (extension set)
    tools/make_figures.py    the figure in the paper
    data/sample/             one exported simulated session

## The benchmark

Market. Either two simulated instruments, each a limit order book driven by background flow whose
market orders respond to displayed imbalance, or a replay of recorded exchange order-by-order data.

Firm. Legitimate accounts built to look like manipulation (market makers including slow
re-quoters and a ladder, execution algorithms, discretionary accounts, basis traders), and
manipulating accounts that each run one template. Only the firm's own orders and fills, with
book features captured at each order entry, are visible to a detector. Every seeded order carries
a hidden label.

Templates and sources (quoted facts and assumptions are in `SOURCES` in `spoofbench/templates.py`):

- chen: In re Tanius Technology, LLC, CFTC Docket No. 22-34 (2022)
- coscia: In re Panther Energy Trading LLC and Coscia, CFTC Docket No. 13-26 (2013)
- oystacher: CFTC v. Oystacher and 3Red Trading LLC, No. 1:15-cv-09196 (N.D. Ill. 2015)
- sarao: CFTC v. Nav Sarao Futures Limited PLC and Sarao (N.D. Ill. 2015)
- lebental: In re Sidney Lebental, CFTC Docket No. 26-01 (2026)

Thirty percent of episodes are evasive variants (smaller, slower), reported separately.

## Extension set: equities layering (v0.4)

Three more templates, from SEC and FINRA documents, run as a separate set so that the five
templates above and every number in the paper stay exactly reproducible:

- trillium: FINRA action against Trillium Brokerage Services, LLC (Sept. 13, 2010)
- hold: In re Hold Brothers On-Line Investment Services, LLC, SEC Admin. Proc. File No. 3-15046 (2012)
- milrud: SEC v. Milrud, No. 15-cv-00237 (D.N.J. 2015), where one account layers and a second takes the fill

    python run_equities.py              # 60 simulated sessions; writes results_ext/results_equities.json and .md
    python tools/diag_hold.py           # which test removes the Hold Brothers episodes

Findings and limits: `FINDINGS_EQ.md`. Quoted facts and assumptions: `SOURCES_EQ` in
`spoofbench/equities.py`. These templates run on the simulated market only.

## Recorded market data

    python tools/get_cme_mbo.py                           # needs a Databento account and API key
    python tools/prep_dbn.py DAYFILE.dbn.zst WINDIR       # one MBO day file -> six 30-minute windows
    python run_real.py sim  WINDIR LOGDIR ES              # replay every window, write one log per window
    python run_real.py eval LOGDIR ES OUTDIR              # all experiments; writes results_real_ES.json
    python report.py OUTDIR/results_real_ES.json

Firm orders in the replay are hypothetical. They queue behind the recorded displayed size and
are filled when the recorded flow would have reached them; they do not change the recorded book
and nobody reacts to them. The market data is licensed and is not part of this repository. The
results files hold aggregate statistics only.

## Limits

- The firm's accounts are simulated. False-case rates on a real firm's flow will differ.
- The recorded market does not react to the firm's orders.
- The legitimate accounts and two of the templates use the same lot sizes on every market, so
  comparisons of depth multiples across contracts reflect that design (see `FINDINGS_REAL.md`).
- Template parameters that the source documents do not state are assumptions, listed in `SOURCES`.
- Two contracts, ten trading days. The cross-instrument pattern is tested on the simulated market only.
- A flagged instance is a pattern that warrants review. It is not a finding of intent.

## Citation

See `CITATION.cff`.

## Licence and patent notice

Apache License 2.0; see `LICENSE` and `NOTICE`. Patent pending (U.S. Provisional Application
No. 64/205,097). Section 3 of the licence grants users of this code a patent licence.
