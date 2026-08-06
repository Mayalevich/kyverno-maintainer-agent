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