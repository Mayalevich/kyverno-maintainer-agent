import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maintainer_agent.triage import (  # noqa: E402
    Issue,
    find_duplicates,
    suggest_labels,
    triage,
)


def _iss(n, title, body="", labels=None):
    return Issue(n, title, body, labels or [])


def test_area_label_from_keywords():
    assert "type:cli" in suggest_labels(_iss(1, "[Bug] kyverno apply crashes on CEL"))
    assert "imageVerify" in suggest_labels(_iss(2, "[Bug] cosign image signature not verified"))
    assert "type:controller" in suggest_labels(_iss(3, "background reconcile loop stuck"))


def test_bug_label_and_no_duplicate_of_existing():
    labels = suggest_labels(_iss(4, "[Bug] webhook panic", labels=["bug"]))
    assert "bug" not in labels          # already present, not re-suggested
    assert "webhook" in labels


def test_duplicate_detection_by_title_overlap():
    a = _iss(10, "webhook admission timeout on large policy")
    b = _iss(11, "webhook admission timeout with large policy set")
    c = _iss(12, "CLI apply ignores exceptions")
    assert find_duplicates(a, [a, b, c]) == [11]
    assert find_duplicates(c, [a, b, c]) == []


def test_incomplete_bug_flagged_and_complete_not():
    thin = triage(_iss(20, "[Bug] it breaks", "broken"), [])
    assert thin.needs_more_info
    full_body = ("Steps to reproduce: apply policy X. Expected: allowed. "
                 "Actual: denied. Kyverno version: 1.11.0. " + "detail " * 80)
    rich = triage(_iss(21, "[Bug] denial", full_body), [])
    assert not rich.needs_more_info
