# Per-family chat template reference

Load this when the operator names a model family. Each section: required flags → known bugs with issue URLs → operator recovery.

---

## Table of contents

1. [Qwen3 (dense + MoE + Coder)](#qwen3)
2. [DeepSeek-R1 / V3 / V3.1 / V3.2](#deepseek)
3. [GPT-OSS (20B / 120B)](#gpt-oss)
4. [Kimi-K2 (and K2.5)](#kimi-k2)
5. [Llama-4 Maverick / Scout](#llama-4)
6. [Mistral / Mistral-Small / Pixtral / Devstral](#mistral)
7. [Gemma-3 / Gemma-4](#gemma)
8. [Phi-4 / Phi-4-reasoning](#phi-4)
9. [GLM-4.7 / GLM-5.1](#glm)
10. [Hermes / Granite / Hunyuan / Toolace / XLAM / FunctionGemma](#other-tool-families)

---

## Qwen3

**Flags (general):**

```
--model Qwen/Qwen3-30B-A3B-Instruct-2507
--tool-call-parser hermes         # Qwen3 dense + MoE (Hermes-style <tool_call> JSON)
--reasoning-parser qwen3
# tokenizer default chat template — don't pass --chat-template
```

**Flags (Qwen3-Coder 480B / 30B-A3B Coder):** do NOT use `hermes` — model emits XML, not Hermes JSON.

```
--model Qwen/Qwen3-Coder-480B-A35B-Instruct
--tool-call-parser qwen3_xml
--chat-template examples/tool_chat_template_qwen3coder.jinja
```

**Thinking toggle** via OpenAI client:

```python
client.chat.completions.create(
    model="Qwen/Qwen3-30B",
    messages=[...],
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
```

Default is `enable_thinking=True`. `False` inserts empty `<think>\n\n</think>\n\n` in prefill; parser treats all output as content.

### Known bugs

| Issue | Summary | Fix / status |
|---|---|---|
| [vLLM #18819](https://github.com/vllm-project/vllm/issues/18819) | Structured output / `guided_json` breaks when `enable_thinking=false` — model emits stray `{`, `[`, or triple-backtick leaders. | Keep thinking on; or post-process. |
| [vLLM #19513](https://github.com/vllm-project/vllm/issues/19513) | Reasoning on → tool-call parsing fails (Hermes parser didn't skip `<think>` blocks). | Upgrade vLLM; combined Hermes+Qwen3 reasoning fixed. |
| [vLLM #20611](https://github.com/vllm-project/vllm/issues/20611) | Streaming + `enable_thinking=false` → `tool_calls` field missing, `finish_reason` wrong. | Upgrade. |
| [vLLM #21711](https://github.com/vllm-project/vllm/issues/21711) | Qwen3 tool-call regressions across transformers versions. | Pin transformers version per model card. |
| [ms-swift #5836](https://github.com/modelscope/ms-swift/issues/5836) | Downstream harness fails to forward `enable_thinking=False` through vLLM. | Client-side fix — ensure `extra_body.chat_template_kwargs` is passed. |

### `<think>` history handling (subtle)

Qwen3 template walks messages in reverse and preserves `<think>` blocks only for assistant turns *after the last non-tool user turn*. Earlier thoughts are pruned — token savings, but means tool responses must carry enough context to recover reasoning state. [HF blog: Qwen3 deep dive](https://huggingface.co/blog/qwen-3-chat-template-deep-dive).

### Argument serialization fix

Qwen3 template checks `tool_call.arguments is string` before `| tojson` — avoids the double-escape bug that plagued earlier Hermes-style templates.

---

## DeepSeek

### R1 / V3 / V3.1 / V3.2 flag matrix

| Model | `--chat-template` | `--tool-call-parser` | Extra |
|---|---|---|---|
| DeepSeek-R1 (0528) | `examples/tool_chat_template_deepseekr1.jinja` | `deepseek_v3` | `--reasoning-parser deepseek_r1` |
| DeepSeek-V3-0324 | `examples/tool_chat_template_deepseekv3.jinja` | `deepseek_v3` | — |
| DeepSeek-V3.1 | `examples/tool_chat_template_deepseekv31.jinja` | `deepseek_v31` | `--reasoning-parser deepseek_r1` |
| DeepSeek-V3.2 | (covered by `--tokenizer-mode deepseek_v32`) | `deepseek_v32` | `--enable-auto-tool-choice`, `--reasoning-parser deepseek_r1` |

### Known bugs

| Issue | Summary | Fix / status |
|---|---|---|
| [HF DeepSeek-R1 #144](https://huggingface.co/deepseek-ai/DeepSeek-R1/discussions/144) | Template hard-prepends `<think>\n` into prefill → opening `<think>` never appears in output → `reasoning_content` returns `null`. | Post-process prepend; or use updated template where parser sees only `</think>`. |
| [vLLM #12999](https://github.com/vllm-project/vllm/issues/12999) | Same root cause — `reasoning_content` always None. | Same — fixed parser handles this now. |
| [vLLM discussion #12708](https://github.com/vllm-project/vllm/discussions/12708) | Nested `<think>` / `</think>` confuses parser. | Switch to vLLM ≥0.11. |
| [vLLM #28804](https://github.com/vllm-project/vllm/issues/28804) | V3.1 tool parser: leading whitespace progressively accumulates across multi-turn tool calls. | Closed NOT_PLANNED 2026-03-23 (verified 2026-04-24). Apply client-side mitigation (strip leading whitespace between turns); no upstream fix planned. |
| [vLLM forum](https://discuss.vllm.ai/t/deepseek-v3-tool-choice-auto-not-working-but-tool-choice-required-is-working/1006/) | `tool_choice="auto"` fails, `"required"` works. | Use `required` or named tool. |

### API contract gotchas (vLLM vs official DeepSeek API)

| Concern | vLLM | DeepSeek official API |
|---|---|---|
| Thinking toggle | `extra_body={"chat_template_kwargs": {"thinking": true}}` | `extra_body={"thinking": {"type": "enabled"}}` |
| Reasoning field | `reasoning_content` (post #28472) | `reasoning_content` |
| Empty tool calls | `tool_calls: []` | `null` |

Clients that hard-code one fail on the other.

---

## GPT-OSS

`openai/gpt-oss-20b`, `openai/gpt-oss-120b`. Uses **Harmony** response format.

**Flags:**

```
--tool-call-parser openai
--reasoning-parser gpt_oss   # harmony-native
```

**Endpoint guidance:** Prefer `/v1/responses` over `/v1/chat/completions` for tool calling until chat-completions parity lands.

### Known bugs

| Issue | Summary | Workaround |
|---|---|---|
| [vLLM #22578](https://github.com/vllm-project/vllm/issues/22578) | `/v1/chat/completions` tool calling broken. `hermes` parser crashes at startup; `mistral`/`llama3_json` start but emit "incorrect number of parameters" or empty `arguments`. | Closed NOT_PLANNED 2026-01-23 (verified 2026-04-24) — **permanent guidance**: use `/v1/responses` for gpt-oss tool calling. |
| [vLLM #23015](https://github.com/vllm-project/vllm/issues/23015) | User-supplied `--chat-template` appears hard-coded / ignored for gpt-oss. | Closed NOT_PLANNED 2026-04-20 (verified 2026-04-24) — intentional; use the Harmony endpoint. |
| [HF gpt-oss-20b #218](https://huggingface.co/openai/gpt-oss-20b/discussions/218) | Function-call token ordering mismatch vs Harmony spec. | Pending upstream fix. |
| [HF gpt-oss-20b #160](https://huggingface.co/openai/gpt-oss-20b/discussions/160) | Chat template doesn't match Harmony spec. | Same. |
| [HF gpt-oss-120b #69](https://huggingface.co/openai/gpt-oss-120b/discussions/69) | Errors in 120b chat template vs spec. | Same. |
| [vLLM #22403](https://github.com/vllm-project/vllm/issues/22403) | "Expected 2 output messages (reasoning and final), got 7." Harmony parser confused by multi-segment output. | Upgrade vLLM; retry. |
| [vLLM #37909](https://github.com/vllm-project/vllm/issues/37909) | `reasoning_effort="none"` doesn't disable reasoning and can break output. | Omit or use `"low"`. |
| `openai_harmony` offline vocab | Raises `HarmonyError` when loading tiktoken vocab offline. | Pre-download tiktoken encodings, set `TIKTOKEN_ENCODINGS_BASE`. |

---

## Kimi-K2

`moonshotai/Kimi-K2-Instruct`, `moonshotai/Kimi-K2-Instruct-0905`.

**Flags:**

```
--tool-call-parser kimi_k2
--reasoning-parser kimi_k2
# tokenizer default template (post-fix commit)
```

### Minimum HF revision SHAs (critical)

Before these commits, templates are broken. Pin revision:

| Model | Minimum commit |
|---|---|
| Kimi-K2-Instruct-0905 | `94a4053eb8863059dd8afc00937f054e1365abbd` |
| Kimi-K2-Instruct | `0102674b179db4ca5a28cd9a4fb446f87f0c1454` |

### Three compatibility bugs (vLLM blog, Oct 2025)

[vllm.ai/blog/Kimi-K2-Accuracy](https://vllm.ai/blog/Kimi-K2-Accuracy):

1. **`add_generation_prompt` silently dropped.** vLLM PR #25794 only forwarded explicitly-declared tokenizer kwargs; Kimi's tokenizer accepted it via `**kwargs`, so the flag vanished → prompts ended at user message → `finish_reason=stop` with no tool calls. Fixed by PR #27622 (whitelists standard HF kwargs).

2. **Empty-string content → list conversion.** vLLM wraps `''` into `[{'type':'text','text':''}]`; Kimi's Jinja expected a string and rendered the list literally. Template updated to type-check content.

3. **Over-strict tool-call ID regex.** Parser required `functions.<name>:<idx>` exactly; models occasionally emitted `search:2` → `IndexError` → all tool calls silently discarded. Fixed by PR #27565 (hardens parser + normalizes historical IDs).

Result: internal benchmark success rate went from ~18% → 99.925%.

### Related

| Issue | Summary |
|---|---|
| [vLLM #22718](https://github.com/vllm-project/vllm/issues/22718) | `tool_call_regex` fails when whitespace follows the colon. |
| [vLLM #33654](https://github.com/vllm-project/vllm/issues/33654) | Kimi-K2.5 empty content responses. |
| [MoonshotAI/Kimi-K2 #41](https://github.com/MoonshotAI/Kimi-K2/issues/41) | Complex tool calls → empty output / FSM advance failure. |

---

## Llama-4

Maverick, Scout (17B × 16E and similar).

**Flags (pythonic recommended):**

```
--tool-call-parser llama4_pythonic
--chat-template examples/tool_chat_template_llama4_pythonic.jinja
```

JSON variant (`llama4_json.jinja`) exists; pythonic is generally better.

### Known bugs

| Issue | Summary |
|---|---|
| [vLLM #13978](https://github.com/vllm-project/vllm/issues/13978) | Chat template crashes on `tool_calls=[]` in previous assistant messages. |
| [HF Scout #78](https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E-Instruct/discussions/78) | `fix_tool_call` template edits. |
| [vLLM forum](https://discuss.vllm.ai/t/help-llama4-maverick-failure-in-langgraph-swarm-handoff-tools/1755) | LangGraph Swarm handoff tools fail on Maverick; single tool calls work, multi-agent orchestration breaks. |
| [PR #16463](https://github.com/vllm-project/vllm/pull/16463) | Added Llama-4 pythonic templates (earlier defaults inadequate). |

### Gotchas

- Tool-call and tool-response messages must terminate with `<|eom|>`.
- `<|python_start|>` / `<|python_end|>` tokens are **not guaranteed** in output — parser must be lenient.
- Parallel tool calls: supported (unlike Llama-3).
- Smaller pythonic-format models (Llama-3.2-1B/3B, Scout variants) frequently emit malformed pythonic — parser has no fallback.

---

## Mistral

**Critical: two incompatible formats, two flag sets. Operators pick the wrong one constantly.**

### Format 1: Mistral native (mistral-common tokenizer)

```
--tokenizer-mode mistral
--config-format mistral
--load-format mistral
--tool-call-parser mistral
# NO --chat-template (silently ignored)
```

### Format 2: Hugging Face format

```
--tokenizer-mode hf
--config-format hf
--load-format hf
--tool-call-parser mistral
--chat-template examples/tool_chat_template_mistral_parallel.jinja
```

### Known bugs

| Issue | Summary |
|---|---|
| [vLLM #25401](https://github.com/vllm-project/vllm/issues/25401) | **`--chat-template` silently dropped when `--tokenizer-mode mistral`**; warning only. Operators edit template, nothing changes. Closed COMPLETED 2025-10-09 (verified 2026-04-24) — behavior at least louder in current vLLM; test on your version before assuming silent drop. |
| [vLLM #16292](https://github.com/vllm-project/vllm/issues/16292) | `MistralTokenizer` not working with Mistral-Small-3.1 in HF format; missing `pad_token`/`sep_token`. |
| [vLLM #18090](https://github.com/vllm-project/vllm/issues/18090) | Auto tokenizer mode doesn't detect mistral — operators must set explicitly. |
| [vLLM #9059](https://github.com/vllm-project/vllm/issues/9059) | `--tokenizer-mode mistral` not compatible with OpenAI-API tool-use tests. |
| [vLLM #19545](https://github.com/vllm-project/vllm/issues/19545) | Jinja missing `parallel_tool_prompt` injection; incorrect `tool_response`. |
| [HF Pixtral #22](https://huggingface.co/mistral-community/pixtral-12b/discussions/22) | Chat template correctness for vLLM. |
| [HF Mistral-Small-3.1 #49](https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503/discussions/49) | HF-format template broken under vLLM. |

### Tool-call ID quirk (HF format only)

Mistral's HF chat template requires **exactly-9-digit** `tool_call_id`s. vLLM generates longer IDs → Jinja exception. Shipped `examples/tool_chat_template_mistral.jinja` truncates to last 9 digits; `_parallel.jinja` variant adds a parallel-tool system prompt for better reliability.

---

## Gemma

### Gemma-3 / 3n

No native JSON tool calling in tokenizer template — use community pythonic.

```
--tool-call-parser pythonic
--chat-template examples/tool_chat_template_gemma3_pythonic.jinja
```

| Issue | Summary |
|---|---|
| [vLLM #16482](https://github.com/vllm-project/vllm/issues/16482) | No native JSON-based tool calling. |
| [vLLM #15403](https://github.com/vllm-project/vllm/issues/15403) | Same. |
| [vLLM #14734](https://github.com/vllm-project/vllm/issues/14734) | Setup guidance unclear for Gemma-3 tool calling. |
| [vLLM #20341](https://github.com/vllm-project/vllm/issues/20341) | Gemma-3 produces empty or repeated output. |

### Gemma-4 (2026)

```
--tool-call-parser gemma4
--reasoning-parser gemma4
--chat-template examples/tool_chat_template_gemma4.jinja
```

| Issue | Summary | Workaround |
|---|---|---|
| [vLLM #39392](https://github.com/vllm-project/vllm/issues/39392) | `<pad>` tokens under concurrent load; sequential requests succeed. | `--max-num-seqs 1` (performance hit); or wait for fix. |
| [vLLM #38855](https://github.com/vllm-project/vllm/issues/38855) | Reasoning parser fails — `<|channel>` tokens stripped before parser sees them. | `extra_body={"skip_special_tokens": false}`. |
| [vLLM #39043](https://github.com/vllm-project/vllm/issues/39043) | Tool calling broken with Claude Code client. | — |
| [HF gemma-4-31B #28](https://huggingface.co/google/gemma-4-31B-it/discussions/28) | Missing `reasoning` field in response. | Upstream. |

---

## Phi-4

### Phi-4-mini (tool calling)

```
--tool-call-parser llama3_json
--chat-template examples/tool_chat_template_phi4_mini.jinja
```

### Phi-4-reasoning-plus

Do **not** use `deepseek_r1` reasoning parser — causes a repeating-phrase loop ([vLLM #18141](https://github.com/vllm-project/vllm/issues/18141)). Phi-4 has its own reasoning format; parser selection matters.

### Known bugs

| Issue | Summary |
|---|---|
| [vLLM #14682](https://github.com/vllm-project/vllm/issues/14682) | Phi-4-mini function calling doesn't work even with custom Jinja + `llama3_json` parser. |
| [vLLM #16510](https://github.com/vllm-project/vllm/issues/16510) | Phi-4 GGUF broken across all vLLM versions. |
| [vLLM #18141](https://github.com/vllm-project/vllm/issues/18141) | Phi-4-reasoning-plus repeating-phrase loop with wrong reasoning parser. |

---

## GLM

GLM-4.7, GLM-5.1-FP8. Uses Jinja templates shipped in `examples/tool_chat_template_glm4.jinja`.

### Known bugs

| Issue | Summary |
|---|---|
| [vLLM #39614](https://github.com/vllm-project/vllm/issues/39614) | GLM-5.1-FP8 + `--chat-template-content-format auto`: tool result `{"type":"text","text":"..."}` hits else branch checking `.name` → renders `<tools>\n</tools>` instead of result. |
| [vLLM #39611](https://github.com/vllm-project/vllm/issues/39611) | Tool results ignored on `/v1/chat/completions` but work on `/v1/completions`. |

---

## Other tool families (shipped tool templates)

These all live in `examples/tool_chat_template_<name>.jinja`:

- `granite`, `granite_20b_fc` — IBM Granite
- `hermes` — Hermes-family (NousResearch)
- `hunyuan_a13b` — Tencent Hunyuan
- `internlm2_tool` — InternLM2
- `minimax_m1`, `mistral_parallel` — MiniMax
- `toolace` — ToolACE
- `xlam_llama`, `xlam_qwen` — Salesforce xLAM
- `functiongemma` — Gemma function-calling variant

Pair each with the matching `--tool-call-parser`. If unsure, check the vLLM docs page [`docs/features/tool_calling.md`](https://docs.vllm.ai/en/latest/features/tool_calling/) — per-family table is authoritative.

---

## Complete list of shipped tool templates

27 files in `examples/`:

**JSON-based:** `tool_chat_template_llama3.1_json.jinja`, `llama3.2_json.jinja`, `llama4_json.jinja`, `deepseekv3.jinja`, `deepseekv31.jinja`, `deepseekr1.jinja`, `mistral.jinja`, `mistral3.jinja`, `glm4.jinja`, `gemma4.jinja`

**Pythonic:** `llama3.2_pythonic.jinja`, `llama4_pythonic.jinja`, `gemma3_pythonic.jinja`

**Model-specific:** `granite.jinja`, `granite_20b_fc.jinja`, `hermes.jinja`, `hunyuan_a13b.jinja`, `internlm2_tool.jinja`, `minimax_m1.jinja`, `mistral_parallel.jinja`, `qwen3coder.jinja`, `toolace.jinja`, `xlam_llama.jinja`, `xlam_qwen.jinja`, `phi4_mini.jinja`, `functiongemma.jinja`
