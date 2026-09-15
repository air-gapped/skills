# Improvement Backlog — vllm-configuration

Work-not-done log from skill-improver passes. Open = attempted but not applicable in one atomic iteration.

## Resolved — 2026-09-15 (the auth-bypass CVE has a floor; the advisory just never recorded it)

- **CVE-2026-48746 is fixed in v0.22.0 (2026-05-29).** The entry was left reading
  "unresolved or unrecorded" because the advisory's range is `>=0.3.0` with no
  upper bound and `first_patched_version` null — read literally, every release
  ever made is vulnerable and nothing can satisfy the floor.
- **It is unrecorded, not unresolved.** `updated_at` still equals `published_at`
  (2026-06-02), and the fix — PR #43426 — merged 2026-05-22, a week before
  v0.22.0 shipped and eleven days before the advisory was published.
- **Confirmed in the tree, not from the PR title.** Through v0.21 the middleware
  took its path from `URL(scope=scope).path`, which starlette rebuilds from the
  `Host:` header; from v0.22.0 it reads `scope["path"]`, the raw ASGI path that
  no header can influence. That is the bypass and its removal.
- **The mechanism is worth stating because it decides the mitigation.** A `Host:`
  header containing `/` or `?` steers the reconstructed path, so the middleware
  authorises against a different path than FastAPI routes on. The advisory notes
  instances behind an RFC-conforming server such as nginx were never exposed —
  a proxy that forwards `Host:` verbatim without validating it is not that.
- **Technique recorded in the skill, since the record shape recurs:** an
  unbounded range plus a null patched version is not a floor. Resolve it from
  the References' fix PR — merge commit, then ask the repo which tag first
  carried it — rather than reporting "no safe version". A *bounded* range is the
  opposite case and its upper bound is the floor, which is what the upgrade
  skills rely on.
