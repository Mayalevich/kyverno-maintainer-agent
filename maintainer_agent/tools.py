"""Read-only tools the agent uses to investigate one PR itself.

The agent is given only a PR number and must call these to gather facts, then
submit a recommendation. Mirrors an MCP-style tool surface. All read-only.
"""
from __future__ import annotations

from .github_tools import PRInfo


class PRToolbox:
    def __init__(self, pr: PRInfo):
        self.pr = pr

    def get_pr_meta(self) -> str:
        p = self.pr
        return (f"number={p.number}\ntitle={p.title}\nauthor={p.author}\n"
                f"mergeable={p.mergeable}")

    def get_ci_status(self) -> str:
        return f"ci={self.pr.ci}"

    def get_changed_files(self) -> str:
        return "\n".join(self.pr.files) or "(none)"


TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_pr_meta",
        "description": "Get the PR title, author, and mergeable state.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_ci_status", "description": "Get the PR's CI status.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_changed_files", "description": "List the files the PR changes.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "submit",
        "description": "Submit the final recommendation once you have the facts.",
        "parameters": {"type": "object", "properties": {
            "action": {"type": "string", "enum": ["auto_merge", "human_review"]},
            "reason": {"type": "string"}},
            "required": ["action", "reason"]}}},
]


def dispatch(box: PRToolbox, name: str, args: dict) -> str:
    try:
        if name == "get_pr_meta":
            return box.get_pr_meta()
        if name == "get_ci_status":
            return box.get_ci_status()
        if name == "get_changed_files":
            return box.get_changed_files()
    except Exception as e:  # noqa: BLE001 - a tool must never crash the run
        return f"tool error: {type(e).__name__}: {e}"
    return f"unknown tool {name}"
