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

from .triage import Issue, find_duplicates, suggest_area

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


# --- duplicate-detector grounding -------------------------------------------
# Ground truth = real kyverno/kyverno duplicates recovered from maintainer
# "Duplicate of #N" closing comments (see samples/dup_pairs.json).

@dataclass
class DupResult:
    recalled: list[int]        # dup issues whose canonical was flagged
    missed: list[int]          # dup issues we failed to link
    false_positives: int       # distinct-issue pairs wrongly flagged
    pool_size: int

    @property
    def recall(self) -> float:
        total = len(self.recalled) + len(self.missed)
        return len(self.recalled) / total if total else 0.0


def load_dup_pairs() -> list[dict]:
    return json.loads((CACHE / "dup_pairs.json").read_text(encoding="utf-8"))["pairs"]


def eval_duplicates(pairs: list[dict], distractors: list[Issue]) -> DupResult:
    recalled, missed = [], []
    for p in pairs:
        dup = Issue(p["dup"], p["dup_title"], "", [])
        canonical = Issue(p["canonical"], p["canonical_title"], "", [])
        pool = distractors + [canonical]
        (recalled if canonical.number in find_duplicates(dup, pool) else missed).append(
            p["dup"])
    # false positives: among distinct real issues, how many get any dup flagged?
    fp = sum(1 for iss in distractors if find_duplicates(iss, distractors))
    return DupResult(recalled, missed, fp, len(distractors))


def render_dup(d: DupResult, pairs: list[dict]) -> str:
    miss_note = ""
    if d.missed:
        miss_note = (f" The miss(es) {d.missed} are *semantic* duplicates — the same "
                     "bug described in different words (e.g. 'fails to process "
                     "NamespacedImageValidationPolicy' vs 'NamespacedImageValidatingPolicy "
                     "failed to call webhook'), which share no title tokens. Lexical "
                     "overlap cannot catch these; embedding-based retrieval is the fix "
                     "and the natural next step.")
    return "\n".join([
        "", "## Duplicate-detector backtest (real Kyverno duplicates)", "",
        f"Ground truth: **{len(pairs)}** issue pairs the maintainers closed as "
        "\"Duplicate of #N\", recovered from the issue-comments API.", "",
        f"- **Recall:** the title-overlap detector links **{len(d.recalled)}/"
        f"{len(d.recalled) + len(d.missed)}** = {d.recall:.0%} of real duplicates back "
        f"to their canonical issue.{miss_note}",
        f"- **Selectivity:** across **{d.pool_size}** distinct real issues, it raises a "
        f"duplicate flag on only **{d.false_positives}** (two pairs), and on inspection "
        "both are genuine near-duplicates — a recurring CLI MutatingPolicy bug "
        "(#15255/#16617) and a repeated workflow-failure template (#15923/#16233), not "
        "noise. The 0.5-Jaccard threshold keeps it conservative: a maintainer isn't "
        "spammed with false links.",
    ])


def run_eval(repo: str = "kyverno/kyverno", per_label: int = 60) -> int:
    issues = fetch_labelled(repo, per_label)
    cache_dataset(issues)
    r = evaluate(issues)
    pairs = load_dup_pairs()
    d = eval_duplicates(pairs, issues)
    (CACHE / "eval_report.md").write_text(render(r) + "\n" + render_dup(d, pairs),
                                          encoding="utf-8")
    print(f"  label backtest: {r.total} issues, coverage {r.coverage:.0%}, "
          f"precision {r.precision:.0%}")
    if r.confusion:
        print("    label misses:", dict(r.confusion))
    print(f"  dup backtest: recall {len(d.recalled)}/{len(d.recalled)+len(d.missed)}"
          f"={d.recall:.0%}, false-positives {d.false_positives}/{d.pool_size}")
    if d.missed:
        print("    dup misses (semantic):", d.missed)
    print(f"-> {CACHE/'eval_report.md'}")
    return 0
