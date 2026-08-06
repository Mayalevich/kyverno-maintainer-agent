"""CLI: python -m maintainer_agent <fetch|review|agent>."""
from __future__ import annotations

import argparse
from pathlib import Path

from .github_tools import cache_prs, get_pr, list_dep_prs, load_prs
from .review import render_comment, review_pr

OUT = Path(__file__).resolve().parent.parent / "samples"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="cache recent dependency PRs")
    f.add_argument("--repo", default="kyverno/kyverno")
    f.add_argument("--limit", type=int, default=8)

    sub.add_parser("review", help="deterministic policy review of cached PRs")

    a = sub.add_parser("agent", help="LLM agent investigates each PR via tools")
    a.add_argument("--model", default="qwen2.5:7b")

    args = ap.parse_args(argv)

    if args.cmd == "fetch":
        prs = [get_pr(args.repo, n) for n in list_dep_prs(args.repo, args.limit)]
        path = cache_prs(prs)
        print(f"cached {len(prs)} dependency PRs -> {path}")
        return 0

    if args.cmd == "agent":
        from .agent import run_agent
        return run_agent(args.model)

    # review
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


if __name__ == "__main__":
    raise SystemExit(main())
