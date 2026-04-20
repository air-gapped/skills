# Debugging and testing chat templates

A practical cheat sheet for when a template isn't doing what's expected.
Organized by failure mode: error class, silent wrong output, tokenization
drift, engine divergence.

---

## Table of contents

1. Error message cheat sheet
2. In-template debugging (`{% debug %}`, `DebugUndefined`)
3. Minimum reproduction strategy
4. Branch coverage
5. Parity testing (Python Jinja ⇄ transformers)
6. Engine-render bypass (Layer 2.5)
7. Full-pipeline live testing (Layer 4)

---

## 1. Error message cheat sheet

### `jinja2.exceptions.TemplateSyntaxError`

The template didn't parse. Fatal at compile time.

Common causes:
- `{% do ... %}` — `ext.do` is not loaded in the chat-template env.
- `{% trans %}` — `ext.i18n` is not loaded.
- Mismatched tags: `{% if %}...{% endfor %}` or unclosed blocks.
- Unknown filter: `{{ x | nonexistent_filter }}`.

The error message includes the line number and a snippet. Read it —
Jinja's parse errors are unusually good.

### `jinja2.exceptions.UndefinedError`

A variable was referenced but not set, and the template tried to use it in
a way that forces resolution (arithmetic, attribute chain, truthy-test that
reads subattrs).

Defense: `x is defined`, `x | default(...)`, or `StrictUndefined` to
catch these earlier in dev.

### `jinja2.exceptions.TemplateError`

Something called `raise_exception("msg")` from inside the template. The
message is whatever was passed. Treat this as "the template itself is
signaling what's wrong."

### `jinja2.sandbox.SecurityError`

A template tried to mutate a sandboxed object (`.append`, `.pop`,
`.update`, …) or access an unsafe attribute (`_private`, `__dunder__`).

Defense: `namespace()` for mutation; filter chains for transformation.
See `seven-failure-categories.md` §7.

### The silent wrong-output case

**No exception, but the rendered prompt is wrong.**

This is the nasty class. The usual suspects:

- **Loop-scope escape** (§2 of seven-failure-categories): `{% set x = ... %}`
  inside a loop doesn't persist. Fix: `namespace()`.
- **Content bifurcation** (§1): template stringified a list of content parts.
  Fix: `is string` / `is sequence` branches.
- **Whitespace drift** (§5): stray `\n` shifts tokenization. Fix: aggressive
  `{%- -%}`.

Diagnosing these requires rendering and reading the output byte-for-byte,
not just checking whether an exception fired.

---

## 2. In-template debugging

### `{% debug %}` (requires opt-in extension)

Dumps the current render context and the list of available filters/tests
to stdout. Comes from `jinja2.ext.debug` — which the chat-template env
does **not** load, so `{% debug %}` raises `TemplateSyntaxError:
Encountered unknown tag 'debug'` under `apply_chat_template`.

Workaround: render through a parallel dev env that adds the extension.

```python
env = ImmutableSandboxedEnvironment(
    trim_blocks=True, lstrip_blocks=True,
    extensions=['jinja2.ext.loopcontrols', 'jinja2.ext.debug'],
)
print(env.from_string(template_str).render(**ctx))
```

In that env, `{% debug %}` reveals immediately whether a variable is in
scope or shadowed. Do **not** commit `{% debug %}` to the shipped template
— it will break production rendering.

### `DebugUndefined`

When building a test environment, use `DebugUndefined` so that
missing variables render as `{{ foo }}` literal instead of empty strings:

```python
from jinja2 import DebugUndefined
from jinja2.sandbox import ImmutableSandboxedEnvironment

env = ImmutableSandboxedEnvironment(
    undefined=DebugUndefined,  # render missing as "{{ foo }}"
    trim_blocks=True,
    lstrip_blocks=True,
    extensions=['jinja2.ext.loopcontrols'],
)
```

Now `{{ messages[0].nonexistent }}` renders as `{{ messages[0].nonexistent }}`
in the output — visible, not silently empty.

### `StrictUndefined`

Even stricter — raises `UndefinedError` on any access to an undefined
variable. Use in tests to catch typos immediately:

```python
from jinja2 import StrictUndefined
env.undefined = StrictUndefined
```

### `find_undeclared_variables`

Inspect a template for references to undefined variables statically:

```python
from jinja2 import meta
ast = env.parse(template_source)
undeclared = meta.find_undeclared_variables(ast)
# → set of names referenced but not set inside the template
```

