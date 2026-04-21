# Chat-template Jinja rendering contract

The environment transformers builds for `apply_chat_template`, the
globals it registers, and the semantics of `add_generation_prompt`
and `continue_final_message`. All pinned against
`src/transformers/utils/chat_template_utils.py` (v5.0.0+).

---

## The environment

`chat_template_utils.py:234`:

```python
jinja_env = ImmutableSandboxedEnvironment(
    trim_blocks=True,
    lstrip_blocks=True,
    extensions=[AssistantTracker, jinja2.ext.loopcontrols],
)
```

Import at line 16:

```python
from jinja2.sandbox import ImmutableSandboxedEnvironment
```

### ImmutableSandboxedEnvironment

Blocks all mutation of passed-in objects. Templates **cannot**:
- Call `.pop()`, `.append()`, `.__setitem__()` on `messages`, `tools`,
  etc.
- Assign to object attributes.
- Invoke disallowed built-in methods.

Consequence: template authors that need mutable scratch space must
create local variables with `{% set x = [] %}`.

### trim_blocks + lstrip_blocks

Both `True`. Whitespace around `{% ... %}` is aggressively trimmed:
- `trim_blocks`: first newline after a block tag is stripped
- `lstrip_blocks`: leading whitespace on the same line as `{%` is
  stripped

A template that relies on explicit newlines inside tags will render
differently than a naive Jinja env. Operators that try to re-render
a template outside transformers' apply_chat_template path must build
their env with these flags set.

### Extensions

1. **`AssistantTracker`** — internal class defined earlier in
   `chat_template_utils.py`. Records `(start_index, end_index)`
   character offsets of assistant-generated spans during rendering.
   Used by `return_assistant_tokens_mask=True` to build per-token
   assistant masks for training loss.

2. **`jinja2.ext.loopcontrols`** — enables `{% break %}` and
   `{% continue %}` inside loops. Several templates (Kimi, GLM, some
   Llama variants) use these. A stripped-down Jinja env missing the
   extension raises `TemplateSyntaxError: Encountered unknown tag
   'break'`.

---

## Registered globals and filters

Lines ~233–236:

```python
jinja_env.filters["tojson"] = tojson
jinja_env.globals["raise_exception"] = raise_exception
jinja_env.globals["strftime_now"] = strftime_now
```

### `tojson` filter

Defined at line 228 of `chat_template_utils.py`:

```python
def tojson(x, ensure_ascii=False, indent=None, separators=None, sort_keys=False):
    return json.dumps(x, ensure_ascii=ensure_ascii, indent=indent,
                      separators=separators, sort_keys=sort_keys)
```

**Critical difference from stdlib Jinja:**
- stdlib `jinja2.ext.tojson` defaults to `ensure_ascii=True`
- transformers `tojson` defaults to **`ensure_ascii=False`**

Templates that dump tool schemas containing CJK, emoji, or
combining characters rely on the transformers default. A preflight
tool that renders a template in a naive `ImmutableSandboxedEnvironment`
(without re-registering the `tojson` override) produces
HTML-escaped output the model never trained on.

### `raise_exception`

```python
def raise_exception(message):
    raise jinja2.exceptions.TemplateError(message)
```

Used defensively:

```jinja
{% if not tools %}
  {{ raise_exception("Tools required for this conversation") }}
{% endif %}
```

A preflight tool rendering a template will encounter
`TemplateError` if the model expects certain fields (tools,
documents, a specific role ordering) and the test fixture doesn't
provide them. That's not a bug — it's the template asserting its
contract.

### `strftime_now`

```python
def strftime_now(fmt):
    return datetime.now().strftime(fmt)
```

**Local time, not UTC.** `datetime.now()` returns naive local time.

Llama-3.1/3.2 templates inject a date stamp:

```jinja
{% set date_string = strftime_now("%d %b %Y") %}
```

Host TZ affects the rendered prompt. A container running in UTC
produces different prompts than a laptop in CET. A preflight tool
should note the TZ when comparing rendered outputs across runs.

Workaround (as-of 2026 — no transformers-side fix): patch the global
at render time if determinism needed.

---

## Compilation and caching

- `_compile_jinja_template` at `chat_template_utils.py:209`,
  `@lru_cache`-decorated. Memoized on the template source string.
- `_cached_compile_jinja_template` at line 214 — public cache
  wrapper.

A template string is compiled once per process. Preflight tools
that render many test fixtures against the same template benefit
from the cache automatically.

---

## `render_jinja_template` signature

`chat_template_utils.py:445`:

```python
def render_jinja_template(
    conversations: list[ChatType],
    tools: list[dict | Callable] | None = None,
    documents: ChatType | None = None,
    chat_template: str | None = None,
    return_assistant_tokens_mask: bool = False,
    continue_final_message: bool = False,
    add_generation_prompt: bool = False,
    **kwargs,
) -> str:
```

`**kwargs` is the path by which `chat_template_kwargs` (e.g.
`enable_thinking`, `reasoning_effort`) reach the template — they
become Jinja-context variables accessible as `{{ enable_thinking }}`.

---

## `add_generation_prompt` semantics

The flag is passed into the Jinja context as a boolean. Template
author branches on it:

