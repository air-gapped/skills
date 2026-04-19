# Debugging chat-template problems

Load when nothing in the triage table fits, or when verifying before changing flags.

## Contents

- [Golden rule](#golden-rule)
- [Stepwise workflow](#stepwise-workflow) — log prompt, bypass vLLM, capture raw output, pin versions, check known bugs
- [Error-message catalog](#error-message-catalog)
- [Silent-misbehavior triage](#when-the-model-silently-misbehaves-no-exception) — `reasoning_content` null, empty `tool_calls`, wrong prompt, stateful breakage
- [Passing `chat_template_kwargs` correctly](#how-to-pass-chat_template_kwargs-correctly)
- [Verifying kwargs reach template](#verifying-the-kwarg-actually-reached-the-template)
- [Raw prompt dump without running inference](#raw-prompt-dump-without-running-inference)
- [Verifying tool template resolves](#verifying-a-tool-template-resolves-correctly)
- [Last resort — copy a known-good template](#last-resort-copy-a-known-good-template-and-edit)

## Golden rule

**Change one thing at a time.** Template, parser, and kwargs are three independent layers — mixing changes makes it impossible to know which fix worked.

## Stepwise workflow

### Step 1: Log the actual prompt

Enable prompt logging and compare byte-for-byte against the model card's example:

```
vllm serve --disable-log-requests=False --log-level DEBUG ...
```

In the OpenAI client, send a minimal request and `grep "prompt_token_ids\|prompt:"` the server log. If the rendered prompt lacks expected tokens (`<|im_start|>`, `<tool_call>`, `<think>`, chat-role delimiters), the chat template is the problem.

### Step 2: Bypass vLLM — reproduce with transformers alone

If the tokenizer itself produces wrong output, vLLM isn't to blame:

```python
from transformers import AutoTokenizer
t = AutoTokenizer.from_pretrained("the/model", revision="<sha>")
print(t.apply_chat_template(
    messages,
    tools=tools,                       # if applicable
    add_generation_prompt=True,
    tokenize=False,
    enable_thinking=True,              # if Qwen3
))
```

- Output matches the model card → tokenizer is fine, vLLM is dropping a kwarg. Check the allowlist (pattern #6).
- Output doesn't match the model card → tokenizer's shipped template is broken. Override with `--chat-template examples/tool_chat_template_<family>.jinja` or pin to a revision where it worked.

### Step 3: Capture raw model output

Disable all output parsing to see what the model actually emits:

```
vllm serve ...
# don't pass --tool-call-parser or --reasoning-parser
```

Then send a request and inspect `choices[0].message.content`. If the model:

- Emits `<think>...</think>` → use `--reasoning-parser` matching family.
- Emits `<tool_call>{...}</tool_call>` JSON → `--tool-call-parser hermes`.
- Emits `[{"name": ...}]` pythonic-style → `pythonic` / `llama4_pythonic`.
- Emits XML like `<tool_name>...</tool_name>` → `qwen3_xml` or model-specific.
- Emits nothing / repeats itself → template is wrong; model is seeing a malformed prompt.

### Step 4: Pin versions

Before filing a bug, record:

```bash
vllm --version
python -c "import transformers; print(transformers.__version__)"
python -c "import vllm; from vllm.model_executor.models import registry as r; print(r.ModelRegistry.get_supported_archs()[:3])"
# HF model revision — from .cache/huggingface/hub/... or huggingface-cli scan-cache
```

Many template bugs track a specific `tokenizer_config.json` commit. Mention revision SHA in issues.

### Step 5: Check known bugs

Before assuming a new issue, search the skill's `references/sources.md` for the model family. ~80% of reports match a known issue.

## Error-message catalog

Exact strings operators see, with meaning:

| Error | Meaning | Fix |
|---|---|---|
| `ChatTemplateResolutionError: "As of transformers v4.44, default chat template is no longer allowed..."` | Neither `--chat-template`, processor, nor tokenizer provided a template. | Supply `--chat-template <path>`. |
| `ValueError: "The supplied chat template ... appears path-like, but doesn't exist!"` | `--chat-template` path invalid. | `ls` the path; or use relative `examples/tool_chat_template_X.jinja`. |
| `ValueError: "Found unexpected chat template kwargs from request: {...}"` | Request passed reserved kwargs (`chat_template`, `tokenize`). | Remove from `extra_body`. |
| `ValueError: "Found more '<##IMAGE##>' placeholders in input prompt than actual multimodal data items."` | Template has more image placeholders than images in request. | Reduce placeholders or include more images. |
| `ValueError: "Missing 'type' field in multimodal part."` | Malformed content part. | Every `content` item needs `{"type": "..."}`. |
| `ValueError: "Mixing raw image and embedding inputs is not allowed"` | Request has both `image_url` and `image_embeds`. | Pick one. |
| `ValueError: "You must set \`--enable-mm-embeds\` to input \`image_embeds\`"` | Embeddings provided but flag missing. | Add `--enable-mm-embeds`. |
| `ValueError: "Cannot put tools in the first user message when there's no first user message!"` | Tool template injects into first user msg; none exists. | Prepend a user message. |
| `ValueError: "This model only supports single tool-calls at once!"` | Multiple tool calls in message but template is single-call. | Switch to parallel-tool template or send one at a time. |
| `HarmonyError: ...` (on gpt-oss) | `openai_harmony` vocab load failed. | Pre-download tiktoken; set `TIKTOKEN_ENCODINGS_BASE`. |
| Template renders `<tools>\n</tools>` instead of tool result | `--chat-template-content-format auto` misrouting. | Set content-format to `openai` or `string` explicitly; see GLM #39614. |
| Jinja `_try_extract_ast()` exception | `\n` escape double-converted. | Pass template file path, don't shell-interpolate string. |

## When the model silently misbehaves (no exception)

### Symptom: `reasoning_content` is `null`

Order of checks:

1. Is `--reasoning-parser <name>` set and matching the model family?
2. Is the model emitting `<think>...</think>` in raw output (step 3 above)?
3. Is the template **prepending** `<think>\n` before generation? → DeepSeek-R1 pattern. Opening tag never appears in output; parser sees only `</think>`.
4. Is `skip_special_tokens=true` stripping control tokens? Try `extra_body={"skip_special_tokens": false}`.

If 3 applies: newer vLLM versions' `deepseek_r1` parser handles the missing open tag. Upgrade.

### Symptom: `tool_calls` is empty but model clearly tried

1. Is `--tool-call-parser` right? Common mismatches:
   - Qwen3-Coder with `hermes` → wrong (use `qwen3_xml`).
   - Llama-4 with `hermes` → wrong (use `llama4_pythonic`).
   - Gemma-3 with `hermes` → wrong (use `pythonic`).
2. Is the template injecting `tools` at all? Dump prompt (step 1) and look for tool definitions.
3. Try `tool_choice="required"` or a named tool. If it works, the model emits tool calls but the `auto`-mode parser can't detect them — fall through to `required` or fix the template.
4. Multi-turn: is there a `tool_calls=[]` history item that crashes the template (Llama #13978)?

### Symptom: Prompt doesn't match model card

1. Check which template actually resolved — grep server startup log for "chat template". vLLM logs the path used.
2. Does the `--chat-template` path exist? If not, vLLM raises on some tokenizer modes, silently ignores on others.
3. Tokenizer mode: `--tokenizer-mode mistral` silently ignores `--chat-template` (#25401).
4. Multimodal: AutoProcessor template is skipped when `tools` is in request (intentional).

### Symptom: Works once, breaks on second request

1. Whitespace accumulation in template? DeepSeek V3.1 #28804.
2. Template is stateful and mutating global? Rare but happens — restart server between requests to confirm.
3. Concurrent load? Gemma-4 `<pad>` token bug #39392 — try `--max-num-seqs 1` to isolate.

## How to pass `chat_template_kwargs` correctly

The OpenAI Python client swallows unknown top-level kwargs. Use `extra_body`:

```python
response = client.chat.completions.create(
    model="Qwen/Qwen3-30B-A3B-Instruct-2507",
    messages=[{"role": "user", "content": "hi"}],
    extra_body={
        "chat_template_kwargs": {
            "enable_thinking": False,
        }
    },
)
```

Not:

```python
# WRONG — silently dropped by OpenAI client
response = client.chat.completions.create(
    ...,
    chat_template_kwargs={"enable_thinking": False},
)
```

## Verifying the kwarg actually reached the template

Write a throwaway Jinja template that emits the kwarg value:

```jinja
{%- if enable_thinking is defined -%}
  DEBUG: enable_thinking={{ enable_thinking }}
{%- endif -%}
...
```

Save as `/tmp/debug.jinja`, pass `--chat-template /tmp/debug.jinja`, fire a request, inspect server log for the rendered prompt. If `DEBUG:` line is missing, the kwarg got dropped.

## Raw-prompt dump without running inference

Use `scripts/render_template.py` (if present in the vLLM checkout) or run directly in Python:

```python
from vllm.transformers_utils.tokenizer import get_tokenizer
t = get_tokenizer("Qwen/Qwen3-30B", trust_remote_code=True)
print(t.apply_chat_template(
    [{"role":"user","content":"hi"}],
    tokenize=False, add_generation_prompt=True,
))
```

Use this to test chat-template overrides before starting a server.

## Verifying a tool template resolves correctly

After starting the server, one-off request:

```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "Qwen/Qwen3-30B",
    "messages": [{"role": "user", "content": "what time is it?"}],
    "tools": [{
      "type": "function",
      "function": {"name": "now", "description": "current time", "parameters": {"type": "object"}}
    }],
    "tool_choice": "required"
  }' | jq .
```

`tool_choice: "required"` forces a structured-output FSM — if the model still can't produce a tool call, the template isn't injecting tools at all.

## Last resort: copy a known-good template and edit

The `examples/tool_chat_template_*.jinja` files are maintained by model-family experts. For a near-sibling model (e.g. Llama-3.1 template applied to a Llama-3 finetune), copy the existing template, adjust the `bos_token` / `eos_token` / role tokens to match the target tokenizer, then test. Writing Jinja from scratch requires understanding how the family's native parser expects its output shaped — the chat template must match the parser's state machine, not the other way around.
