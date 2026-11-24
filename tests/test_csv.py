"""Run with: python -m pytest tests  (or python tests/test_csv.py)"""
import json, os, sys
ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
from spoofbench.bench import make_session
from spoofbench.detect import Index, detect
from tools.emit_alerts import emit, reference_params, validate, SCHEMA, CLASS_K
from tools.run_on_csv import load, params_for

SAMPLE = os.path.join(ROOT, "data", "sample")


def _log():
    return load(os.path.join(SAMPLE, "orders_030.csv.gz"), os.path.join(SAMPLE, "fills_030.csv.gz"),
                os.path.join(SAMPLE, "episodes_030.json"), sid="30")


def test_files_give_the_same_flags_as_the_session_they_were_written_from():
    """The published sample is session 30 of the benchmark. Run from the files alone, the procedures
    flag the same orders as they do on the session in memory."""
    s = make_session(30, 20261123 + 10000)
    mem = sorted((i["acct"], i["proc"], tuple(i["oids"])) for i in detect([Index(s)], reference_params(s)))
    log = _log()
    csv = sorted((i["acct"], i["proc"], tuple(i["oids"])) for i in detect([Index(log)], params_for(log, CLASS_K, 0.1)))
    assert len(mem) > 0 and mem == csv


def test_alerts_from_files_follow_schema_and_read_no_labels():
    log = _log()
    assert all(o.ep is None and o.role is None for o in log.orders)
    alerts = emit([Index(log)], params_for(log, CLASS_K, 0.1), budget=None)
    schema = json.load(open(SCHEMA))
    assert alerts and all(validate(a, schema) == [] for a in alerts)
    assert all("false_case_budget_per_100" not in a["calibration"] for a in alerts)


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
