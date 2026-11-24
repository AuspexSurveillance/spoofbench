# spoofbench

A seeded benchmark for spoofing and layering surveillance. It plants order sequences taken from
public enforcement documents into a simulated market and into replayed exchange order-by-order
data, runs rule-based detection procedures against them, and measures recall and false alerts.
It also contains the calibration method that the measurements support: thresholds chosen per
account class and per instrument on seeded sessions, under a budget on false cases.

Paper: Allen Yilun Li, "Calibrating Spoofing and Layering Surveillance Without Labelled Cases:
A Seeded Benchmark on Simulated and Recorded Futures Order Books" (2026).
SSRN: https://papers.ssrn.com/abstract=7747058

Maintained by Auspex Surveillance, Inc.: https://auspexsurveillance.com

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

## v0.5: a learned detector that starts from the cancel

`spoofbench/learned.py` scores groups of orders that an account cancels together, with or without a
fill, using a model trained on the seeded baseline sessions. `FINDINGS_V05.md` has the method, how
it was developed, every result and the limits. Same sessions, same false-case budget as above
(simulated / ZN / ES, test sessions):

- Share of all seeded attempts found, including those in which the genuine order never traded:
  procedures 38.8% / 24.3% / 47.3%; learned detector 97.2% / 99.4% / 76.7%.
- Share of completed faithful episodes (the measure used above): procedures
  76.3% / 88.4% / 74.5%; learned detector 97.7% / 99.6% / 88.7%.
- False cases among legitimate account-sessions: procedures 5 of 540 / 3 of 480 / 2 of 160; learned detector
  2 of 540 / 0 of 480 / 0 of 160.
- Three equities patterns that were never used in training or development (v0.4 sessions):
  trillium 97.6%, hold 99.9%, milrud 87.3% of all attempts
  (procedures: 68.1%, 0.2%, 0.7%).
- A futures pattern left out of training, share of all its attempts found (simulated / ZN / ES):
  chen 85.0% / 65.6% / 42.6%; coscia 100.0% / 100.0% / 89.1%; oystacher 88.1% / 67.5% / 42.6%;
  sarao 90.4% / 94.2% / 80.8%; lebental 66.0% (simulated only).
- What does not work yet. A legitimate account type that is missing from the baseline is flagged in
  nearly every session (stress tier: Scalper 60 of 60, LeggedHedger 56 of 60, BlockWorker 60 of 60;
  the procedures flag 1, 60 and 15). For a pattern left out of training, the thresholds either keep
  recall and lose control of false cases in one ZN run, or hold false cases and lose recall; both
  settings are reported.

All of this is on simulated accounts. Seeded episodes are more regular than real manipulation, so
results for patterns seen in training flatter any trained model.

```
python run_learned.py --tier std        # also: --tier eq, --tier stress
python run_real_learned.py prep DATADIR WINDIR ZN && python run_real_learned.py sim WINDIR RECDIR ZN && python run_real_learned.py eval RECDIR ZN results_v05
python report_v05.py
```

## Run it

    python tests/test_basic.py          # 5 checks, under a minute
    python run_benchmark.py             # 60 simulated sessions, about 2 minutes; writes results/results.json
    python report.py                    # writes results/results.md
    python run_benchmark.py --dump data # also writes every session as CSV (orders, fills) and JSON (labels)
    python tools/make_figures.py        # docs/fig_sweep.pdf and .png

The simulator, templates and detectors use only the Python standard library (3.9+). The ranking
experiment needs numpy and scikit-learn. A fixed seed (20261123) reproduces every number exactly.

## Specification and alert record (draft)

`spec/PROCEDURES.md` states the procedures, the calibration method and the alert record without
reference to this code, so they can be implemented independently. `spec/alert.schema.json` is the
JSON Schema of an alert and `spec/example_alert.json` is one alert.

    python tools/emit_alerts.py         # one seeded session -> alerts.jsonl, each record checked against the schema
    python tests/test_alerts.py         # 4 checks

To run the procedures on your own order and fill files, see `docs/RUN_ON_YOUR_OWN_RECORDS.md`:

    python tools/run_on_csv.py --orders data/sample/orders_030.csv.gz --fills data/sample/fills_030.csv.gz \
        --classes data/sample/episodes_030.json
    python tests/test_csv.py            # the files flag the same orders as the session they were written from

## Layout

    spoofbench/sim.py        price-time-priority order book, two correlated instruments, background flow
    spoofbench/accounts.py   legitimate account types (the hard negatives)
    spoofbench/templates.py  five manipulation templates and where each pattern fact comes from
    spoofbench/bench.py      account roster, session builder, CSV export
    spoofbench/detect.py     candidate pairing, detection procedures, two variants, calibration, scoring
    spoofbench/replay.py     replay of recorded order-by-order data with a queue-position model
    spoofbench/equities.py   extension set: three equities layering templates, account linking
    spoofbench/learned.py    v0.5 learned detector: pull groups, features, model, out-of-fold thresholds, scoring
    spoofbench/stress.py     v0.5 stress tier: harder legitimate accounts and adaptive manipulation
    run_benchmark.py         all experiments on the simulated market
    run_real.py              replay and experiments on recorded data
    run_equities.py          the extension set on the simulated market
    run_learned.py           v0.5 learned detector against the procedures (tiers std, eq, stress)
    run_real_learned.py      v0.5 learned detector on recorded data
    report_v05.py            results_v05/*.json -> FINDINGS_V05.md
    report.py                results JSON -> Markdown
    tools/get_cme_mbo.py     prices, buys and downloads CME MBO files from Databento (asks before buying)
    tools/prep_dbn.py        cuts a Databento MBO day file into 30-minute session windows
    tools/selfq_floor.py     own-percentile calibration with and without a floor
    tools/diag_flip.py       why flip episodes are missed on a thin book
    tools/diag_hold.py       why the Hold Brothers template is missed (extension set)
    tools/fill_fix.py        test of two changes to the fill-ratio test on recorded-data logs
    tools/make_figures.py    the figure in the paper
    tools/emit_alerts.py     detector output as alert records that follow spec/alert.schema.json
    tools/run_on_csv.py      the procedures on order and fill files in the published CSV format
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

## catrecon: seeded CAT reporting errors

A second study that reuses the simulated sessions as a broker's order records. It writes the CAT events
the firm would report, plants 19 kinds of labelled reporting error, and scores three controls: the CAT
feedback checks described in the public Industry Member specification, reconciliation against the firm's
own records, and reconciliation against exchange acknowledgements.

    cd catrecon
    python catrecon.py                  # coverage of each error kind by each control; writes results/results.json
    python extras.py                    # error rate shown, sampled review, clock offsets; writes results/extras.json
    python make_figs.py                 # figures (needs matplotlib)

Paper: Allen Yilun Li, "What CAT Feedback Cannot See: A Seeded Test of Three Controls for Consolidated
Audit Trail Reporting Errors" (2026). The CAT checks are a simplified reimplementation from the public
specification, not the CAT system.
SSRN: https://papers.ssrn.com/abstract=7747778

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

## If you use it

If you run the benchmark against your own detector or data, please open a "Usage report" issue and say
what you ran and what you found. Reports of things that break are as useful as results.
You can also write to hello@auspexsurveillance.com.

## Citation

See `CITATION.cff`.

## Licence and patent notice

Apache License 2.0; see `LICENSE` and `NOTICE`. Patent pending (U.S. Provisional Application
No. 64/205,097). Section 3 of the licence grants users of this code a patent licence.
