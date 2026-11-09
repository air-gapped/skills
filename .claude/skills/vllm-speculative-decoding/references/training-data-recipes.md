# Training-data recipes for EAGLE-3 and DFlash drafters

Load when training (or auditing the published recipe of) a custom EAGLE-3 or
DFlash drafter for a target model. The same recipe families recur across both
methods.

## Rules that hold across every recipe

- **Reuse only the prompts; regenerate every assistant response through the
  target model.** Every recipe below does this. Training on the dataset's own
  responses teaches the drafter another model's tokens, and acceptance is poor.
- **Regenerate in the mode you will serve.** Model cards state it per
  checkpoint ("no reasoning", "with reasoning"); a drafter trained on thinking
  responses under-accepts on non-thinking traffic and vice versa.
- **There is no single standard recipe.** Pick by the table below, then measure
  acceptance on your own traffic.

## Recipe families

Each row is stated on the listed model cards. Many published drafters name no
training data at all.

| Prompt source | Samples | Stated by | Notes |
|---|---|---|---|
| **Magpie-Llama-3.1-Pro-300K-Filtered + UltraChat-200k** (`train_sft`) | ~500K | `RedHatAI/gemma-4-31B-it-speculator.eagle3`, `RedHatAI/gpt-oss-120b-speculator.eagle3`, `RedHatAI/DeepSeek-V4-Flash-speculator.dflash`, `nvidia/gpt-oss-120b-Eagle3-short-context` / `-long-context`, `nvidia/Llama-3.3-70B-Instruct-Eagle3`, `nvidia/Qwen3-235B-A22B-Eagle3` | Used by Speculators-library checkpoints. `RedHatAI/Qwen3-8B-speculator.dflash` adds `nvidia/Nemotron-Personas-USA` |
| **ShareGPT (`Aeala/ShareGPT_Vicuna_unfiltered`) + UltraChat-200k** | — | `RedHatAI/Llama-3.1-8B-Instruct-speculator.eagle3`, `RedHatAI/Llama-3.3-70B-Instruct-speculator.eagle3`, `RedHatAI/Qwen3-8B-speculator.eagle3`, `RedHatAI/Qwen3-32B-speculator.eagle3`, `z-lab/LLaMA3.1-8B-Instruct-DFlash-UltraChat` | The original EAGLE-3 pairing. Use it to compare a new drafter against an EAGLE-3 baseline on equal data |
| **Open-PerfectBlend** (`mlabonne/open-perfectblend`) | 1.1–1.4M, or ~300K per phase | `lmsys/SGLang-EAGLE3-Qwen3-30B-A3B-Instruct-2507-SpecForge-Nex` (1.4M, 2 epochs), `lightseekorg/kimi-k2.5-eagle3` (phase 1), `florianleibert/kimi-k26-dflash-mi300x` (~1.16M), `RedHatAI/gemma-4-31B-it-speculator.dflash` | The SpecForge default. Pre-mixed instruction blend |
| **ShareGPT 45% + UltraChat 35% + PerfectBlend 20%** | 54K | `thoughtworks/Gemma-4-31B-Eagle3`, `thoughtworks/GLM-4.7-Flash-Eagle3`, `thoughtworks/Qwen2.5-7B-Instruct-Eagle3` | 3 epochs. `thoughtworks/MiniMax-M2.5-Eagle3` pre-trains 9 epochs on it, then fine-tunes 6 epochs on 20K regenerated samples |
| **UltraChat-200k alone** | 464K–600K | `Tengyunw/qwen3_8b_eagle3`, `Tengyunw/qwen3_30b_moe_eagle3` (600K, 1B tokens), `WhiFlash/Qwen3-8B-EAGLE3` (~464K), `ruipeterpan/Qwen2.5-7B-Instruct_EAGLE3_UltraChat` | Cheapest baseline: one public dataset |
| **Nemotron-Post-Training-Dataset-v2** (prompts) | 112K–1.6M | `nvidia/Kimi-K2.5-Thinking-Eagle3` (112K multilingual), `nvidia/Kimi-K2.6-Eagle3`, `nvidia/gpt-oss-120b-Eagle3-throughput` (+ UltraChat, 1.6M), `nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB-DFlash`, `z-lab/gpt-oss-120b-DFlash` (+ `theblackcat102/evol-codealpaca-v1`, 800K) | Math, code, STEM and conversational prompts. The dataset is gated — request access before an air-gapped build |
| **EagleChat** (`zhaode/EagleChat`) | up to ~2M | `taobao-mnn/Qwen3-VL-8B-Instruct-Eagle3`, `taobao-mnn/Qwen3-4B-Instruct-2507-Eagle3` (3 epochs), `AQ-MedAI/Kimi-K25-eagle3` (2M with Open-PerfectBlend and multimodal data) | Bilingual Chinese + English: ShareGPT, UltraChat-200k and smoltalk-chinese merged. Also used for a vision-language target |
| **Infinity-Instruct-0625** with target-generated responses | — | `nebius/EAGLE3-Llama-3.3-70B-Instruct`, `nebius/EAGLE3-Qwen3-235B-A22B-Instruct-2507`, `nebius/EAGLE3-gpt-oss-20b` | The regenerated corpus is itself published (`nebius/<target>-Infinity-Instruct-0625`) — reusable when the target matches |

