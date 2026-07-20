# Responses API Adoption

**Last refreshed**: 2026-07-19 (provenance: `references/sources.md`).

## Contents
- [Timeline](#timeline) — March 2025 launch through July 2026
- [Chat Completions](#chat-completions) — still supported, not deprecated
- [Why Responses API](#why-responses-api) — differentiators vs Chat Completions
- [Client Adoption](#client-adoption) — Responses-only, default, switchable, Chat-only
- [OpenResponses Ecosystem](#openresponses-ecosystem) — open spec, backers
- [What This Means for Proxies and Gateways](#what-this-means-for-proxies-and-gateways)
- [Scale](#scale) — OpenAI API usage numbers

## Timeline

- **March 11, 2025**: Responses API launched alongside Agents SDK and built-in tools
- **August 26, 2025**: Assistants API deprecated (sunset: August 26, 2026)
- **December 9, 2025**: Codex CLI deprecated Chat Completions support
- **January 15, 2026**: Open Responses open standard announced (openresponses.org)
- **February 2026**: Codex CLI dropped `wire_api` flag client-side (PR #10498) — Responses hard-coded
- **2026-02-05**: Vercel ships `@ai-sdk/open-responses` package (first dedicated Open Responses client SDK)
- **2026-02-09**: Roo-Code migrates OpenAI Native + Codex paths to AI SDK Responses-first (#11330, #11352)
- **2026-02-10**: OpenAI ships the "agentic triad": **Compaction**, **Hosted Shell**, **Skills**
- **2026-02-21**: Continue.dev adds Responses API for OpenAI native provider (#9411)
- **2026-02-23**: WebSocket transport launches (`wss://api.openai.com/v1/responses`); OpenAI Agents SDK Python adds support (#2530)
- **2026-02-24**: `phase` field introduced; gpt-5.3-codex added
- **2026-02-25**: OpenCode bug #15016 (forced-Responses) closed
- **2026-02-28**: Llama Stack joins Open Responses as backer (PR #29)
- **2026-03-05**: GPT-5.4 + 5.4-pro launch; Tool Search launches; Computer tool GA (rename from `computer_use_preview`)
- **2026-03-06**: OpenAI Agents Python adds Tool Search (#2610)
- **2026-03-12**: Sora video output item type; Vercel AI SDK makes xAI Responses API the default (#13340)
- **2026-03-17**: GPT-5.4-mini + 5.4-nano added
- **2026-03-25**: `ResponseInputMessageItem.type` becomes required (breaking)
- **2026-03-25**: Cline adds `useResponsesApi` opt-out (#11809)
- **2026-03-30**: Strands adds **stateful mode** (`previous_response_id`) — major (#2004)
- **2026-03-30**: Microsoft Agent Framework .NET refactors Foundry agents onto Responses (#4502)
- **2026-03-31**: Strands adds built-in tool support (web_search, shell, mcp) (#2011)
- **2026-04-01**: Mastra ships **Responses and Conversations API server** (#14339) — Mastra is both client AND server
- **2026-04-02**: Microsoft Agent Framework reaches **1.0 GA** (python + dotnet)
- **2026-04-07**: Vercel adds reasoning-summary for OpenResponses (#14115)
- **2026-04-08**: Roo-Code migrates xAI to Responses API (#11962)
- **2026-04-10**: Pydantic AI adds server-side compaction (#4943)
- **2026-04-13**: AWS joins Open Responses as backer (PR #67); LiteLLM ships Codex multi-turn merge fix (#25618)
- **2026-04-14**: Pydantic AI fixes `openai_previous_response_id='auto'` (#5086)
- **2026-04-15**: Codex rust-v0.121.0 GA (MCP Apps, marketplace, memory endpoints)
- **2026-04-16**: Pydantic AI adds stateful compaction mode (#5108)
- **2026-04-24**: GPT-5.5 + 5.5 Pro launch (1M token context); OpenResponses spec release 2026-04-24 (WebSocket transport, `phase` field, optional `logprobs` enter the open spec)
- **2026-05-11**: `return_token_budget` parameter for longer web search runs
- **2026-05-29**: `prompt_cache_retention` default flips `in_memory` → `24h` for non-ZDR orgs
- **2026-06-01**: OpenAI models available on Amazon Bedrock via a Responses API endpoint
- **2026-06-02**: Container (shell/code_interpreter) billing moves to per-minute granularity, 5-minute minimum
- **2026-06-04**: `moderation` object accepted on Responses + Chat Completions for input/output assessment
- **2026-06-09**: Web search returns image results in Responses requests
- **2026-07-09**: GPT-5.6 family launches — Programmatic Tool Calling, explicit prompt-caching controls, persisted reasoning, multi-agent orchestration (beta) in Responses API

## Chat Completions

Not deprecated. Continues to be supported. But: superseded for agentic workloads,
and most major clients now default to Responses API for OpenAI.

## Why Responses API

- **Server-side conversation state**: `previous_response_id` (and
  `/v1/conversations`) eliminate manual context management
- **Reasoning-token persistence across turns** — the single biggest
  differentiator. Chat Completions discards reasoning tokens between turns
- **Built-in hosted tools**: web_search, file_search, code_interpreter, computer_use,
  shell (Feb 2026), tool_search (Mar 2026), MCP, image_gen
- **Agentic loop**: Model calls multiple tools within one API request
- **Server-side compaction** (Feb 10 2026): opt-in context summarization
- **WebSocket transport** (Feb 23 2026): 30-40% faster on 20+ tool-call loops
- **Better reasoning performance**: 3% better SWE-bench with Responses API vs
  Chat Completions (same model); 40-80% better cache utilization (details in
  `spec.md` §Prompt Caching)
- **Typed output items** instead of plain messages

## Client Adoption

### Responses API ONLY

- **Codex CLI** — `wire_api` flag dropped from client-side in PR #10498
  (2026-02-03); Responses is hard-coded. Latest: rust-v0.144.6 (2026-07-18).
  Now sends `client_metadata: {installation_id, session_source}` on every
  request; `x-client-request-id` header populated from `conversation_id`;
  `is_azure_responses_provider` flag for Azure routing.
- **OpenAI Agents SDK** (Python + TypeScript) — Built natively on Responses API.
  Python v0.14.1 (2026-04-15) now has Tool Search, WebSocket, `AnyLLMModel`
  adapter for Mozilla any-llm project.

### Responses API preferred (default), Chat Completions fallback

- **OpenCode** — OpenAI provider uses `sdk.responses()`; `openai-compatible`
  provider still Chat Completions. Issues #7793 still open. Latest v1.18.3
  (2026-07-16).
  **Pitfall (live-verified v1.18.3, 2026-07-19):** the built-in `openai`
  provider with a custom `baseURL` **hangs at init — no request is ever
  sent** — when the model ID is not in opencode's models.dev catalog
  (headless runs time out with zero events). Workaround: declare a custom
  provider with `"npm": "@ai-sdk/openai"` + `baseURL` — verified working
  against vLLM `/v1/responses` including multi-step tool calling. Related:
  on upstream 404s the run retries silently and exits without an `error`
  event.
  **Anthropic-provider alternative (production-proven via LiteLLM;
  live-verified direct-to-vLLM 2026-07-19):** opencode's **anthropic
  provider** works against LiteLLM's `/v1/messages` adapter → vLLM, and
  against vLLM ≥ v0.25's **native `/v1/messages`** directly. It sidesteps
  both the openai-provider catalog hang (which is openai-provider-specific —
  the anthropic provider handles non-catalog model IDs fine) and the
  Responses↔ChatCompletions bridge event-ordering issues (#20975/#24445),
  at the cost of Responses-specific features (server-side state, encrypted
  reasoning replay, built-in tools). Footnote: opencode's title-generation
  side-call may 404 harmlessly against a single-model server unless
  `small_model` is pinned to the served model.
- **Vercel AI SDK** — `openai.responses()` is the default OpenAI provider from
  AI SDK 5+; `openai.chat` required to opt out. **New in 2026**:
  `@ai-sdk/open-responses` package (PR #11836) — first dedicated Open
  Responses open-spec client SDK. xAI provider defaulted to Responses (#13340).
  ZDR-compatible encrypted reasoning round-trip (#14497).
- **Microsoft Agent Framework** — `OpenAIResponsesClient` and
  `AzureOpenAIResponsesClient`. **GA 1.0** hit 2026-04-02 (python + dotnet).
  `FoundryAgent` refactored to Responses-native (PR #4502).
- **Amazon Strands SDK** — `OpenAIResponsesModel` now **stateful-capable**
  (previously stateless-only): PR #2004 (2026-03-30) adds `stateful` flag,
  server-side `previous_response_id` chaining, session manager persistence.
  PR #2011 (2026-03-31) adds built-in tool support (web_search, file_search,
  code_interpreter, shell, mcp).
- **Aider** — Works via LiteLLM. No Responses-specific PRs since 2025-06 —
  behavior tracks LiteLLM.
- **Continue.dev** — Responses API for OpenAI native (PR #9411, 2026-02-21).
  Response chaining (#9270, #9285).
- **Cline** — `useResponsesApi` opt-out knob added (PR #11809, 2026-03-25).
  Uses WebSocket per Cline's report of 30-40% speedup.
- **Zed** — Graduated from feature flag to default (Jan 2026). Reasoning
  summaries for Responses (#50959). GPT-5.4 BYOK (#50858, #50896).
- **Roo-Code** (Roo Cline) — xAI and OpenAI Native migrated to AI SDK
  Responses-first (PRs #11330, #11352, #11962). Uses `include:
  ["reasoning.encrypted_content"]` for ZDR.
- **Haystack** — `OpenAIResponsesChatGenerator` (shipped Nov 2025); added
  `SUPPORTED_MODELS` on the generator (PR #10844, 2026-03-17).
- **AutoGen** (Microsoft) — `OpenAIAgent` uses Responses (from 2025-06). Project
  effectively frozen in favor of Microsoft Agent Framework — no Feb-Apr 2026 PRs.

### Responses API supported via provider switch

- **Pydantic AI** — v2.13.0 (2026-07-18; crossed 2.0 between Apr and Jul 2026).
  `OpenAIResponsesModel` coexists with Chat Completions model. **Added 2026**: server-side compaction via
  `OpenAICompaction` + `AnthropicCompaction` (PR #4943, 2026-04-10), stateful
  compaction mode (#5108), `openai_previous_response_id='auto'` fix (#5086).
- **LangChain / langchain-openai** — Responses auto-selected for gpt-5.x codex
  and pro models (PR #35058). `phase` param support (#36161). Content blocks
  without `type` in Responses conversion (#36725).
- **LlamaIndex** — Preserve assistant text alongside tool calls (#21180);
  GPT-5.4 support (#20976); `input_file` serialization fix (#21172).

### NEW — clients that IMPLEMENT Responses API as a server

- **Mastra** — PR #14339 (2026-04-01): adds Mastra Responses and
  Conversations API endpoints. Threads map to Conversations. Mastra is now
  both a client (via AI SDK) and a server.
- **Llama Stack** — Full `/v1/responses` reference impl with `/v1/responses/compact`.
- **Bifrost** — Native Responses with ChatGPT OAuth passthrough for Codex.
- **TensorRT-LLM**, **Lemonade** (AMD) — see backend matrix.

### Chat Completions only (no Responses support)

- **Claude Code** — Uses native Anthropic Messages API, not OpenAI's Responses API
- **Block Goose** — v1.31.0 (2026-04-17). Routes via LiteLLM; no Responses in OpenAI provider
- **CrewAI** — v1.14.2 (2026-04-17). Routes via LiteLLM; nothing Responses-specific
- **Task Master AI** — v0.43.1 (2026-03-31). AI SDK indirection only
- **Void Editor** — v1.3.4-beta (2025-04-15, stale)
- **Cursor / Windsurf / Codeium** — closed-source; status uncertain. Cognition
  acquired Windsurf Dec 2025; Windsurf Arena Mode launched Feb 2026 (multi-model
  comparison). Codeium `language-server` inactive after v2.12.5 (Jan 2026).
- **Gemini CLI** — Google; Gemini-only by design

## OpenResponses Ecosystem

Launched 2026-01-15 (Apache-2.0); latest spec release 2026-04-24. Spec scope,
governance, and the compliance runner are covered in `spec.md`
§OpenResponses Specification — this section tracks only the adoption signal.

Backers, with join dates: NVIDIA, Vercel, OpenRouter, HuggingFace, LM Studio,
OpenAI, Ollama, vLLM, **Llama Stack** (joined 2026-02-28), **Databricks**
(joined 2026-02-17), **Red Hat** (joined 2026-03-04), **AWS** (joined
2026-04-13).

## What This Means for Proxies and Gateways

1. **The ecosystem is Responses-default.** Most major clients (Codex, OpenCode,
   Continue, Cline, Zed, Roo-Code, Vercel-AI-SDK-based integrations) now default
   to Responses. Gateways/proxies that don't handle `/v1/responses` will see
   this traffic bypass them.

2. **Stateful is table-stakes.** Strands added it March 30. Pydantic AI added
   stateful compaction April 10/16. Mastra ships its own Conversations API.
   Proxies must decide whether to pass-through `previous_response_id` /
   `conversation` or synthesize state; stateless-only breaks clients.

3. **Open Responses is a formal standard, not a marketing term.** The
   openresponses.org interactive compliance runner provides a concrete way to
   audit conformance for any proxy or backend claiming Responses support.

4. **New traffic shapes a proxy must not strip:**
   - `client_metadata` headers from Codex.
   - `include: ["reasoning.encrypted_content"]` from ZDR / Roo-Code users.
   - `phase` on assistant messages from gpt-5.3-codex+ — preserve verbatim.
   - `compaction` output items — opaque; preserve byte-for-byte.
   - `conversation` field as alternative to `previous_response_id`.

5. **Upstream bugs still in the wild** (as of 2026-07-19): LiteLLM #20975
   (Azure passthrough strips setup events — still open). vLLM #39584
   (parallel tool call crash) was fixed by the June 2026 Responses refactor;
   LiteLLM #22102 (gpt-5.3-codex skipping `output_item.added`) was
   stale-closed 2026-06-27 without a confirmed upstream fix. Any proxy in
   the path should still be resilient to out-of-order SSE events.

## Scale

- 3 million active developer accounts on OpenAI API (5x growth since 2022)
- ~8.6 trillion tokens/day processed (Oct 2025)
- Named adopters: Zencoder, Revi, MagicSchool AI
