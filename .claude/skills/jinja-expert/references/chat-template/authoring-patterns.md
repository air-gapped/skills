# Authoring patterns for chat templates

This reference is positive-space: *how* to write chat templates that hold up.
It complements `seven-failure-categories.md` (which is negative-space — what
goes wrong and how to fix it).

---

## Table of contents

1. The canonical skeleton
2. System message placement
3. The message loop
4. Content-format coercion idiom
5. Tool definitions and tool calls
6. Tool results
7. `add_generation_prompt` handling
8. Reasoning-model patterns
9. Raising exceptions
10. Putting it together — a minimal reference template

---

## 1. The canonical skeleton

Every modern chat template follows the same three-phase shape. Start from
this and fill in model-specific details:

```jinja
{#- Phase 1: optional preamble (BOS, tools, system extraction) -#}

{#- Phase 2: main message loop -#}
{%- for message in messages -%}
  ... one branch per role ...
{%- endfor -%}

{#- Phase 3: generation primer (inference only) -#}
{%- if add_generation_prompt -%}
  <|im_start|>assistant
{%- endif -%}
```

The three phases are a useful mental model. When debugging, ask "which phase
is wrong?" — preamble, loop, or primer.

---

## 2. System message placement

Most templates treat system as a single message at position 0. If the model
only supports one system message (the common case), extract it at the top:

```jinja
{%- if messages[0].role == 'system' -%}
  {%- set system_message = messages[0].content -%}
  {%- set loop_messages = messages[1:] -%}
{%- else -%}
  {%- set system_message = none -%}
  {%- set loop_messages = messages -%}
{%- endif -%}

{%- if system_message is not none -%}
  <|im_start|>system
  {{ system_message }}<|im_end|>
{%- endif -%}

{%- for message in loop_messages -%}
  {%- if message.role == 'system' -%}
    {{ raise_exception('Multiple system messages not supported') }}
  {%- endif -%}
  ... handle user/assistant/tool ...
{%- endfor -%}
```

This pattern:
- Extracts the first system message if present.
- Uses `raise_exception` to fail loudly on subsequent system messages.
- Handles absence of a system message (`system_message is not none`).

Some newer models support multiple or interleaved system messages — in which
case, fold the system branch into the main loop and skip the extraction.

---

## 3. The message loop

The main loop branches on `role`:

```jinja
{%- for message in loop_messages -%}
  {%- if message.role == 'user' -%}
    <|im_start|>user
    {{- render_content(message) -}}<|im_end|>
  {%- elif message.role == 'assistant' -%}
    <|im_start|>assistant
    {{- render_assistant(message) -}}<|im_end|>
  {%- elif message.role == 'tool' -%}
    <|im_start|>tool
    {{- render_tool_result(message) -}}<|im_end|>
  {%- else -%}
    {{ raise_exception("Unknown role: " ~ message.role) }}
  {%- endif -%}
{%- endfor -%}
```

Where `render_content`, `render_assistant`, `render_tool_result` are macros
or inline blocks handling the content-format coercion (§4 below).

