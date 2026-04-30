# Training-data recipes for EAGLE-3 and DFlash drafters

Load when training (or auditing the published recipe of) a custom EAGLE-3 or
DFlash drafter for a target model. Cross-cutting because the same five recipe
families recur across both methods.

## TL;DR — there is no single standard

Surveying the top ~50 EAGLE-3 and top ~25 DFlash checkpoints on HuggingFace by
download count (369 EAGLE-3 + 97 DFlash repos total, 2026-04-30) shows **five
distinct recipe families** in active use. Magpie + UltraChat is *one* of them
(the RedHat / NVIDIA convention for Western models), not the universal default.

**Universal rule across all recipes**: only the *prompts* are reused; the
assistant responses are regenerated through the target model. This is the
RedHat-coined "response regeneration" step. Skipping it is the single most
common reason a published recipe underperforms on real traffic.

## The five families

| Recipe | Sample size | Used by | Notes |
|---|---|---|---|
| **Magpie-Llama-3.1-Pro + UltraChat** | ~500k | All `RedHatAI/*` EAGLE-3 + DFlash, `nvidia/gpt-oss-120b-Eagle3-long-context` | The Speculators-library default. Heavy English chat skew. |
| **Open-PerfectBlend** (regenerated) | ~1.1–1.4M | All `lmsys/SGLang-EAGLE3-*-SpecForge`, `lightseekorg/kimi-k2.5-eagle3` (Phase 1), `florianleibert/kimi-k26-dflash-mi300x` | The SGLang/SpecForge default. Pre-mixed instruction blend. |
| **ShareGPT 45% + UltraChat 35% + PerfectBlend 20%** | 54k | All `thoughtworks/*` (Gemma-4, MiniMax-M2.5, GLM-4.7-Flash) | Small, focused mix. 3–9 epochs typical. |
| **UltraChat-200k alone** (regenerated) | 200k–600k | `Tengyunw/qwen3_8b_eagle3`, `Tengyunw/qwen3_30b_moe_eagle3`, `ruipeterpan/Qwen2.5-7B-Instruct_EAGLE3_UltraChat`, `z-lab/LLaMA3.1-8B-Instruct-DFlash-UltraChat` | Cheapest baseline. Often expanded to 600k by sampling multiple completions. |
| **NVIDIA Nemotron-Post-Training-Dataset-v2** | <1B tokens | `nvidia/Kimi-K2.5-Thinking-Eagle3`, `BobbieBieee/dflash-qwen3-8b-5layer-reasonmix` | NVIDIA convention. Heavy synthetic + reasoning. |
| **EagleChat** (Alibaba/Taobao) | ~2M | `taobao-mnn/Qwen3-VL-8B-Instruct-Eagle3`, `AQ-MedAI/Kimi-K25-eagle3` | Multilingual, includes VL. Weights toward Chinese. |

## Phase-2 mix recipes (when the target is multilingual / agentic)

The two best-documented Kimi-class drafters use a **two-phase** training
schedule. Phase 2 adds domain-specific data after the Phase 1 backbone:

- `lightseekorg/kimi-k2.5-eagle3`: Phase 1 = regenerated Open-PerfectBlend.
  Phase 2 = mixed (English + VL + Chinese + function-call + agent + creative
  writing). Training data published at `lightseekorg/kimi-mtp-dataset`. Per-domain
  acceptance lengths in the model card: HumanEval 3.28, CEval 2.30.
- `modularai/kimi-k2.5-eagle3`: takes the lightseek Phase-2 checkpoint and
  post-trains on open-source coding datasets specifically.

## Recipe-by-target-family guidance

When **training your own** drafter (not picking a published one), match the
recipe to the target's home ecosystem:

