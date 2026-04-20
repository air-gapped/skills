# The transformers chat-template dialect

Every HuggingFace chat template is rendered through the exact same Python
Jinja2 environment. vLLM and sglang both delegate to
`tokenizer.apply_chat_template`, so what's described here is the complete,
canonical contract — nothing more, nothing less.

The source of truth is
`transformers/src/transformers/utils/chat_template_utils.py`. If this file
disagrees with that source code, trust the source code.

---

## Table of contents

1. The environment construction
2. What's loaded (and what's deliberately not)
3. Custom globals and filters
4. Variables injected at render time
5. Sandbox semantics
6. vLLM and sglang delegation paths
7. Divergent implementations (minja, minijinja)
8. Practical implications

---

## 1. The environment construction

```python
from jinja2.sandbox import ImmutableSandboxedEnvironment
import jinja2.ext

jinja_env = ImmutableSandboxedEnvironment(
    trim_blocks=True,
    lstrip_blocks=True,
    extensions=[AssistantTracker, jinja2.ext.loopcontrols],
)
jinja_env.filters["tojson"]          = tojson             # overridden
jinja_env.globals["raise_exception"] = raise_exception
jinja_env.globals["strftime_now"]    = strftime_now
```

- **`ImmutableSandboxedEnvironment`** — subclass of `SandboxedEnvironment`
  that additionally blocks mutation of any object the caller passed in.
- **`trim_blocks=True`** — the newline *after* a `{% %}` block is stripped.
- **`lstrip_blocks=True`** — leading whitespace *before* a `{% %}` block
  (same line) is stripped.
- **`keep_trailing_newline`** is not set, so the default `False` applies —
  the last `\n` of the template file is dropped.

Requires `jinja2 >= 3.1.0`. Any env that matches these four things
(`ImmutableSandboxedEnvironment`, `trim_blocks`, `lstrip_blocks`,
`keep_trailing_newline=False`) plus the three customizations below will
render identically.

---

## 2. What's loaded (and what's deliberately not)

### Loaded extensions

**`jinja2.ext.loopcontrols`** — enables `{% break %}` and `{% continue %}`.
Rare in templates, but legal.

**`AssistantTracker`** — a custom extension defined inline in
`chat_template_utils.py`. Adds one new statement tag,
`{% generation %}...{% endgeneration %}`, used only when
`return_assistant_tokens_mask=True` is passed to `apply_chat_template`.
Safe to ignore unless building assistant-token masks for training.

### NOT loaded

- **`jinja2.ext.do`** — so `{% do list.append(x) %}` does **not parse**.
  It's a syntax error, not a sandbox violation.
- **`jinja2.ext.i18n`** — so `{% trans %}` / `_(...)` don't exist.
- **`jinja2.ext.debug`** — so `{% debug %}` does **not parse** in the
  chat-template env (`TemplateSyntaxError: Encountered unknown tag 'debug'`).
  To use it for local development, build a parallel
  `ImmutableSandboxedEnvironment` with
  `extensions=[jinja2.ext.loopcontrols, 'jinja2.ext.debug']` and render
  there — never via `apply_chat_template` on a real tokenizer.

### What this means for writing templates

- Lists and dicts can't be mutated in place. Use `namespace()` to
  accumulate state, or build lists with filter chains (`| map`, `| join`,
  `| selectattr`).
- `{% trans %}` for localization is unavailable. Chat templates aren't
  localized anyway.
- `{% break %}` / `{% continue %}` work inside loops for early exit.

---

## 3. Custom globals and filters

### `tojson` (filter, overridden)

Default Jinja `tojson` HTML-escapes and uses `ensure_ascii=True`. The
transformers override does neither:

```python
def tojson(x, ensure_ascii=False, indent=None, separators=None, sort_keys=False):
    return json.dumps(x, ensure_ascii=ensure_ascii, indent=indent,
                      separators=separators, sort_keys=sort_keys)
```

**Why `ensure_ascii=False` matters**: tool-call arguments with non-Latin
characters (Chinese, Arabic, Cyrillic, emoji) would otherwise emit as
`\uXXXX` escape sequences. Models trained on real characters see an
out-of-distribution input when the template emits escapes. This is the
single most important customization transformers added.

Signature matches Python's `json.dumps` — `indent=2`,
`separators=(',', ': ')`, and `sort_keys=True` are all accepted.

### `raise_exception` (global)

```python
def raise_exception(message):
    raise jinja2.exceptions.TemplateError(message)
```

Usage inside a template:

```jinja
{% if message.role not in ['user', 'assistant', 'system', 'tool'] %}
  {{ raise_exception("Unknown role: " ~ message.role) }}
{% endif %}
```

The **idiomatic way to fail loudly from inside a template** — without it,
unreachable branches silently emit empty strings and the model sees
corrupted input.

Good places to use `raise_exception`:
- Unknown role in the message loop
- Multiple system messages when only one is supported
- Assistant turn with neither `content` nor `tool_calls`
- Tool message without a matching prior `tool_calls`
- Alternating-user-assistant requirement violated (Llama-2 era)