**Notes**:
- Close every assistant turn with `<|im_end|>` (or the model's equivalent).
  This is what the model is trained to predict.
- Close every user and tool turn with `<|im_end|>` too, so the model learns
  to expect the turn boundary.
- Use `{%- -%}` on the `{% for %}` and branch tags to prevent stray newlines.

---

## 4. Content-format coercion idiom

`message.content` can be string, list of parts, or None. Handle all three:

```jinja
{%- macro render_content(message) -%}
  {%- if message.content is string -%}
    {{- message.content -}}
  {%- elif message.content is sequence and message.content is not string -%}
    {%- for part in message.content -%}
      {%- if part is mapping and part.type == 'text' -%}
        {{- part.text -}}
      {%- elif part is mapping and part.type == 'image_url' -%}
        {#- emit whatever multimodal placeholder the model expects -#}
        [image]
      {%- endif -%}
    {%- endfor -%}
  {%- elif message.content is none -%}
    {#- assistant with only tool_calls; emit nothing -#}
  {%- else -%}
    {#- defensive catch-all -#}
    {{- message.content | string -}}
  {%- endif -%}
{%- endmacro -%}
```

Key choices:
- Test `is string` first (strings are also sequences).
- Guard the `sequence` branch with `is not string`.
- Handle `None` explicitly; it's a legal shape for assistant-with-tool-calls.
- Catch-all prevents silent failure on unexpected shapes.

---

## 5. Tool definitions and tool calls

### Rendering the tools block (preamble)

When `tools` is non-empty, serialize the schema as part of the preamble:

```jinja
{%- if tools -%}
  <|im_start|>system
  Available tools:
  {% for tool in tools %}
    {{ tool | tojson }}
  {% endfor %}
  <|im_end|>
{%- endif -%}
```

Different models wrap tools in different markers (`<tools>`,
`<|tool_list_start|>`, `[AVAILABLE_TOOLS]`, …). Match the model's training
format exactly — this is one of the things that can't be abstracted.

### Rendering tool calls in assistant messages

```jinja
{%- macro render_assistant(message) -%}
  {%- if message.content -%}
    {{- render_content(message) -}}
  {%- endif -%}
  {%- if message.tool_calls -%}
    {%- for tool_call in message.tool_calls -%}
      {%- set args = tool_call.function.arguments -%}
      <tool_call>
        {"name": "{{ tool_call.function.name }}",
         "arguments": {{ args if args is string else args | tojson }}
         {%- if tool_call.get('id') -%}
         , "id": "{{ tool_call.id }}"
         {%- endif -%}
        }
      </tool_call>
    {%- endfor -%}
  {%- endif -%}
{%- endmacro -%}
```

Key choices:
- Emit `content` first if present; some assistant turns have both text and
  tool calls.
- `args if args is string else args | tojson` — handles both shapes of
  `arguments` without double-encoding.
- `tool_call.get('id')` — tolerant of missing `id`.
- The specific markup (`<tool_call>`, JSON format) is model-dependent; this
  is illustrative.

### Compact alternative: all-JSON tool-call emission

Many modern templates (Qwen3, Mistral v3+) just emit one JSON object per
tool call with no wrapper:

```jinja
{%- for tool_call in message.tool_calls -%}
  {%- set args = tool_call.function.arguments -%}
  {{ {
    'name': tool_call.function.name,
    'arguments': args if args is string else args | tojson,
    'id': tool_call.get('id', '')
  } | tojson }}
{%- endfor -%}
```

Works, and dodges the "what if `content` has quote chars" hand-JSON problem.

---

## 6. Tool results

Tool-result messages (`role == 'tool'`) carry a `tool_call_id` matching a
prior assistant `tool_call.id`. The template must:

1. Know which tool the result is for (via `tool_call_id`).
2. Emit the result in the model's expected format.
3. Tolerate missing `tool_call_id` if callers omit it.

Simple case (model just wants the content):

```jinja
{%- macro render_tool_result(message) -%}
  {%- if message.tool_call_id is defined -%}
    [tool_call_id: {{ message.tool_call_id }}]
  {%- endif -%}
  {{- render_content(message) -}}
{%- endmacro -%}
```

Complex case (model wants to know which tool produced the result). Scan
backward through `messages` to find the matching `tool_call`:

```jinja
{%- macro render_tool_result(message, all_messages, current_index) -%}
  {%- set ns = namespace(tool_name='') -%}
  {%- for prior in all_messages[:current_index] | reverse -%}
    {%- if prior.role == 'assistant' and prior.tool_calls -%}
      {%- for tc in prior.tool_calls -%}
        {%- if tc.get('id') == message.get('tool_call_id') -%}
          {%- set ns.tool_name = tc.function.name -%}
        {%- endif -%}
      {%- endfor -%}
    {%- endif -%}
  {%- endfor -%}
  <tool_response name="{{ ns.tool_name }}">
    {{- render_content(message) -}}
  </tool_response>
{%- endmacro -%}
```

Note the `namespace()` to carry `tool_name` out of the nested loops. Note
also: Jinja doesn't have `break`, so the reverse-scan runs to completion
rather than stopping at the match. Fine for conversation-length loops.

---

## 7. `add_generation_prompt` handling

**Right**:

```jinja
{#- ... entire message loop emitted above ... -#}

{%- if add_generation_prompt -%}
  <|im_start|>assistant
{%- endif -%}
```

- Read the flag at the top level, outside any macro or kwargs access.
- Emit the primer exactly once, after the message loop.
- No content after the primer.

**Wrong** (hardcoded):

```jinja
{#- ... message loop ... -#}
<|im_start|>assistant   {#- always emitted; breaks training -#}
```

**Wrong** (hidden in kwargs):

```jinja
{%- set add_gp = kwargs.get('add_generation_prompt', false) -%}
{%- if add_gp -%}  {#- vLLM AST can't see this; assumes false -#}
  ...
{%- endif -%}
```

---

## 8. Reasoning-model patterns

Reasoning models (DeepSeek-R1, Qwen3-Thinking, QwQ) introduce per-turn
reasoning blocks. Two orthogonal concerns:

### (a) Per-turn toggle

```jinja
{%- if add_generation_prompt -%}
  <|im_start|>assistant
  {%- if enable_thinking is defined and enable_thinking is false -%}
    <think>

    </think>

  {%- endif -%}
{%- endif -%}
```

Pre-closing the `<think>` block forces the model into non-thinking mode.

### (b) Reasoning preservation across turns

OpenAI messages may carry `reasoning` or `reasoning_content` fields:

```jinja
{%- set thinking_text = message.get('reasoning') or message.get('reasoning_content') -%}
{%- if thinking_text -%}
  <think>
  {{ thinking_text }}
  </think>
{%- endif -%}
```

Support both names — OpenAI's API uses `reasoning`, some clients use
`reasoning_content`.

**Common design choice**: strip prior-turn reasoning to bound context-window
cost. OpenAI's Responses API preserves it for chain-of-thought continuation.
Either is valid; document the choice.

---

## 9. Raising exceptions

Use `raise_exception` for any condition that should never happen if the
caller obeys the template's contract. This fails loudly instead of silently
emitting corrupted prompts.

Good targets:

```jinja
{#- Unknown role -#}
{% if message.role not in ['system', 'user', 'assistant', 'tool'] %}
  {{ raise_exception("Unknown role: " ~ message.role) }}
{% endif %}

{#- Multiple system messages when only one supported -#}
{% if loop.index0 > 0 and message.role == 'system' %}
  {{ raise_exception("Only one system message allowed") }}
{% endif %}

{#- Assistant with neither content nor tool_calls -#}
{% if message.role == 'assistant'
      and not message.content
      and not message.tool_calls %}
  {{ raise_exception("Empty assistant message") }}
{% endif %}

{#- Tool message without preceding assistant tool_calls -#}
{% if message.role == 'tool' and not ns.seen_tool_calls %}
  {{ raise_exception("Tool result without matching tool_calls") }}
{% endif %}

{#- Alternating user/assistant requirement (Llama 2 era) -#}
{% if message.role == 'user' and ns.last_role == 'user' %}
  {{ raise_exception("Alternating user/assistant roles required") }}
{% endif %}
```

`raise_exception` raises `jinja2.exceptions.TemplateError`. Upstream engines
(vLLM, sglang) catch this and return HTTP 400 with a useful message.

---

## 10. Putting it together

A minimal but complete reference template. Read this top to bottom; it
demonstrates every pattern above.

```jinja
{#- === Phase 1: preamble === -#}

{#- Tools block -#}
{%- if tools -%}
  <|im_start|>system
  Available tools:
  {% for tool in tools %}
  {{ tool | tojson }}
  {% endfor %}
  <|im_end|>
{%- endif -%}

{#- System message extraction -#}
{%- if messages and messages[0].role == 'system' -%}
  {%- set system_message = messages[0].content -%}
  {%- set loop_messages = messages[1:] -%}
{%- else -%}
  {%- set system_message = none -%}
  {%- set loop_messages = messages -%}
{%- endif -%}

{%- if system_message is not none -%}
  <|im_start|>system
  {%- if system_message is string -%}
    {{ system_message }}
  {%- else -%}
    {%- for part in system_message if part.type == 'text' -%}{{ part.text }}{%- endfor -%}
  {%- endif -%}
  <|im_end|>
{%- endif -%}

{#- === Phase 2: message loop === -#}

{%- set ns = namespace(last_role='') -%}

{%- for message in loop_messages -%}
  {%- if message.role == 'system' -%}
    {{ raise_exception("Only one system message supported") }}
  {%- elif message.role == 'user' -%}
    <|im_start|>user
    {%- if message.content is string -%}
      {{ message.content }}
    {%- elif message.content is sequence and message.content is not string -%}
      {%- for part in message.content if part.type == 'text' -%}{{ part.text }}{%- endfor -%}
    {%- endif -%}
    <|im_end|>
  {%- elif message.role == 'assistant' -%}
    <|im_start|>assistant
    {%- if message.content -%}
      {%- if message.content is string -%}{{ message.content }}{%- endif -%}
    {%- endif -%}
    {%- if message.tool_calls -%}
      {%- for tc in message.tool_calls -%}
        {%- set args = tc.function.arguments -%}
        <tool_call>{{ {'name': tc.function.name, 'arguments': args if args is string else args | tojson, 'id': tc.get('id', '')} | tojson }}</tool_call>
      {%- endfor -%}
    {%- endif -%}
    <|im_end|>
  {%- elif message.role == 'tool' -%}
    <|im_start|>tool
    {%- if message.tool_call_id is defined -%}
      [call_id={{ message.tool_call_id }}]
    {%- endif -%}
    {%- if message.content is string -%}
      {{ message.content }}
    {%- elif message.content is sequence and message.content is not string -%}
      {%- for part in message.content if part.type == 'text' -%}{{ part.text }}{%- endfor -%}
    {%- endif -%}
    <|im_end|>
  {%- else -%}
    {{ raise_exception("Unknown role: " ~ message.role) }}
  {%- endif -%}
  {%- set ns.last_role = message.role -%}
{%- endfor -%}

{#- === Phase 3: generation primer === -#}

{%- if add_generation_prompt -%}
  <|im_start|>assistant
{%- endif -%}
```

This template:
- Handles tools preamble conditionally.
- Extracts system message safely.
- Covers all four roles with explicit branches.
- Coerces string/list/None content consistently.
- Handles tool-call `arguments` in both shapes.
- Tolerates missing `tool_call.id`.
- Uses `namespace()` for cross-loop state.
- Calls `raise_exception` for unknown roles and duplicate systems.
- Emits the generation primer only when the flag is true.

Adapt model-specific delimiters (`<|im_start|>`, `<tool_call>`, etc.) to
match the target model's training format.

---

## See also

- `seven-failure-categories.md` (sibling) — the negative-space view
- `transformers-dialect.md` (sibling) — what's in scope
- `exemplars-and-antiexemplars.md` (sibling) — real templates to study
- `debugging-and-testing.md` (sibling) — verifying the template works
