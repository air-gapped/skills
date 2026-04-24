# Sources — external reference verification log

Tracks external URLs, GitHub issues/PRs, and docs pages cited by this skill. Each row carries a verification date and a brief status note. Refresh via the `freshen` mode of the `skill-improver` skill.

Last skill-wide verification pass: 2026-04-24. vLLM latest release at verification time: **v0.19.1** (2026-04-18).

| Ref | URL | Last verified | Status | Notes |
|---|---|---|---|---|
| Issue #23451 | https://github.com/vllm-project/vllm/issues/23451 | 2026-04-24 | fresh | CLOSED 2025-11-26. Title "[CI]: Use HF_HUB_OFFLINE=1 in CI tests" — vLLM CI itself adopted the flag because startup hits HF unless offline is set. Supports the guidance but is not a runtime bug report; citation adjusted in SKILL.md. |
| Issue #9255 | https://github.com/vllm-project/vllm/issues/9255 | 2026-04-24 | fresh | CLOSED 2024-11-05 (wontfix; workaround is serving via local path). Accepted resolution: `vllm serve /local/path ...` skips online lookups. Gated-model-with-HF_TOKEN guidance still correct. |
| PR #13220 | https://github.com/vllm-project/vllm/pull/13220 | 2026-04-24 | deprecation | CLOSED without merge 2025-06-20 (was marked [WIP]). ModelScope-LoRA fix **never landed**. Skill updated: state the gap as unresolved, point operators to the `--lora-modules name=/local/path` workaround instead of "fix tracked". |
| Issue #8947 | https://github.com/vllm-project/vllm/issues/8947 | 2026-04-24 | fresh | CLOSED 2024-10-05. YAML key-order parser bug; fixed on current main, still seen on old v0.10-v0.11 images. Skill guidance (move `served-model-name` earlier or upgrade) remains correct. |
| docs — env_vars | https://docs.vllm.ai/en/stable/configuration/env_vars/ | 2026-04-24 | version-drift | Page generated from `vllm/envs.py`. All env vars the skill lists are present. **Drift found:** `VLLM_MAIN_CUDA_VERSION` default bumped from `12.9` → `13.0` (now follows PyTorch). `env-vars.md` updated. |
| docs — serve_args | https://docs.vllm.ai/en/latest/configuration/serve_args/ | 2026-04-24 | fresh | Confirms precedence "command line > config file values > defaults". No env-var substitution, no include directive. Matches `config-file.md` and SKILL.md. |
| Discuss.vllm.ai thread | https://discuss.vllm.ai/t/setting-up-vllm-in-an-airgapped-environment/916 | 2026-04-24 | unverified-recent | Not re-probed this pass (budget). Canonical community airgap thread; stable URL across prior skill-creation checks. |
| GH Discussion #1405 | https://github.com/vllm-project/vllm/discussions/1405 | 2026-04-24 | unverified-recent | Not re-probed this pass (budget). Historic offline discussion, low drift risk. |
| vllm/envs.py | https://github.com/vllm-project/vllm/blob/main/vllm/envs.py | 2026-04-24 | fresh | File exists, 87787 bytes on main at verification. Source of truth for env-var table. |
| vLLM latest release | https://github.com/vllm-project/vllm/releases/latest | 2026-04-24 | fresh | `v0.19.1` published 2026-04-18. Skill's "v0.18–v0.20" version-gate wording remains accurate. |

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
