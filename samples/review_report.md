# Dependency PR review (deterministic policy)

Reviewed **8** PRs — **2** safe to auto-merge, **6** need a human.

### #16945 — fix: bump oras.land/oras-go/v2 to v2.6.2 to resolve CVE-2026-50163
🛑 **Recommendation: needs human review**

- **Dependency:** `oras.land/oras-go/v2`  **Change:** `? -> v2` (**major**, security)
- **CI:** green   **Mergeable:** None   **Files:** go.mod, go.sum
- **Why:** major bump needs human judgment
- **Suggested labels:** dependencies, needs-human-review, security

<sub>Proposed by an assistant prototype. This is a suggestion only — no merge or label was applied.</sub>

### #16937 — chore(deps): bump github.com/sigstore/sigstore from 1.10.8 to 1.10.9
✅ **Recommendation: safe to auto-merge**

- **Dependency:** `github.com/sigstore/sigstore`  **Change:** `1.10.8 -> 1.10.9` (**patch**)
- **CI:** green   **Mergeable:** None   **Files:** go.mod, go.sum
- **Why:** patch bump (1.10.8 -> 1.10.9), CI green, manifest-only, mergeable
- **Suggested labels:** dependencies, safe-to-automerge

<sub>Proposed by an assistant prototype. This is a suggestion only — no merge or label was applied.</sub>

### #16936 — chore(deps): bump github.com/google/go-containerregistry from 0.21.7 to 0.21.8
✅ **Recommendation: safe to auto-merge**

- **Dependency:** `github.com/google/go-containerregistry`  **Change:** `0.21.7 -> 0.21.8` (**patch**)
- **CI:** green   **Mergeable:** None   **Files:** go.mod, go.sum
- **Why:** patch bump (0.21.7 -> 0.21.8), CI green, manifest-only, mergeable
- **Suggested labels:** dependencies, safe-to-automerge

<sub>Proposed by an assistant prototype. This is a suggestion only — no merge or label was applied.</sub>

### #16935 — chore(deps): bump the sigstore group across 1 directory with 4 updates
🛑 **Recommendation: needs human review**

- **Dependency:** `sigstore`  **Change:** `? -> ?` (**grouped**)
- **CI:** green   **Mergeable:** None   **Files:** go.mod, go.sum
- **Why:** grouped bump needs human judgment
- **Suggested labels:** dependencies, needs-human-review

<sub>Proposed by an assistant prototype. This is a suggestion only — no merge or label was applied.</sub>

### #16934 — chore(deps): bump Homebrew/actions/limit-pull-requests from 2026.07.29.1 to 2026.08.03.1
🛑 **Recommendation: needs human review**

- **Dependency:** `Homebrew/actions/limit-pull-requests`  **Change:** `? -> ?` (**unknown**)
- **CI:** green   **Mergeable:** None   **Files:** .github/workflows/pr-rate-limiter.yaml
- **Why:** unknown bump needs human judgment
- **Suggested labels:** dependencies, needs-human-review

<sub>Proposed by an assistant prototype. This is a suggestion only — no merge or label was applied.</sub>

### #16933 — chore(deps): bump zgosalvez/github-actions-ensure-sha-pinned-actions from 5.0.4 to 5.0.6
🛑 **Recommendation: needs human review**

- **Dependency:** `zgosalvez/github-actions-ensure-sha-pinned-actions`  **Change:** `5.0.4 -> 5.0.6` (**patch**)
- **CI:** red   **Mergeable:** None   **Files:** .github/workflows/check-sha-pinned-actions.yaml
- **Why:** CI is red, not fully green
- **Suggested labels:** dependencies, needs-human-review

<sub>Proposed by an assistant prototype. This is a suggestion only — no merge or label was applied.</sub>

### #16932 — chore(deps): Upgrade robfig/cron to v3
🛑 **Recommendation: needs human review**

- **Dependency:** `robfig/cron`  **Change:** `? -> v3` (**major**)
- **CI:** green   **Mergeable:** None   **Files:** api/kyverno/v2/cleanup_policy_types.go, api/kyverno/v2beta1/cleanup_policy_types.go, go.mod, go.sum
- **Why:** major bump needs human judgment; changes source files, not just manifests (api/kyverno/v2/cleanup_policy_types.go, api/kyverno/v2beta1/cleanup_policy_types.go)
- **Suggested labels:** dependencies, needs-human-review

<sub>Proposed by an assistant prototype. This is a suggestion only — no merge or label was applied.</sub>

### #16915 — chore(deps): Upgrade gotest.tools to v3
🛑 **Recommendation: needs human review**

- **Dependency:** `gotest.tools`  **Change:** `? -> v3` (**major**)
- **CI:** green   **Mergeable:** None   **Files:** api/kyverno/v1/clusterpolicy_test.go, api/kyverno/v1/image_verification_test.go, api/kyverno/v1/match_resources_test.go, api/kyverno/v1/policy_test.go
- **Why:** major bump needs human judgment; changes source files, not just manifests (api/kyverno/v1/clusterpolicy_test.go, api/kyverno/v1/image_verification_test.go, api/kyverno/v1/match_resources_test.go)
- **Suggested labels:** dependencies, needs-human-review

<sub>Proposed by an assistant prototype. This is a suggestion only — no merge or label was applied.</sub>