## Coding-heavy targets

| Mix | Samples | Stated by |
|---|---|---|
| Nemotron-Post-Training-Dataset-v2 code split + `theblackcat102/evol-codealpaca-v1` + ~2.8K coding-agent execution traces | 289K | `z-lab/Qwen3-Coder-30B-A3B-DFlash` |
| `OpenCoder-LLM/opc-sft-stage1` | 1.4M, 2 epochs | `lmsys/SGLang-EAGLE3-Qwen3-Coder-30B-A3B-Instruct-SpecForge` |
| SWE-bench-Pro + SWE-bench + OpenCodeInstruct + `lightseekorg/kimi-mtp-dataset`, target reasoning traces kept | ~457K, 1 epoch | `Inferact/MiniMax-M3-EAGLE3` |

## Two-phase and continual schedules

- **Two phases** — `lightseekorg/kimi-k2.5-eagle3`: phase 1 on regenerated
  Open-PerfectBlend, phase 2 on a mixed set (English, vision-language, Chinese,
  function-call, agent, creative writing); 20k steps (~300K samples) each.
  Data: `lightseekorg/kimi-mtp-dataset`. Card acceptance lengths: HumanEval 3.28,
  CEval 2.30 — expect the same spread between code and non-English traffic.
- **Continual training for a new target version** —
  `lightseekorg/kimi-k2.6-eagle3-mla` starts from the K2.5 drafter checkpoint
  rather than from scratch. Do the same when the target is a point release of
  one you already have a drafter for.

## Recipe by target family

| Target family | Start from | Precedent |
|---|---|---|
| Llama | ShareGPT + UltraChat, or Magpie + UltraChat | `RedHatAI` Llama EAGLE-3 cards; `nvidia/Llama-3.3-70B-Instruct-Eagle3` |
| Qwen3 / Qwen3-MoE | EAGLE-3: ShareGPT + UltraChat, or Open-PerfectBlend at 1.4M. DFlash: Magpie + UltraChat | `RedHatAI` Qwen3 cards, `lmsys` SpecForge card |
| Kimi K2.x | Open-PerfectBlend phase 1 + mixed phase 2, or Nemotron-v2 prompts | `lightseekorg`, `nvidia` Kimi cards |
| Gemma 4 | EAGLE-3: Magpie + UltraChat. DFlash: Open-PerfectBlend | `RedHatAI` Gemma 4 cards |
| gpt-oss | Magpie + UltraChat; Nemotron-v2 + evol-codealpaca for DFlash | `RedHatAI`, `nvidia`, `z-lab` cards |
| MiniMax / GLM | 54K ShareGPT / UltraChat / PerfectBlend mix; a coding mix for agentic serving | `thoughtworks`, `Inferact` cards |
| Coder models | §Coding-heavy targets | — |
| Chinese + English serving | EagleChat | `taobao-mnn` cards |

## Coding-agent overlay datasets

For workloads dominated by tool-using coding agents, supplement the backbone
with prompts from:

- `nlile/misc-merged-claude-code-traces-v1` — 32k deduplicated real code-agent
  API traces with system prompts, tool definitions, git diffs and
  `messages_json` arrays.
- `AmanPriyanshu/tool-reasoning-sft-CODING-nvidia-Nemotron-Agentic-v1` — 335k
  multi-turn agentic tool-use trajectories.
- `princeton-nlp/SWE-bench_Verified` — real GitHub bug-fix tasks. Small (~500)
  but the prompts are dense.
- `TeichAI/Hunter-Alpha-Coding-Agent-SFT` — generated against the
  `read_file/write_file/edit_file/list_directory/search_code` tool stub set.

These are **prompt sources** — discard responses, regenerate through the
target.

## Reasoning overlay datasets

For thinking-mode targets (extended reasoning, `<think>` blocks):

- `Crownelius/Opus-4.6-Reasoning-3300x` — ~2.2k cleaned rows (problem /
  thinking / solution columns).
- `lordx64/reasoning-distill-opus-4-7-max-sft` — 7.8k single-turn rows with
  `<think>` blocks in Qwen chat template. Strip to user/system before feeding.

Small additions, not backbones.

## What to avoid

- **Training without response regeneration** — see the first rule.
- **5k-sample runs as anything but a pipeline check.** The Speculators examples
  (`examples/train/eagle3_qwen3_8b_ultrachat_online_5k.sh`,
  `dflash_qwen3_8b_ultrachat_online_5k.sh`) say so themselves and report
  acceptance length 1.88 and 2.15 on MT-Bench. The checkpoints above use
  54K–1.6M samples, most of them 289K or more.
- **A drafter whose card names no training data** for a production decision —
  treat its acceptance as unknown until measured on your traffic.