```jinja
{% if add_generation_prompt %}
  {{ '<|assistant|>\n' }}
{% endif %}
```

**Nothing in transformers enforces this.** A template that ignores
`add_generation_prompt` will simply not emit the primer, and the
model's first generated token must then be the primer itself. This
is a common regression vector — a template refactor that drops the
flag check silently breaks generation.

**Preflight test:** render the template twice with
`add_generation_prompt=True` and `=False`, diff the outputs, assert
non-empty difference.

---

## `continue_final_message` semantics

Mutually exclusive with `add_generation_prompt`. When `True`:
- Template strips the trailing EOS / turn-close from the last
  assistant message
- Sampling resumes from the in-progress assistant text

Setting both flags True is an error raised by `apply_chat_template`.

---

## Template resolution order in `apply_chat_template`

`PreTrainedTokenizerBase.apply_chat_template` (on
`tokenization_utils_base.py`). Resolves template in order:

1. **Explicit `chat_template=` argument** — string Jinja, or a named
   template from `additional_chat_templates/`.
2. **`tokenizer.chat_template` attribute** — populated from
   `chat_template.jinja` sidecar file if present, else from
   `tokenizer_config.json["chat_template"]`.
3. **`additional_chat_templates/<name>.jinja`** — only when a named
   template is requested.

If none resolves: raises `ValueError("Cannot use chat template
functions because tokenizer.chat_template is not set and no template
argument was passed!")`.

---

## `chat_template.jinja` loading bugs

### Issue #45205 (open, transformers 5.5.0) {#gemma-4-issue-45205}

Affects `google/gemma-4-E2B-it`, `google/gemma-4-E4B-it`, Python 3.14.

Symptom: `AutoTokenizer.from_pretrained("google/gemma-4-E4B-it")`
loads the tokenizer, but `tokenizer.chat_template` is `None`
despite the repo shipping `chat_template.jinja`. Calling
`apply_chat_template` raises the "not set" ValueError.

Root cause: transformers' file-discovery logic for the chat template
sidecar has a gap in the Gemma-4 path.

Workaround:
```python
from huggingface_hub import hf_hub_download
template_path = hf_hub_download("google/gemma-4-E4B-it", "chat_template.jinja")
with open(template_path) as f:
    tokenizer.chat_template = f.read()
```

Open as of 2026-04-21.

### Issue #42914 (open, transformers 4.57.3)

With `HF_HUB_OFFLINE=1`, `AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-*")`
still tries to reach `huggingface.co/api/models/...` to resolve
`chat_template.jinja`. Plain `tokenizer_config.json` path honors
offline mode; the sidecar discovery does not.

BERT-era models unaffected (no separate jinja file). Opened
2025-12-16, still open as of 2026-04.

For air-gapped preflight:
- Pre-seed the cache during an online phase with an explicit
  `hf_hub_download(repo, "chat_template.jinja")`, OR
- Inline the chat template in `tokenizer_config.json` at snapshot
  time (copy the sidecar content into `tokenizer_config.json["chat_template"]`).

---

## `apply_chat_template` return shape

**v5 change:** returns `BatchEncoding` by default. Was `input_ids`
(list or tensor) in v4 by default. Per `MIGRATION_GUIDE_V5.md`:
*"apply_chat_template now returns a BatchEncoding to be consistent
with other tokenizer methods"*.

Code that does `tokenizer.apply_chat_template(...)[0]` to get the
first token ID breaks under v5 (now gets the `input_ids` key, not a
list). Use `tokenizer.apply_chat_template(..., return_tensors=None)["input_ids"]`
explicitly.

---

## Minimal rebuilt env (for preflight rendering)

If a preflight tool needs to render a template outside
`apply_chat_template` (e.g. to test multiple kwargs permutations
without reloading the tokenizer), rebuild the environment
faithfully:

```python
import json
import re
from datetime import datetime

import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment

def _tojson(x, ensure_ascii=False, indent=None, separators=None, sort_keys=False):
    return json.dumps(x, ensure_ascii=ensure_ascii, indent=indent,
                      separators=separators, sort_keys=sort_keys)

def _raise_exception(message):
    raise jinja2.exceptions.TemplateError(message)

def _strftime_now(fmt):
    return datetime.now().strftime(fmt)

def build_chat_template_env():
    env = ImmutableSandboxedEnvironment(
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=[jinja2.ext.loopcontrols],
    )
    env.filters["tojson"] = _tojson
    env.globals["raise_exception"] = _raise_exception
    env.globals["strftime_now"] = _strftime_now
    return env
```

Missing from this minimal rebuild: `AssistantTracker` — only
matters when rendering for training-time `return_assistant_tokens_mask`.
For preflight inspection, the minimal env suffices.

---

## Primary sources

- `src/transformers/utils/chat_template_utils.py:16, 209, 214,
  228-236, 445` — environment, globals, render entrypoint
- `src/transformers/tokenization_utils_base.py` — `apply_chat_template`
  method
- `src/transformers/utils/hub.py:30-32` — chat template file constants
- [Gemma-4 issue #45205](https://github.com/huggingface/transformers/issues/45205)
- [Offline chat_template issue #42914](https://github.com/huggingface/transformers/issues/42914)
- `MIGRATION_GUIDE_V5.md` — return-shape change
