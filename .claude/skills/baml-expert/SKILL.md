---
name: baml-expert
description: BAML (Boundary ML) expert for projects defining LLM calls as typed functions in .baml files with a generated Python client. Use whenever the repo contains baml_src/, baml_client/, baml-cli commands, or imports from baml_py / baml_client. Covers .baml syntax (function, class, enum, client, test, retry_policy, attributes), Python integration (baml_client sync/async, streaming, ClientRegistry, Collector, TypeBuilder), Schema-Aligned Parsing, ctx.output_format, @@assert / @@check tests, @stream.done / @stream.not_null / @stream.with_state streaming, multimodal (image/audio/pdf), and debugging via BAML_LOG plus Boundary Studio. Trigger even when the user doesn't name BAML — if they ask to "add an LLM function", "fix a failing parse", "add a test for the prompt", "stream the response" in a project with baml_src/, this is the skill. Prefer this over raw LLM-SDK guidance in BAML projects.
---

# BAML expert

BAML = small DSL for typed LLM calls. Author `.baml` files in `baml_src/`, run `baml-cli generate`, get a typed Python package at `baml_client/`. The generated `b` object exposes each function as a typed method. BAML handles prompt rendering, HTTP, retries, fallbacks, streaming, and **Schema-Aligned Parsing (SAP)** — robust coercion of messy LLM output into typed objects.

Use this skill for any task touching `.baml` files, `baml_client`, or calls into it. Read the full repo layout first if unclear: the convention is `baml_src/*.baml` + generated `baml_client/` (gitignored; regenerated on every change).

## Mental model (critical)

```
baml_src/*.baml  ──baml-cli generate──▶  baml_client/   (Pydantic + async/sync client)
```

At call time, for each function:
1. Render the prompt (Minijinja).
2. Build HTTP request for the configured provider.
3. Apply retry / fallback / round-robin / timeout policy.
4. Parse raw output with **SAP** — tolerant of missing quotes, trailing commas, markdown fences, chain-of-thought preamble, fractions as floats, etc.
5. Return typed object OR raise a typed error (`BamlValidationError`, `BamlClientError`, `BamlTimeoutError`, `BamlAbortError`).

**Never edit `baml_client/`.** It regenerates. Edit `.baml` files and rerun `baml-cli generate`.

## Workflow for typical tasks

When the user asks for a change in a BAML project, do this:

1. **Read the BAML sources first.** `ls baml_src/`, then read the relevant `.baml` files. They're plain text, globally visible to each other, no imports needed.
2. **Check the generator config.** Open the file containing `generator` blocks (often `generators.baml` or `main.baml`). Note `output_type` (expect `python/pydantic`), `output_dir`, and `version`. The `version` must match the installed `baml-py` version exactly, or `generate` will fail without `--no-version-check`.
3. **Make the `.baml` change.** Follow the syntax rules below.
4. **Regenerate.** `baml-cli generate` (or `baml-cli generate --from <path-to-baml_src>` if not cwd). VSCode auto-regenerates on save if the extension is installed.
5. **Update the Python call site** if signatures changed.
6. **Add or update a test.** Tests live in `.baml` files as `test` blocks. Run with `baml-cli test -i '<FnName>::<TestName>'` or `baml-cli test` for all.

## Core `.baml` syntax

### Function

```baml
function ExtractResume(resume_text: string) -> Resume {
  client GPT5Mini                     // named client, or inline: client "openai/gpt-5-mini"
  prompt #"
    Extract info from this resume.

    {{ ctx.output_format }}            {# ALWAYS include — renders the return-type schema #}

    {{ _.role("user") }}
    {{ resume_text }}
  "#
}
```

Rules:
- Top-level names are **PascalCase by convention** (functions, classes, enums, clients, tests). The parser accepts other identifiers, but the codebase reads PascalCase everywhere — follow suit in new code.
- Function params use colons (`x: int`). **Class fields do not** (`name string`).
- `#"..."#` is the prompt literal; `##"..."##` when the body itself contains `#"`.
- `{{ ctx.output_format }}` is non-optional for structured outputs. Omitting it is the #1 newbie bug — the model doesn't know the shape and parse fails.

### Class / enum

