"""Deterministic review of one dependency PR, and the auditable comment it emits.

The assistant's *output* is a suggested comment + labels — a reviewable,
revertible artifact a human (or a gated automation) acts on. It never merges.
"""
from __future__ import annotations

from .bump import Bump, classify
from .github_tools import PRInfo
from .policy import Recommendation, review


def review_pr(pr: PRInfo) -> tuple[Bump, Recommendation]:
    bump = classify(pr.title)
    rec = review(bump, pr.ci, pr.files, pr.mergeable)
    return bump, rec


def render_comment(pr: PRInfo, bump: Bump, rec: Recommendation) -> str:
    """The auditable action the assistant proposes (a draft PR comment)."""
    if rec.action == "auto_merge":
        head = "✅ **Recommendation: safe to auto-merge**"
    else:
        head = "🛑 **Recommendation: needs human review**"
    lines = [
        head, "",
        f"- **Dependency:** `{bump.dependency or '?'}`  "
        f"**Change:** `{bump.from_version or '?'} -> {bump.to_version or '?'}` "
        f"(**{bump.severity}**{', security' if bump.is_security else ''})",
        f"- **CI:** {pr.ci}   **Mergeable:** {pr.mergeable}   "
        f"**Files:** {', '.join(pr.files[:4])}",
        f"- **Why:** {rec.reason}",
        f"- **Suggested labels:** {', '.join(rec.labels)}",
        "",
        "<sub>Proposed by an assistant prototype. This is a suggestion only — "
        "no merge or label was applied.</sub>",
    ]
    return "\n".join(lines)
