# External-reference provenance

Cited upstream sources for this skill, probed on the `Last verified` date. Used
by skill-improver Dim 9 (staleness) and by anyone auditing whether a claim is
still current.

Method: `gh pr view` / `gh api repos/.../contents/...?ref=<tag>` / `gh api
repos/.../releases` / HF `/api/models/<id>`. URLs are the canonical upstream;
for pinned line numbers in vLLM source, the skill cites the current file path
(line numbers drift across refactors — re-verify on upgrade).

**Version discipline for this pass:** claims are probed against **v0.27.0**
(2026-08-10) except the DSpark Markov head, probed against **v0.27.1**
(2026-08-11, current stable). v0.27.1 is a single-change patch, so v0.27.0
probes remain valid for everything else and were deliberately **not**
re-stamped. The v0.27.1 **container images** shipped 10:24-10:42Z, before the release; PyPI lag is not a gate here. (`pip install
vllm==0.27.1` does not resolve.

**Headline of the 2026-08-11 pass (v0.25.1 → v0.27.1):** the 2026-07-21 pass
documented **TLI as a capability but never as a configuration**. It told the
reader the same-tokenizer rule was relaxed, and stopped there. TLI is opt-in
(`use_heterogeneous_vocab: true`) and carries two hard `ValueError` constraints
that existed *at v0.25.1 already* — `method` must be `draft_model`, and
`draft_sample_method` must be `greedy`. Anyone acting on the old text would have
hit the exact vocab-size rejection the feature exists to avoid.
**Lesson: when a release note announces a capability, read the config
dataclass, not just the PR title. A feature you cannot spell is not documented.**

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM releases | https://github.com/vllm-project/vllm/releases | 2026-08-11 | **v0.27.1 (2026-08-11T10:47:49Z)** current stable; v0.27.0 2026-08-10; v0.26.0 2026-07-27. Version-gate table extended past v0.25.0. |
| PR #50424 — quantized DSpark Markov heads | https://github.com/vllm-project/vllm/pull/50424 | 2026-08-11 (**ref=v0.27.1**) | MERGED 2026-08-03, **the sole change in v0.27.1**. Verified in `vllm/model_executor/models/qwen3_dspark.py` @ v0.27.1: `class DSparkMarkovHead` (L36) takes `quant_config` (L55) and forwards it to its `ParallelLMHead`-based `markov_w2` (L59-64); `Qwen3DSparkModel` passes `self.quant_config` (L103). W4A16 `markov_w2` weights incl. `weight_scale_2` now load through normal quantization dispatch; unquantized behaviour preserved. **The skill made no claim that the head must be unquantized, so nothing was retracted** — this is a pure addition. Implication recorded in pitfall 8: on ≤ v0.27.0 the head loads unquantized regardless of the checkpoint. |
| vllm/config/speculative.py — `SpeculativeMethod` enum | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/config/speculative.py | 2026-08-11 | **Base-method count unchanged at 13** — frontmatter still correct. Structure unchanged: `EagleModelTypes = ["eagle", "eagle3", "extract_hidden_states", MTPModelTypes, DFlashModelTypes]`, plus `NgramGPUTypes` and `DSparkModelTypes`. **`MTPModelTypes` grew 20 → 22**: new `kimi_k3_mtp`, `inkling_mtp`. `RejectionSampleMethod` unchanged (`standard`/`synthetic`/`block`). File is 1435 lines (was 1276 at v0.25.1). |
| vllm/config/speculative.py — TLI config surface | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/config/speculative.py | 2026-08-11 | **broken (skill under-specified).** `use_heterogeneous_vocab: bool = False` (line 151). Validation at lines 1324-1334 raises on two conditions: *"use_heterogeneous_vocab only works with method='draft_model'"* and *"use_heterogeneous_vocab currently only supports greedy draft sampling."* When the flag is `False`, `verify_equal_vocab_size_if_draft_model()` still runs. **Both constraints were present at v0.25.1** — this is a documentation miss, not new drift. Fixed in SKILL.md pitfall 7, the version-gate row, and `methods.md`. |
| PR #48787 — `kv_cache_dtype` in `speculative_config` | https://github.com/vllm-project/vllm/pull/48787 | 2026-08-11 | MERGED 2026-07-16, ships **v0.26.0**. New `SpeculativeConfig` field — the only field added between v0.25.1 and v0.27.0 (verified by diffing the dataclass field set). Docstring: *"KV cache dtype for the draft model. When `None`, the draft inherits the target model's `--kv-cache-dtype`."* |
| PR #48639 — `sample_from_anchor` from speculators config | https://github.com/vllm-project/vllm/pull/48639 | 2026-08-11 | MERGED 2026-07-20, ships **v0.27.0**. Lives in `vllm/transformers_utils/configs/speculators/algos.py` — it is a **checkpoint** field, not a CLI flag, for both DFlash and DSpark. Docstring: *"Default False (anchor is a bonus token, only mask tokens predict, yielding block_size - 1 speculative tokens)."* Captured in `references/dflash.md`. |
| PR #48892 — multi-layer MTP speculator on MRV2 | https://github.com/vllm-project/vllm/pull/48892 | 2026-08-11 | MERGED 2026-07-30, **v0.27.0**. Added as a version-gate row. |
| aux_hidden_states model support | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/model_executor/models/interfaces.py | 2026-08-11 | **fresh — re-verified, no regression.** `class SupportsEagle3(SupportsEagleBase, Protocol)` at line 1449, `supports_eagle3()` at 1510, `set_aux_hidden_state_layers()` at 1463. `config/speculative.py` still contains **no** allowlist — only the method tuple that consumes aux states (line 307). The 2026-07-21 finding holds two minors later; version markers bumped v0.25.1 → v0.27.0. |
| PR #38174 — TLI universal spec-dec | https://github.com/vllm-project/vllm/pull/38174 | 2026-07-21 | MERGED 2026-07-02, ships v0.25.0. Not re-probed this pass (merged PR, state cannot regress); its *config surface* was probed instead — see the TLI row above. |
| PR #44744 — spec-dec DoS fix | https://github.com/vllm-project/vllm/pull/44744 | 2026-07-21 | Security / DoS in the v0.24.0 notes: remote DoS via invalid recovered-token reinjection. Gate ≥ v0.24.0 stands. Not re-probed (merged). |
| PR #25916 — EAGLE-3 preamble fix (+32% MTBench) | https://github.com/vllm-project/vllm/pull/25916 | 2026-04-24 | MERGED 2025-10-02. v0.11.1 gate still correct. Not re-probed. |
| PR #36847 — DFlash method | https://github.com/vllm-project/vllm/pull/36847 | 2026-04-24 | MERGED 2026-03-30. v0.19 gate still correct. Not re-probed. |
| PR #32887 — Unified Parallel Drafting (P-EAGLE enabler) | https://github.com/vllm-project/vllm/pull/32887 | 2026-04-24 | MERGED 2026-02-05. v0.16 gate still correct. Not re-probed. |
| PR #29184 — ngram_gpu + async scheduler | https://github.com/vllm-project/vllm/pull/29184 | 2026-04-24 | MERGED 2026-03-07. v0.18 gate still correct. Not re-probed. |
| ArcticInference repo (suffix + LSTM speculators) | https://github.com/snowflakedb/ArcticInference | 2026-04-24 | **Stale — not re-probed for three passes.** Last known: v0.1.2 (2026-01-24), repo active 2026-04-23. The `suffix` method depends on this package being installable; if it has gone dormant that is a real operator risk. **Highest-priority row for the next pass.** |
| yuhuili/EAGLE3-LLaMA3.1-Instruct-8B HF checkpoint | https://huggingface.co/yuhuili/EAGLE3-LLaMA3.1-Instruct-8B | 2026-04-24 | Present, 245k downloads, Apache-2.0, last modified 2025-09-19. Not re-probed. |
| EAGLE 3.1 announcement (vLLM blog) | https://vllm.ai/blog/2026-05-26-eagle-3-1 | 2026-05-29 | Config-driven extension of eagle3 (same `method` enum). Captured in `references/eagle3.md`. Not re-probed. |
| HF EAGLE-3 + DFlash recipe survey | `hf models list --search {eagle3,dflash} --limit 500` | 2026-04-30 | 369 EAGLE-3 + 97 DFlash repos, five recurring recipe families. Tabulated in `references/training-data-recipes.md`. Not re-probed. |
| `vllm/vllm-openai` image tags | https://hub.docker.com/v2/repositories/vllm/vllm-openai/tags/ | 2026-08-11 | **`v0.27.1` images exist and predate the GitHub release** — `v0.27.1` (10.53 GB) pushed 10:34:40Z, `-x86_64` 10:24:20Z, `-cu129` 10:41:15Z, `-cu129-ubuntu2404` 10:42:47Z; release published 10:47:49Z. This stack runs the image, so image availability — not the PyPI wheel — is the gate. (PyPI `info.version` was still 0.27.0 when checked.) |

## Classifications summary (2026-08-11 pass)

- **broken: 1** — the TLI documentation gap. Highest-value finding of the pass:
  the capability was named without its flag or its two hard constraints.
- **new-feature: 4** — `kv_cache_dtype` in `--speculative-config` (#48787,
  v0.26.0); `sample_from_anchor` loaded from the speculators config (#48639,
  v0.27.0); multi-layer MTP on MRV2 (#48892, v0.27.0); quantized DSpark Markov
  heads (#50424, v0.27.1).
- **version-drift: 1** — `MTPModelTypes` 20 → 22 (Kimi K3, Inkling now ship
  native MTP heads); method-selection table row 1 updated.
- **fresh: 1** — the `SupportsEagle3` capability interface, re-verified at
  v0.27.0 with no regression. Base method count still 13.
- **not re-probed: 7** — the four original PRs (merged; state cannot regress),
  ArcticInference, the yuhuili checkpoint, the EAGLE 3.1 blog, and the
  training-data recipe survey. Declared, not assumed fresh.

## Known gap for the next pass

**ArcticInference has not been probed since 2026-04-24** — three passes. The
`suffix` method in the method-selection matrix depends on `pip install
arctic-inference` working. Probe it first next time; a dormant dependency
silently invalidates a recommended method.

## Re-verification recipe

```bash
# Method enum + MTP alias list + config surface, all from one fetch
gh api "repos/vllm-project/vllm/contents/vllm/config/speculative.py?ref=vX.Y.Z" \
  --header "Accept: application/vnd.github.raw" > /tmp/spec.py
sed -n '/^MTPModelTypes = Literal\[/,/^\]/p;/^SpeculativeMethod = Literal\[/,/^\]/p' /tmp/spec.py
grep -n "use_heterogeneous_vocab\|draft_sample_method\|kv_cache_dtype\|rejection_sample_method" /tmp/spec.py

# Diff the whole SpeculativeConfig field set against the previous tag — this is
# what catches a new knob that no release note headlines
for t in vA.B.C vX.Y.Z; do
  gh api "repos/vllm-project/vllm/contents/vllm/config/speculative.py?ref=$t" \
    --header "Accept: application/vnd.github.raw" | grep -oP '^    \w+:' | sort -u > "/tmp/f_$t.txt"
done
diff /tmp/f_vA.B.C.txt /tmp/f_vX.Y.Z.txt

# EAGLE-3 support is an interface, not a list — confirm it still is
gh api "repos/vllm-project/vllm/contents/vllm/model_executor/models/interfaces.py?ref=vX.Y.Z" \
  --header "Accept: application/vnd.github.raw" | grep -n "class SupportsEagle3\|def supports_eagle3"

# DSpark / DFlash drafter internals (quant plumbing, sample_from_anchor)
gh api "repos/vllm-project/vllm/contents/vllm/model_executor/models/qwen3_dspark.py?ref=vX.Y.Z" \
  --header "Accept: application/vnd.github.raw" | grep -n "markov_w2\|quant_config"
gh api "repos/vllm-project/vllm/contents/vllm/transformers_utils/configs/speculators/algos.py?ref=vX.Y.Z" \
  --header "Accept: application/vnd.github.raw" | grep -n "sample_from_anchor" -B4 -A2

# Arctic Inference freshness (OVERDUE — run this first)
gh api repos/snowflakedb/ArcticInference/releases/latest --jq '{tag:.tag_name, published:.published_at}'

# Is the release actually installable yet?
curl -s https://pypi.org/pypi/vllm/json | python3 -c \
  'import json,sys;d=json.load(sys.stdin);print(d["info"]["version"])'

# HF checkpoint existence
curl -s "https://huggingface.co/api/models/yuhuili/EAGLE3-LLaMA3.1-Instruct-8B" | head -c 400
```