For chat templates this should return roughly
`{'messages', 'tools', 'add_generation_prompt', ...}` — i.e., just the
variables the caller injects. Anything else is probably a typo or a
missing `set`.

---

## 3. Minimum reproduction strategy

When a template misbehaves on real traffic and the cause isn't visible:

1. **Capture the exact messages list** that triggered the bug. Serialize
   to JSON.
2. **Render it through a standalone `ImmutableSandboxedEnvironment`** that
   matches the transformers config — bypassing the engine. If this
   reproduces, the bug is in the template or in the messages.
3. **Bisect on messages**: render with `[messages[0]]`, then
   `messages[:2]`, `messages[:3]`, … The first length that reproduces
   the bug identifies the triggering message.
4. **Bisect on fields within that message**: strip `tool_calls`, strip
   `content`, swap string for list. Narrow the specific field shape
   that triggers the bug.
5. **Bisect on template branches**: comment out `{% if %}` branches one
   at a time until the bug goes away. Identifies the problematic branch.

Doing this from scratch takes ~10 minutes per bug. Much faster than
reading a 300-line template top-to-bottom.

---

## 4. Branch coverage

A chat template is "correct" only for the message shapes tested against
it. Branch coverage answers: has every `{% if %}` / `{% elif %}` /
`{% for %}` branch been exercised across the fixture set?

### Conceptually

Instrument the Jinja environment to record which template AST nodes were
visited during each render. A branch that's never visited across the
full fixture catalog is either:
- dead code (remove it)
- an untested failure mode (add a fixture that hits it)

Either way, unvisited branches are a signal.

### A canonical fixture catalog

A good fixture catalog hits every branch of a well-written template.
The following set covers the shape variance seen in production chat
templates and is a useful starting point whether fixtures run
in pytest, a bespoke render harness, or inside a broader audit tool:

- `plain-chat` — single user → assistant round-trip
- `multi-turn-with-system` — system + multiple user/assistant rounds
- `tool-call` — assistant emits `tool_calls` with `arguments` as JSON string
- `tool-call-dict-args` — arguments as dict
- `tool-result` — full roundtrip with `role: tool` response
- `parallel-tool-calls` — multiple tool_calls in one assistant turn
- `list-content` — user message with `content=[{"type":"text",...}]`
- `empty-tool-calls` — assistant with `tool_calls: []` AND content
- `no-tools-but-tool-message` — history has tool messages, `tools` unset
- `thinking-on` / `thinking-off` — reasoning-model toggle

If a template has a branch none of these hit, either it handles a
shape that isn't a real concern (dead code, delete it) or a fixture is
missing.

---

## 5. Parity testing (Python Jinja ⇄ transformers)

The contract: rendering a template through a standalone
`ImmutableSandboxedEnvironment` (with the same config) must produce
byte-identical output to `transformers.apply_chat_template`.

### Why

If a standalone render harness diverges from what `apply_chat_template`
does, every verdict built on that harness is unreliable. The engine is
the ground truth; a harness that drifts from the engine silently turns
true positives into false negatives and back. Parity tests catch drift
before it lands.

### How

```python
# Minimal harness that matches transformers.apply_chat_template byte-for-byte:

import jinja2
from jinja2.sandbox import ImmutableSandboxedEnvironment
from transformers import AutoTokenizer

def render_ours(template_str, **kwargs):
    env = ImmutableSandboxedEnvironment(
        trim_blocks=True, lstrip_blocks=True,
        extensions=[jinja2.ext.loopcontrols],
    )
    env.globals["raise_exception"] = lambda msg: (_ for _ in ()).throw(
        jinja2.exceptions.TemplateError(msg))
    env.globals["strftime_now"] = lambda fmt: "2026-01-01"  # frozen
    env.filters["tojson"] = lambda x, **kw: json.dumps(
        x, ensure_ascii=False, **kw)
    return env.from_string(template_str).render(**kwargs)

def render_transformers(template_str, messages, **kwargs):
    tok = AutoTokenizer.from_pretrained("some-model")
    tok.chat_template = template_str
    return tok.apply_chat_template(messages, tokenize=False, **kwargs)

# assert render_ours(...) == render_transformers(...)
```

If they diverge, the divergence is a Layer 2 bug, not a template bug.

### Common causes of divergence

