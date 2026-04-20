# The seven failure categories

These cover roughly 90% of real chat-template bugs. Each entry describes the
symptom, the underlying cause, the defensive idiom, and a pointer to a real
incident where it shipped.

---

## Table of contents

1. Content-format bifurcation
2. Loop-scope escape (`namespace()`)
3. `add_generation_prompt` bimodal
4. Tool-call shape variance
5. Whitespace control
6. Special-token doubling
7. Sandbox mutation attempts

---

## 1. Content-format bifurcation

### Symptom

Template renders as expected in development (content is a plain string), then
misbehaves in production when real traffic sends multimodal or tool-use
messages (content is a list of parts).

In the worst case, the template silently stringifies the Python list repr —
the model sees `[{'type': 'text', 'text': 'hi'}]` in its context window
instead of `hi`.

### Cause

The OpenAI `messages[].content` field can be:

- A plain string: `"hello"`
- A list of content parts: `[{"type": "text", "text": "hello"}, ...]`
- A list containing non-text parts (image_url, input_audio)
- `None` — for assistant messages that have only `tool_calls` and no text

Templates that do `{{ message.content }}` directly work for strings and
break silently for lists. Python's repr of a list is not what the model
should see.

### Defensive idiom

```jinja
{%- if message.content is string -%}
  {{ message.content }}
{%- elif message.content is sequence and message.content is not string -%}
  {%- for part in message.content -%}
    {%- if part is mapping and part.type == 'text' -%}
      {{ part.text }}
    {%- endif -%}
  {%- endfor -%}
{%- elif message.content is none -%}
  {#- assistant message with only tool_calls; emit nothing -#}
{%- else -%}
  {#- catch-all; either raise_exception or emit nothing -#}
{%- endif -%}
```

**Key points**:

- Test `is string` **first**. Jinja strings satisfy `is sequence` (they're
  iterable), so the order of tests matters.
- Test `is sequence and is not string` together to avoid iterating over
  the characters of a string by accident.
- Handle `None` explicitly — an assistant turn with `tool_calls` only has
  no content but isn't an error.
- Do **not** use `isinstance(x, str)`. Not all Jinja implementations
  (minja, minijinja) support `isinstance`. Use Jinja tests.

### Real-world incident

**GLM-5.1**: the original `chat_template.jinja` assumed string content.
When tool results came in as `[{"type": "text", "text": "..."}]`, the
template's tool-result branch iterated over the list looking for a
`.name` attribute on each part, found none, and silently emitted nothing.
The engine's `<tools>\n</tools>` block came out empty, the model saw no
tool result, and it hallucinated a response.

---

## 2. Loop-scope escape (`namespace()`)

### Symptom

A flag set inside a `{% for %}` loop reads back as the initial value
after the loop ends. Assignments inside the loop don't persist.

```jinja
{%- set has_system = false -%}
{%- for m in messages -%}
  {%- if m.role == 'system' -%}
    {%- set has_system = true -%}   {# this does NOT escape the loop #}
  {%- endif -%}
{%- endfor -%}
{%- if has_system -%}
  {# always false, even when a system message was present #}
{%- endif -%}
```

### Cause

Jinja is explicit about this in the docs: *"Loops create a scope. Variables
set inside loops do not persist after the loop ends."* This is by design —
it makes templates easier to reason about in the common case. But it's
the single most-hit footgun in chat templates.

### Defensive idiom — `namespace()`

```jinja
{%- set ns = namespace(has_system=false) -%}
{%- for m in messages -%}
  {%- if m.role == 'system' -%}
    {%- set ns.has_system = true -%}
  {%- endif -%}
{%- endfor -%}
{%- if ns.has_system -%}
  {# now correctly true when the loop saw a system message #}
{%- endif -%}
```

`namespace()` is a built-in Jinja global that returns a mutable object.
Attribute writes on it (`{% set ns.x = ... %}`) *do* escape enclosing
scopes. It's the only blessed mutation primitive in Jinja.

