# Improvement backlog — sgl-model-gateway

Carries open issues across `skill-improver` runs that the loop attempted but couldn't apply in a single iteration. NOT a wishlist — entries here were proposed as hypotheses, attempted or planned, and could not land atomically.

## Open

### Cross-file `hf-hub` vs `reqwest` precision asymmetry (Dim 8) (carried 2026-05-28)
- **Files:** `references/air-gapped.md:66`, `references/pitfalls.md:41`
- **Surfaced by:** iter 10 (final blind validator), 2026-05-09
- **What:** Iter 10 corrected SKILL.md:173 to distinguish `reqwest` (service-discovery probes) from `llm-tokenizer`'s `hf-hub` (tokenizer fetches). The two reference files were not updated in the same iteration and still say only "the Rust gateway uses the `hf-hub` crate" — collapsing both code paths to one. Result is a precision asymmetry across files. SKILL.md and `references/tokenizers.md:127` are correct; `cli-flags.md:242` is also correct (narrow env-var statement). The two stragglers need the same precision.
- **Why not in one iteration:** Iter 10 was a single-file edit (SKILL.md) per the atomicity rule. Propagating to two more files plus harmonising terminology with sources.md row could be one follow-up iteration scoped as "Tighten reqwest/hf-hub split across air-gapped.md and pitfalls.md."

### Inline validation/smoke-test step missing from SKILL.md body (Dim 4 ceiling) (carried 2026-05-28)
- **Files:** `SKILL.md` Path B section, K8s minimal pattern section
- **Surfaced by:** iter 8 (discarded), iter 10 final blind
- **What:** Body has 3-4 bash command examples but no validation/smoke-test follow-ups (`curl -s http://localhost:8080/v1/models | jq` style). One validation pattern lives in `references/air-gapped.md:139` but is not surfaced in SKILL.md proper. Iter 8 added a single validation line — score didn't lift because rubric Dim 4=9 needs **multiple** validation steps. A bundled iteration that adds validation snippets to all 3-4 bash examples would lift Dim 4 from 8 to 9.
- **Why not in one iteration:** Iter 8 was scoped to a single example for atomicity; the rubric requires plural. Author judgement needed on whether to add 3-4 validation snippets (+~12 lines) at the cost of Dim 6 simplicity — the score-tradeoff isn't obvious.

