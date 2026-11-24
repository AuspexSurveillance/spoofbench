"""Run with: python -m pytest tests  (or python tests/test_learned.py). Needs numpy and scikit-learn."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from spoofbench.bench import make_session
from spoofbench.learned import features, featurize, Detector, evaluate, FEATS, USE, SPECIFIC
from spoofbench.stress import make_session_stress, ADAPTIVE


def test_groups_partition_cancelled_orders():
    """Every resting order that was cancelled with quantity left is in exactly one pull group."""
    s = make_session(0, 5, T=300.0)
    X, meta = features(s)
    assert X.shape == (len(meta), len(FEATS)) and not np.isnan(X).any()
    seen = [o for m in meta for o in m["oids"]]
    want = {o.oid for o in s.orders if o.px is not None and o.status in ("C", "R") and o.t_out > o.t_in and o.qty - o.filled > 0}
    assert len(seen) == len(set(seen)) and set(seen) == want
    for m in meta:
        assert m["true"] == int(any(s.by_oid[o].role == "spoof" for o in m["oids"]))


def test_features_ignore_ground_truth():
    """Erasing the labels must not change a single feature."""
    s = make_session(0, 5, T=300.0)
    X1, _ = features(s)
    for o in s.orders:
        o.ep, o.role = None, None
    X2, meta = features(s)
    assert np.array_equal(X1, X2) and not any(m["true"] for m in meta)


def test_no_pattern_specific_feature_in_the_model():
    assert not set(USE) & set(SPECIFIC)


def test_stress_session_runs():
    s = make_session_stress(0, 3, T=300.0)
    assert {e["template"] for e in s.episodes} & set(ADAPTIVE)
    assert {"SCALP_1", "LEG_1", "BLOCK_1"} <= set(s.accounts)


def test_detector_end_to_end():
    base = [featurize(make_session(i, 100 + i, T=600.0)) for i in range(4)]
    test = [featurize(make_session(10 + i, 200 + i, T=600.0)) for i in range(2)]
    det = Detector(folds=2, trees=30).fit(base)
    p, rows = det.score(test)
    ev, hit = evaluate(test, det.flag(rows, p))
    d, n = ev["all_attempts"]
    assert n > 0 and d / n > 0.5
    # an account left out of training and calibration is still scored
    det2 = Detector(folds=2, trees=30).fit(base, exclude={"M_OYST"})
    p2, rows2 = det2.score(test)
    assert len(p2) == len(p)
    e = det.explain(np.vstack([r["X"] for r in test])[:, det.cols][int(np.argmax(p))].astype(float))
    assert 0.0 <= e["score"] <= 1.0 and len(e["drops"]) == 6


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
