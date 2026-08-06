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


def cache_prs(prs: list[PRHealth]) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "pr_health.json"
    out.write_text(json.dumps([asdict(p) for p in prs], indent=2), encoding="utf-8")
    return out


def load_prs() -> list[PRHealth]:
    data = json.loads((CACHE / "pr_health.json").read_text(encoding="utf-8"))
    return [PRHealth(**d) for d in data]
