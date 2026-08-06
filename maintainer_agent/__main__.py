"""CLI for the Kyverno AI Maintainer Assistant prototype.

Three Phase-1 workflows, one shared design (deterministic safety core, auditable
suggestions, real kyverno/kyverno data):
  python -m maintainer_agent fetch | review | agent   # dependency-PR review
  python -m maintainer_agent triage                   # issue triage
  python -m maintainer_agent hygiene                  # open-PR hygiene
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import hygiene as hy
from . import triage as tr
from .github_tools import cache_prs, get_pr, list_dep_prs, load_prs
from .review import render_comment, review_pr

OUT = Path(__file__).resolve().parent.parent / "samples"


def _run_review() -> int:
    prs = load_prs()
    rows = [(pr, *review_pr(pr)) for pr in prs]
    report = ["# Dependency PR review (deterministic policy)", ""]
    auto = sum(1 for _, _, rec in rows if rec.action == "auto_merge")
    report.append(f"Reviewed **{len(rows)}** PRs — **{auto}** safe to auto-merge, "
                  f"**{len(rows) - auto}** need a human.\n")
    for pr, bump, rec in rows:
        report.append(f"### #{pr.number} — {pr.title}")
        report.append(render_comment(pr, bump, rec))
        report.append("")
        flag = "AUTO-MERGE" if rec.action == "auto_merge" else "human"
        print(f"  #{pr.number:6} {bump.severity:8} ci={pr.ci:7} -> {flag:10} {rec.reason[:60]}")
    (OUT / "review_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"-> {OUT/'review_report.md'}")
    return 0


def _run_triage(repo: str, limit: int) -> int:
    issues = tr.fetch_issues(repo, limit)
    tr.cache_issues(issues)
    report = ["# Issue triage (deterministic suggestions — nothing applied)", "",
              f"Triaged **{len(issues)}** open `{repo}` issues. Every line below is a "
              "*suggestion* a maintainer confirms; no label or comment was applied.\n",
              "| issue | suggested labels | possible dup | needs info | note |",
              "|---|---|---|---|---|"]
    acted = 0
    for iss in issues:
        s = tr.triage(iss, issues)
        if s.suggested_labels or s.duplicates or s.needs_more_info:
            acted += 1
        report.append(f"| #{iss.number} | {', '.join(s.suggested_labels) or '—'} | "
                      f"{s.duplicates or '—'} | {'yes' if s.needs_more_info else '—'} | "
                      f"{s.reason} |")
        print(f"  #{iss.number:6} {s.reason[:70]}")
    report.insert(3, f"**{acted}/{len(issues)}** issues have a suggested action.\n")
    (OUT / "triage_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"-> {OUT/'triage_report.md'}")
    return 0


def _run_hygiene(repo: str, limit: int) -> int:
    prs = hy.fetch_open_prs(repo, limit)
    hy.cache_prs(prs)
    report = ["# Open-PR hygiene (deterministic suggestions — nothing applied)", "",
              f"Scanned **{len(prs)}** open `{repo}` PRs for staleness, conflicts, and "
              "drafts. Each row is a suggested nudge; no PR was touched.\n",
              "| PR | idle (d) | mergeable | draft | suggested action | reason |",
              "|---|---|---|---|---|---|"]
    acted = 0
    for pr in prs:
        a = hy.review(pr)
        if a.action not in ("leave", "skip_draft"):
            acted += 1
        report.append(f"| #{pr.number} | {pr.idle_days} | {pr.mergeable} | "
                      f"{'yes' if pr.is_draft else '—'} | **{a.action}** | {a.reason} |")
        print(f"  #{pr.number:6} idle={pr.idle_days:3}d -> {a.action:15} {a.reason[:50]}")
    report.insert(3, f"**{acted}/{len(prs)}** PRs warrant a nudge; the rest are healthy "
                     "or drafts.\n")
    (OUT / "hygiene_report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"-> {OUT/'hygiene_report.md'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="cache recent dependency PRs")
    f.add_argument("--repo", default="kyverno/kyverno")
    f.add_argument("--limit", type=int, default=8)

    sub.add_parser("review", help="deterministic policy review of cached dependency PRs")

    a = sub.add_parser("agent", help="LLM agent investigates each dependency PR via tools")
    a.add_argument("--model", default="qwen2.5:7b")

    t = sub.add_parser("triage", help="triage open issues (labels, dups, completeness)")
    t.add_argument("--repo", default="kyverno/kyverno")
    t.add_argument("--limit", type=int, default=10)

    h = sub.add_parser("hygiene", help="scan open PRs for staleness / conflicts")
    h.add_argument("--repo", default="kyverno/kyverno")
    h.add_argument("--limit", type=int, default=30)

    args = ap.parse_args(argv)

    if args.cmd == "fetch":
        prs = [get_pr(args.repo, n) for n in list_dep_prs(args.repo, args.limit)]
        path = cache_prs(prs)
        print(f"cached {len(prs)} dependency PRs -> {path}")
        return 0
    if args.cmd == "agent":
        from .agent import run_agent
        return run_agent(args.model)
    if args.cmd == "triage":
        return _run_triage(args.repo, args.limit)
    if args.cmd == "hygiene":
        return _run_hygiene(args.repo, args.limit)
    return _run_review()


if __name__ == "__main__":
    raise SystemExit(main())
