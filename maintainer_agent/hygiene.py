"""PR hygiene workflow: find stale / conflicting / behind PRs and suggest a nudge
or a rebase — as auditable suggestions, never applied.

Deterministic and unit-tested. `idle_days` is computed at fetch time so the
cached data is self-contained and the review is reproducible.
"""
from __future__ import annotations

import datetime
import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "samples"

# Thresholds are grounded in Kyverno's real merge-time distribution, not guessed
# (see `lifecycle` command / samples/pr_lifecycle.md). On 300 merged PRs: p50 is
# under a day, 84% merge within 14 days, 95% within 45 (p95 = 47.5d). So a PR idle
# past 14d is already slower than ~84% of all merged PRs (a soft reviewer nudge),
# and past 45d it is in the slowest ~5% (a strong author nudge or a close).
STALE_DAYS = 14
VERY_STALE_DAYS = 45


@dataclass
class PRHealth:
    number: int
    title: str
    idle_days: int
    mergeable: str        # MERGEABLE | CONFLICTING | UNKNOWN
    is_draft: bool
    review: str | None    # reviewDecision


@dataclass
class HygieneAction:
    action: str           # leave | nudge_reviewer | nudge_author | suggest_rebase | skip_draft
    reason: str


def _gh_json(args: list[str]) -> list[dict]:
    out = subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def fetch_open_prs(repo: str, limit: int = 30,
                   today: datetime.date | None = None) -> list[PRHealth]:
    today = today or datetime.date.today()
    # oldest-updated first: a hygiene tool should surface neglected PRs, not fresh ones
    d = _gh_json(["pr", "list", "-R", repo, "--state", "open", "--limit", str(limit),
                  "--search", "sort:updated-asc",
                  "--json", "number,title,updatedAt,mergeable,isDraft,reviewDecision"])
    out = []
    for p in d:
        upd = datetime.date.fromisoformat(p["updatedAt"][:10])
        out.append(PRHealth(
            number=p["number"], title=p["title"], idle_days=(today - upd).days,
            mergeable=p.get("mergeable") or "UNKNOWN", is_draft=p["isDraft"],
            review=p.get("reviewDecision")))
    return out


def review(pr: PRHealth) -> HygieneAction:
    if pr.is_draft:
        return HygieneAction("skip_draft", "draft PR — left for the author")
    if pr.mergeable == "CONFLICTING":
        return HygieneAction("suggest_rebase",
                             f"has conflicts with the base branch (idle {pr.idle_days}d)")
    if pr.idle_days >= VERY_STALE_DAYS:
        return HygieneAction("nudge_author",
                             f"stale for {pr.idle_days}d — nudge author or consider closing")
    if pr.idle_days >= STALE_DAYS and pr.review == "REVIEW_REQUIRED":
        return HygieneAction("nudge_reviewer",
                             f"awaiting review for {pr.idle_days}d — nudge a reviewer")
    return HygieneAction("leave", f"healthy (idle {pr.idle_days}d, {pr.mergeable})")


def percentiles(durations: list[float]) -> dict[str, float]:
    """Nearest-rank percentiles of a duration sample — pure and unit-tested."""
    xs = sorted(durations)
    n = len(xs)
    if not n:
        return {}
    def p(q: int) -> float:
        return round(xs[min(n - 1, int(q / 100 * n))], 1)
    return {"n": n, "p50": p(50), "p75": p(75), "p90": p(90), "p95": p(95),
            "within_14d": round(sum(x <= 14 for x in xs) / n, 3),
            "within_45d": round(sum(x <= 45 for x in xs) / n, 3)}


def fetch_merge_durations(repo: str, limit: int = 300) -> list[float]:
    d = _gh_json(["pr", "list", "-R", repo, "--state", "merged", "--limit", str(limit),
                  "--json", "createdAt,mergedAt"])
    out = []
    for p in d:
        if not p.get("mergedAt"):
            continue
        c = datetime.datetime.fromisoformat(p["createdAt"].replace("Z", "+00:00"))
        m = datetime.datetime.fromisoformat(p["mergedAt"].replace("Z", "+00:00"))
        out.append((m - c).total_seconds() / 86400)
    return out


def run_lifecycle(repo: str, limit: int = 300) -> int:
    stats = percentiles(fetch_merge_durations(repo, limit))
    lines = [
        "# Kyverno PR lifecycle (grounds the hygiene thresholds)", "",
        f"Measured on **{stats['n']}** recently merged `{repo}` PRs "
        "(created -> merged, in days).", "",
        "| p50 | p75 | p90 | p95 | within 14d | within 45d |",
        "|---|---|---|---|---|---|",
        f"| {stats['p50']} | {stats['p75']} | {stats['p90']} | {stats['p95']} | "
        f"{stats['within_14d']:.0%} | {stats['within_45d']:.0%} |", "",
        f"Kyverno merges fast: half of PRs merge in under a day. So the hygiene "
        f"thresholds are set to the tail: **STALE_DAYS={STALE_DAYS}** "
        f"(~{stats['within_14d']:.0%} of PRs merge sooner) triggers a soft reviewer "
        f"nudge, and **VERY_STALE_DAYS={VERY_STALE_DAYS}** (~{stats['within_45d']:.0%} "
        "merge sooner, i.e. the slowest few percent) triggers an author nudge or a "
        "close. These are read off the real distribution, not guessed.",
    ]
    (CACHE / "pr_lifecycle.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"  merged PRs: {stats['n']}  p50={stats['p50']}d p90={stats['p90']}d "
          f"p95={stats['p95']}d  within14d={stats['within_14d']:.0%}")
    print(f"-> {CACHE/'pr_lifecycle.md'}")
    return 0


def cache_prs(prs: list[PRHealth]) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "pr_health.json"
    out.write_text(json.dumps([asdict(p) for p in prs], indent=2), encoding="utf-8")
    return out


def load_prs() -> list[PRHealth]:
    data = json.loads((CACHE / "pr_health.json").read_text(encoding="utf-8"))
    return [PRHealth(**d) for d in data]
