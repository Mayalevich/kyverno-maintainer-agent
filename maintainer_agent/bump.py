"""Classify a dependency bump from a Dependabot-style PR title.

Deterministic and unit-tested: the severity decision must be auditable and
reproducible, never a model guess. Handles the real Kyverno title formats:
  "chore(deps): bump github.com/sigstore/sigstore from 1.10.8 to 1.10.9"
  "chore(deps): Upgrade robfig/cron to v3"
  "chore(deps): bump the sigstore group across 1 directory with 4 updates"
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_FROM_TO = re.compile(r"\bfrom\s+v?(\d+(?:\.\d+){0,2})\s+to\s+v?(\d+(?:\.\d+){0,2})", re.I)
_TO_MAJOR = re.compile(r"\bto\s+v(\d+)\b", re.I)
_GROUP = re.compile(r"\bgroup\b.*\bupdates?\b", re.I)
_CVE = re.compile(r"CVE-\d{4}-\d+", re.I)


@dataclass
class Bump:
    severity: str          # patch | minor | major | grouped | unknown
    from_version: str | None
    to_version: str | None
    is_security: bool      # mentions a CVE
    dependency: str | None


def _parts(v: str) -> list[int]:
    out = []
    for p in v.split("."):
        try:
            out.append(int(p))
        except ValueError:
            out.append(0)
    while len(out) < 3:
        out.append(0)
    return out[:3]


def _severity(frm: str, to: str) -> str:
    a, b = _parts(frm), _parts(to)
    if a[0] != b[0]:
        return "major"
    if a[1] != b[1]:
        return "minor"
    if a[2] != b[2]:
        return "patch"
    return "unknown"


def _dependency(title: str) -> str | None:
    m = re.search(r"bump(?:\s+the)?\s+([^\s]+)", title, re.I) or \
        re.search(r"[Uu]pgrade\s+([^\s]+)", title)
    return m.group(1) if m else None


def classify(title: str) -> Bump:
    security = bool(_CVE.search(title))
    dep = _dependency(title)
    if _GROUP.search(title):
        return Bump("grouped", None, None, security, dep)
    m = _FROM_TO.search(title)
    if m:
        frm, to = m.group(1), m.group(2)
        return Bump(_severity(frm, to), frm, to, security, dep)
    # "Upgrade X to v3" style (no explicit from) -> treat a bare vN as major.
    m2 = _TO_MAJOR.search(title)
    if m2:
        return Bump("major", None, f"v{m2.group(1)}", security, dep)
    return Bump("unknown", None, None, security, dep)
