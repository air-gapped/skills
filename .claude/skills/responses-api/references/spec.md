# Responses API Specification

Source: OpenAI OpenAPI spec, OpenResponses spec (release 2026-04-24), Azure Foundry docs, OpenAI changelog through 2026-07-19.

## Contents
- [Endpoint](#endpoint) — POST /v1/responses and related endpoints
- [Request Schema](#request-schema) — required and optional fields
- [Input Item Types](#input-item-types) — message, function_call, function_call_output, reasoning
- [Response Object](#response-object) — complete JSON structure with usage
- [Output Item Types](#output-item-types) — message, function_call, reasoning, web_search, etc.
- [Tool Definitions](#tool-definitions) — function (flat), shell, tool_search, computer, web_search, file_search, code_interpreter, mcp
- [Conversation State](#conversation-state) — previous_response_id, Conversations API, client-side, compaction
- [Conversations API](#conversations-api) — /v1/conversations endpoint
- [Prompt Caching](#prompt-caching) — prompt_cache_key, prompt_cache_retention
- [Transport Modes](#transport-modes) — HTTP SSE vs WebSocket
- [Breaking Changes 2026](#breaking-changes-2026) — field renames and required-field flips
- [OpenResponses Specification](#openresponses-specification) — open standard differences

## Endpoint

`POST /v1/responses` — Create a model response

Additional endpoints:
- `GET /v1/responses/{id}` — Retrieve stored response
- `GET /v1/responses/{id}?stream=true&starting_after=<seq>` — Resumable streaming after dropped connection
- `DELETE /v1/responses/{id}` — Delete stored response
- `GET /v1/responses/{id}/input_items` — List input items
- `POST /v1/responses/compact` — Standalone one-shot compaction (accepts `model` + `input` or `previous_response_id`, returns compacted response)
- `POST /v1/conversations` — Create persistent conversation (see Conversations API below)
- `GET/DELETE /v1/conversations/{id}` — Manage conversation
- `GET /v1/conversations/{id}/items` — List conversation items

WebSocket transport (launched 2026-02-23): `wss://api.openai.com/v1/responses`.
60-minute connection cap, one in-flight request per socket. See Transport Modes.

## Request Schema

### Required fields
| Field | Type | Description |
|-------|------|-------------|
| `model` | `string` | Model ID |
| `input` | `string \| InputItem[]` | Text or array of typed input items |

### Optional fields
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `instructions` | `string?` | null | System message (NOT carried over via previous_response_id; billed every turn when chaining) |
| `previous_response_id` | `string?` | null | Chain to prior response for multi-turn |
| `conversation` | `string \| object?` | null | Conversation ID (`conv_...`) or object. Coexists with `previous_response_id`; no 30-day TTL |
| `stream` | `boolean?` | false | Enable SSE streaming (ignored on WebSocket transport) |
| `store` | `boolean?` | true | Persist for later retrieval (30 days). ZDR tenants auto-enforce `false` |
| `temperature` | `number?` | 1 | 0-2 |
| `top_p` | `number?` | 1 | 0-1 |
| `max_output_tokens` | `integer?` | null | Min 16 |
| `tools` | `Tool[]` | [] | Tool definitions |
| `tool_choice` | `string \| object` | "auto" | "none"/"auto"/"required"/specific |
| `parallel_tool_calls` | `boolean?` | true | Allow concurrent tools |
| `text` | `object?` | null | `{format: {type: "text"/"json_object"/"json_schema"}}` |
| `reasoning` | `object?` | null | `{effort: "none"/"low"/"medium"/"high"/"xhigh", generate_summary: "concise"/"detailed"/"auto"}`. `"none"` is default on gpt-5.2+ |
| `truncation` | `string?` | "disabled" | "auto" or "disabled" |
| `include` | `string[]?` | null | Extra data: `["reasoning.encrypted_content", "file_search_call.results", "web_search_call.results"]` |
| `metadata` | `object?` | {} | Up to 16 key-value pairs |
| `user` | `string?` | null | End-user ID |
| `service_tier` | `string?` | null | "auto"/"default"/"flex"/"priority" |
| `background` | `boolean` | false | Run asynchronously; retained ~10 min; NOT ZDR-compatible; poll via `GET /v1/responses/{id}` |
| `max_tool_calls` | `integer?` | null | Cap agentic loop iterations |
| `context_management` | `object[]?` | null | Server-side compaction: `[{type: "compaction", compact_threshold: <int>}]`. Min threshold 1000. Emits `compaction` output item when triggered |
| `prompt_cache_key` | `string?` | null | Routing stickiness for prefix cache. Combines with prefix hash |
| `prompt_cache_retention` | `string?` | "24h" (non-ZDR) | `"in_memory"` (5-60 min) or `"24h"`. **Default flipped to `"24h"` for non-ZDR orgs 2026-05-29** (was `"in_memory"`); ZDR orgs stay `"in_memory"`. 24h is pricing-neutral but ZDR-ineligible |
| `client_metadata` | `object?` | null | Free-form metadata; Codex CLI populates `installation_id`, `session_source` here |
| `moderation` | `object?` | null | Input/output moderation assessment (added 2026-06-04, also on Chat Completions) |

## Input Item Types (discriminated by `type`)

| Type | Role | Key Fields | Maps to Chat Completions |
|------|------|------------|--------------------------|
| `message` | user/system/developer/assistant | `content`, optional `phase` on assistant | `messages[]` |
| `function_call` | (replay previous) | `call_id`, `name`, `arguments` | `assistant` message with `tool_calls` |
| `function_call_output` | (tool result) | `call_id`, `output` | `tool` role message |
| `reasoning` | (replay reasoning) | `summary`, `content`, `encrypted_content` | `reasoning_content` field on assistant message |
| `computer_call_output` | (screenshot) | `call_id`, `output`, `acknowledged_safety_checks` | N/A |
| `item_reference` | (pointer) | `id` | N/A |
| `compaction` | (server-emitted) | opaque, encrypted — preserve between turns | N/A |

**Breaking (2026-03-25)**: `ResponseInputMessageItem.type` is REQUIRED.
Implicit-type messages now fail. Also: `InputAudio` removed from
`ResponseInputContent`.

**`phase` field** (added 2026-02-24, REQUIRED on gpt-5.3-codex+): on assistant
messages only, values `"commentary"` or `"final_answer"`. API rejects `phase`
on user messages. Dropping `phase` when replaying silently re-emits preambles
as final answers.

Content types for user messages: `input_text`, `input_image` (image_url +
detail), `input_file` (filename, file_data/file_url). Input files now accept
docs, presentations, spreadsheets, code, and plain text — not only PDFs
(2026-02-24).

## Response Object

```json
{
  "id": "resp_...",
  "object": "response",
  "created_at": 1741476777,
  "status": "completed",       // "completed" | "failed" | "in_progress" | "incomplete"
  "error": null,
  "incomplete_details": null,  // {reason: "max_output_tokens" | "content_filter"}
  "model": "gpt-4o-2024-08-06",
  "output": [...],             // OutputItem[]
  "output_text": "...",        // convenience: aggregated text
  "usage": {
    "input_tokens": 328,
    "input_tokens_details": {"cached_tokens": 0},
    "output_tokens": 52,
    "output_tokens_details": {"reasoning_tokens": 0},
    "total_tokens": 380
  },
  // All request params echoed back:
  "instructions": null, "previous_response_id": null,
  "metadata": {}, "temperature": 1.0, "top_p": 1.0,
  "max_output_tokens": null, "tools": [], "tool_choice": "auto",
  "parallel_tool_calls": true, "truncation": "disabled",
  "store": true, "reasoning": null, "text": null, "user": null
}
```

## Output Item Types (discriminated by `type`)

### `message`
```json
{"type": "message", "id": "msg_...", "role": "assistant", "status": "completed",
 "content": [{"type": "output_text", "text": "Hello!", "annotations": [...]}]}
```

### `function_call`
```json
{"type": "function_call", "id": "fc_...", "call_id": "call_abc123",
 "name": "get_weather", "arguments": "{\"location\":\"SF\"}", "status": "completed"}
```

### `reasoning`
```json
{"type": "reasoning", "id": "rs_...", "status": "completed",
 "summary": [{"type": "summary_text", "text": "Analyzing..."}]}
```

### `web_search_call`
```json
{"type": "web_search_call", "id": "ws_...", "status": "completed"}
```

### `file_search_call`
```json
{"type": "file_search_call", "id": "fs_...", "status": "completed",
 "queries": ["query"], "results": [{file_id, text, filename, score}]}
```

### `computer_call`
```json
{"type": "computer_call", "id": "cu_...", "call_id": "call_...",
 "action": {/* click/type/screenshot/scroll */, "keys": ["ctrl"]},
 "status": "completed"}
```

GPT-5.4+ may batch actions in an `actions[]` array. `keys` array (added
2026-03-17) carries held modifier keys for click/double_click/drag/move/scroll.

### `shell_call` + `shell_call_output` (added 2026-02-10)
```json
{"type": "shell_call", "id": "sh_...", "call_id": "call_...",
 "command": "...", "status": "completed"}
{"type": "shell_call_output", "call_id": "call_...",
 "output": "stdout...", "exit_code": 0}
```

### `tool_search_call` + `tool_search_output` (added 2026-03-05, gpt-5.4+)
```json
{"type": "tool_search_call", "id": "ts_...", "query": "...",
 "status": "completed"}
{"type": "tool_search_output", "id": "tso_...",
 "tools": [/* resolved tools */], "status": "completed"}
```

### `compaction` (server-emitted, added 2026-02-10)
Opaque encrypted item emitted inline in stream when
`context_management.compact_threshold` is crossed. Preserve between turns via
`previous_response_id` or include in next `input` array. Drop items preceding
the most recent compaction when chaining stateless.

### `output_video` (Sora, added 2026-03-12)
Video output item with generated content reference.

### `mcp_approval_request` + `mcp_approval_response`
Surfaces when an MCP call requires approval (see MCP tool `require_approval`).
Clients reply with an `mcp_approval_response` input item.

Additional types: `code_interpreter_call`, `image_generation_call`, `mcp_call`,
`mcp_list_tools`, `custom_tool_call`.

## Tool Definitions

### function (note: flat, NOT nested like Chat Completions)
```json
{"type": "function", "name": "get_weather",
 "description": "Get weather", "parameters": {...}, "strict": true,
 "defer_loading": false}
```

`defer_loading: true` (gpt-5.4+) registers a function without loading its
schema into context until `tool_search` resolves it. Use with large tool sets.

### web_search / web_search_preview
```json
{"type": "web_search_preview",
 "user_location": {"type": "approximate", "city": "SF", "region": "CA", "country": "US"},
 "search_context_size": "medium"}
```

`return_token_budget` (added 2026-05-11) allows longer web search runs.
Web search returns image results alongside text since 2026-06-09.

### file_search
```json
{"type": "file_search", "vector_store_ids": ["vs_..."],
 "max_num_results": 10, "ranking_options": {"ranker": "auto", "score_threshold": 0.0}}
```

### code_interpreter
```json
{"type": "code_interpreter", "container": {"type": "auto", "file_ids": ["file-1"]}}
```

### computer (GA 2026-03-05)
```json
{"type": "computer", "display_width": 1280, "display_height": 800, "environment": "browser"}
```

GA rename from `computer_use_preview`. openai-python 2.26 moved `ComputerTool`
class to GA target; preview moved to `ComputerUsePreview`. Code pinning to the
old class name breaks.

### shell (added 2026-02-10)
```json
{"type": "shell",
 "environment": {"type": "container_auto",
                 "skills": [{"type": "skill_reference", "skill_id": "skill_..."}],
                 "network_policy": {"type": "allowlist", "allowed_domains": ["github.com"]},
                 "file_ids": ["file-1"]}}
```

Debian 12 container with Python 3.11, Node 22, Java 17, Go 1.23, Ruby 3.1.
`skills[]` attaches via three kinds: `skill_reference` (stored skill), curated,
or `inline` (SKILL.md = YAML front-matter name/description + instruction body).
Skills are NOT a top-level tool type — attach inside `shell.environment.skills`.

### tool_search (added 2026-03-05, gpt-5.4+)
```json
{"type": "tool_search", "execution": "server",
 "description": "Search for matching tools",
 "parameters": {"type": "object", "properties": {...}}}
```

`execution: "server"` or `"client"`. Combine with `defer_loading: true` on
large function sets to keep context small.

### mcp (remote or OpenAI-hosted connector)
```json
{"type": "mcp",
 "server_label": "my-server",
 "server_description": "GitHub issues",
 "server_url": "https://mcp.example.com",
 "connector_id": "connector_gmail",
 "authorization": "Bearer OAUTH_TOKEN",
 "headers": {"X-Custom": "value"},
 "allowed_tools": ["tool1"],
 "require_approval": "never",
 "defer_loading": false}
```

**Fields:**
- `server_url` for remote/custom MCP; `connector_id` for OpenAI-hosted connector
  (8 first-party: Dropbox, Gmail, Google Calendar, Google Drive, MS Teams,
  Outlook Calendar, Outlook Email, SharePoint).
- `authorization`: OAuth bearer token. **NOT stored server-side** — resend on
  every request.
- `headers`: also **NOT stored** — resend every request.
- `require_approval`: `"always"` | `"never"` | `{always: {tool_names: [...]}}`
  | `{never: {tool_names: [...]}}`. **BUG**: empty `{never: {tool_names: []}}`
  silently disables ALL approvals — use string `"always"` when the exempt list
  is empty (community 1368778, llama-stack #3443).
- Azure OpenAI makes the outbound MCP call directly from the Azure service over
  the public internet (not from the customer tenant).

## Conversation State

Three options now (as of 2026):

**Server-side via `previous_response_id`** (original): Set `store: true`, pass
`previous_response_id`. Server concatenates `prev.input + prev.output +
new_input`. Instructions NOT carried over — re-send each turn, billed every
time. 30-day TTL.

**Server-side via `conversation`** (Conversations API): Pass `conversation:
"conv_..."`. Items survive across sessions/devices. **No 30-day TTL.** See
Conversations API section below.

**Client-side**: Accumulate `response.output` items, append to next `input`.
Works with `store: false`. Required for ZDR tenants. Must include
`reasoning.encrypted_content` items in the replayed input or GPT-5 quality
drops ~3% on SWE-bench.

**Compaction** (added 2026-02-10): opt-in server-side summarization that emits
a single opaque `compaction` output item when context exceeds
`context_management.compact_threshold`. Works with `store: false` — ZDR-friendly.
Drop items preceding the most recent compaction item when chaining stateless.

## Conversations API

Added 2026. Parallel to `previous_response_id` — both billing-equivalent.

```
POST   /v1/conversations                 -> returns {"id": "conv_..."}
GET    /v1/conversations/{id}
DELETE /v1/conversations/{id}
GET    /v1/conversations/{id}/items
```

To use: pass `conversation: "conv_..."` on `POST /v1/responses` (instead of or
alongside `previous_response_id`). Internally both expand to full history.
Difference: Conversations have no 30-day TTL; `store: true` responses default
to 30-day TTL.

**Assistants API migration mapping** (sunset 2026-08-26):
- Assistants → Prompts (dashboard objects, stable ID in source control)
- Threads → Conversations
- Runs → Responses

OpenAI explicitly states it will **not** provide an automated thread migration
tool — only a Python sample.

## Prompt Caching

Responses API benefits more than Chat Completions from caching because raw
chain-of-thought persists between turns via `previous_response_id` /
`conversation`. Chat Completions discards reasoning tokens entirely on the
next turn, so caching can't help.

Fields:
- `prompt_cache_key: string` — routing stickiness. Combines with prefix hash.
- `prompt_cache_retention: "in_memory" | "24h"` — default `"24h"` for non-ZDR
  orgs since 2026-05-29 (previously `"in_memory"`). Pricing-neutral but 24h is
  ZDR-ineligible.

Reporting:
- `usage.input_tokens_details.cached_tokens` — hit count.
- `usage.input_tokens_details.cache_write_tokens` — tokens written to cache.

Practical numbers (OpenAI-reported):
- 40-80% better hit rate vs Chat Completions
- 60% → 87% customer uplift after adding `prompt_cache_key`
- Flex processing through Responses: +8.5% hit rate vs Batch
- ~15 req/min per (prefix + `prompt_cache_key`) shard before cache-cold overflow

No `cache_salt` field exists. `store: true + previous_response_id` does NOT
guarantee prefix-hit — caching is best-effort, routing is key-driven.

**Stability tips:**
- Never mutate `tools` array mid-session — use `allowed_tools` to narrow.
- Compaction and summarization invalidate cache prefix.

## Transport Modes

### HTTP with SSE (default)
All endpoints above. Stream via `"stream": true` on `POST /v1/responses`.
Resumable after dropped connection:
```
GET /v1/responses/{id}?stream=true&starting_after=<sequence_number>
```

### WebSocket (added 2026-02-23)
`wss://api.openai.com/v1/responses`. Same event model as SSE. Limits:
- 60-minute connection cap
- Sequential only (one in-flight request per socket)
- `stream` and `background` flags ignored (WS is always streaming)
- Optional warm-up: `{"generate": false}` frame
- Send `response.create` frames; receive named events
- Connection-local `previous_response_id` state — proxies without sticky
  routing break multi-turn tool calls on reconnect (CLIProxyAPI #2596).

## Breaking Changes 2026

- **2026-03-05**: `computer_use_preview` → `computer` (GA). openai-python 2.26
  moved `ComputerTool` class to target the GA tool; former preview moved to
  `ComputerUsePreview`.
- **2026-03-25**: `ResponseInputMessageItem.type` is now REQUIRED. Implicit-type
  messages fail.
- **2026-03-25**: `InputAudio` removed from `ResponseInputContent`.
- **Ongoing, gpt-5.3-codex+**: `phase` field required on assistant messages.
  Dropping it silently degrades preamble quality.
- **2026-08-26**: Assistants API sunsets. Migrate to Prompts + Conversations +
  Responses.

## OpenResponses Specification

Open standard at https://www.openresponses.org/ (latest spec release
**2026-04-24**; releases are date-versioned — v2.3.0 was the 2026-04-17-era
label). The 2026-04-24 release pulled **WebSocket transport, the `phase`
field, and optional `logprobs`** into the open spec (previously
OpenAI-proprietary). Apache-2.0. Backers: NVIDIA, Vercel, OpenRouter,
HuggingFace, LM Studio, Databricks, Red Hat, Ollama, OpenAI, vLLM, Llama
Stack, **AWS** (joined 2026-04-13).

Governance: TSC = Core Maintainers + Lead. Majority vote (50% quorum), 2/3 for
charter amendments, 75% to remove Lead. No single vendor may control a majority.

**Deliberately minimal scope.** The OpenResponses OpenAPI has NO MCP,
computer-use, compact, conversations, image-generation, code-interpreter, or
audio schemas. Everything beyond text/reasoning/function-calls is
OpenAI-proprietary behind provider-prefixed types.

Key additions over OpenAI's API:
- Raw reasoning traces via `response.reasoning.{delta,done}` (events), with
  raw `content`, `encrypted_content`, and `summary` all formalized as distinct
  fields. OpenAI uses `response.reasoning_summary_text.{delta,done}` for
  summaries only (plus optional `response.reasoning_text.{delta,done}` in some
  OpenResponses-compatible backends).
- Provider-specific item types with prefixed `type` values (e.g.,
  `openai:web_search_call`, `acme:trace_event`). Custom items require `id`,
  `type`, `status`. Custom events require `type`, `sequence_number`.
- Tool split: externally-hosted (developer-executed) vs internally-hosted
  (provider-executed).
- `OpenResponses-Version: latest` request header.
- Stateless by default.
- Compliance runner (6 categories: Basic Text, Streaming, System Prompt, Tool
  Calling, Image Input, Multi-turn) at https://www.openresponses.org/compliance.
  Interactive, not a leaderboard — no published per-backend pass-rates.

Named collision risk during translation: OpenResponses `response.reasoning.delta`
vs OpenAI `response.reasoning_summary_text.delta` cover overlapping but not
identical semantics. Proxies translating OpenResponses must pass
provider-prefixed item/event types through untouched.