| Target family | Strongest precedent | Why |
|---|---|---|
| Llama / RedHat-published | Magpie + UltraChat | What every `RedHatAI/Llama-*-speculator.eagle3` ships with |
| Qwen3 / Qwen3-MoE | Open-PerfectBlend OR UltraChat-200k | Multiple shipping checkpoints both ways; PerfectBlend wins at 1.4M scale |
| Kimi K2 / K2.5 / K2.6 | Open-PerfectBlend Phase 1 + multilingual Phase 2 | Lightseek's K2.5 is the only public Kimi recipe with documented per-domain numbers |
| Gemma 4 (incl. MoE) | Magpie + UltraChat | RedHat ships both EAGLE-3 and DFlash with this recipe |
| gpt-oss | Magpie + UltraChat OR PerfectBlend | RedHat uses Magpie+UC; LMSYS SpecForge uses PerfectBlend |
| MiniMax M2 / GLM | 54k ShareGPT/UC/PB mix | Thoughtworks recipe; small but matches their target list |
| Qwen3-Coder / coding-heavy | Nemotron code-split + Evol-CodeAlpaca | Used by `z-lab/Qwen3-Coder-30B-A3B-DFlash` (289k samples) |
| Multilingual / VL | EagleChat | Alibaba/Taobao convention, includes Chinese + visual tokens |

## Coding-agent overlay datasets

For workloads dominated by tool-using coding agents (Claude Code shape, Cursor
shape, Codex CLI shape), supplement the backbone above with prompts from:

- `nlile/misc-merged-claude-code-traces-v1` — 32k deduplicated real Claude API
  code-agent traces. Has system prompts + tool definitions + git diffs +
  `messages_json` arrays. Models: claude-sonnet-4.5, claude-haiku-4.5.
- `AmanPriyanshu/tool-reasoning-sft-CODING-nvidia-Nemotron-Agentic-v1` — 335k
  multi-turn agentic tool-use trajectories from NVIDIA Nemotron-Agentic-v1.
- `princeton-nlp/SWE-bench_Verified` — real GitHub bug-fix tasks. Small (~500)
  but the prompts are dense.
- `TeichAI/Hunter-Alpha-Coding-Agent-SFT` — generated against the
  `read_file/write_file/edit_file/list_directory/search_code` tool stub set.

These are **prompt sources** — discard responses, regenerate through the
target. Same rule as the backbone.

## Reasoning overlay datasets

For thinking-mode targets (extended reasoning, `<think>` blocks):

- `crownelius/Opus-4.6-Reasoning-3000x` (`nohurry/...-filtered` is deprecated)
- `lordx64/reasoning-distill-opus-4-7-max-sft` — 7.8k single-turn with
  `<think>` blocks in Qwen chat template. Strip to user/system before feeding.

Small additions, not backbones.

## What to avoid

- **Training without response regeneration.** Magpie's responses are from
  Llama-3.1; using them directly to train a Kimi drafter teaches the drafter
  to predict Llama tokens. Acceptance will be poor.
- **Single 5k-sample runs as anything but sanity checks.** The Speculators repo
  examples (`eagle3_qwen3_8b_sharegpt_online_5k.sh`,
  `dflash_qwen3_8b_sharegpt_online_5k.sh`) explicitly call out that 5k is "to
  verify the pipeline works" — they hit ~14% acceptance / ~1.45 AL, which
  *slows decoding down*. Production checkpoints use 200k–1.4M samples.
- **Reasoning-mode responses for instant-mode serving (and vice versa).** RedHat
  and Qwen explicitly note responses regenerated *with thinking disabled* in
  their model cards. Mode mismatch reduces acceptance.

## Provenance

Surveyed via `hf models list --search "eagle3" --limit 500` and
`hf models list --search "dflash" --limit 500` on 2026-04-30, sorted by
download count. Recipe attributions extracted by `curl`-ing each model card's
`README.md` and grepping for dataset names. Counts: 369 EAGLE-3, 97 DFlash
repositories. Top ~50 EAGLE-3 + top ~25 DFlash inspected for recipe content.
Lower-tail repositories (< ~150 downloads) typically don't document training
data; the patterns above represent the documented majority.
