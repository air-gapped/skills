---
name: vllm-gemma-4-31b
allowed-tools: Bash, Read, Write, Edit, Grep, Glob
description: |-
  Operating-point reference for serving Gemma 4 31B on vLLM — TP sizing, max_model_len, max_num_seqs, gpu_memory_utilization, kv_cache_dtype, EAGLE3 spec-dec, chat_template choice.
when_to_use: |-
  When the user mentions Gemma 4 31B in the context of vLLM deployment, tuning, or performance.
---

# Gemma 4 31B on vLLM — operating-point reference

**One model, measured.** This is a worked operating point, not the general
method. The reusable machinery lives in the `vllm` plugin: flag and env
semantics in **`vllm-configuration`**, the K8s/container manifest in
**`vllm-deployment`**, reproducing or re-measuring these numbers in
**`vllm-benchmarking`**, and the prompt-side template in
**`vllm-chat-templates`**. Deploying a *different* model? Use those, not this.


For platform engineers deploying `google/gemma-4-31B-it` (BF16, FP8) or its
community quants (e.g. `cyankiwi/gemma-4-31B-it-AWQ-4bit`,
`RedHatAI/*-Gemma-4-31B-*`) on vLLM 0.29.0+ (version floor below).
Pulls together measurements from a 2× H100 SXM5 80GB (NVLink) audit on
2026-04-30 — **taken on vLLM 0.20.0
and not re-run since** (see `references/bench-numbers.md`; the shape of the
curves has held, but treat the absolute figures as 0.20.0 observations) — and
the upstream constraints that shape the answer.

