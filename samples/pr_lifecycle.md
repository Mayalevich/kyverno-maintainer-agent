# Kyverno PR lifecycle (grounds the hygiene thresholds)

Measured on **300** recently merged `kyverno/kyverno` PRs (created -> merged, in days).

| p50 | p75 | p90 | p95 | within 14d | within 45d |
|---|---|---|---|---|---|
| 0.9 | 4.1 | 25.1 | 47.5 | 84% | 95% |

Kyverno merges fast: half of PRs merge in under a day. So the hygiene thresholds are set to the tail: **STALE_DAYS=14** (~84% of PRs merge sooner) triggers a soft reviewer nudge, and **VERY_STALE_DAYS=45** (~95% merge sooner, i.e. the slowest few percent) triggers an author nudge or a close. These are read off the real distribution, not guessed.