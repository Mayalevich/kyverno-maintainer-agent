import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from maintainer_agent.bump import classify  # noqa: E402
from maintainer_agent.policy import is_manifest, review  # noqa: E402


def test_classify_patch_minor_major():
    assert classify("chore(deps): bump x from 1.10.8 to 1.10.9").severity == "patch"
    assert classify("chore(deps): bump x from 1.10.8 to 1.11.0").severity == "minor"
    assert classify("chore(deps): bump x from 1.10.8 to 2.0.0").severity == "major"


def test_classify_bare_major_and_group_and_cve():
    assert classify("chore(deps): Upgrade robfig/cron to v3").severity == "major"
    assert classify("chore(deps): bump the sigstore group with 4 updates").severity == "grouped"
    assert classify("fix: bump oras-go to v2.6.2 to resolve CVE-2026-50163").is_security


def test_manifest_detection():
    assert is_manifest("go.mod") and is_manifest("go.sum")
    assert is_manifest(".github/workflows/ci.yml")
    assert not is_manifest("api/kyverno/v2/cleanup_policy_types.go")


def test_patch_green_manifest_only_is_auto_merge():
    b = classify("chore(deps): bump x from 1.10.8 to 1.10.9")
    r = review(b, "green", ["go.mod", "go.sum"], True)
    assert r.action == "auto_merge"


def test_major_is_always_human_even_if_green():
    b = classify("chore(deps): Upgrade robfig/cron to v3")
    r = review(b, "green", ["go.mod", "go.sum"], True)
    assert r.action == "human_review" and "major" in r.reason


def test_red_ci_blocks_auto_merge():
    b = classify("chore(deps): bump x from 1.0.0 to 1.0.1")
    assert review(b, "red", ["go.mod"], True).action == "human_review"


def test_source_file_change_blocks_auto_merge():
    b = classify("chore(deps): bump x from 1.0.0 to 1.0.1")
    r = review(b, "green", ["go.mod", "api/kyverno/v2/types.go"], True)
    assert r.action == "human_review" and "source files" in r.reason


def test_conflicts_block_auto_merge():
    b = classify("chore(deps): bump x from 1.0.0 to 1.0.1")
    assert review(b, "green", ["go.mod"], False).action == "human_review"