- The operational advice is unchanged: run v0.22.0+ **and** front vLLM with an
  authenticating proxy. The v0.28.0 warning that `--api-key` does not gate all
  endpoints (#51999) is independent of this CVE and still stands.

## Resolved — 2026-09-15 (vLLM advisory sweep, 2026-06-01 onward)

35 advisories in that window: 1 critical, 5 high, 27 medium, 2 low. Two change
what this skill tells an operator to rely on.

- **`VLLM_API_KEY` / `--api-key` is not an authentication boundary, and the
  skill listed it without qualification.** CVE-2026-48746 /
  GHSA-94f4-hr76-p5j6, **CRITICAL**, published 2026-06-02 and **not withdrawn**:
  an ASGI/starlette request-scope trust issue lets a caller bypass the OpenAI
  API `AuthenticationMiddleware` and use the API without the configured key.
  The recorded affected range is **`>=0.3.0` with no upper bound and no patched
  version**, so as published it covers every current release — read that as
  unresolved-or-unrecorded, not as a stale entry. Independently, v0.28.0 added
  documentation warning that `--api-key` does not gate all endpoints (#51999).
  Two separate sources, same conclusion: put a real authenticating proxy in
  front.
- **`trust_remote_code=False` is not a guarantee.** GHSA-3c86-2m5g-59q7
  (**HIGH**, 2026-08-28, `< 0.28.0`): the LlavaOnevision2 processor loader
  passed an **inert** `trust_remote_code` kwarg to
  `transformers.get_class_from_dynamic_module`, so a malicious model achieved
  RCE **with the flag set to False**. The skill's pitfall #4 correctly warned
  what the flag enables; it now also says that a loader forgetting to honour it
  silently removes the control, which makes model-directory provenance the real
  boundary.

- **The `first_patched_version` trap recurs here.** All 35 advisories in the
  window have it set to null, exactly as with Open WebUI and Rancher earlier in
  this pass. Any floor must be derived from `vulnerable_version_range`. This is
  now the third upstream where that holds, so treat a populated
  `first_patched_version` as the exception rather than the rule when writing
  tooling against this feed.

- Shape of the rest, for context rather than action: the medium cluster is
  overwhelmingly **request-controlled denial of service** — out-of-range
  `stop_token_ids`, unbounded `cache_salt`, negative token ids on
  `/v1/embeddings` and `/pooling` (that one HIGH, `< 0.28.0`), and media-decode
  bombs. They share a mechanism worth recognising: a request field reaching a
  GPU-side or decoder path without a bound check, killing the engine rather
  than the request.

## Open

- Trim generic implicit triggers (`audit model X`, `deploy-memo`) from `when_to_use` — Dim 1, SKILL.md frontmatter (L7). Not applied: removing these risks under-triggering on the implicit per-model deploy-recipe contexts they were added for. Validating the trade-off needs trigger-mode measurement (60/40 split, 3 runs/query, blinded test scores), which this APPLY stage does not run. Carry to a dedicated trigger-mode pass. (carried 2026-05-28)
- Re-stamp the docs.vllm.ai env_vars / serve_args rows and the discuss.vllm.ai / GH-discussion #1405 rows in sources.md — Dim 9. Not re-confirmed this pass: the canonical docs URL `docs.vllm.ai/en/.../configuration/env_vars.html` 302-redirects and WebFetch of the redirect target 404s from this sandbox; only the `/serving/env_vars.html` variant resolved. Could not truthfully re-stamp those four rows to 2026-05-28, so they retain their 2026-04-24 date. GitHub-hosted rows (#8947, releases/latest) WERE re-verified via `gh` and stamped 2026-05-28. (carried 2026-05-28)

## Resolved — 2026-09-15 (v0.28/v0.29 sweep)

- **Dependency floors moved and an air-gapped mirror seeded for v0.27.x does not
  satisfy them**: `transformers` to 5.15.0 (#51668), `huggingface-hub` to 1.27.0
  then 1.28.0 (#52797), FlashInfer 0.6.18, NIXL 1.3.2, and the runtime image to
  Ubuntu 24.04. Stage these before the image bump.
- **The build now fails closed when the selected precompiled CUDA variant is
  missing** (#52545, v0.29.0), where it could previously fall back silently.
  Better behaviour, but it converts a quiet degradation into a hard stop on the
  first air-gapped build that lacks a variant — worth knowing before it happens.
- Env-var catalog updated: two removed in v0.29.0, one added
  (`VLLM_ALLREDUCE_USE_FLASHINFER`), and `prefix_cache_retention_interval`
  deprecated in its env-var form in favour of the CLI argument.

## Resolved this pass (2026-05-28)

- Release-version freshen: corrected sources.md latest-release line and row from v0.19.1 (2026-04-18) to the real latest **v0.21.0 (2026-05-15)**, verified via `gh api repos/vllm-project/vllm/releases/latest` — Dim 9. (A mid-pass intermediate edit briefly set this to a wrong "v0.11.2 (2026-05-23)"; corrected to v0.21.0. v0.11.2 actually published 2025-11-20.)
- Version-gate freshen: env-vars.md L3 "this table reflects v0.18–v0.20" → "v0.18–v0.21"; removed the stale "~260 lines as of v0.19" envs.py size claim — Dim 9. Gated on a v0.19/v0.20/v0.21 release-notes scan confirming their breaking changes touch torch/C++/pooling, not the operator env vars this table lists.
- #8947 fix-point reconciliation across three files — Dim 8. SKILL.md (config-file gotcha L62) and troubleshooting.md (L51) said "v0.10–v0.11"; config-file.md said "fixed in v0.10.1". Confirmed v0.10.1 tag (published 2025-08-18) and aligned all three to "fixed in v0.10.1 / pre-v0.10.1 affected". sources.md #8947 row re-stamped 2026-05-28 with the v0.10.1 fix detail.
- Removed the duplicate `VLLM_HOST_IP`-is-not-the-API-host pitfall (was Critical-pitfalls #2, a verbatim restatement of "Why this matters" point 3 and the Networking env-var entry) and renumbered the catalog 10→9 entries — Dim 6 simplification, no information lost.

## Resolved — 2026-08-11 (freshen, v0.25.1 → v0.27.0)

- **`config-file.md` documented eight YAML keys that no longer exist**, and a
  rejected key is not ignored — argparse refuses to start the server. Removed:
  `max-num-partial-prefills` + `max-long-partial-prefills` (PR #49244, v0.27.0),
  `preemption-mode` + `scheduler-delay-factor` (PR #25334, 2025-09-21),
  `swap-space` (PR #36216, 2026-03-07), `num-scheduler-steps`,
  `worker-use-ray`, `lora-extra-vocab-size`, `disable-log-requests` (inverted to
  `enable-log-requests`), `disable-frontend-multiprocessing`. Replaced with a
  "Keys that no longer exist" table naming the successor knob for each.
- **The removed partial-prefill args were already inert.** PR #49244's body:
  they "were introduced for the V0 scheduler and explicitly rejected by the V1
  enablement oracle… dead config that can only ever raise
  `UnsupportedFeatureError`". Same shape as the `VLLM_RPC_TIMEOUT` finding one
  pass earlier — documented-but-dead, not merely removed. Ditto `swap-space`,
  which per PR #36216 only ever backed `best_of` and was never allocated in V1.
- **Four CacheConfig defaults had drifted**: `gpu_memory_utilization`
  0.90→**0.92**, `enable_prefix_caching` False→**True**,
  `prefix_caching_hash_algo` builtin→**sha256**, `block_size` 16→**None
  (auto-resolved)**. The last one also corrected in `troubleshooting.md`.
- **"Unset" scheduler defaults are device-gated, and the skill implied a
  constant.** `EngineArgs` fills `max-num-batched-tokens` / `max-num-seqs` from
  the usage context *and* device: **8192 / 1024** for `vllm serve` on a ≥70 GiB
  non-A100 GPU, **2048 / 256** below that. The `SchedulerConfig` class defaults
  (2048 / 128) are test conveniences no server ever runs with.
- **`/dev/shm` was attributed to the wrong subsystem.** The consumer at TP≥2 is
  vLLM's own `MessageQueue` shm ring buffer (≈240 MiB default), not NCCL; lazy
  tmpfs allocation means it fails later as an uncatchable `SIGBUS` surfacing as
  `EngineDeadError`, typically once multimodal payloads start broadcasting.
  v0.27.0 pre-flight-checks and raises a clear `RuntimeError` (PR #48879).
- **Env catalog:** `VLLM_TRITON_USE_TD` added (PR #42436, tri-state, XPU
  auto-select today; old `VLLM_TRITON_ATTN_USE_TD` is warn-and-ignore), plus the
  three Rust-frontend vars (`VLLM_USE_RUST_FRONTEND`, `VLLM_USE_RUST_BENCH`,
  `VLLM_RUST_FRONTEND_PATH`) routed in from the `vllm-benchmarking` pass and
  re-verified here by direct read. Both AOT vars re-documented as **opt-out**,
  not opt-in — their defaults are computed, and the v0.27.0 torch pin of
  **2.13.0** (PR #48155) satisfies both gates. Version gate extended
  v0.18–v0.25 → **v0.18–v0.27**.

**Method note for the next pass:** the 2026-07-21 pass re-checked every env var
by name and caught a dead knob; it checked no *config key* by name and missed
seven removals, one of them eleven months old. Probe both catalogs at the target
tag. Release notes will not surface a removal that happened three minors ago.

**Dependency pins come from `requirements/*.txt`, not the release note.** The
release note's Dependencies section mixes runtime and CI pins — the transformers
figure quoted there (5.14.1) is a CI pin, while the runtime floor is
`>= 5.5.3`. There is also no direct `triton` pin; 3.7.1 arrives via torch.

## Resolved — 2026-07-21 (freshen)

- **`VLLM_RPC_TIMEOUT` deleted from `env-vars.md` — it never worked.** vLLM PR
  #44128 (merged 2026-06-03) removed it, stating it *"has no consumers anywhere
  in the tree — it is a V0 leftover"*; in V1 the engine-core client awaits
  utility RPCs with no timeout argument at all. The skill had been advising
  operators to raise it "on slow networks / large TP groups" — advice that did
  nothing, silently, and would have masked the real cause of a hang. Replaced
  with the four timeout vars that are actually live, defaults re-read from
  `envs.py`: `VLLM_ENGINE_READY_TIMEOUT_S` (600),
  `VLLM_ENGINE_ITERATION_TIMEOUT_S` (60),
  `VLLM_EXECUTE_MODEL_TIMEOUT_SECONDS` (300),
  `VLLM_WORKER_SHUTDOWN_TIMEOUT_SECONDS` (5).
- **Probe lesson recorded in `sources.md`:** presence in `envs.py` is not
  evidence that anything reads the variable, and the published docs page is
  *generated from* `envs.py` — so both advertised a dead knob for as long as it
  existed. Verifying an env var means searching for **consumers**, not for the
  definition.
- **A prior pass's conclusion is retired.** The 2026-05-28 entry above gated its
  version bump on "their breaking changes touch torch/C++/pooling, not the
  operator env vars this table lists". The v0.22–v0.25 window falsified that.
  Version gate extended v0.18–v0.21 → **v0.18–v0.25**, but by re-checking every
  var by name rather than by skimming release notes.
- **vLLM v0.21.0 → v0.25.1**; `envs.py` 87787 → 103853 bytes;
  `VLLM_MAIN_CUDA_VERSION` re-read and still `13.0`. All other listed vars
  present (the `HF_*` / `TRANSFORMERS_*` entries are `huggingface_hub` vars and
  are correctly absent from `envs.py`).
