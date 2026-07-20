# Messages ↔ Chat Completions Translation & Cross-Backend Divergences

The gotchas that bite when Anthropic-format clients talk to non-Anthropic
backends. Compiled from source examination of 7 servers + 3 gateways
(2026-07-19; commits in `sources.md`).

## Contents
- [Canonical field mapping](#canonical-field-mapping)
- [stop_reason divergence table](#stop_reason-divergence-table)
- [The thinking-signature seam](#the-thinking-signature-seam)
- [Streaming divergences](#streaming-divergences)
- [count_tokens approaches](#count_tokens-approaches)
- [Client-side requirements (what servers must tolerate)](#client-side-requirements)
- [Claude Code-specific hacks in the wild](#claude-code-specific-hacks)

## Canonical field mapping

| Messages API | Chat Completions |
|---|---|
| `system` (string or text blocks) | system message, prepended (blocks flattened to text) |
| `messages[].content` blocks | role messages; tool_result→`role:"tool"`, images→image_url parts |
| `tools[].input_schema` | `tools[].function.parameters` (+`type:"object"` default) |
| `tool_choice: auto/any/none/tool` | `auto/required/none/named-function` |
| `tool_use` block | `tool_calls[]` entry (ids fabricated when upstream omits) |
| `max_tokens` (required) | `max_tokens`/`max_completion_tokens` |
| `stop_sequences` | `stop` |
| `thinking` param | `reasoning_effort` (budget→effort heuristics) or dropped — varies |
| thinking blocks | `reasoning_content` (vLLM/SGLang parsers) / `thinking_blocks` (LiteLLM) |
| `stream_options.include_usage` | injected by every bridge (usage needed for message_delta) |

Universal bridge caveats: tool names >64 chars break OpenAI backends (LiteLLM
truncates with restore mapping); images inside tool_result can't ride
`role:"tool"` messages — relayed as a trailing user message (Superagent,
vLLM); assistant-side tool_result blocks get flattened to text (SGLang, vLLM).

## stop_reason divergence table

Anthropic defines end_turn / max_tokens / stop_sequence / tool_use (+
pause_turn, refusal). What implementations actually emit:

| Implementation | stop_sequence emitted? | Unknown finish_reason → | refusal/pause_turn |
|---|---|---|---|
| vLLM | Never (field always null) | null | never |
| SGLang | Never | end_turn + WARNING | never |
| llama.cpp | **Yes** (carries matched stop word) | — (default max_tokens) | never |
| Ollama | Yes (any other non-empty reason) | stop_sequence | never |
| mistral.rs | **Yes (proper)** | end_turn | never |
| LiteLLM bridge | Never | end_turn | never |
| Superagent Gateway | Never | end_turn | never |
| Bifrost | stop_sequence→stop (outbound) | pass through | compaction mapped |

**Rule for clients**: never key logic on `stop_sequence` against third-party
backends; treat end_turn/max_tokens/tool_use as the reliable subset.
(opencode maps pause_turn/refusal and surfaces refusal as a session error —
third-party backends never emit them, so that path is dead against local
serving.)

## The thinking-signature seam

Anthropic's real API signs thinking blocks; replayed thinking is validated.
Third-party implementations fabricate or omit signatures:

| Implementation | Signature on emitted thinking |
|---|---|
| vLLM | **fabricated uuid4** (not verifiable) |
| SGLang / llama.cpp / Ollama | emit signature_delta (parser-derived/synthetic) |
| LiteLLM bridge | `None` |
| Superagent Gateway | empty string |
| Bifrost (Claude passthrough) | **real** (bytes forwarded) |

Consequences:
- **Mixed-backend replay breaks**: thinking synthesized by a bridge/local
  backend fails signature validation if the conversation is later replayed to
  the real Anthropic API. Keep conversations on one side of the boundary, or
  strip thinking blocks when crossing it.
- Clients must tolerate absent/empty signatures (opencode does).
- Input-side handling also diverges: vLLM maps thinking→`reasoning` field and
  drops redacted_thinking; SGLang 400s on redacted_thinking in history;
  mistral.rs silently drops ALL input thinking blocks.

## Streaming divergences

All examined servers emit correct `event: X\ndata: {json}` framing (LiteLLM
bridge synthesizes it too). Differences that matter:

- **ping**: only mistral.rs emits keep-alive pings. Anthropic's real API
  sends ping — clients must not require it; proxies must not choke on it.
- **tool_use argument streaming**: mistral.rs emits one complete
  start/delta/stop triple per call (args arrive at once); others stream
  incremental `input_json_delta`.
- **message_start id**: vLLM uses `chatcmpl-…`, not `msg_…`. Bifrost emits
  `content: []` in message_start (strict-SDK compatible).
- **signature_delta**: emitted before thinking block close by llama.cpp,
  SGLang, Ollama, vLLM; empty from Superagent.
- **usage in message_start**: Ollama estimates input tokens; vLLM computes;
  cache-token fields only appear where the server supports them (vLLM needs
  `--enable-prompt-tokens-details`; mistral.rs has none). Live-verified on
  vLLM v0.25.1 with the flag: cache fields populate in aggregate usage
  (Claude Code warm run: `input_tokens: 304`, `cache_read: 59168` — ~99.5%
  prefix-cache hit), but per-turn `message_start` usage still reports null
  cache fields.
- LiteLLM's bridge holds/merges the final `message_delta` to attach usage and
  splits fake-streamed single chunks.

## count_tokens approaches

| Implementation | /v1/messages/count_tokens |
|---|---|
| vLLM | Real chat-template tokenization (+ non-standard `context_management.original_input_tokens`) |
| SGLang, llama.cpp, mistral.rs, OGX | Served |
| Ollama, Lemonade | **Not served** |
| LiteLLM | Provider counting API else tokenizer approximation; `{"input_tokens": N}` only |
| Superagent Gateway | Native on Anthropic routes; **chars/4 estimate** on OpenAI routes |

opencode never calls count_tokens — its absence only affects clients that
pre-flight token budgets (Claude Code uses it when available).

## Client-side requirements

What a third-party `/v1/messages` server must tolerate from real clients
(from opencode v1.18.3-era source; Claude Code behaves similarly):

- `anthropic-beta: interleaved-thinking-2025-05-14,fine-grained-tool-streaming-2025-05-14`
  **always sent** by opencode's anthropic provider → unknown betas must be
  no-ops (SGLang no-ops; Lemonade accepts `?beta=true`), never 400s.
- `cache_control: {type: "ephemeral"}` blocks on up to 2 system + last 2
  non-system messages → must be ignored gracefully if unsupported.
- A `thinking` body param — `{type:"adaptive", display:"summarized"}` +
  `effort` for newer Claude models, `{type:"enabled", budgetTokens: …}` for
  older → vLLM ignores silently; SGLang accepts-not-enforces.
- Always `stream: true`; SSE parser tolerates missing optional event fields.
- `cache_creation_input_tokens`/`cache_read_input_tokens` may be absent/null.
- baseURL convention: the SDK appends only `/messages` — **configure
  `http://host/v1` as base**, server must serve `POST /v1/messages`.
- opencode retry: SDK maxRetries=0; session layer retries 429+5xx honoring
  `retry-after`, exponential 2s→30s, effectively unbounded.

## Claude Code-specific hacks

- **Billing-header stripping**: vLLM and llama.cpp both strip/normalize the
  `x-anthropic-billing-header` system-prompt prefix Claude Code injects, to
  keep prefix caching effective. Captured on the wire (mitmdump, Claude Code
  v2.1.214, 2026-07-19) — it is the FIRST `system[]` text block, with no
  `cache_control`:
  ```json
  {"type":"text","text":"x-anthropic-billing-header: cc_version=2.1.214.a12; cc_entrypoint=sdk-cli;"}
  ```
  `CLAUDE_CODE_ATTRIBUTION_HEADER=0` removes the block entirely (the rest of
  the body is byte-identical). In v2.1.214 headless the content is
  version+entrypoint only — constant across requests and sessions on the same
  install; the cache-busting risk documented in the SGLang cookbook (per-
  request divergence on GLM-5.2, whose template renders tools before system)
  depends on version/entrypoint variation and template ordering. Backends
  without the strip hack, or with tools-before-system templates, should set
  the env var; backends with the hack (vLLM, llama.cpp) are safe either way.
- **Error-wording preservation**: Superagent forwards non-retryable upstream
  errors byte-for-byte because Claude Code keys retry behavior off message
  wording.
- **Model discovery**: Superagent fabricates `claude-<name>` twins so Claude
  Code's /model picker shows custom models; Ollama (`ollama launch claude`)
  and Lemonade ship launchers that set `ANTHROPIC_BASE_URL`.
- **relax_thinking**: Ollama sets it specifically "to connect to tools like
  claude code".
- OGX runs integration tests driving the real Claude Code CLI + Claude Agent
  SDK against its `/v1/messages`.
