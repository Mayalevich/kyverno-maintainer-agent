"""The agentic layer: an LLM investigates each PR via tools and recommends.

Crucially, whatever the agent recommends is re-checked by the deterministic safety
policy (`policy.review`). If the agent says `auto_merge` but the policy would block
it, the policy wins and we record that the guard fired. This is the trust model
for letting an LLM near a security project: its risky call can never slip through.

Uses Ollama tool-calling (`/api/chat`, qwen2.5). If Ollama is unreachable the run
degrades to the deterministic policy so `agent` still produces a report.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .github_tools import PRInfo, load_prs
from .review import review_pr
from .tools import TOOL_SCHEMAS, PRToolbox, dispatch

SKILL = (Path(__file__).resolve().parent.parent / "skills" / "dep_review.md").read_text(
    encoding="utf-8")
OUT = Path(__file__).resolve().parent.parent / "samples"


@dataclass
class AgentReview:
    agent_action: str
    agent_reason: str
    trajectory: list[str] = field(default_factory=list)
    reached: bool = False   # did the agent submit on its own?


def _chat(model: str, messages: list[dict]) -> dict:
    body = json.dumps({"model": model, "messages": messages, "tools": TOOL_SCHEMAS,
                       "stream": False,
                       "options": {"temperature": 0, "seed": 0}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["message"]


def investigate(pr: PRInfo, model: str, max_steps: int = 6) -> AgentReview:
    box = PRToolbox(pr)
    messages = [{"role": "system", "content": SKILL},
                {"role": "user", "content": f"Review PR #{pr.number}. Investigate "
                                             "with tools, then submit."}]
    res = AgentReview("human_review", "agent did not submit (defaulted to safe)")
    for _ in range(max_steps):
        try:
            msg = _chat(model, messages)
        except Exception as e:  # noqa: BLE001 - degrade to deterministic policy
            res.agent_reason = f"agent unavailable ({type(e).__name__})"
            return res
        calls = msg.get("tool_calls") or []
        if not calls:
            messages.append({"role": "user", "content": "Call a tool or submit."})
            continue
        messages.append(msg)
        for call in calls:
            fn = call["function"]["name"]
            args = call["function"].get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    args = {}
            if fn == "submit":
                action = args.get("action")
                res.agent_action = action if action in ("auto_merge", "human_review") \
                    else "human_review"
                res.agent_reason = str(args.get("reason", ""))[:200]
                res.reached = True
                res.trajectory.append("submit")
                return res
            res.trajectory.append(fn)
            messages.append({"role": "tool", "content": dispatch(box, fn, args)[:1500]})
    return res


def guarded_action(agent_action: str, policy_action: str) -> tuple[str, bool]:
    """Deterministic safety guard: an agent 'auto_merge' the policy would block is
    overridden to 'human_review'. Returns (final_action, guard_fired)."""
    if agent_action == "auto_merge" and policy_action == "human_review":
        return "human_review", True
    return agent_action, False


def run_agent(model: str) -> int:
    prs = load_prs()
    lines = ["# Agentic dependency-PR review (LLM + deterministic safety guard)", "",
             f"Model: `{model}`. The agent investigates each PR with tools and "
             "recommends; the deterministic policy then re-checks it.", "",
             "| PR | severity | agent says | policy says | final | guard fired? | trajectory |",
             "|---|---|---|---|---|---|---|"]
    agree = guard_fired = 0
    for pr in prs:
        ar = investigate(pr, model)
        bump, rec = review_pr(pr)                 # deterministic ground truth
        final, blocked = guarded_action(ar.agent_action, rec.action)
        guard_fired += blocked
        agree += ar.agent_action == rec.action
        traj = " -> ".join(ar.trajectory)[:32]
        lines.append(f"| #{pr.number} | {bump.severity} | {ar.agent_action} | "
                     f"{rec.action} | **{final}** | {'🛡️ yes' if blocked else 'no'} | {traj} |")
        print(f"  #{pr.number:6} agent={ar.agent_action:12} policy={rec.action:12} "
              f"final={final:12} {'GUARD FIRED' if blocked else ''}")
    summary = (f"\n**Agent vs deterministic policy:** agreed on {agree}/{len(prs)}. "
               f"The safety guard overrode the agent on **{guard_fired}** PR(s) — "
               "an unsafe auto-merge can never slip through.")
    lines.insert(4, summary)
    (OUT / "agent_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(summary.strip())
    print(f"-> {OUT/'agent_report.md'}")
    return 0
