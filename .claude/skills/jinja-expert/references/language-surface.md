# Jinja2 language surface

Dialect-neutral cheat sheet for statements, expressions, filters, tests,
globals, and whitespace rules. Applies to every Jinja deployment — chat
templates, Ansible `.j2` files, `values.yaml.j2` preprocessors, Flask
views, the lot. Where a construct is available only in one dialect (e.g.
`{% break %}` requires the `loopcontrols` extension, which is loaded in
the HF chat-template env but not guaranteed elsewhere), that's called
out inline.

For dialect-specific surface (the exact environment config, filters
added on top, sandbox rules), see:

- `chat-template/transformers-dialect.md` — HF `apply_chat_template`
- `ansible-dialect.md` — Ansible's Jinja additions
- `helm-and-jinja.md` — Jinja-around-Helm patterns

Authoritative upstream reference for core Jinja:
<https://jinja.palletsprojects.com/en/stable/templates/>.

---

## Table of contents

1. Statements
2. Expressions and operators
3. Filters (the ones that matter)
4. Tests
5. Globals
6. Whitespace control
7. Undefined values and defaults
8. Template inheritance (mostly irrelevant to chat templates)

---

## 1. Statements

### Control flow

```jinja
{% if cond %}...{% elif other %}...{% else %}...{% endif %}

{% for item in items %}
  {{ loop.index }}  {# 1-based #}
  {{ loop.index0 }} {# 0-based #}
  {{ loop.first }}  {# true on first iteration #}
  {{ loop.last }}   {# true on last iteration #}
  {{ loop.length }} {# total iterations #}
  {{ loop.previtem }} / {{ loop.nextitem }}
  {{ loop.cycle('a', 'b', 'c') }}
{% else %}
  {# runs if the sequence was empty #}
{% endfor %}
```

`{% break %}` and `{% continue %}` are available because `loopcontrols` is
loaded in the chat-template env. They do NOT work in generic Jinja unless the
host explicitly loads the extension.

### Binding

```jinja
{# expression form #}
{% set name = value %}

{# block form — captures the rendered body as a string #}
{% set greeting %}Hello, {{ name }}.{% endset %}

{# scoped binding #}
{% with x = 1, y = 2 %}
  {{ x + y }}
{% endwith %}
```

**Loop scoping gotcha**: variables set inside a `{% for %}` block do NOT
escape the block. This is the single most common footgun. See
`seven-failure-categories.md` §2 for the fix (`namespace()`).

### Macros

```jinja
{% macro input(name, value='', type='text') %}
  <input type="{{ type }}" name="{{ name }}" value="{{ value }}">
{% endmacro %}

{{ input('email', 'me@example.com') }}
```

Macros have a **local scope** — they can't see the calling template's
variables unless those variables are passed in explicitly. Imports
propagate with `{% from 'x.jinja' import mymacro with context %}`
(context) vs `... without context` (default).

### Call blocks

```jinja
{% macro render_tool_call(call) %}
  <tool_call name="{{ call.name }}">{{ caller() }}</tool_call>
{% endmacro %}

{% call render_tool_call(c) %}
  { "args": ... }
{% endcall %}
```

Rare in chat templates but occasionally useful for wrapping repeated structure.

### Raw

```jinja
{% raw %}{{ this_is_literal }}{% endraw %}
```

Use when the template itself needs to emit Jinja-like syntax.

### Includes, extends, imports

```jinja
{% include "header.j2" %}              {# shares context by default #}
{% include "header.j2" without context %}
{% import "macros.j2" as m %}          {# does NOT share context by default #}
{% from "macros.j2" import foo with context %}
{% extends "base.j2" %}                {# template inheritance; blocks override #}
```

**Chat templates are single-file.** Includes/extends/imports don't apply to
`chat_template.jinja` strings rendered via `apply_chat_template` — there's no
loader on the environment.

### Autoescape

```jinja
{% autoescape true %}...{% endautoescape %}
```

Chat templates run with autoescape **off** (Jinja default), which is correct
for emitting plaintext to a tokenizer. Do NOT turn it on — autoescaping
would emit `&lt;|im_start|&gt;` and corrupt tokenization.

