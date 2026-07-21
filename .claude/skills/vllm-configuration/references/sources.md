# Sources — external reference verification log

Tracks external URLs, GitHub issues/PRs, and docs pages cited by this skill. Each row carries a verification date and a brief status note. Refresh via the `freshen` mode of the `skill-improver` skill.

Last skill-wide verification pass: 2026-07-21. vLLM latest release at verification time: **v0.25.1** (2026-07-14).

> **Probe lesson from this pass:** a variable's presence in `vllm/envs.py` does
> **not** prove anything reads it, and the published env-var docs page is
> *generated from* `envs.py` — so a dead knob is advertised by both. When a row
> here asserts an env var *does* something, the probe is a consumer search, not
> a definition lookup.

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
| vllm/envs.py | https://github.com/vllm-project/vllm/blob/main/vllm/envs.py | 2026-07-21 | fresh | 103853 bytes on main (was 87787). Every env var in `env-vars.md` re-checked against it by name this pass — one casualty, see PR #44128 below. |
| vLLM latest release | https://github.com/vllm-project/vllm/releases/latest | 2026-07-21 | version-drift | **`v0.25.1`** published 2026-07-14. Four minors since the last pass (v0.22.1, v0.23.0, v0.24.0, v0.25.0, v0.25.1). **This pass contradicts the previous one's conclusion:** it recorded that breaking changes "touch torch/C++/pooling, NOT the operator env vars this skill lists". That no longer holds — `VLLM_RPC_TIMEOUT` was deleted in this window. Version-gate wording extended to v0.18–v0.25, but the general claim "vLLM minors don't touch operator env vars" is retired as unsafe. |
| PR #44128 (removes `VLLM_RPC_TIMEOUT`) | https://github.com/vllm-project/vllm/pull/44128 | 2026-07-21 | deprecation | **MERGED 2026-06-03.** "[Misc] Remove dead VLLM_RPC_TIMEOUT env var". PR body: the variable *"has no consumers anywhere in the tree — it is a V0 leftover"*; in V1 `SyncMPClient.call_utility` / `AsyncMPClient._call_utility_async` await without any timeout, so there was nothing for it to control. It had been **documented-but-dead**, not merely removed. `env-vars.md` now deletes the row and names the four live timeout vars instead. |

## Probe budget

Pass 2026-04-24 used 7 of 8 allowed probes (4 GH issue/PR lookups + 2 docs.vllm.ai WebFetches + 1 release/contents API). Two refs (discuss.vllm.ai thread, GH discussion #1405) carried over as `unverified-recent` — stable, low-risk URLs not re-probed this cycle.

## Classification legend

- **fresh** — URL live, content matches what the skill says.
- **version-drift** — minor detail changed upstream (default value, version number); skill updated in place.
- **deprecation** — cited PR/issue failed to produce the fix it was cited for; guidance rewritten.
- **new-feature** — upstream added something relevant; skill may want a follow-up pass.
- **broken** — URL 404 or content removed; skill must find a replacement.
- **unverifiable** — couldn't be probed this pass.
- **unverified-recent** — carried over from a previous pass that verified it.