Multiple fields:

```jinja
{%- set ns = namespace(has_system=false, last_role='', counter=0) -%}
```

### Alternative: filter chain

When accumulating rather than computing a flag, filter chains are
often cleaner and more portable:

```jinja
{%- set system_msgs = messages | selectattr('role', 'equalto', 'system') | list -%}
{%- if system_msgs | length > 0 -%}
  {{ system_msgs[0].content }}
{%- endif -%}
```

### When to use which

| Pattern | When |
|---|---|
| `namespace()` | Complex per-iteration state, flags, counters, last-seen tracking |
| `messages | selectattr(...)` | Simple filtering; extract a subset of messages |
| `messages | map(attribute='role') | list` | Transformation across the list |

### Real-world incident

Essentially every chat template written by someone new to Jinja has this
bug at least once. The fix pattern is so standard that unsloth's
`chat_templates.py` registry includes `namespace()` usage in almost every
template it ships.

---

## 3. `add_generation_prompt` bimodal

### Symptom

One of two failure modes:

**(a) Training breaks**: The template always emits the assistant-role
primer (`<|im_start|>assistant\n`) regardless of flag. During training,
the assistant's own content is already in `messages[-1]`, so the model
sees `...assistant\n<|im_start|>assistant\n<actual content>` — the
primer gets loss-masked correctly, but now the model learns to predict
the content after a doubled primer. Model quality degrades subtly.

**(b) Engine can't detect the flag**: Template reads the flag via
`**kwargs` or from within a deep macro. vLLM's AST analysis of the
template can't tell whether `add_generation_prompt` is supported, so
it assumes not. Tool-calling accuracy drops dramatically.

### Cause

The flag is bimodal by design:

| Flag value | Who sets it | Template must |
|---|---|---|
| `True` (inference) | vLLM, sglang, chat completion clients | End with assistant-role primer; NO content |
| `False` (training/eval) | Training harness rendering full conversation | NOT emit the primer; final message's content is already in the loop |

Templates that hardcode the primer break training. Templates that hide the
flag read in a macro or kwarg confuse engine introspection.

### Defensive idiom

```jinja
{%- for m in messages -%}
  ... emit each turn, including closing <|im_end|> ...
{%- endfor -%}

{%- if add_generation_prompt -%}
  <|im_start|>assistant
{%- endif -%}
```

- `add_generation_prompt` is read at the top level, not inside a macro.
- The primer is emitted **outside** the message loop.
- No content after the primer when the flag is True.
- The final message's content is in the loop, so when the flag is False,
  nothing extra is added.

### Test procedure

Render the same messages twice with `add_generation_prompt=True` and `=False`
and diff:

- The True output must end exactly with the assistant primer (no content).
- The False output must **not** contain the primer.
- Everything before the primer must be byte-identical.

If any of those fail, the template has an `add_generation_prompt` bug.

### Real-world incidents

- **Phi-4 (original)**: hardcoded the assistant primer always. Training
  runs against the template produced misaligned models until Microsoft
  patched it.
- **Kimi K2 (v1)**: read `add_generation_prompt` via `kwargs` inside a
  conditional. vLLM's AST analysis couldn't detect the flag, defaulted
  to False, and tool-calling accuracy collapsed — reportedly 4.4× below
  what the model could do with a correct template. Fixed in a later
  Moonshot release.
- **DeepSeek-R1-0528**: hardcoded-on variant; Unsloth published a patched
  template.

---

## 4. Tool-call shape variance

### Symptom

Template crashes with `UndefinedError: 'id'` or produces malformed JSON
when some callers send tool calls with `arguments` as a dict versus a
JSON string.

### Cause

The OpenAI tool-call schema allows:

```python
message.tool_calls = [
    {
        "id": "call_abc123",        # OPTIONAL — some callers omit
        "type": "function",
        "function": {
            "name": "get_weather",
            "arguments": '{"city": "SF"}',  # or {"city": "SF"} — dict!
        },
    },
    ...
]
```

