# Improvement backlog — sgl-model-gateway

Carries open issues across `skill-improver` runs that the loop attempted but couldn't apply in a single iteration. NOT a wishlist — entries here were proposed as hypotheses, attempted or planned, and could not land atomically.

## Open

*(empty — the six items carried since 2026-05-28 were completed or withdrawn on
2026-08-19; see below. An entry belongs here only when something specific and
external prevents doing it now, named in the entry.)*

## Resolved — 2026-08-19 (backlog drain)

All six carried items closed. Five were done; one was withdrawn as a
non-finding. None had an external blocker — they had been carried since
2026-05-28 on "needs author judgement", which is a decision, not an obstacle.

- **reqwest/hf-hub precision propagated.** `air-gapped.md` and `pitfalls.md` said
  only "the Rust gateway uses the `hf-hub` crate", collapsing two distinct network
  paths into one. Both now match SKILL.md:184 — service discovery on raw
  `reqwest`, tokenizer fetches via `llm-tokenizer`'s `hf-hub`
  (`crates/tokenizer/src/hub.rs`), neither `HF_ENDPOINT`-aware.
- **Validation steps added to the two body examples.** The Path B launch snippet
  now has a three-command check (`/v1/models`, `/workers`, `smg_`-prefixed
  `/metrics`) with the empty-`/workers`-but-healthy-`/v1/models` failure called
  out; the K8s pattern gets `rollout status` + a worker-count assertion, noting
  that a mis-scoped `--selector` or missing RBAC verb still yields a healthy-looking
  gateway.
- **`history.md` is no longer stranded.** The architecture paragraph now states
  where "stateless" stops: `/v1/responses` and `/v1/conversations` keep state in
  `--history-backend`, default in-process `memory`, lost on restart and not shared
  across replicas (`history.md:71`) — which is the condition that sends an operator
  to that reference.
- **Assets validated as far as this environment allows, and one stale example
  fixed.** Both manifests parse as multi-doc streams (8 and 9 docs) with every doc
  carrying `apiVersion`, `kind` and `metadata.name`; `yamllint` is clean apart from
  cosmetic spacing. The image-tag cross-check found the placeholders' example
  comments still reading `# e.g. v0.3.1` against the skill's `:v0.3.2` — corrected
  in both files. `kubeconform`/`kubeval` remain uninstalled, but deep schema typing
  is a marginal add over the above and is not worth carrying as an open item;
  re-run it if one ever lands in the environment.
- **WITHDRAWN — policy/tokenizer decision-tree duplication.** The entry answered
  itself: the overlap is summary-vs-detail, not verbatim, and the SKILL.md summary
  earns its place as a one-glance operator reference. Nothing to fix.
- **WITHDRAWN — mesh paragraph density.** Same shape: the entry conceded the
  density may be a feature (one-glance HA reference). No evidence it misleads, so
  there is no defect to act on.

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
- **The "image/tag skew" was never a skew — it is a missing git tag, and the
  skill described it backwards.** The old note said the image "legitimately
  *trails* the release-tag scheme"; `v0.3.2` in fact **leads** `gateway-v0.3.1`.
  Commit history resolves it: `[smg] release 0.3.2 (#17168)` merged 2026-01-15,
  bumping `Cargo.toml` and shipping crate + image as 0.3.2 — but **no
  `gateway-v0.3.2` tag was ever cut**. So `gh release list` under-reports the
  real release state, and `Cargo.toml` + Docker Hub are the authority. Prompted
  by the operator noticing the image was on 0.3.2 and calling it strange; it was,
  and the previous explanation had rationalised it away.
- **Published images are ~5 weeks behind `main`, and that is operationally
  live.** Docker Hub carries only 4 tags, with `v0.3.2`/`latest` last built
  **2026-05-27**. Meanwhile `sgl-model-gateway/` has commits through
  **2026-07-03** — PD-router cancel-paired-decode, DP-aware PD dispatch (#26245),
  a PD cache-aware routing fix, and a cargo-workspace restructure (2026-06-12).
  None of it is in a published image. Recorded in `sources.md` so nobody assumes
  `:v0.3.2` contains recent PD fixes. `crdts = "7.3"` unchanged.
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
