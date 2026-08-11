# Sources — external reference verification log

Tracks external URLs, GitHub issues/PRs, and docs pages cited by this skill. Each row carries a verification date and a brief status note. Refresh via the `freshen` mode of the `skill-improver` skill.

Last skill-wide verification pass: 2026-08-11. **Everything below was probed at tag `v0.27.0`** (published 2026-08-10). Latest stable is **v0.27.1** (published 2026-08-11, mid-pass) — a single-change patch ("Support quantized DSpark Markov heads", #50424) that touches no config surface, so the v0.27.0 probes stand and are stamped v0.27.0 deliberately rather than restamped to a tag nobody read. The `v0.27.1` container images were pushed 10:24-10:42Z, *before* the 10:47Z release — image availability, not the PyPI wheel, is what gates this stack.

> **Probe lesson from this pass:** a variable's presence in `vllm/envs.py` does
> **not** prove anything reads it, and the published env-var docs page is
> *generated from* `envs.py` — so a dead knob is advertised by both. When a row
> here asserts an env var *does* something, the probe is a consumer search, not
> a definition lookup.

> **Probe lesson, 2026-08-11:** the same trap applies to *config keys*, and the
> 2026-07-21 pass fell into it. That pass re-checked every env var by name but
> checked no YAML key by name, so `config-file.md` kept advertising
> `preemption-mode`, `scheduler-delay-factor`, `swap-space`, `worker-use-ray`,
> `lora-extra-vocab-size`, `disable-log-requests` and
> `disable-frontend-multiprocessing` — all of which had been gone for one to
> eleven months. Release-note skimming will not surface these; only reading the
> `vllm/config/*.py` dataclasses at the target tag will. Probe the catalog you
> publish, not the catalog you remember.

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| Issue #23451 | https://github.com/vllm-project/vllm/issues/23451 | 2026-04-24 | fresh | CLOSED 2025-11-26. Title "[CI]: Use HF_HUB_OFFLINE=1 in CI tests" — vLLM CI itself adopted the flag because startup hits HF unless offline is set. Supports the guidance but is not a runtime bug report; citation adjusted in SKILL.md. |
| Issue #9255 | https://github.com/vllm-project/vllm/issues/9255 | 2026-04-24 | fresh | CLOSED 2024-11-05 (wontfix; workaround is serving via local path). Accepted resolution: `vllm serve /local/path ...` skips online lookups. Gated-model-with-HF_TOKEN guidance still correct. |
| PR #13220 | https://github.com/vllm-project/vllm/pull/13220 | 2026-04-24 | deprecation | CLOSED without merge 2025-06-20 (was marked [WIP]). ModelScope-LoRA fix **never landed**. Skill updated: state the gap as unresolved, point operators to the `--lora-modules name=/local/path` workaround instead of "fix tracked". |
| Issue #8947 | https://github.com/vllm-project/vllm/issues/8947 | 2026-05-28 | fresh | CLOSED 2024-10-05; fix landed in v0.10.1 (tag published 2025-08-18). YAML key-order parser bug. Skill guidance (move `served-model-name` earlier or upgrade past v0.10.1) remains correct. |
| docs — env_vars | https://docs.vllm.ai/en/stable/configuration/env_vars/ | 2026-07-21 | version-drift | Page generated from `vllm/envs.py`. `VLLM_MAIN_CUDA_VERSION` re-read: still `13.0`. **`VLLM_RPC_TIMEOUT` no longer exists** — every other var the skill lists is still present (the `HF_*` / `TRANSFORMERS_*` entries are `huggingface_hub` vars and correctly absent from `envs.py`). |
| docs — serve_args | https://docs.vllm.ai/en/latest/configuration/serve_args/ | 2026-04-24 | fresh | Confirms precedence "command line > config file values > defaults". No env-var substitution, no include directive. Matches `config-file.md` and SKILL.md. |
| Discuss.vllm.ai thread | https://discuss.vllm.ai/t/setting-up-vllm-in-an-airgapped-environment/916 | 2026-04-24 | unverified-recent | Not re-probed this pass (budget). Canonical community airgap thread; stable URL across prior skill-creation checks. |
| GH Discussion #1405 | https://github.com/vllm-project/vllm/discussions/1405 | 2026-04-24 | unverified-recent | Not re-probed this pass (budget). Historic offline discussion, low drift risk. |
| vllm/envs.py | `gh api .../contents/vllm/envs.py?ref=v0.27.0` | 2026-08-11 | fresh | 105852 bytes at `v0.27.0` (was 103853). `VLLM_MAIN_CUDA_VERSION` re-read: still `13.0`. `VLLM_USE_AOT_COMPILE` / `VLLM_USE_MEGA_AOT_ARTIFACT` re-read as *computed* defaults that both resolve **on** under the v0.27.0 torch pin. New rows added: `VLLM_TRITON_USE_TD`, `VLLM_USE_RUST_FRONTEND`, `VLLM_USE_RUST_BENCH`, `VLLM_RUST_FRONTEND_PATH`. `VLLM_RPC_TIMEOUT` re-confirmed absent. |
| vllm/config/{scheduler,cache,lora}.py, vllm/engine/arg_utils.py, vllm/entrypoints/openai/cli_args.py | `gh api .../contents/<path>?ref=v0.27.0` | 2026-08-11 | deprecation | The catalog probe `config-file.md` had never had. **Eight documented YAML keys are absent at v0.27.0** — see the "Keys that no longer exist" table in `config-file.md`. Also caught default drift: `gpu_memory_utilization` 0.90→**0.92**, `enable_prefix_caching` False→**True**, `prefix_caching_hash_algo` builtin→**sha256**, `block_size` 16→**None (auto)**. And the "unset" batching defaults are device-gated (`arg_utils.py` L2544-2563): ≥70 GiB non-A100 → 8192/1024 for `vllm serve`, else 2048/256. |
| PR #49244 (removes partial-prefill args) | https://github.com/vllm-project/vllm/pull/49244 | 2026-08-11 | deprecation | **MERGED 2026-07-21**, ships in v0.27.0. Body: the fields "were introduced for the V0 scheduler and explicitly rejected by the V1 enablement oracle in #13726. With V0 removed, the fields are now dead config that can only ever raise `UnsupportedFeatureError` — they have no consumer." Already inert before removal, not merely dropped. |
| PR #25334 / #36216 / #48549 (preemption-mode, delay-factor, swap-space) | https://github.com/vllm-project/vllm/pull/36216 | 2026-08-11 | deprecation | All MERGED — #25334 2025-09-21 (preemption mode + delay factor), #36216 2026-03-07 (swap_space; body: only ever backed `best_of`, and V1 hardcodes `num_cpu_blocks = 0`), #48549 2026-07-14 (warning cleanup). Long-standing staleness two prior passes missed. |
| PR #48155 (torch 2.13.0) | https://github.com/vllm-project/vllm/pull/48155 | 2026-08-11 | version-drift | **MERGED 2026-07-23.** Confirmed against `requirements/cuda.txt@v0.27.0`: `torch==2.13.0`, `torchvision==0.28.0`, `torchaudio==2.11.0`, `flashinfer-python==0.6.16.post3`. **No direct `triton` pin exists** — 3.7.1 arrives transitively via torch, so do not cite it as a requirements-file fact. Runtime transformers floor is `>= 5.5.3` (`requirements/common.txt`); the 5.14.1 figure in the release note is a CI pin. Makes both AOT-compile gates default-satisfied. |
| PR #48879 (`/dev/shm` fail fast) | https://github.com/vllm-project/vllm/pull/48879 | 2026-08-11 | new-feature | **MERGED 2026-07-27.** Corrects this skill's attribution: the `/dev/shm` consumer at TP≥2 is vLLM's own `MessageQueue` shm ring buffer (≈240 MiB default), not NCCL. Lazy tmpfs → uncatchable `SIGBUS` → opaque `EngineDeadError`. v0.27.0 pre-flight-checks and raises a clear `RuntimeError`. |
| PR #42436 (`VLLM_TRITON_USE_TD`) | https://github.com/vllm-project/vllm/pull/42436 | 2026-08-11 | new-feature | **MERGED 2026-07-29.** Tri-state; unset = backend auto-select (XPU only today). Old name `VLLM_TRITON_ATTN_USE_TD` is registered warn-and-ignore. |
| Rust frontend env vars | `vllm/envs.py@v0.27.0` L156-158, L556-587 | 2026-08-11 | new-feature | `VLLM_USE_RUST_FRONTEND` (`0`), `VLLM_USE_RUST_BENCH` (`0`), `VLLM_RUST_FRONTEND_PATH` (`auto`). Routed in from the `vllm-benchmarking` freshen pass and re-verified here by direct read, not accepted on report. Both failure directions read out of `_resolve_rust_cli_path`: path-without-flag warns and is ignored; flag-with-missing-binary raises `FileNotFoundError` at startup. |
| vLLM latest release | https://github.com/vllm-project/vllm/releases | 2026-08-11 | version-drift | **v0.27.0** published 2026-08-10; **v0.27.1** published 2026-08-11 (one change, #50424, quantized DSpark Markov heads — no config surface). v0.26.0 was 2026-07-27. Version gate extended v0.18–v0.25 → **v0.18–v0.27**. The 2026-07-21 pass's method (re-check every env var by name) held up — no env-var casualties this window — but it did not generalise to config keys, which is where this window's damage was. |
| PR #44128 (removes `VLLM_RPC_TIMEOUT`) | https://github.com/vllm-project/vllm/pull/44128 | 2026-07-21 | deprecation | **MERGED 2026-06-03.** "[Misc] Remove dead VLLM_RPC_TIMEOUT env var". PR body: the variable *"has no consumers anywhere in the tree — it is a V0 leftover"*; in V1 `SyncMPClient.call_utility` / `AsyncMPClient._call_utility_async` await without any timeout, so there was nothing for it to control. It had been **documented-but-dead**, not merely removed. `env-vars.md` now deletes the row and names the four live timeout vars instead. |

## Probe budget

Pass 2026-04-24 used 7 of 8 allowed probes (4 GH issue/PR lookups + 2 docs.vllm.ai WebFetches + 1 release/contents API). Two refs (discuss.vllm.ai thread, GH discussion #1405) carried over as `unverified-recent` — stable, low-risk URLs not re-probed this cycle.

Pass 2026-08-11 spent its budget on **source-tree reads at tag `v0.27.0`** rather
than docs pages — `gh api .../contents/<path>?ref=v0.27.0` on `vllm/envs.py`,
`vllm/config/{scheduler,cache,lora,compilation,parallel,vllm}.py`,
`vllm/engine/arg_utils.py`, `vllm/entrypoints/openai/cli_args.py`,
`vllm/utils/argparse_utils.py` and `requirements/{cuda,common}.txt`, plus seven PR
lookups. That is the cheapest possible answer to "does this key still exist", and
it is strictly stronger than the generated docs page. The four
`unverified-recent` rows (discuss.vllm.ai, GH discussion #1405, docs serve_args,
issue #23451) were again not re-probed — low drift risk, and the budget was
better spent on the catalog.

## Classification legend

- **fresh** — URL live, content matches what the skill says.
- **version-drift** — minor detail changed upstream (default value, version number); skill updated in place.
- **deprecation** — cited PR/issue failed to produce the fix it was cited for; guidance rewritten.
- **new-feature** — upstream added something relevant; skill may want a follow-up pass.
- **broken** — URL 404 or content removed; skill must find a replacement.
- **unverifiable** — couldn't be probed this pass.
- **unverified-recent** — carried over from a previous pass that verified it.