> **Version floor: run vLLM 0.29.0 or newer; 0.30.0+ is the production line.**
> Do not pin 0.25.1 or older: they carry the `<turn|>` / `enable_thinking`
> bug ([#49955](https://github.com/vllm-project/vllm/issues/49955)) that
> [#52430](https://github.com/vllm-project/vllm/pull/52430) fixed in v0.29.0,
> and miss the 0.27.0+ ViT CUDA graph (#46837) and the 0.30.0+
> multimodal-prefix Triton fix (#53147, fact #1).
>
> Known open issue on 0.26.0+, a headroom problem rather than a reason to
> downgrade: [#50159](https://github.com/vllm-project/vllm/issues/50159).
> Under saturating load, Model Runner V2 can run out of CUDA memory, and with
> EAGLE it fails sooner. The cause is CUDA-graph capture headroom: MRv2
> reserves ~0.12 GiB for capture where MRv1 reserves ~0.65 GiB. It is worst
> on large models on small cards. Pick one mitigation:
> - leave ≥0.5 GiB/GPU more margin than MRv1 needed (lower
>   `--gpu-memory-utilization` by ~0.01 on 80 GB cards);
> - `VLLM_USE_V2_MODEL_RUNNER=0` to force MRv1 (present through v0.32.0);
> - `--enforce-eager` (removes the gap, costs decode speed).
>
> [#50477](https://github.com/vllm-project/vllm/issues/50477) (named /
> `required` `tool_choice` unenforced, fix PR #51524 open) affects every
> version from v0.24.0 on (see the pitfall below).

## Three load-bearing facts

1. **Gemma 4 has heterogeneous head_dim (256 sliding / 512 global)**, so
   vLLM picks the attention backend itself (`Gemma4Config` in
   `vllm/model_executor/models/config.py`). Leave `--attention-backend`
   unset and read the startup log line `Gemma4 model has heterogeneous head
   dimensions …`:
   - `FA4 not available, forcing TRITON_ATTN backend` — every layer on
     Triton. This is the path the v0.20.0 audit and its numbers ran on.
   - `Using FA4 for all layers …` — FA4 available, not the SM90 + FP8-KV case.
   - **v0.31.0+, H100/H200 with `--kv-cache-dtype fp8`** (both recipes):
     `Using per-layer FA3/FA4 selection for FP8 KV cache on SM90` — causal
     text runs FA3 (256) / FA4 (512); multimodal-prefix requests run
     TRITON_ATTN (#53175). A different kernel path: re-bench, do not reuse
     these numbers. The Triton path gained the multimodal-prefix
     sliding-window fix in v0.30.0 (#53147, up to 3-4x E2E) and the FP8-KV
     softmax-underflow fix in v0.32.0 (#60156) — automatic, no flag.
2. **Throughput plateaus at batch=64 on H100, batch=128 on H200.** This is
   *not* a hardcoded vLLM cap — it's HBM-bandwidth-bound saturation. H100
   SXM5 has ~3.35 TB/s HBM3, H200 has ~4.8 TB/s HBM3e (~43% more). The
   bandwidth ratio approximately matches the batch ratio. See
   `references/hbm-saturation.md` for the source-code investigation
   (`get_batch_defaults()` in vllm/engine/arg_utils.py is the only
   hardware-aware batch default in the engine; H100 and H200 take the
   *same* code path — re-verified at v0.32.0). **Don't set
   `max_num_seqs` above the bandwidth knee** — it just inflates TPOT and
   TTFT without moving throughput.
3. **Serve Google's canonical chat template via `--chat-template`; never the
   one bundled in the cyankiwi quant.** That bundled file is frozen at the
   2026-04-30 canonical (`94899c0f…`), 114 lines behind, and silently drops
   `preserve_thinking`, the turn-closure fix and the thought re-open after
   `tool_response`. Pin google revision `68abe480` (sha256 `ae53464b…8de4c6d4`);
   treat a hash change on `main` as a re-vet trigger, not an auto-adopt. Do NOT
   strip the `\n` before `<channel|>` (7%+ tool-calling regression). A
   pre-2026-07-21 `--revision` pin of a cyankiwi repo 404s (history squashed) —
   re-pin to `6f1b616c` (AWQ-4bit) / `e0814036` (qat-AWQ-INT4). Defect list,
   hash chain, re-vet commands and watched template PRs:
   `references/chat-template-drift.md`.

## Decision guide — which TP for which workload

| Prod traffic shape | Deploy | Why |
|---|---|---|
| Short chat (≤4K input), many concurrent users | **2× TP=1 LIGHT**, one per H100 | 408 tok/s/H100 × 2 = 816 tok/s aggregate vs TP=2's 745 (per-H100 TP=2 has ~9% TP communication overhead) |
| Long context (≥16K input), document summarization, RAG | **1× TP=2 PUSH** | Same long-ctx aggregate throughput (~284 tok/s) but **2-3× faster TTFT** (58-137s vs 200-319s), single endpoint, can serve documents up to 256K. **TP=1 cannot serve docs >100K** at all (per-card KV is only ~102K) |
| Mixed (chat + occasional long doc) | **1× TP=2 PUSH** | Versatile; small short-ctx penalty (~10%) acceptable for long-doc capability |
| Per-H100 cost-efficiency only | **TP=1 LIGHT** | Best $/tok at short context |
| Latency-sensitive single-user | **TP=2** | Always lower TPOT (78–193 ms vs 141–201 ms) |

## Operating-point recipes — copy-paste ready

### LIGHT — short-mostly chat, max throughput per H100

Run **2 replicas** on a 2-H100 box, one pinned per GPU via
`--gpus device=N`. Two endpoints (port 8000 + 8001 for example).

```bash
vllm serve cyankiwi/gemma-4-31B-it-AWQ-4bit \
  --tensor-parallel-size 1 \
  --max-model-len 32768 \
  --gpu-memory-utilization 0.85 \
  --max-num-seqs 64 \
  --max-num-batched-tokens 8192 \
  --kv-cache-dtype fp8 \
  --chat-template /path/to/google-31b-chat-template.jinja \
  --trust-request-chat-template \
  --enable-auto-tool-choice \
  --reasoning-parser gemma4 --tool-call-parser gemma4 \
  --speculative-config '{"method":"eagle3","model":"RedHatAI/gemma-4-31B-it-speculator.eagle3","num_speculative_tokens":3}' \
  --no-scheduler-reserve-full-isl
```

Headline numbers per H100 (random 4K input / 512 output, EAGLE3 acceptance ~43%
on random — would be 50–80% on real chat):
- **408 tok/s output** (3688 tok/s total)
- **TPOT mean 141 ms** at concurrency 64-80
- KV cache size: ~85K tokens at fp8

### PUSH — long-context RAG / document summarization

Run **1 replica** spanning both H100s. Single endpoint. Accepts any
prompt up to the architectural max (262144 tokens).

```bash
vllm serve cyankiwi/gemma-4-31B-it-AWQ-4bit \
  --tensor-parallel-size 2 \
  --max-model-len 262144 \
  --gpu-memory-utilization 0.94 \
  --max-num-seqs 256 \
  --max-num-batched-tokens 16384 \
  --kv-cache-dtype fp8 \
  --chat-template /path/to/google-31b-chat-template.jinja \
  --trust-request-chat-template \
  --enable-auto-tool-choice \
  --reasoning-parser gemma4 --tool-call-parser gemma4 \
  --speculative-config '{"method":"eagle3","model":"RedHatAI/gemma-4-31B-it-speculator.eagle3","num_speculative_tokens":3}' \
  --no-scheduler-reserve-full-isl
```

**Why these specific values:**

- `gpu-memory-utilization 0.94` — measured cliff. **0.95+ runtime-OOMs**
  during cudagraph capture for the 35 default capture sizes × max_num_seqs=256.
  0.94 leaves ~1.8 GB headroom per card.
- `max-model-len 262144` — Gemma 4 architectural max (`text_config.max_position_embeddings`).
  Engine reports `Maximum concurrency for 262,144 tokens per request: 6.11x`
  meaning ~6 simultaneous full-context requests fit. Real prod will see
  more concurrency since few prompts hit the full max.
- `max-num-seqs 256` — past the HBM-bandwidth knee (~128 on H100 effective
  for TP=2), but the chunked-prefill scheduler caps actual in-flight at
  ~100 anyway. Keep this high; it's headroom, not a binding constraint.

Headline numbers (TP=2 PUSH):
- Short ctx (4K/512): **745 tok/s output, ~78 ms TPOT** (vs LIGHT's 741 — basically tied)
- Long ctx (16K/1K): **284 tok/s output @ c=128, ~193 ms TPOT, ~137s TTFT**
- KV cache: 244K tokens at fp8 / 0.94 util
- Saturation point: c=128 (engine self-caps in-flight at ~100)

### H200 141GB — start point, not a measured recipe

No H200 run backs a recipe here. Start from the H100 recipe for the workload,
set `--max-num-seqs 128` (the H200 knee, fact #2), then find the knee and the
util cliff on the target box — do not reuse the H100 values:

```bash
for c in 64 96 128 192; do
  vllm bench serve --backend openai-chat --endpoint /v1/chat/completions \
    --model cyankiwi/gemma-4-31B-it-AWQ-4bit --dataset-name random \
    --random-input-len 4096 --random-output-len 512 \
    --num-prompts 400 --num-warmups 5 --max-concurrency "$c"
done
```

Keep the smallest `max_num_seqs` past which output tok/s stays flat while TPOT
keeps rising. Raise `--gpu-memory-utilization` in 0.01 steps from 0.90 and stop
at the first boot or capture OOM minus 0.01 (pitfalls below).

## Coming from gemma-3-27B-fp8

Do not port a gemma-3-27B-fp8 TP choice. Where that model favours TP=2 on
H100/H200, Gemma 4 31B AWQ-4bit favours TP=1 on short context (table above).
Re-bench on the target hardware. Candidate mechanisms (unmeasured) and the
open bench questions: `references/open-questions.md`.

## Pitfalls — things that have already burned a deploy once

### Thinking + tool use on template ≥ 68abe480: no leak on vLLM ≥ 0.24.0, but CoT is silently dropped

The 2026-07-15 canonical template adds a generation-prompt branch that
ends the prompt with an **open** `<|channel>thought\n` when the last
message is a `tool` response and `enable_thinking=true`; the model then
continues in-thought without re-emitting the opener. Stock vLLM handles
this since [#45852](https://github.com/vllm-project/vllm/pull/45852)
(fixing #45834, in v0.24.0+): `adjust_initial_state_from_prompt()`
reverse-scans the prompt token ids and pre-initialises the reasoning
parser when the prompt ends inside an open `<|channel>` block
(`vllm/parser/gemma4.py:482` at v0.25.1). Live-verified 2026-08-02 on
v0.25.1 (temp 0, stream + non-stream, with and without tool schemas in
the request): **no CoT leaks into `content`**.

The remaining defect is the opposite one: the generated CoT is
**silently dropped** — a raw-completions bypass of the same prompt shows
real thought text before `<channel|>`, while the chat path returns
`reasoning_content: ""`. Tokens are generated and billed but never
surfaced. Harmless for most tool workloads; a problem when the client
needs CoT visibility. On vLLM ≤ 0.23 the original leak applies —
mitigate there by running tool deployments thinking-off. Either way this
shape is invisible to benchmark suites whose multi-turn fixtures always
end on a *user* message — test the tool-terminated shape explicitly
(render-probe the prompt tail, then diff bypass vs chat output).

### Bare tool-call openers silently dropped on < v0.30.0 (fixed)

Some checkpoints emit `<|tool_call>:name{...}` — colon directly after the
opener, no `call` prefix. Before v0.30.0 the gemma4 parser state machine had
no transition for a bare `COLON` token there, so the tool call was silently
dropped instead of parsed. Fixed by
[#53444](https://github.com/vllm-project/vllm/pull/53444)
(`vllm/parser/gemma4.py`, `gemma4_config()`), which adds the
`(TOOL_PREAMBLE, "COLON") -> TOOL_NAME` transition. No flag or config
change needed — take v0.30.0+ when serving a checkpoint that emits this
opener shape.

### Named / `required` tool_choice is silently unenforced on stock vLLM

From v0.24.0 through v0.32.0 the gemma4 tool parser sets
`supports_required_and_named = False`
(`vllm/tool_parsers/gemma4_engine_tool_parser.py`): named and `required`
`tool_choice` get **no grammar** and are parsed as `auto`. A model that
prefers prose answers in prose — HTTP 200, `finish_reason: "tool_calls"`,
`tool_calls: null` ([#50477](https://github.com/vllm-project/vllm/issues/50477);
fix PR #51524 open). Upstream: task-description system prompts trigger it.
Where a grammar *is* applied, xgrammar's stop set is tokenizer `<eos>`
only — eos ids 106 (`<turn|>`) and 50 (`<|tool_response>`) stay matchable,
so it can still end without a call. Treat forced `tool_choice` output as
unvalidated: check the tool call materialized before acting on it.
(2026-08-02 v0.25.1 happy-path probes produced correct calls; that shape
does not stress the failure — keep validating.)

### EAGLE3: verify acceptance rate after every engine upgrade or traffic change

Check the engine's acceptance metric against the baseline (~43% on
random, 50–72% on MT-Bench). A collapsed number has two known causes:
- **Non-English traffic.** `RedHatAI/gemma-4-31B-it-speculator.eagle3`
  has `draft_vocab_size: 32000` drawn from English data; it cannot emit
  most non-English tokens, so acceptance collapses by construction
  (~0.45/draft at K=3 on Russian). Run without spec-decode or use a
  drafter trained on the traffic's language.
- **TP ranks disagree.** [#50158](https://github.com/vllm-project/vllm/issues/50158)
  (open; fix PR #50280 open): embed_tokens sharing is decided per-rank.

### A trailing `<turn|>` can leak into streamed output (≤ v0.28.x)

| Engine | Status | Action |
|---|---|---|
| ≤ v0.28.x | affected — [#49955](https://github.com/vllm-project/vllm/issues/49955) | send `enable_thinking` explicitly on **every** request |
| v0.29.0+ | root cause fixed by [#52430](https://github.com/vllm-project/vllm/pull/52430); #49955 still open, unconfirmed on a release | keep sending `enable_thinking` explicitly; run the test below |

Mechanism: the template defaults `enable_thinking` to `false` while the
pre-fix `Gemma4Parser` defaulted it to `True`. With no explicit value the
parser enters the reasoning phase, the tool parser is never dispatched, and
token 106 (`<turn|>`) falls through as content. The discriminator is
**streaming** (`stream=true` leaks, `stream=false` does not); spec-decode (MTP)
amplifies it but is not required. [#50263](https://github.com/vllm-project/vllm/pull/50263)
does not fix it.

Test: temp-0 chat completions **with `stream=true`**, grep the tail for
`<turn|>`. A non-streaming probe misses it. Strict clients (e.g. Copilot)
hard-fail on the leaked token.

### `--max-model-len 262144` will refuse to boot if KV doesn't fit

vLLM enforces `KV_cache_size ≥ max_model_len ÷ engine_concurrency_factor`
at startup. When the util/maxSeqs/spec-dec config leaves insufficient
KV, the engine errors with the **estimated maximum**. Take that number
minus 5% margin to avoid cliff-edge boot variance from CUDA fragmentation.
Worked example: on 2× H100 SXM5, vLLM said 65120 was the ceiling at
TP=1 + util=0.94 + EAGLE3; first boot at 65120 failed (KV=2.44 GiB needed
2.47), second boot succeeded by coincidence. Drop to ≤ 60000 for
reproducible boots.

### One restart = fail, not "let it retry"

Boot succeeding on retry is CUDA-fragmentation luck, not a fix. Treat
restart-1 as a config failure and drop the offending knob (max_model_len,
util, max_num_seqs). The cliff-edge boot at the previous pitfall is
exactly this scenario.

### `parallel_drafting:true` (P-EAGLE) needs a **prepared** checkpoint

`RedHatAI/gemma-4-31B-it-speculator.eagle3` is *vanilla* EAGLE3, no
P-EAGLE prep tokens. `vllm/v1/spec_decode/llm_base_proposer.py` requires
one of `dflash_config.mask_token_id` / `pard_token` / `ptd_token_id` in
the draft `config.json` (checked in that order at v0.25.1, re-verified
2026-07-21; grep `parallel_drafting_token_id` rather than a line number).
Don't pass `parallel_drafting:true` with the vanilla checkpoint — engine
init will fail with exactly that `ValueError` — **at v0.32.0 it names five keys**, `dflash_config.mask_token_id`, `mask_token_id`, `dspark_noise_token_id`, `pard_token`, `ptd_token_id`.

### MTP (`gemma-4-31B-it-assistant`) — 0% acceptance on quantized targets

Google's MTP drafters ("up to 3× speedup") are real, but every published
number is **BF16-target**: the drafter reads the *target model's
activations* and shares its KV cache, so pairing the BF16 assistant with
an AWQ-4bit target measured **0% acceptance at every position**
(2026-05-06 head-to-head, ~37k drafted tokens all rejected) — throughput
0.26–0.39× of EAGLE3, worse than no spec-decode at all. Gemma-4 MTP
ships in stable releases since **v0.21.0** (#41745; MRv2 since v0.23.0,
#43241). On builds before v0.29.0, MTP amplifies the trailing `<turn|>`
leak above. The community DSpark speculator
(`RedHatAI/gemma-4-31B-it-speculator.dspark`) still fails to load at all
([#49475](https://github.com/vllm-project/vllm/issues/49475), re-checked
2026-10-18 — still OPEN). Note what *did* ship: v0.26.0 added a
**Gemma4-12B** DSpark draft model (#47216, for
`deepseek-ai/dspark_gemma4_12b_block7`) — a different model size and a
different checkpoint, so it does not unblock the 31B path.
**On quantized targets use EAGLE3; revisit MTP on BF16 hardware or if
Google ships a quant-matched assistant.**

### DFlash speculator unsupported on sm_89 (RTX 4060 Ti / Ada)

DFlash needs non-causal attention. Only `flash_attn` and
`flex_attention` declare `supports_non_causal=True` on CUDA. On Ada,
`flash_attn` is blocked by fp8 KV + multimodal; `flex_attention` is
PyTorch fallback (no Ada kernel). vLLM skill scopes DFlash to "B200
class". Use EAGLE3 instead.

### Spec-dec acceptance on random tokens is meaningless

EAGLE3 acceptance is ~22-44% on random (vs ~50-72% on MT-Bench, ~80-92%
claimed on aligned chat). When benchmarking, use a real-text dataset
(MT-Bench, ShareGPT, NuminaMath) for realistic acceptance numbers.
Random benchmarks give worst-case lower bound.

### gpu-memory-utilization=0.97 OOM on cudagraph capture

Reproducible failure on TP=2 H100 with `max-num-seqs 256
max-num-batched-tokens 16384`: cudagraph capture for the 35 default
sizes ([1,2,4,8,...,256]) needs ~336 MiB and OOMs at 0.97. Stay at 0.94.

### Multimodal at high util OOMs at runtime

util=0.94 on 16 GB Ada cards (RTX 4060 Ti) caused runtime CUDA OOM
on the first multimodal request — image batch all_gather needed 394 MiB,
only 337 MiB free. On 80 GB H100 with TP=2, util=0.94 is fine for text;
for multimodal traffic specifically, drop to 0.92 or 0.90.

## Stock parsers vs an out-of-tree Rust parser plugin

**Use the stock `gemma4` reasoning and tool parsers on vLLM ≥ 0.24.0** unless
the client needs CoT visibility or hard forced-`tool_choice` guarantees. Stock
caveats, both under Pitfalls: CoT is silently dropped on tool-turn
continuations (no leak), and named/`required` `tool_choice` is parsed as
`auto` with no grammar.

Head-to-head on 2× H100 (vLLM 0.20.0, canonical template; thinking + tools and
happy-path forced `tool_choice` re-checked on v0.25.1):

| Measure | Result |
|---|---|
| Correctness | stock passes every lane the plugin passes (`xgrammar_schema_enforce`, `image_token_in_output`, 6 parser-suite + 9 multimodal lanes) |
| Throughput, TPOT mean | identical within noise (<1%) |
| TPOT P99 | plugin ~8-11% lower in 3 of 3 runs (no Python GIL/GC pauses) |

## References

- `references/hbm-saturation.md` — vLLM source-code investigation, GH issues, the bandwidth-bound saturation explanation
- `references/chat-template-drift.md` — canonical vs bundled template: defect list, vetted pins, re-vet commands, hash chain
- `references/open-questions.md` — unmeasured mechanisms (gemma-3 vs gemma-4 TP curve) and bench questions still open
- `references/bench-numbers.md` — full benchmark table from the 2026-04-30 2× H100 audit, all 12+ data points
- `references/sources.md` — dated index of upstream URLs (HF model + chat_template, vLLM source paths, GH issues / PRs) with `Last verified:` and `Pinned:` markers
