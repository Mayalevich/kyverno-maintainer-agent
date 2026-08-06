"""Honest backtest of the deterministic area-label suggester.

Kyverno maintainers have already labelled thousands of issues with an area label
(`type:controller`, `type:cli`, `imageVerify`). We treat those as ground truth and
measure how often the keyword rules in `triage.suggest_area` agree with the humans.

This turns "the labels look plausible" into a number on real data — and surfaces
where the rules are wrong, which is the point of measuring.
"""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .triage import Issue, suggest_area

CACHE = Path(__file__).resolve().parent.parent / "samples"
AREAS = ["type:controller", "type:cli", "imageVerify"]


@dataclass
class EvalResult:
    total: int
    covered: int            # we suggested some area
    correct: int            # suggestion matched the true area
    confusion: Counter      # (true, predicted) pairs we got wrong

    @property
    def coverage(self) -> float:
        return self.covered / self.total if self.total else 0.0

    @property
    def precision(self) -> float:
        return self.correct / self.covered if self.covered else 0.0


def fetch_labelled(repo: str, per_label: int = 60) -> list[Issue]:
    """Issues carrying exactly one of the AREAS labels — unambiguous ground truth."""
    seen: dict[int, Issue] = {}
    for lbl in AREAS:
        out = subprocess.run(
            ["gh", "issue", "list", "-R", repo, "--state", "all", "--label", lbl,
             "--limit", str(per_label), "--json", "number,title,body,labels"],
            capture_output=True, text=True, check=True).stdout
        for i in json.loads(out):
            names = [x["name"] for x in i["labels"]]
            if sum(a in names for a in AREAS) != 1:
                continue  # skip multi-area issues; ground truth must be singular
            seen[i["number"]] = Issue(i["number"], i["title"], i.get("body") or "", names)
    return list(seen.values())


def true_area(issue: Issue) -> str:
    return next(a for a in AREAS if a in issue.labels)


def evaluate(issues: list[Issue]) -> EvalResult:
    covered = correct = 0
    confusion: Counter = Counter()
    for iss in issues:
        pred = suggest_area(iss)
        if pred is None:
            continue
        covered += 1
        gold = true_area(iss)
        if pred == gold:
            correct += 1
        else:
            confusion[(gold, pred)] += 1
    return EvalResult(len(issues), covered, correct, confusion)


def cache_dataset(issues: list[Issue]) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "eval_issues.json"
    out.write_text(json.dumps(
        [{"number": i.number, "title": i.title, "body": i.body, "labels": i.labels}
         for i in issues], indent=2), encoding="utf-8")
    return out


def load_dataset() -> list[Issue]:
    data = json.loads((CACHE / "eval_issues.json").read_text(encoding="utf-8"))
    return [Issue(**d) for d in data]


def render(r: EvalResult) -> str:
    lines = [
        "# Triage label-suggester backtest (real Kyverno ground truth)", "",
        f"Evaluated against **{r.total}** issues the Kyverno maintainers have "
        f"already labelled with exactly one area label ({', '.join(AREAS)}).", "",
        f"- **Coverage:** the rules propose an area on **{r.covered}/{r.total}** "
        f"= {r.coverage:.0%} of issues (they stay silent rather than guess otherwise).",
        f"- **Precision:** when they do propose, they match the maintainer's label "
        f"on **{r.correct}/{r.covered}** = {r.precision:.0%}.", "",
    ]
    if r.confusion:
        lines.append("Where the rules disagreed with the humans (true -> predicted):")
        for (gold, pred), n in r.confusion.most_common():
            lines.append(f"- {gold} labelled as {pred}: {n}")
        lines.append("")
    lines.append("Silence is deliberate: an unlabelled suggestion costs a maintainer "
                 "nothing, a wrong one costs trust. The rules only speak when a keyword "
                 "clearly matches.")
    return "\n".join(lines)


def run_eval(repo: str = "kyverno/kyverno", per_label: int = 60) -> int:
    issues = fetch_labelled(repo, per_label)
    cache_dataset(issues)
    r = evaluate(issues)
    (CACHE / "eval_report.md").write_text(render(r), encoding="utf-8")
    print(f"  dataset: {r.total} singly-labelled issues")
    print(f"  coverage: {r.covered}/{r.total} = {r.coverage:.0%}")
    print(f"  precision: {r.correct}/{r.covered} = {r.precision:.0%}")
    if r.confusion:
        print("  misses:", dict(r.confusion))
    print(f"-> {CACHE/'eval_report.md'}")
    return 0
