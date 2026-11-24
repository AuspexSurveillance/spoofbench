# Spoofing and layering surveillance: procedures, calibration and alert record

Open specification, draft 0.1, published 2026-11-24.

This document states, without reference to any product, the detection procedures, the calibration
method and the alert record that the code in this repository implements. A firm, a vendor or a
regulator can implement it from this text alone. `spoofbench/detect.py` is the reference
implementation, and where the two differ the code is the bug.

The procedure numbers (5.1, 5.2, 5.8) follow the design specification the benchmark was built to test.

## 1. Scope

Three procedures over one firm's own orders and fills:

- 5.1 spoofing: orders on one side, large against displayed depth, cancelled around a fill on the other side.
- 5.2 layering: the same, with the orders at several price levels. A persistent variant covers layers that rest for a long time and are not cancelled in response to a fill.
- 5.8 cross-product: the same, with the fill in a correlated instrument.

Wash trading, prearranged trading, marking the close, quote stuffing and momentum ignition are out of scope.

## 2. Inputs

The procedures read only what a firm's surveillance system has.

Order record, one per order:

- `oid`, `acct`, `inst`: order, account and instrument identifiers.
- `side`: +1 buy, -1 sell.
- `px`: limit price in ticks; empty for a market order.
- `qty`, `filled`: order quantity and quantity executed.
- `t_in`, `t_out`: entry time and the time the order left the book.
- `status`: F filled, C cancelled, R replaced, L still live at the end of the session.
- `aggr`: true if the order executed on entry.
- `dist`: ticks behind the same-side best price at entry. Zero is at the touch; negative improved it.
- `depth[0..8]`: displayed quantity on the order's side at each of the nine price levels from the touch, at entry, with the account's own orders excluded.
- `own_same`, `own_opp`: the account's own resting quantity within three ticks of the touch on the order's side and on the opposite side, at entry.

Fill record: time, `oid`, quantity, price, and whether the order was the aggressor.

Account master: for each account, its class. The reference classes are market maker (`mm`), execution (`exec`), proprietary or discretionary (`prop`) and basis (`basis`).

The last three order fields are market-data features. A firm computes them from its market-data feed at the time of each entry.

## 3. Candidates

For each fill of account A at time t on an order G of side g, and for G's instrument and each instrument listed as correlated with it, collect A's orders that:

- are on side -g in that instrument,
- are limit orders with status C,
- were entered between t - 30 s and t,
- left the book between t - 0.05 s and t + 20 s,
- are not G, and
- have not already been paired with an earlier fill.

Each order is paired once, with the first fill that follows its entry. A non-empty set is a candidate. It is cross-instrument if its instrument differs from G's.

## 4. Tests

Let `lat` be an order's exit time minus t. An order in a candidate is kept if all of these hold:

- distance: `dist` <= `d`;
- fill ratio: `filled` <= `f_max` x `qty`;
- entry window: `t_in` >= t - `W`;
- cancel latency: 0 <= `lat` <= `t_cancel`, plus `lag` if the candidate is cross-instrument. In the flip variant (section 7) an order with `lat` < 0 is also kept if G executed on entry.

If no order is kept the candidate is dropped. Otherwise let Q be the total quantity of the kept orders and D the displayed depth within `d` ticks at the entry of the earliest kept order (the sum of `depth[0..d]`).

- size: Q >= max(`q_min`, k x D), where k is the multiple in force for the account (section 9).

## 5. Exclusions

A candidate that passes the tests is dropped if either holds:

- two-sided quoting: at the entry of the earliest kept order, `own_opp` >= `sym` x (`own_same` + Q);
- re-quote: within `requote` seconds after the last kept order left the book, counted from that time inclusive, the account entered at least 0.5 x Q on the same side of the same instrument.

A candidate that survives is an instance.

## 6. Classification and repetition

An instance is 5.8 if it is cross-instrument; otherwise 5.2 if the kept orders are at `L` or more distinct prices; otherwise 5.1.

An instance is flagged, and raises an alert, if the account has `n` or more instances in the trailing `P_sessions` sessions, the current one included.

## 7. Variants

Two variants are off in the literal procedure and on in the reference configuration. The benchmark shows each is needed: without it the pattern it covers is not found.

