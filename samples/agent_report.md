# Agentic dependency-PR review (LLM + deterministic safety guard)

Model: `qwen2.5:7b`. The agent investigates each PR with tools and recommends; the deterministic policy then re-checks it.


**Agent vs deterministic policy:** agreed on 5/8. The safety guard overrode the agent on **3** PR(s) — an unsafe auto-merge can never slip through.
| PR | severity | agent says | policy says | final | guard fired? | trajectory |
|---|---|---|---|---|---|---|
| #16945 | major | auto_merge | human_review | **human_review** | 🛡️ yes | get_pr_meta -> get_ci_status ->  |
| #16937 | patch | auto_merge | auto_merge | **auto_merge** | no | get_pr_meta -> get_ci_status ->  |
| #16936 | patch | auto_merge | auto_merge | **auto_merge** | no | get_pr_meta -> get_ci_status ->  |
| #16935 | grouped | auto_merge | human_review | **human_review** | 🛡️ yes | get_pr_meta -> get_ci_status ->  |
| #16934 | unknown | auto_merge | human_review | **human_review** | 🛡️ yes | get_pr_meta -> get_ci_status ->  |
| #16933 | patch | human_review | human_review | **human_review** | no | get_pr_meta -> get_ci_status ->  |
| #16932 | major | human_review | human_review | **human_review** | no | get_pr_meta -> get_ci_status ->  |
| #16915 | major | human_review | human_review | **human_review** | no | get_pr_meta -> get_ci_status ->  |