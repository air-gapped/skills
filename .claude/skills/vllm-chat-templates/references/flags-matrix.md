# Flag-matrix quick lookup

Copy-paste recipes for the models that show up in issue-tracker traffic. Always cross-check against the model card and `model-families.md` for minimum commit SHAs.

## Contents

- [Qwen](#qwen) — Qwen3 dense/MoE, Qwen3-Coder (XML parser)
- [DeepSeek](#deepseek) — R1, V3-0324, V3.1, V3.2
- [GPT-OSS](#gpt-oss) — harmony + `/v1/responses`
- [Kimi-K2](#kimi-k2) — minimum HF revision pin
- [Llama-4](#llama-4) — pythonic preferred
- [Mistral — TWO formats](#mistral-two-formats) — HF vs mistral tokenizer mode
- [Gemma](#gemma) — Gemma-3 + Gemma-4
- [Phi-4](#phi-4) — mini vs reasoning parser pitfall
- [Thinking toggle at request time](#thinking-toggle-at-request-time-qwen3-kimi-k2-deepseek)
- [`skip_special_tokens=false` workaround](#skip-special-tokens-per-request-workaround)
- [`tool_choice` semantics](#tool-choice-semantics)

## Qwen

```bash
# Qwen3 dense / MoE / Instruct-2507
vllm serve Qwen/Qwen3-30B-A3B-Instruct-2507 \
  --tool-call-parser hermes \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice

# Qwen3-Coder (emits XML, not Hermes JSON)
vllm serve Qwen/Qwen3-Coder-480B-A35B-Instruct \
  --tool-call-parser qwen3_xml \
  --chat-template examples/tool_chat_template_qwen3coder.jinja \
  --enable-auto-tool-choice
```

## DeepSeek

```bash
# DeepSeek-R1-0528
vllm serve deepseek-ai/DeepSeek-R1-0528 \
  --chat-template examples/tool_chat_template_deepseekr1.jinja \
  --tool-call-parser deepseek_v3 \
  --reasoning-parser deepseek_r1 \
  --enable-auto-tool-choice

# DeepSeek-V3-0324
vllm serve deepseek-ai/DeepSeek-V3-0324 \
  --chat-template examples/tool_chat_template_deepseekv3.jinja \
  --tool-call-parser deepseek_v3 \
  --enable-auto-tool-choice

# DeepSeek-V3.1
vllm serve deepseek-ai/DeepSeek-V3.1 \
  --chat-template examples/tool_chat_template_deepseekv31.jinja \
  --tool-call-parser deepseek_v31 \
  --reasoning-parser deepseek_r1 \
  --enable-auto-tool-choice

# DeepSeek-V3.2
vllm serve deepseek-ai/DeepSeek-V3.2 \
  --tokenizer-mode deepseek_v32 \
  --tool-call-parser deepseek_v32 \
  --reasoning-parser deepseek_r1 \
  --enable-auto-tool-choice
```

## GPT-OSS

```bash
# Prefer /v1/responses endpoint — /v1/chat/completions tool calling is broken (#22578)
vllm serve openai/gpt-oss-120b \
  --tool-call-parser openai \
  --reasoning-parser gpt_oss

# Offline harmony vocab:
export TIKTOKEN_ENCODINGS_BASE=/path/to/tiktoken-cache
```

## Kimi-K2

```bash
# Pin minimum HF revision (see model-families.md)
vllm serve moonshotai/Kimi-K2-Instruct-0905 \
  --revision 94a4053eb8863059dd8afc00937f054e1365abbd \
  --tool-call-parser kimi_k2 \
  --reasoning-parser kimi_k2 \
  --enable-auto-tool-choice
```

## Llama-4

```bash
# Pythonic recommended over JSON
vllm serve meta-llama/Llama-4-Maverick-17B-128E-Instruct \
  --chat-template examples/tool_chat_template_llama4_pythonic.jinja \
  --tool-call-parser llama4_pythonic \
  --enable-auto-tool-choice
```

## Mistral — TWO formats

```bash
# Format 1: Mistral native (mistral-common)
# NOTE: --chat-template silently dropped here (#25401)
vllm serve mistralai/Mistral-Small-3.1-24B-Instruct-2503 \
  --tokenizer-mode mistral \
  --config-format mistral \
  --load-format mistral \
  --tool-call-parser mistral \
  --enable-auto-tool-choice

# Format 2: HF format
vllm serve mistralai/Mistral-Small-3.1-24B-Instruct-2503 \
  --tokenizer-mode hf \
  --config-format hf \
  --load-format hf \
  --chat-template examples/tool_chat_template_mistral_parallel.jinja \
  --tool-call-parser mistral \
  --enable-auto-tool-choice
```

## Gemma

```bash
# Gemma-3 — no native JSON tools, use pythonic
vllm serve google/gemma-3-27b-it \
  --chat-template examples/tool_chat_template_gemma3_pythonic.jinja \
  --tool-call-parser pythonic \
  --enable-auto-tool-choice

# Gemma-4 (workaround: skip_special_tokens=False for reasoning)
vllm serve google/gemma-4-31b-it \
  --chat-template examples/tool_chat_template_gemma4.jinja \
  --tool-call-parser gemma4 \
  --reasoning-parser gemma4 \
  --enable-auto-tool-choice
```

## Phi-4

```bash
# Phi-4-mini (tool-calling)
vllm serve microsoft/Phi-4-mini-instruct \
  --chat-template examples/tool_chat_template_phi4_mini.jinja \
  --tool-call-parser llama3_json \
  --enable-auto-tool-choice

# Phi-4-reasoning-plus
# DO NOT use --reasoning-parser deepseek_r1 (causes loops, #18141)
vllm serve microsoft/Phi-4-reasoning-plus
```

## Thinking toggle at request time (Qwen3, Kimi-K2, DeepSeek)

```python
from openai import OpenAI
c = OpenAI(base_url="http://localhost:8000/v1", api_key="EMPTY")
c.chat.completions.create(
    model="Qwen/Qwen3-30B-A3B-Instruct-2507",
    messages=[{"role": "user", "content": "compute 37 * 41"}],
    extra_body={
        "chat_template_kwargs": {"enable_thinking": True},
    },
)
```

## Skip-special-tokens per-request workaround

For Gemma-4 (#38855), Qwen3 reasoning, and gpt-oss harmony when special tokens get stripped before the parser sees them:

```python
extra_body={"skip_special_tokens": False}
```

## Tool-choice semantics

- `"auto"` — free-form output, regex parse. Brittle; fails on near-misses.
- `"required"` — structured-outputs FSM, always produces a tool call. Reliable.
- `{"type":"function","function":{"name":"foo"}}` — named tool, same FSM.

If `auto` fails and `required` works, the issue is usually the tool-call parser, not the template.
