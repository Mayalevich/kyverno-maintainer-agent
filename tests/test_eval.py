import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maintainer_agent.eval_triage import evaluate, load_dataset  # noqa: E402


def test_backtest_precision_holds_on_cached_ground_truth():
    """Regression guard: the tuned keyword rules must keep agreeing with the real
    maintainer labels on the cached Kyverno dataset (164 singly-labelled issues)."""
    ds = load_dataset()
    assert len(ds) >= 150
    r = evaluate(ds)
    assert r.coverage >= 0.95
    assert r.precision >= 0.92
