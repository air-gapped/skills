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
`RedHatAI/*-Gemma-4-31B-*`) on vLLM 0.20–0.25.1. Pulls together measurements
from a Verda 2× H100 SXM5 80GB audit on 2026-04-30 — **taken on vLLM 0.20.0
and not re-run since** (see `references/bench-numbers.md`; the shape of the
curves has held, but treat the absolute figures as 0.20.0 observations) — and
the upstream constraints that shape the answer.

> **Version ceiling (re-verified 2026-08-11): hold at vLLM 0.25.1. Do not
> take 0.26.0, 0.27.0 or 0.27.1.** All three gemma-4-relevant regressions are
> still **OPEN**, and every fix PR for them is still **unmerged**, so neither
> 0.27.0 (2026-08-10) nor the 0.27.1 patch (2026-08-11 — a single change,
> #50424, scoped to `Qwen3DSparkModel`, nothing Gemma) clears any of them:
> [#49955](https://github.com/vllm-project/vllm/issues/49955) (trailing
> `<turn|>` leaked into output — **not spec-decode-specific after all**, see
> the pitfall below; fix PR
> [#50964](https://github.com/vllm-project/vllm/pull/50964) open, and
> [#50263](https://github.com/vllm-project/vllm/pull/50263) was tested by the
> reporter and did *not* fix it),
> [#50477](https://github.com/vllm-project/vllm/issues/50477) (gemma4
> parser silently ignores named forced `tool_choice`; a second reporter
> extends it to `tool_choice: "required"`, which returns
> `finish_reason: "tool_calls"` with prose in `content` and `tool_calls:
> null` — fix PR [#51524](https://github.com/vllm-project/vllm/pull/51524)
> open),
> [#50159](https://github.com/vllm-project/vllm/issues/50159) (Model
> Runner V2 over-reports available KV → CUDA OOM under saturating load;
> crashes earlier with EAGLE — no fix PR at all). Two independent A/B runs
> on #50159 now localise it: the gap is **CUDA-graph capture headroom**, not
> KV capacity. MRv1 reserves ~0.65 GiB for capture where MRv2 reserves
> ~0.12 GiB, and the whole discrepancy disappears under `--enforce-eager`.
> Severity scales with model size and inversely with card size.
>
> The one thing 0.27.0 does add for this model is the **ViT CUDA graph**
> ([#46837](https://github.com/vllm-project/vllm/pull/46837), merged
> 2026-07-25, listed in the v0.27.0 release notes): full
> `SupportsEncoderCudaGraph` for `Gemma4ForConditionalGeneration`, making the
> vision encoder 100% statically compiled by replacing the pooler's
> data-dependent slicing with a fixed-shape gather. Relevant only to
> multimodal traffic, and not worth taking the three regressions for —
> re-evaluate when #49955 and #50159 close.

## Three load-bearing facts

1. **Gemma 4 has heterogeneous head_dim (256 dense / 512 attention)**, which
   forces vLLM to use `TRITON_ATTN` backend, not FLASH_ATTN. This is
   automatic — vLLM logs `Gemma4 model has heterogeneous head dimensions
   (head_dim=256, global_head_dim=512). Forcing TRITON_ATTN backend to
   prevent mixed-backend numerical divergence`. Don't try to override
   with `--attention-backend FLASH_ATTN` — vLLM rejects it (`kv_cache_dtype
   not supported`, `partial multimodal token full attention not supported`).
2. **Throughput plateaus at batch=64 on H100, batch=128 on H200.** This is
   *not* a hardcoded vLLM cap — it's HBM-bandwidth-bound saturation. H100
   SXM5 has ~3.35 TB/s HBM3, H200 has ~4.8 TB/s HBM3e (~43% more). The
   bandwidth ratio approximately matches the batch ratio. See
   `references/hbm-saturation.md` for the source-code investigation
   (`get_batch_defaults()` in vllm/engine/arg_utils.py is the only
   hardware-aware batch default in the engine; H100 and H200 take the
   *same* code path — re-verified at v0.25.1). **Don't set
   `max_num_seqs` above the bandwidth knee** — it just inflates TPOT and
   TTFT without moving throughput.
3. **The chat_template shipped with the cyankiwi quant is frozen, and the
   gap is now measured — not assumed.** (The RedHatAI speculator ships no
   `chat_template.jinja` at all, so it inherits whatever the base model
   supplies.) On 2026-08-11
   `cyankiwi/gemma-4-31B-it-AWQ-4bit/chat_template.jinja` still hashed
   `94899c0f…25bff413` — **byte-identical to the canonical template as it
   stood on 2026-04-30**. Canonical has moved twice in that window:

   > **Revision-pin hazard (2026-07-21):** both cyankiwi repos
   > (`gemma-4-31B-it-AWQ-4bit`, `gemma-4-31B-it-qat-AWQ-INT4`)
   > **squashed their git history** — every pre-squash revision SHA now
   > returns 404, so any `--revision` pin from before that date
   > crash-loops on a cold boot with an empty HF cache. Current HEADs:
   > `6f1b616c` (AWQ-4bit), `e0814036` (qat-AWQ-INT4). All config,
   > tokenizer, and template files were verified byte-identical across
   > the squash, so re-pinning needs no re-audit.

   | Pulled | sha256 | Bytes |
   |---|---|---|
   | 2026-04-30 | `94899c0f…25bff413` | 16934 |
   | 2026-05-28 | `36e3a42e…bead3f0` | 17466 |
   | 2026-07-21 | `ae53464b…8de4c6d4` | 18683 |
   | 2026-08-11 | `ae53464b…8de4c6d4` | 18683 (**held** — first pass with no drift) |

   The current file opens with a Google-authored header: *"Published:
   2026-07-09 — Fixed tool-calling loops, turn closures, and thinking
   content-ordering."* 114 lines differ from the frozen copy. Serving the
   quant's bundled template therefore silently gives up:

   - `preserve_thinking` — new kwarg gating whether thinking content
     survives past the last user turn on tool-call messages (absent
     entirely in the frozen copy)
   - the `continues_into_next` turn-closure fix — the frozen copy emits
     duplicate `<|turn>model` markers on model→assistant continuations
   - `<|channel>thought` re-opened after a `tool_response` when thinking
     is on
   - `argument is none` → renders `null`; the frozen copy falls straight
     into the string branch
   - `messages and messages[0]` guards against an empty message list

   Serve the canonical template via `--chat-template`, but **pin the
   vetted revision rather than blind-pulling `main` per deploy** —
   currently google revision `68abe480` (2026-07-15, sha256
   `ae53464b…8de4c6d4`, unchanged on `main` through at least 2026-08-11;
   the one later commit `842da379` only added `response_template`
   metadata to tokenizer_config.json). Template updates change
   parser-facing behavior (see the thinking + tools pitfall below), so
   re-hash `main` periodically and treat a hash change as a re-vet
   trigger, not an auto-adopt. Unmerged upstream template PRs worth
   watching before the next adoption:
   [#137](https://huggingface.co/google/gemma-4-31B-it/discussions/137)
   (keep tool-call reasoning across later user turns — prefix-cache win
   on agent loops) and
   [#140](https://huggingface.co/google/gemma-4-31B-it/discussions/140)
   (multimodal placeholders emitted outside the tool_response block).
   Do NOT strip the `\n` before `<channel|>` in local candidates —
   Google measured 7%+ tool-calling regressions without it
   ([#135](https://huggingface.co/google/gemma-4-31B-it/discussions/135)).

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

## Why gemma-4-31B-AWQ behaves differently than gemma-3-27B-fp8

An existing prod running gemma-3-27B-fp8 may favour TP=2 over TP=1 or
TP=4 on H100/H200 — that experience is correct for that model. Gemma 4
31B AWQ-4bit shows a different curve (TP=1 wins on short-ctx per-H100
efficiency). The four reasons below are plausible mechanisms, not
measured attributions — confirming each needs a one-variable-at-a-time
bench (see "What was NOT measured" below).

1. **AWQ-4bit weights are smaller than fp8** (4 bits vs 8 bits, ~16 GB vs
   ~27 GB). Less benefit from TP weight-splitting since weights already
   fit comfortably on one H100 with KV headroom.
2. **TRITON_ATTN backend has different TP scaling than FLASH_ATTN**.
   gemma-3 uses FLASH_ATTN (homogeneous head_dim); Gemma 4 forces
   TRITON_ATTN — different per-rank communication characteristics.
3. **EAGLE3 spec-dec compute scales asymmetrically with TP**. The drafter
   weights are also sharded across TP ranks; for a small drafter (4.5 GB
   BF16 split across 2 cards) the per-rank compute is small, but the
   draft-verify cycle adds extra all-reduces that hurt at TP=2.
4. **31B vs 27B**: 31B has more layers + hidden dim → larger weight
   bytes per token; HBM bandwidth saturation knee shifts with weight
   size.

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
surfaced. Harmless for most tool workloads; a problem if your client
needs CoT visibility. On vLLM ≤ 0.23 the original leak applies —
mitigate there by running tool deployments thinking-off. Either way this
shape is invisible to benchmark suites whose multi-turn fixtures always
end on a *user* message — test the tool-terminated shape explicitly
(render-probe the prompt tail, then diff bypass vs chat output).

### Named / `required` tool_choice is silently unenforced on stock vLLM

vLLM's xgrammar backend builds its stop-token set from the tokenizer
`<eos>` only — generation_config's extra eos ids 106 (`<turn|>`) and 50
(`<|tool_response>`) are ordinary tokens to the grammar, so their texts
are matchable through any region admitting `<` and the constraint can
terminate without a conforming tool call. Root-caused 2026-07-18
(request-level bisect); the same failure class is reported upstream as
[#50477](https://github.com/vllm-project/vllm/issues/50477). Treat
forced `tool_choice` output as unvalidated on stock — check the tool
call actually materialized before acting on it. Auto tool choice is
unaffected. (2026-08-02 live probes on v0.25.1: named + `required` both
produced correct calls on a happy-path prompt — but that shape doesn't
stress the failure mode, which needs the model *preferring* to end its
turn; keep validating.)

### EAGLE3 + TP=2: verify acceptance rate after every engine upgrade

[#50158](https://github.com/vllm-project/vllm/issues/50158) (open,
2026-08): the EAGLE drafter's embed_tokens-sharing decision is made
per-rank without cross-rank agreement, so TP ranks can build *different*
drafters and acceptance collapses to ~0.45/draft — spec-decode still
"works" but silently loses most of its win. Both recipes below are
TP-capable EAGLE3 shapes. Check the engine's acceptance metric against
the baseline (~43% on random, 50–72% on MT-Bench); a collapsed number
means you're hit.

### A trailing `<turn|>` can leak into streamed output — not only under spec-decode

[#49955](https://github.com/vllm-project/vllm/issues/49955), still open.
The original report was MTP-only, and this skill previously recorded
"not reproducible without spec-decode." **That is now contradicted by the
same reporter's own matrix** (2026-07-31): reproduces on 0.25.1 and
0.26.0, clean on 0.24.0 — and reproduces on 0.26.0 with **MTP completely
disabled**. The discriminating variable in that environment is
**streaming**: `stream=true` leaks, `stream=false` does not. A vLLM
contributor separately could not reproduce it at all on 0.26.0 without
spec-decode, so the trigger is evidently config-sensitive; treat
spec-decode as an amplifier, not the cause.

Instrumented root cause (community, unconfirmed by maintainers): an
`enable_thinking` default mismatch. `examples/tool_chat_template_gemma4.jinja`
renders `enable_thinking | default(false)` while `Gemma4Parser` reads
`chat_kwargs.get("enable_thinking", True)` — **both verified verbatim in
the v0.27.0 tree** (template line 180, `vllm/parser/gemma4.py` line 403).
With no explicit value the template renders thinking *off* while the
parser behaves as if it were *on*; the outer parser enters the reasoning
phase, the inner engine stays in `CONTENT`, the tool parser is never
dispatched, and token 106 — correctly mapped to `__DROP__` but preserved
under `skip_tool_parsing=True` — falls through as ordinary content. Model
output that happens to emit a real channel block masks the bug by
correcting the state mid-stream.

**Mitigation on an affected engine: send `enable_thinking` explicitly on
every request** rather than relying on either default. Fix PR
[#50964](https://github.com/vllm-project/vllm/pull/50964) is open and
unmerged; [#50263](https://github.com/vllm-project/vllm/pull/50263) was
tested by the reporter and did not fix it.

Cheap test: temp-0 chat completions **with `stream=true`**, grep the tail
for `<turn|>`. Non-streaming probes miss it. Strict clients like Copilot
hard-fail on the leaked token.

### `--max-model-len 262144` will refuse to boot if KV doesn't fit

vLLM enforces `KV_cache_size ≥ max_model_len ÷ engine_concurrency_factor`
at startup. When the util/maxSeqs/spec-dec config leaves insufficient
KV, the engine errors with the **estimated maximum**. Take that number
minus 5% margin to avoid cliff-edge boot variance from CUDA fragmentation.
Worked example: on Verda 2× H100, vLLM said 65120 was the ceiling at
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
init will fail with exactly that three-name `ValueError`.

### MTP (`gemma-4-31B-it-assistant`) — 0% acceptance on quantized targets

Google's MTP drafters ("up to 3× speedup") are real, but every published
number is **BF16-target**: the drafter reads the *target model's
activations* and shares its KV cache, so pairing the BF16 assistant with
an AWQ-4bit target measured **0% acceptance at every position**
(2026-05-06 head-to-head, ~37k drafted tokens all rejected) — throughput
0.26–0.39× of EAGLE3, worse than no spec-decode at all. Also: gemma-4
MTP support is still nightly-only — **no stable release through 0.27.0
carries it** (neither the v0.26.0 nor the v0.27.0 release notes list a
Gemma-4 MTP entry), and MTP is an amplifier of the trailing `<turn|>`
leak above. The community DSpark speculator
(`RedHatAI/gemma-4-31B-it-speculator.dspark`) still fails to load at all
([#49475](https://github.com/vllm-project/vllm/issues/49475), re-checked
2026-08-11 — still OPEN). Note what *did* ship: v0.26.0 added a
**Gemma4-12B** DSpark draft model (#47216, for
`deepseek-ai/dspark_gemma4_12b_block7`) — a different model size and a
different checkpoint, so it does not unblock the 31B path.
**On quantized targets use EAGLE3; revisit MTP on BF16 hardware or if
Google ships a quant-matched assistant.** Full memo:
`findings/cyankiwi/gemma-4-31B-it-AWQ-4bit/mtp-vs-eagle3/deploy-memo.2026-05-06.md`.

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

util=0.94 on the 16 GB lab cards (RTX 4060 Ti) caused runtime CUDA OOM
on the first multimodal request — image batch all_gather needed 394 MiB,
only 337 MiB free. On 80 GB H100 with TP=2, util=0.94 is fine for text;
for multimodal traffic specifically, drop to 0.92 or 0.90.

## Stock vs preflight parser plugin

The 2026-04-30 audit measured stock vLLM 0.20.0 + the new Google
chat_template against the preflight Rust parser plugin head-to-head on
H100. Result:

- **Correctness**: stock + new chat_template now passes everything
  preflight passes (`xgrammar_schema_enforce`, `image_token_in_output`,
  all 6 parser-suite + 9 multimodal-battery lanes).
- **Throughput**: identical at noise floor (<1% delta).
- **TPOT mean**: identical.
- **TPOT P99**: preflight ~8-11% lower in 3 of 3 runs (Rust avoids
  Python GIL/GC pauses) — small but consistent.

**Supersession note (2026-08-02, updated same day after live A/B):**
the 04-30 "stock passes everything" conclusion extends further than
first thought. Verified on v0.25.1: stock handles the template-≥
`68abe480` thinking+tools prefill with no CoT leak (see Pitfalls; the
caveat is silent CoT drop, not leakage), and happy-path forced
tool_choice (named + `required`) produced correct calls. Remaining
stock caveats: the xgrammar stop-token-set gap means forced tool_choice
can still terminate through stop-token *text* when the model prefers
ending its turn (see Pitfalls — happy-path probes don't stress this),
and `reasoning_content` is empty on tool-turn continuations. **Stock
parsers are the right call for tool-calling deployments on ≥ 0.24.0
unless you need CoT visibility or hard forced-tool_choice guarantees.**
Full memo:
`findings/cyankiwi/gemma-4-31B-it-AWQ-4bit/verda-stock-vs-preflight/comparison-memo.2026-04-30.md`.

## What was NOT measured

The following questions need a follow-up bench:

1. **`num_speculative_tokens=2` vs 3 on real-text**. At higher real
   acceptance (50-80%) k=3 may pay off but at low acceptance k=2 might
   win. Untested on Gemma 4.
2. **No-spec-dec baseline**. Operator brief was EAGLE3-only; if real
   acceptance drops below ~30% on prod traffic, no-spec might be
   competitive on aggregate throughput at high concurrency.
3. **AWQ-Marlin kernel** vs vanilla AWQ. Marlin is faster mid-batch on
   H100; cyankiwi quant uses compressed-tensors format which dispatches
   to Marlin automatically when available, but worth confirming via the
   `[compressed_tensors_wNa16] Using MarlinLinearKernel` log line.
4. **TP=4 hypothetical**. Would need a 4-H100 SKU. The bandwidth-bound
   knee should shift again, but TP communication overhead grows
   non-linearly past TP=2.
5. **Real-text long-context**. The 16K/1K random benchmark is
   conservative; ShareGPT-long or NuminaMath would give more realistic
   acceptance + throughput.

## References

- `references/hbm-saturation.md` — vLLM source-code investigation, GH issues, the bandwidth-bound saturation explanation
- `references/bench-numbers.md` — full benchmark table from the 2026-04-30 Verda audit, all 12+ data points
- `references/sources.md` — dated index of upstream URLs (HF model + chat_template, vLLM source paths, GH issues / PRs) with `Last verified:` and `Pinned:` markers

## Reproduction artifacts

The benchmark logs + memos referenced in this skill live in the
`model-preflight` repo at:

```
findings/cyankiwi/gemma-4-31B-it-AWQ-4bit/
├── verda-tp1-tp2-search/
│   ├── max-perf-tp1-vs-tp2-memo.2026-04-30.md
│   ├── tp1-stock-eagle3-max-perf.md
│   └── p{1,2,3}-*.log              # raw bench output
├── verda-stock-vs-preflight/
│   ├── comparison-memo.2026-04-30.md
│   └── parser-suite-{stock,preflight}.jsonl
└── eagle3-sweep/
    └── deploy-memo.2026-04-29.md
```
