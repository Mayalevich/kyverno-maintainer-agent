import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maintainer_agent.hygiene import (  # noqa: E402
    STALE_DAYS,
    VERY_STALE_DAYS,
    PRHealth,
    percentiles,
    review,
)


def _pr(idle, mergeable="MERGEABLE", draft=False, rev="REVIEW_REQUIRED"):
    return PRHealth(1, "t", idle, mergeable, draft, rev)


def test_draft_is_skipped_even_if_stale():
    assert review(_pr(90, draft=True)).action == "skip_draft"


def test_conflicts_take_priority():
    assert review(_pr(3, mergeable="CONFLICTING")).action == "suggest_rebase"


def test_fresh_pr_is_left_alone():
    assert review(_pr(2)).action == "leave"


def test_stale_awaiting_review_nudges_reviewer():
    assert review(_pr(20)).action == "nudge_reviewer"


def test_very_stale_nudges_author():
    assert review(_pr(60)).action == "nudge_author"


def test_stale_but_approved_is_not_a_reviewer_nudge():
    # idle but already approved -> not a REVIEW_REQUIRED nudge
    assert review(_pr(20, rev="APPROVED")).action == "leave"


def test_percentiles_and_thresholds_sit_in_the_tail():
    xs = [float(i) for i in range(1, 101)]  # 1..100
    p = percentiles(xs)
    assert p["n"] == 100
    assert p["p50"] == 51.0 and p["p95"] == 96.0
    assert 0.0 <= p["within_14d"] <= 1.0
    # thresholds are meant to sit in the tail of the real merge-time distribution
    assert STALE_DAYS < VERY_STALE_DAYS
    assert percentiles([]) == {}
