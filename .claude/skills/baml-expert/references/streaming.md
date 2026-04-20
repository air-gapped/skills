# Streaming — full reference

## Contents
- [Python API](#python-api) — sync, async, runtime options
- [Partial types](#partial-types) — `baml_client.partial_types`, numbers-not-partial rule
- [Semantic streaming attributes](#semantic-streaming-attributes) — `@stream.done`, `@stream.not_null`, `@stream.with_state`, transform table, when to use each
- [Cancellation](#cancellation) — `AbortController`, FastAPI disconnect pattern
- [Server-to-client patterns](#server-to-client-patterns) — NDJSON, SSE, WebSocket, React hooks
- [Reading collector data during streaming](#reading-collector-data-during-streaming)
- [Common pitfalls](#common-pitfalls)

BAML streams partial objects, not raw tokens. The generated client gives you a typed iterator that yields progressively-filled instances of your return class. When the stream completes, call `get_final_response()` for the validated full object.

This is a more useful abstraction than raw SSE for most UIs: you don't have to re-parse JSON on every delta, and you get typed fields as they become valid.

## Python API

### Sync

```python
from baml_client import b

stream = b.stream.ExtractResume(text)
for partial in stream:
    # partial is baml_client.partial_types.PartialResume
    # All fields are nullable by default; Streaming attributes change that
    render(partial)
final = stream.get_final_response()     # baml_client.types.Resume
```

### Async

```python
from baml_client.async_client import b

stream = b.stream.ExtractResume(text)
async for partial in stream:
    render(partial)
final = await stream.get_final_response()
```

### Runtime options on streaming calls

`baml_options=` is supported:

```python
stream = b.stream.ExtractResume(text, baml_options={
    "client": "openai/gpt-4o-mini",
    "collector": col,
    "abort_controller": ctl,
})
```

## Partial types

For every class `X` in `baml_client.types`, there's a mirror `PartialX` in `baml_client.partial_types` where every field is made nullable. Nested classes also become partial. If you need to narrow in app code, `hasattr`-like checks or `if partial.name is not None` are the idiomatic pattern.

**Numbers never stream partially.** `int`/`float` fields stay `None` until the final object. Don't render a "73% complete" progress bar from a number that's streaming in — render it from a separate streaming string.

## Semantic streaming attributes

These reshape how partial streaming behaves. Put them on fields (`@`) or whole types (`@@`).

| Attribute | Effect |
|---|---|
| `@stream.done` | Field only appears once complete. Default for numbers; opt-in for strings/objects. |
| `@stream.not_null` | Containing object isn't emitted until this field has a value. Crucial for discriminators. |
| `@stream.with_state` | Wraps value in `StreamState<T> { value: T, state: "incomplete" | "complete" }`. Perfect for per-field loading UI. |
| `@@stream.done` on a class | The whole class is atomic — appears only when fully complete. |

**Type transform table** — what the partial type looks like per annotation:

| BAML declaration | Partial type |
|---|---|
| `foo T` | `Optional[Partial[T]]` |
| `foo T @stream.done` | `Optional[T]` |
| `foo T @stream.not_null` | `Partial[T]` |
| `foo T @stream.done @stream.not_null` | `T` |
| `foo T @stream.with_state` | `StreamState[Optional[Partial[T]]]` |

### When to use each

- **`@stream.done`** for fields where partial values are misleading — e.g. a `percentage` string that reads weird mid-generation (`"99"` before `"99.5%"`).
- **`@stream.not_null`** on the discriminator of a union: `type: "error" | "success" @stream.not_null`. The UI shouldn't render anything until it knows which branch.
- **`@stream.with_state`** for per-field loading spinners: a `summary string @stream.with_state` gives you `summary.state == "incomplete"` for the spinner and `summary.value` for what's arrived.
- **`@@stream.done` on element types in lists**: `(OutputItem @stream.done)[]` — the list grows incrementally but each element is atomic. Great for chat-message lists, tool-call lists.

## Cancellation

Use an `AbortController`:

```python
from baml_py import AbortController

ctl = AbortController()
stream = b.stream.ExtractResume(text, baml_options={"abort_controller": ctl})

# In another task:
ctl.abort(reason="user cancelled")

# Catch in the consumer:
from baml_py.errors import BamlAbortError
try:
    async for partial in stream: render(partial)
except BamlAbortError as e:
    log.info("cancelled: %s", e.reason)
```

For FastAPI-style cancellation on disconnect, tie the abort to the request lifecycle:

```python
@app.post("/extract")
async def extract(req: Request):
    ctl = AbortController()
    async def gen():
        try:
            async for partial in b.stream.ExtractResume(req.text, baml_options={"abort_controller": ctl}):
                yield partial.model_dump_json() + "\n"
        except BamlAbortError:
            return
    async def on_disconnect():
        if await req.is_disconnected():
            ctl.abort(reason="client disconnect")
    # wire on_disconnect into a background task as appropriate
    return StreamingResponse(gen(), media_type="application/x-ndjson")
```

## Server-to-client patterns

Serving partials to a browser:
- **NDJSON** (one JSON object per line): simplest; works over HTTP streaming. `yield partial.model_dump_json() + "\n"`.
- **SSE** (`text/event-stream`): good if you need named events. Prefix each chunk with `data: ` and terminate with `\n\n`.
- **WebSocket**: when you need bidi (e.g. user can inject cancellation mid-stream without a separate HTTP route).

React/Next: BAML has a `typescript/react` generator that auto-emits `use<FunctionName>()` hooks handling the stream for you. If the colleague's project has `output_type "typescript/react"` it's already wired.

## Reading collector data during streaming

`Collector` captures per-SSE-response data too:

```python
col = Collector()
stream = b.stream.Fn(text, baml_options={"collector": col})
async for p in stream: ...
await stream.get_final_response()
for chunk in col.last.calls[-1].sse_responses():
    # each chunk is a provider-specific SSE event
    ...
```

Useful for debugging why the partial-parse pipeline produced the sequence it did.

## Common pitfalls

- **Numbers stream as `None` → final value.** If your UI renders a progress number it'll jump; design around that.
- **`@stream.not_null` on a field of a class that's itself `T[]`**: delays each array element until the field populates. Can look like "nothing happens" for a while — that's intentional. Add `@stream.with_state` on the array or an element if you want a visible spinner.
- **Sync streaming with a client whose `default_client_mode` is `"async"`** — the sync stream still works (always generated), but if you mix, import from the right module: `from baml_client import b` for sync, `from baml_client.async_client import b` for async.
- **`get_final_response()` can raise `BamlValidationError`** even after a full stream if the aggregate result didn't parse. Wrap it.
- **Partial classes aren't Pydantic `validate_strict`.** They allow nullable fields where the base class doesn't. Don't pass a partial where a validated `X` is expected; use `get_final_response()` first.
