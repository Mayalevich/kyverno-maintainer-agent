import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maintainer_agent.agent import guarded_action  # noqa: E402


def test_guard_blocks_unsafe_agent_auto_merge():
    # The whole trust model: agent says auto_merge, policy says human -> blocked.
    assert guarded_action("auto_merge", "human_review") == ("human_review", True)


def test_guard_allows_agreed_auto_merge():
    assert guarded_action("auto_merge", "auto_merge") == ("auto_merge", False)


def test_guard_never_upgrades_human_to_auto():
    # A conservative agent is never overridden toward the risky action.
    assert guarded_action("human_review", "auto_merge") == ("human_review", False)
    assert guarded_action("human_review", "human_review") == ("human_review", False)