---

## 2. Expressions and operators

- **Arithmetic**: `+ - * / // % **`
- **Comparison**: `== != < <= > >=`
- **Logical**: `and or not`
- **Containment**: `in`, `not in`
- **String concat**: `~` (preferred — coerces non-strings). `+` works only on
  homogeneous strings and breaks the moment one side is int or None.
- **Conditional**: `a if cond else b`
- **Attribute fallback**: `obj.foo` tries `obj.foo` first, then `obj["foo"]` —
  so dict access and attribute access look identical. This is a Jinja
  feature, not a Python one.
- **Subscripts and slicing**: `lst[0]`, `lst[1:3]`, `lst[::-1]` — full Python
  slice syntax.
- **Literals**: strings, numbers, lists `[1, 2]`, tuples `(1, 2)`,
  dicts `{"a": 1}`, sets `{1, 2, 3}`, booleans (lowercase `true`/`false`),
  `none`.

---

## 3. Filters (the ones that matter)

Jinja has ~50 built-in filters. These are the ones chat templates use all the
time; the rest are either HTML-specific (`escape`, `striptags`, `urlize`,
`xmlattr`) or general-purpose string/number manipulation available in the
Pallets docs as needed.

| Filter | What it does | Chat-template use |
|---|---|---|
| `tojson` | JSON-serialize (chat-template env overrides to `ensure_ascii=False`) | Serializing tool schemas, tool-call arguments, any structured payload |
| `default(value, true=false)` | Replace undefined; with `true` replaces any falsy | Optional fields: `{{ m.name \| default('unnamed') }}` |
| `length` (alias `count`) | Container length | Gating: `{% if tools \| length > 0 %}` |
| `lower` / `upper` / `title` / `capitalize` | Case changes | Role normalization |
| `trim` / `striptags` | Whitespace and tag stripping | Cleaning content |
| `replace(old, new)` | String replace | Escaping model-specific delimiters |
| `join(sep)` | Concatenate iterable | `{{ parts \| join('\n') }}` |
| `map(attribute='x')` / `map('filter_name')` | Extract / transform | `{{ messages \| map(attribute='role') \| list }}` |
| `selectattr('attr', 'test', arg)` / `rejectattr(...)` | Filter by attribute test | `{{ messages \| selectattr('role', 'equalto', 'tool') }}` |
| `select(test)` / `reject(test)` | Filter scalars by test | |
| `first` / `last` | Index 0 / -1 | `{% if messages \| first.role == 'system' %}` |
| `items` | Dict to `[(k, v)]` pairs | Iterating dicts in order |
| `string` / `int` / `float` | Type coercion | Ensuring expected type |
| `safe` | Mark as already-escaped | Irrelevant in chat templates (autoescape off) |

**Filter argument syntax**:
- `value | filter` — no args
- `value | filter(arg)` — positional
- `value | filter(key=arg)` — keyword
- Filters can be chained: `value | trim | lower | replace('_', '-')`

---

## 4. Tests

Used with `is` / `is not`:

```jinja
{% if x is defined %}...{% endif %}
{% if x is not none %}...{% endif %}
{% if x is string %}...{% elif x is sequence %}...{% endif %}
{% if x is mapping %}...{% endif %}
{% if x is iterable %}...{% endif %}
{% if n is number %}...{% endif %}
{% if m.role is eq 'user' %}...{% endif %}   {# or: m.role == 'user' #}
{% if x is in seq %}...{% endif %}            {# or: x in seq #}
```