Two axes of variance:

- **`tool_call.id`** is optional. Some callers always set it; some omit
  it when there's only one tool call in the turn.
- **`tool_call.function.arguments`** is sometimes a JSON-encoded string
  (what OpenAI's API returns), sometimes a dict (what many Python
  clients pass before serialization).

Unguarded templates crash or double-encode.

### Defensive idiom — arguments

```jinja
{%- set args = tool_call.function.arguments -%}
{%- if args is string -%}
  {{ args }}
{%- elif args is mapping -%}
  {{ args | tojson }}
{%- else -%}
  {{ args | string }}
{%- endif -%}
```

Or the compact conditional form:

```jinja
{{ args if args is string else args | tojson }}
```

### Defensive idiom — id

```jinja
{%- set call_id = tool_call.get('id') or tool_call.id | default('') -%}
{%- if call_id -%}
  ...emit with id...
{%- else -%}
  ...emit without id...
{%- endif -%}
```

Or unconditionally with default:

```jinja
{{ tool_call.get('id', '') }}
```

### Real-world incident

**Kimi K2 (original)**: the template did `{{ tool_call['id'] }}` bare.
When internal callers sent tool calls without `id` (common for
single-call rounds where the id was unambiguous), the template raised
`UndefinedError`. Moonshot pushed a fix after users reported sporadic
500s from vLLM.

---

## 5. Whitespace control

### Symptom

Tokenization shifts. `tokenizer.encode("<|im_start|>user")` produces one
token count when rendered from the current template vs another count when
the model was trained. Output quality degrades from coherent to noticeably
worse without any code change.

### Cause

A stray newline before a special delimiter changes tokenization. Consider:

```
<|im_start|>user\n
```
vs
```
\n<|im_start|>user\n
```

These tokenize differently. The model was trained on the first form. A
template that emits the second puts every turn boundary 1 token "off"
from what the model expects. The effect is subtle — no errors, just
measurably degraded output.

### Defensive idiom

The env defaults handle common cases:

```python
trim_blocks=True         # strips newline AFTER {% %} block
lstrip_blocks=True       # strips leading whitespace BEFORE same-line {% %} block
```

But be explicit with inline modifiers anyway, because `{%- -%}` also
strips **across** newlines (not just same-line leading whitespace):

```jinja
{# BUG: emits "\n<|im_start|>user\n..." — the newline before the tag #}
{% for m in messages %}
<|im_start|>{{ m.role }}
{{ m.content }}
<|im_end|>
{% endfor %}

{# CORRECT: {%- eats the newline before <|im_start|> #}
{%- for m in messages -%}
<|im_start|>{{ m.role }}
{{ m.content }}
<|im_end|>
{% endfor -%}
```

### Rule of thumb

- Wrap every `{% %}` block that's on its own line with `{%-` and `-%}`.
- Inside `{{ }}`, use `{{-` and `-}}` only when strictly necessary to
  strip whitespace around a value.
- Test by tokenizing the rendered output with the target tokenizer and
  verifying the token count matches the expected training format.

### Real-world incident

This one is mostly a quality-degradation class rather than a discrete bug
— it rarely causes visible failures, just lower model performance. But
it's universal: virtually every chat template shipped by a model lab has
had at least one whitespace-control fix across its version history.

---

## 6. Special-token doubling

### Symptom

Tokenizer output has two BOS tokens in a row: `<BOS><BOS>...`. Model
drift, occasional weirdness at the start of conversations.

### Cause

BOS is emitted by **either** the tokenizer (when `add_bos_token=True`
in `tokenizer_config.json`) **or** the template (when it has
`{{ bos_token }}` at the top). Doing both → double BOS.

```jinja
{#- Template emits BOS at top: -#}
{{ bos_token }}
{%- for m in messages -%}
  ...
{%- endfor -%}
```

