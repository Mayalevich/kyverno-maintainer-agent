# kyverno-maintainer-agent

A working prototype for the CNCF **Kyverno AI Maintainer Assistant** mentorship
([kyverno/kyverno#16665](https://github.com/kyverno/kyverno/issues/16665)). It
implements **three Phase-1 workflows** against **real `kyverno/kyverno` data**,
all sharing one design: a **deterministic safety core**, output that is only ever
an **auditable suggestion** (a draft comment / label / nudge — never an applied
action), and a **human in the loop**.

| workflow | command | what it does | real Kyverno run |
|---|---|---|---|
| **Dependency PRs** | `agent` / `review` | classify the bump, gate auto-merge behind a deterministic policy | LLM tried to auto-merge a major CVE bump; the guard caught it |
| **Issue triage** | `triage` | suggest area labels, flag likely duplicates, catch incomplete bug reports | labelled/dup-checked 10 open issues |
| **PR hygiene** | `hygiene` | surface stale / conflicting PRs and suggest a nudge or rebase | flagged 5 PRs stale 86–117d + 4 awaiting review 14–17d |

The core question the mentorship has to answer is *"can you let an autonomous LLM
agent near a security project?"* This prototype's answer: **an LLM where it adds
value, but every consequential decision is re-checked by deterministic,
unit-tested code, and the assistant only ever proposes reviewable, revertible
actions — never a merge, label, or push.**

## Workflow 1 — dependency PRs: the trust model (the whole point)
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
reason.

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
every one.** That's the design working: the LLM is useful on the clear cases, but
its risky mistakes cannot reach a merge. A perfect agent would make the guard look
unnecessary; a fallible one *proves* it.

## Workflow 2 — issue triage
For each open issue, deterministic and reproducible suggestions
(`triage.py`): an **area label** from keyword rules (`type:cli`, `imageVerify`,
`type:controller`, …), **likely duplicates** via title-token Jaccard overlap, and
a **completeness check** that flags bug reports with no repro steps or version.
Output is a draft — labels a maintainer confirms, never applied. Ran on 10 real
open issues; e.g. it proposes `type:cli` on the CLI bug #16946 and `bug` on the
unlabelled #16949.

**It's backtested, not just plausible** (`eval_triage.py`, `python -m
maintainer_agent eval`). Kyverno maintainers have already area-labelled thousands
of issues; treating those as ground truth, on **164** issues carrying exactly one
area label the rules **agree with the maintainer's label 94% of the time** (151/161)
and stay silent on the rest rather than guess (98% coverage). The remaining misses
are genuinely ambiguous (an image bug reproduced via the CLI). One miss cluster the
backtest exposed — image issues grabbed by the CLI rule — was fixed by reordering
the rules, taking precision from 92% to 94%; a test locks the number in so it
can't silently regress.

**The duplicate detector is grounded too.** I recovered **3 real duplicate pairs**
from Kyverno's "Duplicate of #N" closing comments (issue-comments API) and
backtested against them: the title-overlap detector recalls **2/3**, and stays
selective — across 164 distinct issues it raises only two flags, both genuine
near-duplicates (a recurring CLI MutatingPolicy bug, a repeated workflow-failure
template), not noise. The one miss is honest and instructive: #16523 vs #15286
are the same bug worded differently ("fails to process
NamespacedImageValidationPolicy" vs "NamespacedImageValidatingPolicy failed to
call webhook") and share no title tokens — lexical overlap *cannot* catch that, so
embedding-based retrieval is the motivated next step (and retrieval is my
background).

## Workflow 3 — PR hygiene
`hygiene.py` scans open PRs oldest-first (a hygiene tool should surface the
*neglected* PRs, not the fresh ones) and classifies each deterministically: skip
drafts, suggest a **rebase** on conflicts, **nudge a reviewer** when a PR has
awaited review past a threshold, **nudge the author** when it's very stale. On
real Kyverno PRs it flagged five stale 86–117 days and four awaiting review
14–17 days — the exact PRs a maintainer would want surfaced.

**The thresholds aren't guessed** (`python -m maintainer_agent lifecycle`,
`samples/pr_lifecycle.md`). Measured on **300** merged Kyverno PRs, half merge in
under a day, **84% within 14 days**, **95% within 45** (p95 = 47.5d). So the
14-day soft-nudge and 45-day author-nudge thresholds are read straight off the
tail of the real merge-time distribution: a PR idle past 14 days is already slower
than ~84% of everything that merges, and past 45 days it's in the slowest few
percent.

## Quickstart
```bash
python -m maintainer_agent fetch --repo kyverno/kyverno   # cache real dep PRs (uses gh auth)
python -m maintainer_agent review                         # deterministic dep-PR policy (no LLM)
python -m maintainer_agent agent --model qwen2.5:7b       # LLM agent + safety guard (needs ollama)
python -m maintainer_agent triage                         # issue triage on live issues
python -m maintainer_agent hygiene                        # PR-hygiene scan on live PRs
python -m maintainer_agent eval                           # backtest triage vs real labels
python -m maintainer_agent lifecycle                      # measure real merge-time -> thresholds
```
Every deterministic path needs no LLM; the agent adds the autonomous layer on the
one workflow where a wrong call is dangerous (auto-merge).

## Design notes
- **Everything is read-only and the output is a *suggestion*** — a draft comment,
  label, or nudge, never a merge/label/push. Least privilege, human-in-the-loop,
  auditable, revertible — the constraints the mentorship emphasizes.
- **Every safety decision is deterministic and unit-tested** (`bump.py`,
  `policy.py`, `triage.py`, `hygiene.py`) — verifiable and reproducible, not a
  model guess, and the triage rules are **backtested against real maintainer
  labels (94% precision) and real duplicate pairs (2/3 recall)**. **24 tests.**
- **Reproducible:** data is cached to `samples/`; LLM calls use a fixed seed;
  `idle_days` is frozen at fetch time.
- Reuses the tool-calling agent pattern and Claude-Code-style skill I built for a
  prior project (an agentic CI-flake categorizer, `flakescope`).

## Scope and honesty
Three of the proposed Phase-1 workflows, run against live data. It does not act on
GitHub, run in a sandbox runtime (OpenHands/Hermes), or cover scoped test
selection — those are the mentorship. The label/dup/severity heuristics read
titles and bodies; richer signals (changelog/API diff, embedding-based dup search)
are natural next steps. The agent layer is currently on the dependency-PR workflow
where a wrong action is costly; the same agent-plus-guard pattern extends to the
others.
