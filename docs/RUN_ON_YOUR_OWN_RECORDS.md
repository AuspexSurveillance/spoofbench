# Run the procedures on your own records

Draft. This is the path for a firm that wants to try the procedures on its own orders and fills.
Nothing is sent anywhere: it runs on your machine, with Python 3.9 or later and no other package.

## 1. Write two files

Orders, one row per order, CSV (optionally gzipped), with these columns:

    oid, acct, inst, side, px, qty, filled, t_in, t_out, status, aggr, dist, own_same, own_opp, depth_0 ... depth_8

- `side`: 1 buy, -1 sell. `px`: limit price in ticks, empty for a market order.
- `t_in`, `t_out`: seconds from the start of the session, to the microsecond.
- `status`: F filled, C cancelled, R replaced, L still live at the end.
- `aggr`: 1 if the order executed on entry.
- `dist`: ticks behind the same-side best price at entry (0 at the touch, negative if it improved it).
- `depth_0` to `depth_8`: displayed quantity on the order's side at each of nine price levels from
  the touch at entry, your own orders excluded.
- `own_same`, `own_opp`: your account's own resting quantity within three ticks on the order's side
  and on the other side, at entry.

Fills, one row per fill: `t, oid, qty, px, aggressor`.

The last three groups of order columns come from your market-data feed at the time of each entry.
`data/sample` holds one session in this format. Full definitions are in `spec/PROCEDURES.md`, section 2.

## 2. Say which class each account is

A CSV with the columns `acct,class`, where class is `mm` (market maker), `exec` (execution),
`prop` (proprietary or discretionary) or `basis`. Accounts you leave out use the multiple given by `--k`.

## 3. Run

    python tools/run_on_csv.py --orders orders.csv.gz --fills fills.csv.gz --classes classes.csv --out alerts.jsonl

On the sample:

    python tools/run_on_csv.py --orders data/sample/orders_030.csv.gz --fills data/sample/fills_030.csv.gz \
        --classes data/sample/episodes_030.json

    22,744 orders, 8,509 fills, 26 accounts
    49 alerts written to alerts.jsonl; schema errors: 0

## 4. Read the output

One JSON record per alert, following `spec/alert.schema.json`. Each record lists the flagged orders
and the opposite-side order, the book at entry, every test with the value observed and the threshold
in force, the exclusions, the repetition count, the parameters and a one-paragraph narrative built
from those fields.

## What this does and does not do

- It applies size multiples you give it (`--k-class`, `--k`). The defaults are the values the seeded
  calibration chose on the simulated market. They are not right for your instruments: the paper
  shows the workable value differs by a factor of up to 200 between two futures contracts.
- It does not choose the multiples for you. The seeded calibration is implemented for the simulated
  market (`run_benchmark.py`) and for recorded exchange order-by-order data (`run_real.py`). A version
  that seeds a firm's own log is not written yet.
- `tests/test_csv.py` checks that the sample files, run through this path, flag exactly the same
  orders as the session they were written from.
