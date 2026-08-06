# kyverno-maintainer-agent

A working prototype for the CNCF **Kyverno AI Maintainer Assistant** mentorship
([kyverno/kyverno#16665](https://github.com/kyverno/kyverno/issues/16665)). It
implements the first Phase-1 workflow — **safe, auditable triage of dependency
PRs** — against **real `kyverno/kyverno` PRs**.

The core question this project has to answer is *"can you let an autonomous LLM
agent near a security project?"* This prototype's answer: **an LLM agent, but
gated by a deterministic safety policy, so an unsafe action can never slip
through — and the assistant only ever proposes reviewable, revertible actions
(a comment + labels), never a merge.**

## The trust model (the whole point)
Two layers, and the second one is not optional:
1. **An LLM agent** investigates a PR with read-only tools (`get_pr_meta`,
   `get_ci_status`, `get_changed_files`) and recommends `auto_merge` or
   `human_review`. It's driven by a declarative **skill**
   (`skills/dep_review.md`, Claude-Code-style with YAML frontmatter).
2. **A deterministic safety policy** (`policy.py`) independently re-checks the
   agent. If the agent says `auto_merge` but the policy would block it, the
   **policy wins** and we log that the guard fired.

Auto-merge is only ever recommended when **all** hold: CI fully green, the bump is
**patch/minor** (never major), **only** manifests changed (never source code),
and the PR is mergeable. Everything else → a human, with the exact blocking
reason. When in doubt, ask a human.

## It ran on real Kyverno PRs — and the guard mattered
`python -m maintainer_agent agent` on 8 real dependency PRs:

| PR | severity | agent | policy | final | guard |
|---|---|---|---|---|---|
| #16945 (major, CVE) | major | `auto_merge` | `human_review` | **human_review** | 🛡️ fired |
| #16937 (patch) | patch | `auto_merge` | `auto_merge` | auto_merge | |
| #16936 (patch) | patch | `auto_merge` | `auto_merge` | auto_merge | |
| #16935 (grouped) | grouped | `auto_merge` | `human_review` | **human_review** | 🛡️ fired |
| #16934 (unknown) | unknown | `auto_merge` | `human_review` | **human_review** | 🛡️ fired |
| #16933 (CI red) | patch | `human_review` | `human_review` | human_review | |
| #16932 / #16915 (major + source) | major | `human_review` | `human_review` | human_review | |

**The 7B agent tried to auto-merge a major CVE bump, a grouped update, and an
unknown-version bump — all genuinely unsafe — and the deterministic guard caught
every one.** That's the design working: the LLM is useful on the clear cases
(safe patches → auto-merge; red-CI / major-with-code → human), but its risky
mistakes cannot reach a merge. A perfect agent would make the guard look
unnecessary; a fallible one *proves* it.

## Quickstart
```bash
python -m maintainer_agent fetch --repo kyverno/kyverno   # cache real dep PRs (uses gh auth)
python -m maintainer_agent review                         # deterministic policy (no LLM)
python -m maintainer_agent agent --model qwen2.5:7b       # LLM agent + safety guard (needs ollama)
```
The deterministic path needs no LLM; the agent adds the autonomous layer.

## Design notes
- **Everything is read-only and the output is a *suggestion*** — a draft comment
  + labels (`render_comment`), never a merge/label/push. Least privilege,
  human-in-the-loop, auditable, revertible — the constraints the mentorship
  emphasizes.
- **The safety decision is deterministic and unit-tested** (`bump.py`, `policy.py`),
  so it's verifiable and reproducible — not a model guess. 11 tests.
- **Reproducible:** PRs are cached to `samples/`; LLM calls use a fixed seed.
- Reuses the tool-calling agent pattern and Claude-Code-style skill I built for a
  prior project (an agentic CI-flake categorizer, `flakescope`).

## Scope and honesty
This is one workflow (dependency PRs), one Phase-1 slice of the proposed
assistant. It does not act on GitHub, run in a sandbox runtime (OpenHands/Hermes),
or handle the other workflows (PR hygiene, scoped test selection, issue triage) —
those are the mentorship. The version-severity heuristic reads the PR title;
richer breaking-change detection (changelog/API diff) is future work.