- Flip. The opposite-side execution may follow the cancel by a few milliseconds instead of preceding it. Section 4 gives the rule. Reference case: CFTC v. Oystacher.
- Persistent layering (5.2P). Take the account's limit orders on one side with `dist` >= 2, status C or R, no fills and a positive lifetime. The pattern is "on" while such orders rest at `L` or more distinct prices and their total quantity is at least max(`q_min`, `kP` x R), where R is the displayed quantity at levels 2 and beyond at the entry of the newest of them. An alert is raised when an "on" period ends after lasting `T_min` or longer and the account had a fill on the other side between its start and `W` after its end. At equal timestamps entries are applied before exits, so a cancel-replace does not break the period. The repetition rule of section 6 does not apply to this variant. Reference case: CFTC v. Sarao.

Two optional settings change the fill-ratio test. `flip_fill` = false drops the test for orders kept by the flip variant. `f_touch` sets a different limit for orders entered at or inside the touch. On recorded E-mini S&P 500 data the first recovered 18 of 53 missed flip episodes with no added false case; the second roughly doubled or tripled false cases (`FINDINGS_REAL.md`).

## 8. Parameters

Defaults of the literal procedure:

- `W` 30 s: window from entry to the opposite-side fill.
- `k` 2.0: size multiple of displayed depth. Not usable as a default; see section 9.
- `d` 3 ticks.
- `t_cancel` 5 s; `lag` 1 s added for cross-instrument candidates.
- `f_max` 0.05.
- `n` 3 instances within `P_sessions` 1 session.
- `L` 3 price levels.
- `q_min` 5 lots.
- `sym` 0.5; `requote` 0.5 s.
- `kP` 1.0; `T_min` 20 s.

## 9. Calibration of the size multiple

A single default for k does not work. On the benchmark the default found between 0.0% and 2.6% of completed seeded episodes, and the multiple that worked for one class of account differed by a factor of up to 200 between two futures contracts. A multiple taken from each account's own history (the 99.5th percentile of its entry size over displayed depth) found 3.1% to 7.8%, because an account that manipulates carries its manipulation in its own history.

The method:

1. Take baseline sessions of the firm's own orders and fills for the instrument.
2. Seed them with labelled episodes that follow documented manipulative sequences, sized as the firm's accounts trade.
3. For each value of k on a grid, run the procedures with the variants on, and count false cases: account-sessions of legitimate accounts with at least one flagged instance and no true one.
4. For each account class, choose the smallest k on the grid whose false cases are within the budget. The reference budget is 2 per 100 account-sessions of that class.
5. Report recall on the seeded episodes at the chosen values. Keep the report with the date, the grid and the budget.
6. Repeat for each instrument. Do not carry a value from one instrument to another.

The reference grid is 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0 for the simulated market, with smaller values added for deep books.

## 10. Alert record

An alert is a JSON object that follows `spec/alert.schema.json`. `spec/example_alert.json` is an example and `tools/emit_alerts.py` writes one record per flagged instance.

Rules for the record:

- It holds every number needed to check the alert by hand: the flagged orders and the opposite-side order as a list of events, the book at entry, each test with the value observed and the threshold in force, each exclusion with whether it was applied and whether it was met, the repetition count, and the parameters in force.
- It states where the size multiple came from: the default, the account's class, or the account.
- The narrative is assembled from the fields by a fixed template. It contains no free text.
- It carries no ground truth. A record written from a seeded session does not say which orders were seeded.

A raised alert passes every test it lists, meets no applied exclusion and meets the repetition rule. `tests/test_alerts.py` checks this.

## 11. Conformance

`python run_benchmark.py` with the fixed seed 20261123 reproduces `results/results.json` exactly. An independent implementation conforms if, on the sessions written by `python run_benchmark.py --dump data`, it flags the same instances as the reference implementation under the same parameters. `data/sample` holds one such session, `tools/run_on_csv.py` runs the procedures from such files alone, and `tests/test_csv.py` checks that the sample files flag exactly the orders the session in memory does.

## 12. Status and terms

Draft. The text and the code are under the Apache License 2.0. The calibration method in section 9 is the subject of U.S. Provisional Application No. 64/205,097. Section 3 of the licence gives users of the code a patent licence. Terms for implementations that do not use the code have not been set; write to hello@auspexsurveillance.com.
