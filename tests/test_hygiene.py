import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maintainer_agent.hygiene import PRHealth, review  # noqa: E402


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
