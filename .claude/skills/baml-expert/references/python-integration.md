# Python integration — advanced

## Contents
- [Runtime client overrides (ClientRegistry)](#runtime-client-overrides-clientregistry) — add/override clients at runtime, precedence vs `baml_options["client"]`
- [TypeBuilder (dynamic classes/enums)](#typebuilder-dynamic-classesenums) — `@@dynamic` field injection
- [Observability — Collector](#observability--collector) — http_request/response, usage tracking, multi-collector, Bedrock quirk
- [Production tracing — Boundary Studio](#production-tracing--boundary-studio) — `BOUNDARY_API_KEY`, `@trace`
- [LLM-fixup pattern](#llm-fixup-pattern-retry-with-a-cheaper-model) — retry via smaller model
- [Error class hierarchy](#error-class-hierarchy)
- [Cancellation](#cancellation)

SKILL.md covers the common call patterns. Load this file when the task involves runtime client overrides, dynamic types, or observability.

## Runtime client overrides (`ClientRegistry`)

Use when you need to register entirely new clients at runtime — A/B tests, per-tenant routing, ad-hoc model swaps that aren't declared in `.baml` files. For one-off client name swaps, the `baml_options={"client": "openai/gpt-4o-mini"}` shorthand is simpler and doesn't need ClientRegistry.

```python
from baml_py import ClientRegistry                 # NOT from baml_client — easy to miss

cr = ClientRegistry()
cr.add_llm_client(name="Experimental", provider="openai", options={
    "model": "gpt-5-mini",
    "api_key": os.environ["OPENAI_API_KEY"],
    "temperature": 0.0,
})
cr.set_primary("Experimental")
resume = b.ExtractResume(text, baml_options={"client_registry": cr})
```

**Precedence**: `"client"` in `baml_options` overrides `"client_registry"` when both are set.

**Overriding existing named clients** (e.g. tighten a timeout):

```python
cr = ClientRegistry()
cr.override("GPT5Mini", options={"http": {"request_timeout_ms": 120000}})
b.Fn(text, baml_options={"client_registry": cr})
```

## TypeBuilder (dynamic classes/enums)

Fields marked `@@dynamic` in `.baml` let you inject runtime-discovered fields before the call:

```python
from baml_client.type_builder import TypeBuilder  # IS from baml_client (unlike ClientRegistry)

tb = TypeBuilder()
tb.Resume.add_property("gpa", tb.float().optional()).description("GPA if present")
tb.Seniority.add_value("PRINCIPAL")
resume = b.ExtractResume(text, baml_options={"tb": tb})
```

Common uses: user-configurable output schemas, A/B testing output shapes, domain-specific field additions without touching `.baml` sources.

## Observability — `Collector`

Canonical runtime inspection. Prefer over ad-hoc logging or parsing BAML_LOG output.

```python
from baml_py import Collector

col = Collector(name="resume-extraction")
resume = b.ExtractResume(text, baml_options={"collector": col})

col.last.id                                    # request ID
col.last.usage                                 # input_tokens, output_tokens, cached_input_tokens
col.last.raw_llm_response
col.last.calls[-1].http_request                # exact bytes sent to provider
col.last.calls[-1].http_response
col.last.calls[-1].sse_responses()             # streaming: per-event data
col.last.tags
col.usage                                      # aggregated across all calls on this collector
```

Multiple collectors per call supported: `baml_options={"collector": [a, b]}`.

Tags merge with parent `@trace` tags when wrapped.

**AWS Bedrock quirk**: does not report cached-token counts; `cached_input_tokens` reads null even when caching is active.

## Production tracing — Boundary Studio

Set `BOUNDARY_API_KEY=...` and traces ship automatically. Web UI: `studio.boundaryml.com`. `@trace` decorator wraps arbitrary Python functions for Studio visibility.

Note: Studio v1 at `app.boundaryml.com` deprecates end-of-March 2026 — migrate to v2.

## LLM-fixup pattern (retry with a cheaper model)

When parse fails intermittently, the official remedy is a fix-up BAML function:

```baml
function FixupResume(error_message: string) -> Resume {
  client CheapFallback
  prompt #"
    The previous extraction failed with this error:
    {{ error_message }}
    Produce a valid result.
    {{ ctx.output_format }}
  "#
}
```

```python
try:
    resume = b.ExtractResume(text)
except BamlValidationError as e:
    log.warning("parse failed", extra={"raw": e.raw_output, "prompt": e.prompt})
    resume = b.FixupResume(error_message=str(e))
```

Often a smaller/cheaper model succeeds where the primary failed, because SAP needs fewer conventions to recover a partial result.

## Error class hierarchy

```python
from baml_py.errors import (
    BamlError,                      # base
    BamlValidationError,            # parse/coercion failed — .prompt, .raw_output, .detailed_message
    BamlClientError,
    BamlClientHttpError,            # .status_code
    BamlClientFinishReasonError,
    BamlTimeoutError,               # .timeout_type, .elapsed_ms, .configured_value_ms
    BamlAbortError,                 # .reason
    BamlInvalidArgumentError,
)
```

`BamlValidationError.detailed_message` includes the parse attempt chain with reasons, not just the final error — essential for debugging SAP coercion issues.

## Cancellation

```python
from baml_py import AbortController

ctl = AbortController()
stream = b.stream.ExtractResume(text, baml_options={"abort_controller": ctl})
# later, from another task or on client disconnect:
ctl.abort(reason="user cancelled")
```

Consumer catches `BamlAbortError`. For FastAPI/Starlette disconnect-driven cancellation, see `references/streaming.md`.
