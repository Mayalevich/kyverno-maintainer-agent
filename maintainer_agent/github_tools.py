"""Read-only GitHub access via the `gh` CLI (reuses the user's auth).

Everything here is read-only: the assistant inspects PRs and never mutates them.
Results are cached to `samples/` so a review run is reproducible and offline.
"""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "samples"


@dataclass
class PRInfo:
    number: int
    title: str
    author: str
    ci: str                # green | red | pending | unknown
    files: list[str]
    mergeable: bool | None


def _gh_json(args: list[str]) -> dict:
    out = subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def summarize_ci(checks: list[dict]) -> str:
    if not checks:
        return "unknown"
    c = Counter((x.get("conclusion") or x.get("state") or "").upper() for x in checks)
    if c.get("FAILURE") or c.get("ERROR") or c.get("TIMED_OUT") or c.get("CANCELLED"):
        return "red"
    if c.get("PENDING") or c.get("IN_PROGRESS") or c.get("") or c.get("QUEUED"):
        return "pending"
    return "green"


def get_pr(repo: str, number: int) -> PRInfo:
    d = _gh_json(["pr", "view", str(number), "-R", repo, "--json",
                  "number,title,author,mergeable,files,statusCheckRollup"])
    mergeable = {"MERGEABLE": True, "CONFLICTING": False}.get(d.get("mergeable"))
    return PRInfo(
        number=d["number"], title=d["title"], author=d["author"]["login"],
        ci=summarize_ci(d.get("statusCheckRollup") or []),
        files=[f["path"] for f in d.get("files", [])],
        mergeable=mergeable,
    )


def list_dep_prs(repo: str, limit: int = 8) -> list[int]:
    """Recent dependency PRs (dependabot or 'bump/deps' titles)."""
    import re
    prs = _gh_json(["pr", "list", "-R", repo, "--state", "all", "--limit", "40",
                    "--json", "number,title,author"])
    kw = re.compile(r"bump|chore\(deps|build\(deps|deps:|upgrade\s", re.I)
    out = [p["number"] for p in prs
           if "dependabot" in p["author"]["login"].lower() or kw.search(p["title"])]
    return out[:limit]


def cache_prs(prs: list[PRInfo]) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "prs.json"
    out.write_text(json.dumps([asdict(p) for p in prs], indent=2), encoding="utf-8")
    return out


def load_prs() -> list[PRInfo]:
    data = json.loads((CACHE / "prs.json").read_text(encoding="utf-8"))
    return [PRInfo(**d) for d in data]