**Order matters for `is string` vs `is sequence`**: Jinja strings satisfy
`is sequence` (they're iterable). Always test `is string` first, then
`is sequence and is not string`.

Full list: `boolean`, `callable`, `defined`, `divisibleby`, `eq` / `==` /
`equalto`, `even`, `false`, `filter`, `float`, `ge` / `>=`, `gt` / `>` /
`greaterthan`, `in`, `integer`, `iterable`, `le` / `<=`, `lower`, `lt` / `<` /
`lessthan`, `mapping`, `ne` / `!=`, `none`, `number`, `odd`, `sameas`,
`sequence`, `string`, `test`, `true`, `undefined`, `upper`.

---

## 5. Globals

Called as functions inside `{{ ... }}` or `{% set ... %}`:

- **`range(stop)`** / `range(start, stop[, step])` — integer range
- **`dict(**kwargs)`** — build a dict literal from kwargs
- **`namespace(**kwargs)`** — the only mutable object in Jinja. See
  `seven-failure-categories.md` §2.
- **`cycler('a', 'b', 'c')`** — stateful cycler; call `.next()` to advance.
  Rare in chat templates.
- **`joiner(sep=', ')`** — returns `sep` after first call, `''` on first.
  Useful for conditional separators; chat templates usually use `loop.first`
  instead.

**Chat-template additions** (injected by transformers):

- **`raise_exception(msg)`** — raises `jinja2.exceptions.TemplateError(msg)`.
  Idiomatic in `{% else %}` branches for unreachable cases.
- **`strftime_now(fmt)`** — `datetime.now().strftime(fmt)`. Non-deterministic,
  so freeze time in tests.

---

## 6. Whitespace control

The canonical chat-template environment sets:

```python
trim_blocks=True         # strip first newline AFTER a {% %} block
lstrip_blocks=True       # strip leading whitespace BEFORE a {% %} block (same line)
keep_trailing_newline=False  # drop the last \n of the template
```

Inline modifiers strip whitespace on the marked side, regardless of env
settings:

- `{%-` / `-%}` — strip before/after a statement tag (including newlines,
  not just same-line)
- `{{-` / `-}}` — strip before/after an expression

**Rule of thumb for chat templates**: whenever emitting structured tokenized
text (delimiters like `<|im_start|>`), use `{%-` and `-%}` aggressively.
A stray `\n` before `<|im_start|>` can shift tokenization from 1 token to 2,
and the model drifts. This is silent and catastrophic.

Compare:

```jinja
{# BUG: emits "\n<|im_start|>user\n..." — leading newline #}
{% for m in messages %}
<|im_start|>{{ m.role }}
{{ m.content }}
<|im_end|>
{% endfor %}

{# CORRECT: no leading newline #}
{%- for m in messages -%}
<|im_start|>{{ m.role }}
{{ m.content }}
<|im_end|>
{% endfor -%}
```

---

## 7. Undefined values and defaults

Jinja has four `Undefined` subclasses:

- **`Undefined`** (default): `{{ missing }}` renders as empty; `missing + 1`
  raises `UndefinedError`.
- **`ChainableUndefined`**: silent even through attribute chains
  (`missing.foo.bar` is still empty). Handy for optional deep structures.
- **`DebugUndefined`**: renders as `{{ missing }}` to reveal what's
  missing. Great for development.
- **`StrictUndefined`**: raises `UndefinedError` immediately on any access
  to `missing`. Strictest — use in tests.

The chat-template env uses the default `Undefined`, so `{{ messages[0].name }}`
on a message without `name` renders as empty rather than crashing. This is
load-bearing for defensive template idioms like
`{{ m.name | default('user') }}`.

**Patterns**:

```jinja
{{ x | default('fallback') }}              {# only replaces undefined #}
{{ x | default('fallback', true) }}        {# replaces any falsy (empty string, [], 0, None) #}
{% if x is defined and x %}                {# defined AND truthy #}
{% if x is defined and x is not none %}    {# defined, could be empty string/list #}
```

---

## 8. Template inheritance

Not used in single-file chat templates — no loader on the environment. Covered
here only for recognition when encountering it in other Jinja codebases (Flask,
Django-with-Jinja, Pelican).

```jinja
{# base.j2 #}
<html>
  <body>
    {% block content %}{% endblock %}
  </body>
</html>

{# child.j2 #}
{% extends "base.j2" %}
{% block content %}Hello, {{ name }}.{% endblock %}
```

`super()` inside a block calls the parent block's content. Scoped blocks
(`{% block foo scoped %}`) inherit outer-loop variables.

---

## See also

- `references/chat-template/transformers-dialect.md` — the exact env and what's injected
- `references/chat-template/seven-failure-categories.md` — real-world traps
- <https://jinja.palletsprojects.com/en/stable/templates/> — authoritative
