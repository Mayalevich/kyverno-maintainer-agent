"""The safe review policy — deterministic, conservative, human-in-the-loop.

This is the heart of the assistant and the answer to the real fear of giving an
autonomous agent write access to a security project: it only ever *recommends*
auto-merge for the narrowest, provably-safe case, and flags everything else for a
human. It never merges. Every decision comes with an explicit, auditable reason.

Auto-merge is recommended ONLY when ALL hold:
  - CI is fully green (no failures, nothing pending),
  - the bump is patch or minor (never major / grouped / unknown),
  - only dependency manifests changed (never source code),
  - the PR is mergeable (no conflicts).
Anything else -> human review, with the specific blocking reason.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .bump import Bump

# Files that are *only* dependency manifests / pinned action versions.
_MANIFEST = re.compile(
    r"(^|/)(go\.mod|go\.sum|package(-lock)?\.json|yarn\.lock|requirements[^/]*\.txt|"
    r"Cargo\.(toml|lock)|poetry\.lock)$"
    r"|^\.github/workflows/.*\.ya?ml$", re.I)


@dataclass
class Recommendation:
    action: str            # "auto_merge" | "human_review"
    reason: str
    labels: list[str]
    blocking: list[str]    # the reasons a human is needed (empty if auto_merge)


def is_manifest(path: str) -> bool:
    return bool(_MANIFEST.search(path))


def review(bump: Bump, ci: str, files: list[str], mergeable: bool | None) -> Recommendation:
    """ci in {'green','red','pending','unknown'}."""
    blocking: list[str] = []
    code = [f for f in files if not is_manifest(f)]

    if ci != "green":
        blocking.append(f"CI is {ci}, not fully green")
    if bump.severity in ("major", "grouped", "unknown"):
        blocking.append(f"{bump.severity} bump needs human judgment")
    if code:
        blocking.append(f"changes source files, not just manifests ({', '.join(code[:3])})")
    if mergeable is False:
        blocking.append("has merge conflicts")

    if not blocking:
        reason = (f"{bump.severity} bump ({bump.from_version} -> {bump.to_version}), "
                  "CI green, manifest-only, mergeable")
        labels = ["dependencies", "safe-to-automerge"]
        if bump.is_security:
            labels.append("security")
            reason += " — security update, prioritized"
        return Recommendation("auto_merge", reason, labels, [])

    labels = ["dependencies", "needs-human-review"]
    if bump.is_security:
        labels.append("security")
    return Recommendation("human_review", "; ".join(blocking), labels, blocking)
