# Triage label-suggester backtest (real Kyverno ground truth)

Evaluated against **164** issues the Kyverno maintainers have already labelled with exactly one area label (type:controller, type:cli, imageVerify).

- **Coverage:** the rules propose an area on **161/164** = 98% of issues (they stay silent rather than guess otherwise).
- **Precision:** when they do propose, they match the maintainer's label on **151/161** = 94%.

Where the rules disagreed with the humans (true -> predicted):
- imageVerify labelled as type:controller: 3
- type:cli labelled as helm: 2
- type:cli labelled as imageVerify: 2
- type:controller labelled as webhook: 1
- type:controller labelled as type:cli: 1
- type:controller labelled as imageVerify: 1

Silence is deliberate: an unlabelled suggestion costs a maintainer nothing, a wrong one costs trust. The rules only speak when a keyword clearly matches.

## Duplicate-detector backtest (real Kyverno duplicates)

Ground truth: **3** issue pairs the maintainers closed as "Duplicate of #N", recovered from the issue-comments API.

- **Recall:** the title-overlap detector links **2/3** = 67% of real duplicates back to their canonical issue. The miss(es) [16523] are *semantic* duplicates — the same bug described in different words (e.g. 'fails to process NamespacedImageValidationPolicy' vs 'NamespacedImageValidatingPolicy failed to call webhook'), which share no title tokens. Lexical overlap cannot catch these; embedding-based retrieval is the fix and the natural next step.
- **Selectivity:** across **164** distinct real issues, it raises a duplicate flag on only **4** (two pairs), and on inspection both are genuine near-duplicates — a recurring CLI MutatingPolicy bug (#15255/#16617) and a repeated workflow-failure template (#15923/#16233), not noise. The 0.5-Jaccard threshold keeps it conservative: a maintainer isn't spammed with false links.