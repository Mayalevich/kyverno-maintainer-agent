"""kyverno-maintainer-agent — a prototype of Kyverno's AI Maintainer Assistant.

Phase 1, first workflow: safely triage dependency PRs. A deterministic policy
engine decides (auditably) whether a bump is safe to auto-merge or needs a human,
and an optional tool-calling agent reaches the same verdict by investigating the
PR itself. The assistant only ever proposes reviewable, revertible actions
(a comment + labels); it never merges.
"""
__version__ = "0.1.0"