### `SKILL.md` mesh paragraph density (Dim 6) (carried 2026-05-28)
- **Files:** `SKILL.md` line 123 (the `--enable-mesh` paragraph in §"Hosting multiple replicas")
- **Surfaced by:** iter 10 final blind
- **What:** Single paragraph crams 7 distinct mesh-sync facts (CRDT crate, what syncs, what doesn't, default port, two annotation names, two peer-discovery wire methods, `first()` quirk). Could split or move the wire-up details into `references/kubernetes.md` HA section. Not attempted in this run because iter 6+ already addressed bigger redundancy targets and the trim was less obvious.
- **Why not in one iteration:** Multi-file move (relocate ~150 chars to `kubernetes.md` and replace with pointer) is atomic-relocation, but author judgement needed on whether the density is a feature (one-glance HA reference) or a bug.

### `references/history.md` is stranded (Dim 5 / Dim 8 mild) (carried 2026-05-28)
- **Files:** `SKILL.md` body (no motivating section), `references/history.md` (existing file)
- **Surfaced by:** iter 10 final blind
- **What:** "Where to go next" line 209 points at `references/history.md` but no SKILL.md body section motivates when an operator would need a non-`memory` history backend. The reference exists in isolation — no body cross-link contextualises it. Either add one motivating sentence under §"Architecture in one paragraph" or §"Sibling skills", or accept that history is a niche tangential topic and demote the pointer.
- **Why not in one iteration:** Author judgement — content that doesn't fit the operator's main path may legitimately stay terse. A "did you know about /v1/responses" sentence adds value but also adds scope creep.

### Policy set / tokenizer-location decision-tree duplication (Dim 6) (added 2026-05-28)
- **Files:** `SKILL.md` §"Architecture in one paragraph" + §"Decision tree — where the tokenizer must live"; `references/policies-and-tokenizer.md` (the deep-dive lives across `cli-flags.md:42-48` and `tokenizers.md`)
- **Surfaced by:** RECON hypothesis (Dim 6 7→8), 2026-05-28
- **What:** The policy set and the tokenizer-location decision tree are stated in SKILL.md and re-stated in the reference files (cli-flags.md policy table, tokenizers.md "When the gateway uses a tokenizer" table). RECON proposed collapsing to one canonical location with a pointer.
- **Why not in one iteration:** Picking the canonical home and rewriting the pointer without orphaning a section is a multi-section restructure that needs author judgement on whether the SKILL.md summary earns its place as a one-glance operator reference (it arguably does — the duplication is summary-vs-detail, not verbatim). Deferred to avoid a content-dropping edit under the atomicity rule.

### YAML assets not schema-validated against a live Kubernetes schema (Dim 7) (added 2026-05-28)
- **Files:** `assets/sglang-gateway-deployment.yaml`, `assets/vllm-behind-gateway.yaml`
- **Surfaced by:** RECON hypothesis (Dim 7 7→8), 2026-05-28
- **What:** Both assets were confirmed this pass to parse cleanly as multi-doc YAML streams (7 docs: ServiceAccount/Role/RoleBinding/Deployment/Service/ServiceMonitor/PDB; 9 docs incl. a deliberate leading null comment-header doc). Full Kubernetes-schema validation (kubeconform/kubeval) and an image-tag cross-check against the SKILL.md `:v0.3.2` bump were NOT completed: no kubeconform/kubeval/yamllint is installed in this environment (python3 only), and the final asset Read calls returned empty due to a transient harness output fault.
- **Why not in one iteration:** Schema validation needs a linter not present in the environment; the image-tag cross-check inside the assets could not be Read reliably at edit time, and a blind `old_string` edit would violate the truthfulness rule. Re-run once kubeconform is available (or once tool I/O is stable) to confirm/align the in-asset gateway image tag with `:v0.3.2`.

## Resolved — 2026-07-21 (freshen)

Upstream is quiet; the findings are about **how to read upstream**, not about
version numbers.

- **`CLOSED` + `stateReason: COMPLETED` does not mean fixed in this repo.** Both
  tracked issues — #20184 (service discovery watches one port per pod) and
  #17623 (cache_aware ≈ round-robin with abundant KV) — are now closed, and the
  GitHub API reports **COMPLETED** for both. Reading only those fields, the
  correct-looking move is to delete the one-port limitation from `SKILL.md` §5
  and `kubernetes.md`. That would be wrong: the closing comment on each is
  *"This issue has been automatically closed due to inactivity."* No fix landed.
  The limitation is re-affirmed inline, and `sources.md` now carries the
  `gh issue view … --jq` incantation that surfaces the closing comment.
- **The gateway is four releases behind its own tokenizer crate.**
  `llm-tokenizer` is at **1.5.0** on crates.io (2026-07-18, via 1.4.0/1.4.1/1.4.2)
  while `sgl-model-gateway/Cargo.toml` still pins `="1.3.2"` — re-read on `main`
  this pass, unchanged. This matters because `tokenizers.md`'s "not yet
  supported" list (SentencePiece, GGUF) is scoped to 1.3.2; those formats may
  have landed in 1.4/1.5, but the *gateway* still cannot use them. Both files
  now say which version the claims describe.
- **No new gateway release in 6+ months.** `gateway-v0.3.1` (2026-01-09) is still
  the newest `gateway-*` tag and the crate is still v0.3.2 — the image/tag skew
  the previous pass warned not to churn is still exactly as described. `crdts =
  "7.3"` unchanged.
- **A stale-state carry, noted for honesty:** #17623 closed 2026-04-14 but was
  stamped "Last verified 2026-05-09" as a live citation. It is cited as an
  *operator measurement* rather than as an open bug, so the citation survives
  intact — but the date was stamped without re-reading the issue state.

## Resolved — 2026-05-28

- Freshen: container image tag `:v0.3.x` / `:v0.3.1` → `:v0.3.2` in SKILL.md (rename table L38, K8s Gateway Deployment L160, `--help` verify line L215) — matches Docker Hub `lmsysorg/sgl-model-gateway:v0.3.2` (last_updated 2026-05-27) and live Cargo.toml `version = "0.3.2"`. Lifted Dim 8 8→9. 2026-05-28
- Dim 9 policy-count over-claim: description said "eight load-balancing policies" implying eight equal `--policy` peers; corrected to "the load-balancing policy set (six `--policy`-selectable, `cache_aware` default)" and reworded the architecture paragraph to mark `consistent_hashing` + `bucket` as policy-factory-only (not in the `--policy` value_parser, `src/policies/factory.rs:77-91`), removing the unflagged over-claim. Lifted Dim 9 8→9. 2026-05-28
- Freshen: re-stamped 8 `sources.md` rows re-verified online this session (sglang home, gateway dir, upstream docs, PRs #14283/#14312/#13120, crates.io llm-tokenizer 1.3.2, Cargo.toml, Docker image, metric-history) to `Last verified: 2026-05-28`; bumped container-image row Pinned to `image v0.3.2 / release tag gateway-v0.3.1` and recorded the legitimate image-vs-release-tag version split so future freshens don't churn. 2026-05-28
- Resource check: both `assets/*.yaml` confirmed to parse as valid multi-doc Kubernetes manifests (addresses RECON's "not validated this pass" note; full kubeconform schema check still Open above). 2026-05-28

### Resolved in run 1 (2026-05-09)

- Dim 9 hard-fail (description = 1339 chars > 1024 spec cap) — split into description (797) + when_to_use (684), iter 1
- Dim 3 second-person voice (21 occurrences) — converted to imperative in iters 2 and 7; SKILL.md body now has zero second-person matches
- Dim 6 redundancy: Path B re-stated cache_aware-text-not-tokens — shrunk to one-line cross-reference, iter 3
- Dim 6 redundancy: Air-gapped tail "Cache_aware works on raw text" — trimmed, iter 5
- Dim 6 redundancy: pitfalls #1 + #12 canonical-restatement parentheticals — trimmed, iter 6
- Dim 9 staleness cap (no `sources.md`) — created `references/sources.md` with 26 dated rows, all `Last verified: 2026-05-09`, iter 4
- Dim 8 contradiction at SKILL.md:173 ("no `hf-hub` Rust crate" while air-gapped.md said it uses `hf-hub`) — corrected SKILL.md to name both `reqwest` and `hf-hub` paths, iter 10. **Note: cross-file propagation is still Open** (see above).
- Dim 6 redundancy: pitfall #6 restating §"Hosting multiple replicas" — collapsed to pointer, iter 9

## Run summary

| Run | Date | Baseline (cold) | Final (cold) | Final (blind) | Iterations | Kept | Discarded |
|---|---|---|---|---|---|---|---|
| 1 | 2026-05-09 | 74 | 85 | 86 | 10 | 8 | 1 partial + 1 discard |
| 2 | 2026-05-28 | 84 | 86 | — | 2 | 2 | 0 |

Run 1 net lift: +11 to +12 across 10 iterations. Dominant drivers: Dim 9 (3→9 via frontmatter split + sources.md), Dim 3 (5→9 via second-person sweep), Dim 6 (6→8 via redundancy trims).

Run 2 net lift: +2 (84→86). Drivers: Dim 8 8→9 (image-tag freshen to v0.3.2) and Dim 9 8→9 (policy-count over-claim corrected to the 6-CLI/2-factory split, sources.md re-stamped). Ceiling now at the six Open items above (Dim 6 dedup + Dim 7 schema-lint are the highest-leverage remaining, both blocked on environment tooling / restructure judgement).
