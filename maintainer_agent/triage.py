"""Issue triage workflow: suggest area labels, flag likely duplicates, and check
bug-report completeness — all as auditable suggestions, never applied.

Deterministic and unit-tested. Label mapping and duplicate detection are
reproducible; nothing is guessed by a model in the safety path.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

CACHE = Path(__file__).resolve().parent.parent / "samples"

# Keyword -> Kyverno area label. First match wins; order matters.
_AREA = [
    (r"\bCLI\b|kyverno apply|kubectl kyverno", "type:cli"),
    (r"image ?validat|imageverif|cosign|image signature|attestation", "imageVerify"),
    (r"\bCEL\b|mutatingpolicy|validatingpolicy", "type:controller"),
    (r"controller|background|reconcil|globalcontext", "type:controller"),
    (r"webhook|admission", "webhook"),
    (r"\bhelm\b|install|deployment manifest", "helm"),
    (r"\bCRD\b|api |apiversion|openapi", "API Call"),
]
_STEPS = re.compile(r"reproduce|steps to|expected|actual|version:|kyverno version", re.I)


@dataclass
class Issue:
    number: int
    title: str
    body: str
    labels: list[str]


@dataclass
class TriageSuggestion:
    suggested_labels: list[str]
    duplicates: list[int]
    needs_more_info: bool
    reason: str


def _gh_json(args: list[str]) -> list[dict]:
    out = subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def fetch_issues(repo: str, limit: int = 10) -> list[Issue]:
    d = _gh_json(["issue", "list", "-R", repo, "--state", "open", "--limit", str(limit),
                  "--json", "number,title,body,labels"])
    return [Issue(i["number"], i["title"], i.get("body") or "",
                  [x["name"] for x in i["labels"]]) for i in d]


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


def suggest_labels(issue: Issue) -> list[str]:
    labels: list[str] = []
    text = f"{issue.title}\n{issue.body}"
    if re.search(r"\[bug\]|panic|crash|does not|doesn't|fails|incorrect", text, re.I):
        labels.append("bug")
    for pat, lab in _AREA:
        if re.search(pat, text, re.I):
            labels.append(lab)
            break
    # only suggest labels the issue doesn't already have
    return [lab for lab in labels if lab not in issue.labels]


def find_duplicates(issue: Issue, others: list[Issue], threshold: float = 0.5) -> list[int]:
    """Title-token Jaccard similarity — a simple, deterministic dup signal."""
    a = _tokens(issue.title)
    out = []
    for o in others:
        if o.number == issue.number:
            continue
        b = _tokens(o.title)
        if a and b and len(a & b) / len(a | b) >= threshold:
            out.append(o.number)
    return out


def triage(issue: Issue, others: list[Issue]) -> TriageSuggestion:
    labels = suggest_labels(issue)
    dups = find_duplicates(issue, others)
    is_bug = bool(re.search(r"\[bug\]|\bbug\b", issue.title, re.I))
    needs_info = is_bug and (len(issue.body) < 500 or not _STEPS.search(issue.body))
    bits = []
    if labels:
        bits.append(f"suggest labels {labels}")
    if dups:
        bits.append(f"possible duplicate of {dups}")
    if needs_info:
        bits.append("bug report looks incomplete (no clear repro/version)")
    return TriageSuggestion(labels, dups, needs_info,
                            "; ".join(bits) or "already triaged / no action")


def cache_issues(issues: list[Issue]) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "issues.json"
    out.write_text(json.dumps([asdict(i) for i in issues], indent=2), encoding="utf-8")
    return out


def load_issues() -> list[Issue]:
    data = json.loads((CACHE / "issues.json").read_text(encoding="utf-8"))
    return [Issue(**d) for d in data]