### `strftime_now` (global)

```python
def strftime_now(fmt):
    return datetime.now().strftime(fmt)
```

Used by models that embed "today's date" in the system prompt (Llama 3.1+
was one of the first). Non-deterministic — golden-fixture tests must
freeze time.

---

## 4. Variables injected at render time

`render_jinja_template` calls:

```python
compiled_template.render(
    messages=chat,
    tools=tool_schemas,
    documents=documents,
    add_generation_prompt=add_generation_prompt,
    **kwargs,
)
```

And `PreTrainedTokenizerBase.apply_chat_template` injects before calling:

- `**self.special_tokens_map` — one variable per special token type:
  `bos_token`, `eos_token`, `unk_token`, `sep_token`, `pad_token`,
  `cls_token`, `mask_token`, `additional_special_tokens`.
- `date_string = strftime_now("%d %B %Y")` as a pre-computed fallback for
  templates that use it directly rather than calling `strftime_now`.
- Anything else the caller passed as `chat_template_kwargs`.

### The full list of variables a chat template can expect

| Variable | Type | Meaning |
|---|---|---|
| `messages` | `list[dict]` | OpenAI-format messages |
| `tools` | `list[dict]` or None | Tool schemas (JSON-Schema function form) |
| `documents` | `list[dict]` or None | RAG-style documents (rare) |
| `add_generation_prompt` | `bool` | True for inference, False for training |
| `bos_token` | `str` | e.g. `<s>`, `<|begin_of_text|>` |
| `eos_token` | `str` | e.g. `</s>`, `<|eot_id|>` |
| `pad_token` | `str` | Often equal to `eos_token` (problematic) |
| `unk_token` | `str` | Rare in modern templates |
| `additional_special_tokens` | `list[str]` | Extra special tokens |
| `date_string` | `str` | Pre-formatted date |
| `enable_thinking` | `bool` | Reasoning models (Qwen3-Thinking) |
| ... | | Anything else the caller passed |

### `message` shape (what each dict looks like)

```python
{
    "role": "system" | "user" | "assistant" | "tool",
    "content": str | list[ContentPart] | None,
    # Optional, present on assistant turns with tool use:
    "tool_calls": [
        {
            "id": str,                 # optional — some callers omit it
            "type": "function",
            "function": {
                "name": str,
                "arguments": str | dict,  # SOMETIMES string, sometimes dict
            },
        },
        ...
    ],
    # Optional, present on role=tool messages:
    "tool_call_id": str,
    "name": str,
    # Optional, reasoning-model extensions:
    "reasoning": str,
    "reasoning_content": str,
}
```

Where `ContentPart` is `{"type": "text", "text": str}` or
`{"type": "image_url", "image_url": {...}}` or
`{"type": "input_audio", "input_audio": {...}}` — the OpenAI multimodal
content-part shapes.

---

## 5. Sandbox semantics

### What the sandbox blocks

`SandboxedEnvironment` (parent class) blocks:
- Access to any attribute starting with `_` or `__`. So
  `obj.__class__.__mro__` raises `SecurityError`. This closes the classic
  Python template escape
  (`().__class__.__bases__[0].__subclasses__()` → arbitrary code exec).

`ImmutableSandboxedEnvironment` additionally blocks mutation methods on:
- `list`: `append`, `clear`, `extend`, `insert`, `pop`, `remove`,
  `reverse`, `sort`
- `dict`: `clear`, `pop`, `popitem`, `setdefault`, `update`
- `set`: `add`, `clear`, `difference_update`, `discard`,
  `intersection_update`, `pop`, `remove`, `symmetric_difference_update`,
  `update`
- `collections.deque`: all mutation methods

Calling any of these inside a template raises
`jinja2.sandbox.SecurityError`, not a silent no-op.

### What the sandbox allows

- All **non-mutating** string, list, and dict methods: `.split`, `.strip`,
  `.replace`, `.lower`, `.upper`, `.startswith`, `.endswith`, `.find`,
  `.format`, `.join`, `.encode`, `.isdigit`, `.isalpha`, `.splitlines`,
  `.get`, `.keys`, `.values`, `.items`, `.copy`.
- Reading any non-underscore attribute.
- Constructing new objects via template syntax: `{'a': 1}`, `[1, 2]`,
  `(1, 2)`, `{1, 2}`.
- Calling any global, filter, or test registered on the env.

### Why the immutable variant

Chat templates run against the caller's **live** `messages` and `tools`
lists. If a template could `messages.append(...)` or `tools.clear()`, a
malicious `chat_template.jinja` shipped in a HuggingFace repo could
corrupt the calling program's state across the Jinja boundary. Immutable
sandbox is defense-in-depth against untrusted template files.

Practical consequence: the **only** way to accumulate state across
iterations is `namespace()`. Filter chains (`| selectattr | map | join`)
are the declarative alternative. Every real-world chat template that
tracks "did I emit a system prompt yet" uses one of these two patterns.

---