```baml
class Education {
  school string
  degree string
  year int @description("Year of graduation")
}

enum Seniority {
  JUNIOR @description("0-2 years")
  MID
  SENIOR @alias("staff_engineer")   // how the LLM sees it
  STAFF @skip                        // hidden from prompt + parser
  @@alias("Level")                   // class/enum-level alias to the model
  @@dynamic                          // allow TypeBuilder additions at runtime
}

class Resume {
  name string
  skills string[]
  education Education[]
  seniority Seniority
  bio string?                        // optional
}
```

Hard rules:
- **No colon** between field name and type.
- **No inheritance** — compose via nested classes.
- **Optional arrays/maps ARE supported** (`string[]?`, `map<string, string>?` — added via #1251). Public docs at `fern/03-reference/baml/types.mdx` still incorrectly say "arrays cannot be optional"; trust the behavior. That said, prefer non-optional `T[]` + empty-list convention unless you specifically need to distinguish "missing" from "empty".
- Enum values start with a letter; no inline enum definitions.

### Types

- Primitives: `bool`, `int`, `float`, `string`, `null`.
- Optional: `T?`. Union: `T | U` — **order matters** (tries left-to-right; `int | string` parses `"1"` as int).
- List: `T[]`. Map: `map<K, V>` where K ∈ string / enum / literal string.
- Literals: `"red" | "green"`, `1 | 2 | 3`.
- Aliases: `type Graph = map<string, string[]>` (recursion ok via containers).
- Media: `image`, `audio`, `pdf`, `video` (keywords; can't name a var `image`).
- Not supported: `any`, `json`, `datetime`, tuples, sets. For dates use `string @description("ISO-8601")`.

### Attributes cheat sheet

Field-level (`@`):

| Attribute | Purpose |
|---|---|
| `@alias("x")` | Rename field in prompt + accept on parse |
| `@description("...")` | Description injected into schema (and `pydantic.Field(description=...)`) |
| `@skip` | Hide enum value from prompt + parser |
| `@assert(name?, {{ jinja }})` | Hard check — fails parse (element dropped in container) |
| `@check(name?, {{ jinja }})` | Soft check — surfaces in `Checked<T>` wrapper |
| `@stream.done` | Field only streams when complete |
| `@stream.not_null` | Parent only streams once this field has value |
| `@stream.with_state` | Wraps in `StreamState<T>` — has `value` + `state: "incomplete" | "complete"` |

Class/enum-level (`@@`): `@@alias`, `@@description`, `@@dynamic`, `@@assert`, `@@check`, `@@stream.done`.

### Client

Minimal shorthand (OpenAI defaults): `client "openai/gpt-5-mini"`. Named `client<llm> X { provider ... options { model ... api_key env.FOO ... } }` when you need retry policies, timeouts, headers, fallback, or round-robin. Providers: `openai`, `openai-responses`, `anthropic`, `google-ai`, `vertex-ai`, `aws-bedrock`, `azure`, `openai-generic` (vLLM/Ollama/OpenRouter/Together/Groq/LiteLLM/LMStudio), plus composite `fallback` and `round-robin`. Full syntax, retry policies, timeout MIN-wins composition, provider quirks → `references/providers.md`.

### Test

```baml
test BasicResume {
  functions [ExtractResume]
  args {
    resume_text #"
      John Doe
      Python, Rust
      UC Berkeley, B.S. CS, 2020
    "#
  }
  @@check(nonempty_name, {{ this.name|length > 0 }})
  @@assert({{ this.seniority == "JUNIOR" or this.seniority == "MID" }})
  @@assert({{ _.latency_ms < 30000 }})
}
```

Jinja in tests: `this` is the result. Also `_.result`, `_.checks.<name>`, `_.latency_ms`. Tests can target multiple functions that share a signature. See `references/testing.md` for full patterns, multimodal tests, TypeBuilder injection, CLI flags.

### Template string (reusable prompt fragment)

```baml
template_string PrintMessages(messages: Message[]) #"
  {% for m in messages %}
    {{ _.role(m.role) }}
    {{ m.content }}
  {% endfor %}
"#
```

## Prompts: Minijinja + BAML magic

- `{{ expr }}` output, `{% stmt %}` control flow, `{# comment #}`.
- **Always include `{{ ctx.output_format }}`** for structured output. It renders the return type as a compact schema tuned to survive in prompts better than JSON Schema.
- Tunable: `{{ ctx.output_format(prefix="Answer in JSON:", always_hoist_enums=true, or_splitter=" or ", hoist_classes="auto") }}`.
- `{{ ctx.client }}` → `{provider, model, name}` for provider-conditional prompting.
- `{{ _.role("user") }}` / `{{ _.role("system") }}` — split the prompt into messages. Default is a single `system` message (or `user` when images present).
- Role with metadata (Anthropic prompt caching): `{{ _.role("user", cache_control={"type": "ephemeral"}) }}` — requires `options { allowed_role_metadata ["cache_control"] }` on the client.
- Filters: standard Jinja plus `value|format(type="yaml" | "json" | "toon")` (BAML-aware serialization, respects aliases), `value|regex_match(pattern)`.
- String formatting: Python-style `.format()` (e.g. `"{:,}".format(1234567)`). `|format` is the serialization filter — don't confuse.

## Python integration

### Install + codegen

```bash
pip install baml-py
baml-cli init                     # first time: scaffolds baml_src/ + generators.baml
baml-cli generate                 # emits baml_client/
```

Wire into build: `npm run`-style task or `uv run baml-cli generate` in a pre-commit or justfile target. `baml_client/` should be in `.gitignore`.

### Call sites

```python
# Default: sync client (if generator has default_client_mode "sync")
from baml_client import b
from baml_client.types import Resume                         # Pydantic models live here

resume: Resume = b.ExtractResume("...resume text...")

# Async (always generated; import from async_client)
from baml_client.async_client import b as ab
resume = await ab.ExtractResume("...")

# Per-call overrides via baml_options (since 0.216)
resume = b.ExtractResume("...", baml_options={
    "client": "openai/gpt-4o-mini",   # override client just for this call
    "collector": my_collector,
    "tb": my_type_builder,
    "tags": {"req_id": "abc"},
    "abort_controller": controller,
})

# Reusable overrides
cheap_b = b.with_options(client="openai/gpt-4o-mini")
```

**Important import paths** — these are NOT in `baml_client`, they're in the SDK:

```python
from baml_py import Collector, ClientRegistry, AbortController
from baml_client.type_builder import TypeBuilder     # TypeBuilder IS from baml_client
```

### Streaming

```python
stream = b.stream.ExtractResume(text)                # sync generator, yields partial types
for partial in stream:
    # partial is PartialResume with optional fields; numbers arrive only at end
    render(partial)
final: Resume = stream.get_final_response()

# Async
async for partial in ab.stream.ExtractResume(text): ...
final = await ab.stream.ExtractResume(text).get_final_response()
```

Partial types live at `baml_client.partial_types`. Semantic streaming attributes (`@stream.done`, `@stream.not_null`, `@stream.with_state`) shape how partials arrive. See `references/streaming.md`.

### Multimodal

```python
from baml_py import Image, Audio, Pdf, Video

img = Image.from_url("https://...")                  # or from_base64("image/png", b64)
pdf = Pdf.from_base64("application/pdf", b64)        # PDFs: NO url form. Always base64.
result = b.DescribeImage(myImg=img)
```

In `.baml`, declare the param as `image` / `audio` / `pdf` / `video`.

### Error handling

```python
from baml_py.errors import BamlValidationError, BamlTimeoutError, BamlClientError

try:
    resume = b.ExtractResume(text)
except BamlValidationError as e:
    # e.prompt, e.raw_output, e.detailed_message available
    ...
```

Full error class hierarchy + the LLM-fixup retry pattern: `references/python-integration.md`.

### Advanced: ClientRegistry, TypeBuilder, Collector

For runtime client overrides (A/B tests, per-tenant routing), dynamic classes (`@@dynamic` runtime field injection), and observability via `Collector` (HTTP request/response inspection, usage tracking, Boundary Studio), see `references/python-integration.md`.

## Tests — first-class workflow

BAML tests are authoritative for regression-testing LLM functions. Run them before shipping prompt changes.

```bash
baml-cli test                              # all tests
baml-cli test -i 'ExtractResume::Basic*'   # glob
baml-cli test -x pattern                   # exclude
baml-cli test --parallel 8
baml-cli test --list                       # show without running
baml-cli test --dotenv-path .env.test
```

Exit codes: `0` pass, `1` fail, `2` human-eval-required, `3` cancelled, `4` no tests found.

Assertions inside tests:
- `@@check(name, {{ expr }})` — named soft check, result visible in report.
- `@@assert({{ expr }})` — hard assertion, fails the test.
- Jinja context: `this` / `_.result` (return value), `_.checks.<name>`, `_.latency_ms`.

See `references/testing.md` for multimodal inputs, `type_builder` in tests, templated args, and CI patterns.

## Debugging

1. **`BAML_LOG`** — set to `debug` for full request/response trace, `info` for per-call summary (default), `off` to silence.
   ```bash
   BAML_LOG=debug python my_script.py
   ```
2. **`BOUNDARY_MAX_LOG_CHUNK_CHARS=3000`** — truncate noisy payloads.
3. **VSCode playground** — Cursor/VSCode with Boundary extension shows rendered prompt and raw cURL for every test. Single most useful debug view. CodeLens "Open Playground" above each function.
4. **Collector** — inspect programmatically (see above). `.calls[-1].http_request` is the exact bytes sent.
5. **Boundary Studio** — `BOUNDARY_API_KEY` ships traces. Web UI at studio.boundaryml.com (v1 at app.boundaryml.com is deprecated end-of-March 2026).

When parse fails: read `BamlValidationError.detailed_message` — it includes the parse attempt chain with reasons, not just the final error.

## Most-common gotchas

Syntax rules covered above (class fields no colon, union order, optional arrays, `{{ ctx.output_format }}` required) — not repeated here. These are runtime/integration-only:

- **`baml_client/` is gitignored + generated.** Never edit. Regenerate after every `.baml` change.
- **Generator `version` must match installed `baml-py`.** Mismatch → `generate` fails unless `--no-version-check`. Pin them together.
- **Docs staleness**: public types page still claims "arrays cannot be optional" but optional lists/maps landed in #1251. Trust the code + CHANGELOG.
- **Env vars are lazy.** Missing `OPENAI_API_KEY` only errors at call time. `baml-cli test` auto-loads `.env` (0.214.0+); use `--dotenv-path` for alternates.
- **`ClientRegistry` is imported from `baml_py`**, not `baml_client`. Easy miss.
- **PDFs require base64.** No URL form, any provider.
- **Numbers never stream partially.** `int`/`float` fields are `null` until final.
- **Composite-client timeouts take the MIN** of parent + child. Long parent timeout doesn't loosen a strict child.
- **`o1` / `o1-mini`**: set `max_tokens null`, rely on `max_completion_tokens`. `openai-responses` doesn't support `o1-mini` — use `openai`.
- **Anthropic adapter**: only the first `system` message is used; subsequent `system` roles cast to `assistant`. Check raw cURL.
- **Media files in tests must live under `baml_src/`** — external paths won't resolve.

## When to go deeper

Load these references only when the task involves them:

- `references/providers.md` — full provider catalogue, provider-specific options, Anthropic prompt caching, AWS Bedrock, Vertex w/ Anthropic models.
- `references/streaming.md` — partial-type mechanics, `@stream.*` attribute truth table, cancellation patterns, FastAPI/async server integration.
- `references/testing.md` — multimodal test inputs, TypeBuilder in tests, template string args, glob/exclude, CI integration, `--require-human-eval`.
- `references/python-integration.md` — ClientRegistry, TypeBuilder, Collector, error class hierarchy, LLM-fixup pattern, cancellation.
- `references/cli.md` — `baml-cli init/generate/test/serve/dev/fmt/grep/describe/optimize/run` with all flags.
- `references/canary-features.md` — features new on canary / 0.221+ (lambdas, `?.`/`??`, `ns_*` namespaces, void returns, `baml run` VM, BEPs). Only relevant if working directly on the BAML repo itself.
- `references/sources.md` — dated index of official docs, spec URLs, PR references (for freshen audits).
