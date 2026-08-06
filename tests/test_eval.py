import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maintainer_agent.eval_triage import (  # noqa: E402
    eval_completeness,
    eval_duplicates,
    evaluate,
    load_closed_bugs,
    load_dataset,
    load_dup_pairs,
)


def test_backtest_precision_holds_on_cached_ground_truth():
    """Regression guard: the tuned keyword rules must keep agreeing with the real
    maintainer labels on the cached Kyverno dataset (164 singly-labelled issues)."""
    ds = load_dataset()
    assert len(ds) >= 150
    r = evaluate(ds)
    assert r.coverage >= 0.95
    assert r.precision >= 0.92


def test_duplicate_detector_recovers_real_duplicates():
    """The title-overlap detector must recover the exact-title real duplicates and
    stay selective on distinct issues. The one known miss is a semantic duplicate
    (different wording), which documents the lexical-matching limitation."""
    ds = load_dataset()
    pairs = load_dup_pairs()
    d = eval_duplicates(pairs, ds)
    assert d.recall >= 0.66            # 2/3 real pairs; the miss is semantic
    assert 16523 in d.missed           # the different-wording pair is the known miss
    assert d.false_positives <= 6      # stays conservative on 164 distinct issues


def test_completeness_check_is_conservative_on_fixed_bugs():
    """On real bugs that were complete enough to be fixed (closed COMPLETED), the
    completeness check must stay quiet on the large majority — it flags thin reports,
    it does not nag well-formed ones."""
    bugs = load_closed_bugs()
    c = eval_completeness(bugs)
    assert c["by_reason"]["COMPLETED"]["n"] >= 100
    assert c["specificity"] >= 0.90