- Forgot the `loopcontrols` extension → `{% break %}` fails to compile.
- Default `tojson` → emits `\uXXXX` escapes, bytes don't match.
- Missing `raise_exception` or `strftime_now` → `UndefinedError`.
- Different `trim_blocks` / `lstrip_blocks` values → whitespace differs.
- Forgot to inject `bos_token`, `eos_token`, etc.

---

## 6. Engine-render bypass (Layer 2.5)

Even with perfect parity between a standalone Jinja env and transformers,
the engine might still render differently. Reasons:

- The engine has a different template loaded (version skew vs the
  snapshot under audit).
- The engine applies message-level preprocessing (list-content coercion,
  tool-args reformatting, BOS prepending) before rendering.

### The probe

vLLM exposes `/v1/chat/completions/render` (CPU-only endpoint). Ask the
engine what prompt *it* would render for a given `ChatRequest`:

```python
resp = httpx.post(
    f"{endpoint}/v1/chat/completions/render",
    json={"model": model, "messages": messages, "tools": tools, ...},
)
engine_rendered = resp.json()["prompt"]
```

Diff `engine_rendered` against the offline render byte-for-byte.

If they diverge, investigate which side is correct — usually the engine
has newer or preprocessed behavior (message-level coercion, tool-args
reformatting, BOS prepending) that the offline render doesn't
replicate. The engine is ground truth; the offline render should
converge on it.

### Fallback for older engines

Older vLLM / sglang don't have `/render`. Fall back to `/tokenize` +
`/detokenize`:

```python
tokens = httpx.post(f"{endpoint}/tokenize", json={"messages": messages}).json()["tokens"]
text = httpx.post(f"{endpoint}/detokenize", json={"tokens": tokens}).json()["text"]
```

Less clean (a round-trip through tokens), but works on almost every
vLLM/sglang version.

### Per-request `chat_template` override

For iterating on template fixes, pass a candidate template in the
request body. Requires the engine to be launched with
`--trust-request-chat-template`; without that flag vLLM returns HTTP 400:

```python
resp = httpx.post(
    f"{endpoint}/v1/chat/completions",
    json={
        "model": model,
        "messages": messages,
        "chat_template": candidate_template_string,  # <<< override
        ...
    },
)
```

No filesystem round-trips, no engine restart. Seconds per iteration.

---

## 7. Full-pipeline live testing — the bypass comparison

The ultimate test: does the model produce the expected output when the
template is used in anger? The **bypass comparison** technique:

For each fixture, run it twice:

1. **Chat path**: `POST /v1/chat/completions` with the original
   `messages`. The engine renders the template server-side.
2. **Completions path**: `POST /v1/completions` with the prompt
   manually rendered via an offline Jinja harness. The engine does
   NOT apply a template — it just completes from the prompt as-is.

Compare outcomes:

| Chat | Completions | Verdict |
|---|---|---|
| Pass | Pass | `PASS` (both work) |
| Fail | Pass | `TEMPLATE_BUG` — engine's template mangles input Layer 2 got right |
| Pass | Fail | `PARSER_BUG` — engine's response parser misreads correct output |
| Fail | Fail | `MODEL_LIMITATION` — neither path works; not a template bug |

The bypass comparison is self-calibrating: it reveals whether the
failure is fixable (template) or not (model).

### Deterministic defaults for Layer 4

Layer 4 requests set `seed=42`, `temperature=0.0`, `max_tokens=256`,
`include_reasoning=False`, and thread a per-run UUID as `cache_salt` to
defeat vLLM's prefix cache. Rationale: comparing behaviors across paths
and runs is only meaningful with stable sampling.

---

## Summary: when to use which

| Problem | Tool |
|---|---|
| Template doesn't parse | Read the `TemplateSyntaxError` message |
| Template raises at render | Read the error class: Security, Template, Undefined |
| Template renders wrong output, no error | Render through dev env with `ext.debug` + `{% debug %}`, or bisect on messages |
| Is my fixture catalog exhaustive? | Branch coverage |
| Am I rendering differently from transformers? | Parity test |
| Is the engine rendering differently from me? | `/render` bypass |
| Is this a template bug or a model limitation? | Layer 4 chat/completions bypass |

---

## See also

- `seven-failure-categories.md` (sibling) — what the bugs look like
- `transformers-dialect.md` (sibling) — the canonical env to match
- `openspec/specs/template-render-harness/spec.md` — formal spec