## 6. vLLM and sglang delegation paths

**vLLM**: `vllm/entrypoints/openai/serving_chat.py → apply_hf_chat_template`
calls `tokenizer.apply_chat_template(...)`. Same Python Jinja2 pipeline
as transformers.

**sglang**:
`python/sglang/srt/entrypoints/openai/serving_chat.py` imports `jinja2`
directly and calls `tokenizer.apply_chat_template(...)`. Same pipeline.
Catches `jinja2.TemplateError` explicitly.

### `/v1/chat/completions/render` (vLLM)

A CPU-only endpoint that renders the prompt but doesn't generate. Added
in vLLM PR #34551. Returns the exact prompt string the engine would send
to the model plus the token IDs. Useful because it answers the question
"what is the engine actually rendering?" without burning a GPU inference.

Audit tooling (including engine-render probes and CI drift checks) can
use this to compare a snapshot template's byte output against what the
live engine renders. Falls back to `/tokenize` + `/detokenize` on older
vLLM that lacks `/render`.

### `--trust-request-chat-template`

An opt-in vLLM flag that allows per-request `chat_template` in the
`ChatCompletionRequest` body. Off by default because a user-supplied
template is effectively arbitrary code execution against the model's
trust boundary (even sandboxed). When off, vLLM returns HTTP 400:
*"chat template is passed with request, but --trust-request-chat-template
is not set"*.

Pairs with `chat_template_kwargs` and `default_chat_template_kwargs` on
the server. Unlocks fast iteration during `tune` loops — candidate
templates can be tested per-request without writing to the filesystem
or restarting the engine.

---

## 7. Divergent implementations (minja, minijinja)

These are **not** in the Python serving path for transformers, vLLM, or
sglang — but they ARE in the C++ serving path for llama.cpp, and some
HuggingFace inference stacks (e.g., TGI) have used minijinja historically.
Know the divergences exist:

### minja (Google, C++, header-only)

- Used by: llama.cpp, GPT4All, Docker Model Runner.
- Written specifically to render HF chat templates from C++.
- Frequent source of cross-engine divergence — the template is valid
  Python Jinja2, minja implements slightly different semantics, and the
  engine's render diverges from the Python reference render.
- Common gaps: some filter edge cases, `tojson` with custom separators,
  specific `namespace()` scoping interactions.

### minijinja (Armin Ronacher, Rust)

- Separate from Pallets Jinja despite same author.
- Used by: some HF TGI versions, various Rust LLM serving stacks.
- Subset of Jinja; notable historical gaps around `loopcontrols`
  extension, `namespace()` edge cases, and filter argument handling.
- `examples/minijinja-cli` renders templates standalone for
  bisection.

### What this means for authoring

**For transformers/vLLM/sglang targets**, stick to the Python
dialect described here. When the target includes llama.cpp, add
explicit defensive patterns:

- **Avoid `isinstance(x, str)`** — not all implementations support it.
  Use Jinja tests: `x is string`.
- **Test with real engines before shipping.** Template correctness under
  Python Jinja does not guarantee correctness under minja or minijinja;
  the cheapest guard is a live-engine smoke test (send a canonical
  chat + tool-call fixture, compare token IDs or prompt text to the
  offline render).
- **Prefer filter chains over `namespace()` when possible** — filter
  chains are more portable across implementations.

---

## 8. Practical implications

When writing or debugging a chat template, these are the rules to
internalize:

1. **Variables the template can rely on**: the list in §4. Anything else
   must be guarded with `is defined`.
2. **What breaks vs what's fine**:
   - `{{ messages.append(...) }}` → `SecurityError`.
   - `{% do messages.append(...) %}` → syntax error (ext.do not loaded).
   - `{% set ns = namespace(x=0) %}{% set ns.x = ns.x + 1 %}` → fine.
   - `{{ messages | selectattr('role', 'eq', 'tool') | list }}` → fine.
3. **Whitespace**: `trim_blocks=True, lstrip_blocks=True` is built in.
   Use `{%-` / `-%}` aggressively anyway — they override env settings
   and give explicit control when emitting tokenized delimiters.
4. **Unknown roles or malformed messages**: call `raise_exception(...)`.
   Don't silently emit nothing.
5. **Non-ASCII in tool arguments**: `tojson` handles it because
   `ensure_ascii=False` is the default. Override only when necessary.
6. **Time**: `strftime_now(fmt)` is the injected path; `date_string` is
   pre-computed for convenience.
7. **Across Python Jinja, minja, minijinja**: parity is not guaranteed.
   For llama.cpp or HF TGI targets, test against the real engine.

---

## See also

- `../language-surface.md` — the Jinja language itself
- `seven-failure-categories.md` (sibling) — what goes wrong in practice
- `authoring-patterns.md` (sibling) — how to write templates that hold up
- [transformers source](https://github.com/huggingface/transformers/blob/main/src/transformers/utils/chat_template_utils.py)
- [Pallets sandbox docs](https://jinja.palletsprojects.com/en/stable/sandbox/)