If the same tokenizer has `"add_bos_token": true` in its config, every
encode-the-rendered-prompt pipeline produces `<BOS><BOS>...`.

### Defensive idiom

**Decide which side owns BOS**, and stick to it. Most modern templates
include `{{ bos_token }}` explicitly and set `add_bos_token: false`.

Before adding `{{ bos_token }}` to a template:

1. Read the tokenizer config: `cat tokenizer_config.json | jq .add_bos_token`
2. If `true`: either remove `{{ bos_token }}` from the template, or set
   `add_bos_token: false` in the config. Pick one.
3. Test by encoding the rendered prompt with the target tokenizer and
   counting BOS tokens.

### Real-world incident

**Llama-2-Chat, Gemma-2-IT**: both shipped with `add_bos_token: true` in
`tokenizer_config.json` AND `{{ bos_token }}` in the template. Double BOS
on every conversation. Fixed in subsequent releases but tripped up many
downstream fine-tunes.

---

## 7. Sandbox mutation attempts

### Symptom

Template compiles fine, then raises `SecurityError: access to attribute
'append' of 'list' object is unsafe` at render time.

Or, if using `{% do %}` syntax, the template doesn't even parse:
`TemplateSyntaxError: Encountered unknown tag 'do'`.

### Cause

The chat-template env is `ImmutableSandboxedEnvironment`, which blocks
mutation methods on list/dict/set/deque. Additionally, `jinja2.ext.do`
is **not** loaded, so the `{% do %}` statement doesn't exist.

```jinja
{# SecurityError at render time: #}
{% set xs = [] %}
{% for m in messages %}
  {% set _ = xs.append(m.role) %}   {# .append blocked by immutable sandbox #}
{% endfor %}

{# TemplateSyntaxError at compile time: #}
{% do xs.append(m.role) %}            {# ext.do not loaded #}
```

### Defensive idiom

Use one of:

**`namespace()` for flags/counters:**

```jinja
{%- set ns = namespace(count=0) -%}
{%- for m in messages -%}
  {%- set ns.count = ns.count + 1 -%}
{%- endfor -%}
Total: {{ ns.count }}
```

**Filter chains for list/dict accumulation:**

```jinja
{%- set roles = messages | map(attribute='role') | list -%}
Roles: {{ roles | join(', ') }}
```

**String concatenation via namespace if the filter chain doesn't fit:**

```jinja
{%- set ns = namespace(buf='') -%}
{%- for part in message.content -%}
  {%- if part.type == 'text' -%}
    {%- set ns.buf = ns.buf ~ part.text -%}
  {%- endif -%}
{%- endfor -%}
{{ ns.buf }}
```

### Full list of blocked mutation methods

| Type | Blocked |
|---|---|
| `list` | `append`, `clear`, `extend`, `insert`, `pop`, `remove`, `reverse`, `sort` |
| `dict` | `clear`, `pop`, `popitem`, `setdefault`, `update` |
| `set` | `add`, `clear`, `difference_update`, `discard`, `intersection_update`, `pop`, `remove`, `symmetric_difference_update`, `update` |
| `deque` | all mutation methods |

Non-mutating methods are fine: `.get`, `.keys`, `.values`, `.items`,
`.index`, `.count`, `.copy`.

### Real-world context

This isn't so much a "ships in production" category as a "blocks the
template author immediately" category. The failure mode is loud
(`SecurityError` or `TemplateSyntaxError`), so it doesn't sneak past
review. But the fix is always the same: `namespace()` or filter chain.

---

## See also

- `references/chat-template/transformers-dialect.md` — the sandbox and what's loaded
- `references/chat-template/authoring-patterns.md` — positive idioms that avoid these traps
- `references/chat-template/debugging-and-testing.md` — how to catch these before shipping
- `references/chat-template/exemplars-and-antiexemplars.md` — broken templates annotated
  against these seven categories
