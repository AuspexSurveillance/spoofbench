"""Run with: python -m pytest tests  (or python tests/test_alerts.py)"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from spoofbench.bench import make_session
from spoofbench.detect import Index, detect
from tools.emit_alerts import emit, reference_params, validate, SCHEMA


def _alerts():
    s = make_session(0, 5, T=600.0)
    ix = Index(s)
    P = reference_params(s)
    return s, ix, P, emit([ix], P)


def test_alerts_follow_schema():
    """Every alert the reference configuration raises is a valid record, one per flagged instance."""
    s, ix, P, alerts = _alerts()
    schema = json.load(open(SCHEMA))
    assert len(alerts) == len(detect([ix], P)) > 0
    for a in alerts:
        assert validate(a, schema) == []


def test_alert_is_checkable_by_hand():
    """A raised alert passes every test it reports, meets no applied exclusion and meets the repetition rule."""
    s, ix, P, alerts = _alerts()
    for a in alerts:
        assert all(t["passed"] for t in a["tests"])
        assert not any(e["applied"] and e["met"] for e in a["exclusions"])
        assert a["repetition"]["count"] >= a["repetition"]["required"]
        flagged = sum(e["quantity"] for e in a["events"] if e["role"] == "flagged" and e["action"] == "enter")
        size = [t for t in a["tests"] if t["name"] == "size"]
        assert not size or size[0]["observed"] == flagged


def test_alert_has_no_ground_truth():
    """The record carries nothing from the labels."""
    s, ix, P, alerts = _alerts()
    text = json.dumps(alerts)
    assert '"ep"' not in text and '"role": "spoof"' not in text and '"true"' not in text


def test_validator_rejects_bad_records():
    s, ix, P, alerts = _alerts()
    schema = json.load(open(SCHEMA))
    a = json.loads(json.dumps(alerts[0]))
    del a["tests"]
    a["procedure"]["id"] = "9.9"
    a["extra"] = 1
    assert len(validate(a, schema)) == 3


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
