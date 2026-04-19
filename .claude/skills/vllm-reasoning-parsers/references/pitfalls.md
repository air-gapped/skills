# Reasoning parser pitfalls

Every item has a repro condition, observed symptom, root cause, and fix.

## 1. `reasoning_content: null` on DeepSeek-R1 (start token eaten by template)

**Repro.** Serve DeepSeek-R1 with `--reasoning-parser deepseek_r1`, call `/v1/chat/completions` non-streaming. Response has filled `content` but `reasoning_content` is null.

**Symptom.** Chat template appends `<think>\n` to the prompt after `add_generation_prompt`. The model therefore only emits `...</think>answer` — no `<think>` in its output. A naive parser that requires a matched `<think>...</think>` pair fails.

**Root cause.** The base `BaseThinkingReasoningParser.extract_reasoning` uses `partition`, which already tolerates missing start tokens. But several older/third-party parsers matched on a regex requiring both sides — those see no match and fall through to `(None, model_output)`.

**Fix.** Use / inherit `BaseThinkingReasoningParser`. For custom parsers, always design for "start token may or may not appear; end token delimits". See `qwen3_reasoning_parser.py:75–87` for the canonical strip-if-present pattern.

**Upstream.** [HF discussion](https://huggingface.co/deepseek-ai/DeepSeek-R1/discussions/144), [#13125](https://github.com/vllm-project/vllm/issues/13125).

## 2. CoT leaks into `reasoning_content` with `enable_thinking=False`

**Repro.** Qwen3 with `chat_template_kwargs={"enable_thinking": False}`. Expected: all output in `content`, `reasoning_content` null. Actual: `content` empty, everything in `reasoning_content`.

**Root cause.** The Qwen3 chat template (thinking-disabled path) injects `<think>\n\n</think>\n\n` into the prompt itself, so the model's output never emits `</think>`. The parser sees no `</think>` in generated tokens and — with `thinking_enabled=True` (its default) — returns `(model_output, None)`.

**Fix.** Parser must branch on `chat_template_kwargs`. Current Qwen3 parser reads `chat_kwargs.get("enable_thinking", True)` at init time and switches truncation policy. If your parser doesn't, xgrammar also stays gated → see pitfall #3.

**Upstream.** [#19222](https://github.com/vllm-project/vllm/issues/19222) (DeepSeek-R1 variant with same root cause), [#23429](https://github.com/vllm-project/vllm/issues/23429) (DeepSeek-V3.1 `thinking: false` mis-routing — fixed by `DeepSeekV3ReasoningParser` delegating to `IdentityReasoningParser`).

## 3. `guided_json` produces gibberish with `enable_thinking=False`

**Repro.** `--reasoning-parser qwen3 --guided-decoding-backend xgrammar`, request with `response_format={"type":"json_object"}` and `chat_template_kwargs={"enable_thinking": False}`. Output is valid-adjacent JSON with extra tokens, or total gibberish.

**Root cause.** xgrammar waits for `is_reasoning_end(prompt_token_ids)` before enforcing the grammar. With thinking-disabled, the Qwen3 chat template injects `<think>\n\n</think>\n\n` into the prompt. If the parser's `is_reasoning_end` recognizes this and returns True, xgrammar enforces from token 0. If it doesn't (because the template omits the fake think block, or uses an older 2507-style template, or because `chat_template_kwargs` got filtered by the allowlist — see `vllm-chat-templates`), xgrammar waits for a `</think>` that never comes, and the model emits free-form text before the JSON.

`BaseThinkingReasoningParser.is_reasoning_end` does a reverse scan and returns True when `end_token_id` is seen before any `start_token_id` in the prompt — which is exactly the `<think>\n\n</think>\n\n` shape. So Qwen3 *should* gate correctly on a standard thinking-disabled template. Custom templates that drop the block break this silently.

**Fixes (in order of preference).**

1. **Fix the chat template** so it emits the `<think>…</think>` sandwich when `enable_thinking` is false. Render it locally with `tokenizer.apply_chat_template(..., enable_thinking=False)` and confirm the sandwich is present.
2. **Bypass the gate**: `--structured-outputs-config.enable_in_reasoning=true`. This makes `should_fill_bitmask` return True unconditionally (`vllm/v1/structured_output/__init__.py:285-290`) — grammar enforces from token 0 whether reasoning is "on" or not. Useful when you want structured output during CoT (emerging pattern) or when you can't control the chat template.
3. **Drop `--reasoning-parser` entirely** if the model is a non-thinking SKU (e.g. `Qwen3-235B-A22B-Instruct-2507`). With no reasoner attached, xgrammar short-circuits to always-enabled.
4. **Set a server-side default** `--default-chat-template-kwargs '{"enable_thinking": false}'` so every request gets the correct template rendering without relying on client cooperation.

**Upstream.** [#18819](https://github.com/vllm-project/vllm/issues/18819), [#39130](https://github.com/vllm-project/vllm/issues/39130) (silently disabled xgrammar on gemma4).

## 4. Truncated output = everything in wrong field

**Repro.** Any R1-style parser. Request with `max_tokens` small enough that the model stops mid-CoT, before emitting `</think>`.

**Symptom per parser.**

- `qwen3` (`enable_thinking=True`, default): `(model_output, None)` — all reasoning, no content.
- `qwen3` (`enable_thinking=False`): `(None, model_output)` — all content.
- `deepseek_r1`: `(model_output, None)` — all reasoning.
- `nemotron_v3` with `enable_thinking=False` OR `force_nonempty_content=True`: fields swapped if content ended up None — ensures at least one field non-empty.
- `granite`: if "Here is my response:" never appeared, `(None, model_output)` — all content.
- `mistral`: depends on which of BOT/EOT appeared. If only `[THINK]`: `(post_bot, prev_bot if non-empty else None)`. If neither: `(None, model_output)`.

**Takeaway.** There is no universal policy. Document the policy choice in the parser docstring and test it explicitly.

## 5. Nested `<think>` in output splits wrong

**Repro.** Some distilled DeepSeek-R1 variants occasionally emit `<think>outer <think>inner</think> outer</think>` in certain edge cases (prompt bleed-through).

**Symptom.** `extract_reasoning` returns `(outer_before_inner, "outer</think>final")` because `partition` stops at the first `</think>`. Content now contains a stray `</think>`.

**Fix for counting.** `count_reasoning_tokens` in `BaseThinkingReasoningParser` uses a depth counter and handles this correctly.

**Fix for split.** No general fix — at the split level, the first `</think>` is authoritative. Filter the content for stray end tokens if downstream tooling chokes.

**Upstream.** [Discussion #12708](https://github.com/vllm-project/vllm/discussions/12708).

## 6. Tool calls empty when reasoning parser is on

**Repro.** `--reasoning-parser deepseek_r1 --tool-call-parser hermes --enable-auto-tool-choice`. Model emits `<think>…</think><tool_call>…</tool_call>`. Non-streaming response has reasoning but `tool_calls: []`.

**Root cause.** `OpenAIServingChat` runs tool parser on the **content** half of `extract_reasoning` — see `vllm/entrypoints/openai/chat_completion/serving.py:1365-1370`. If the reasoning parser returned `(everything, None)` (e.g. because model didn't emit `</think>` due to training drift), tool parser sees an empty content string.

**Fix.**
- Ensure the model actually emits `</think>` before tool calls (chat-template job).
- If the model stops reasoning implicitly at a tool-call sentinel (Kimi K2), the parser must recognize that sentinel — `KimiK2ReasoningParser.is_reasoning_end` checks `<|tool_calls_section_begin|>`.
- For models where reasoning and tool-call interleave (rare), consider a specialized parser.

**Upstream.** [#17655](https://github.com/vllm-project/vllm/issues/17655), [#19051](https://github.com/vllm-project/vllm/issues/19051).

## 7. Hunyuan stateful parser corruption under concurrency

**Repro.** Monkey-patch vLLM to cache the `HunyuanA13BReasoningParser` instance across requests. Fire 4 concurrent streaming requests.

**Symptom.** Reasoning/content boundaries interleave across requests. `current_state = "think"` from request A carries into request B.

**Root cause.** Instance state on `self`: `current_state`, `sequence_index`, `token_buffer`, `text_buffer`.

**Fix.** Don't cache. vLLM's `OpenAIServingChat` already instantiates fresh per request (`serving.py:240`). If writing a custom parser with state, do the same: no class-level mutable state, no global caches.

## 8. Multi-token delimiter can't use `BaseThinkingReasoningParser`

**Repro.** Model uses `<|analysis|>` as think-start, but the tokenizer encodes it as `["<|analysis", "|>"]` (two tokens).

**Symptom.** `BaseThinkingReasoningParser.__init__` calls `self.vocab.get("<|analysis|>")` → `None` → `RuntimeError("could not locate think start/end tokens")`.

**Fix.** Inherit `ReasoningParser` directly. Resolve IDs with `tokenizer.encode("<|analysis|>", add_special_tokens=False)` → list of IDs. Use sequence matching in `is_reasoning_end` (see `gptoss_reasoning_parser.py:86-113` for the pattern — backward scan for the prefix sequence, then forward bounded scan for the suffix).

For `ReasoningConfig.initialize_token_ids` to work (which derives IDs automatically for structured-output lookahead), expose `reasoning_start_str` / `reasoning_end_str` properties; the config will call `tokenizer.encode(...)` itself.

## 9. Streaming emits empty delta (single-token start/end)

**Repro.** Custom parser doesn't skip single-token start/end deltas.

**Symptom.** Client receives `data: {"choices":[{"delta":{"content":""}}]}` chunk — technically valid, but noisy and some clients choke.

**Fix.** Standard guard at the top of `extract_reasoning_streaming`:

```python
if len(delta_token_ids) == 1 and delta_token_ids[0] in (self.start_token_id, self.end_token_id):
    return None
```

All built-in parsers do this.

## 10. Harmony model parsed as `<think>` model

**Repro.** Serve GPT-OSS with `--reasoning-parser deepseek_r1` (wrong parser selected).

**Symptom.** `RuntimeError: ... could not locate think start/end tokens in the tokenizer!` at first request. Harmony uses `<|channel|>analysis<|message|>` — no `<think>` token exists in GPT-OSS vocab.

**Fix.** `--reasoning-parser openai_gptoss`. Note its quirks:
- `extract_reasoning` (non-streaming) raises `NotImplementedError` — the harmony branch in `api_server` / `parser/harmony_utils.py` handles non-streaming via `parse_chat_output`.
- `prepare_structured_tag` returns JSON for a `structural_tag` xgrammar directive that isolates the analysis channel for structured generation.
- `is_reasoning_end` searches for the `<|channel|>final<|message|>` sequence with up to `reasoning_max_num_between_tokens = 20` tokens between prefix and suffix (allows `<|constrain|>json` et al).

## 11. Mistral parser rejects HF tokenizer

**Repro.** `--reasoning-parser mistral` on a Magistral model served with `--tokenizer-mode auto` (HF tokenizer, not Mistral tokenizer).

**Symptom.** `ValueError: The tokenizer must be an instance of MistralTokenizer.`

**Fix.** Add `--tokenizer-mode mistral`. The Mistral parser uses `tokenizer.tokenizer.get_special_token(SpecialTokens.begin_think)` which is only defined on `MistralTokenizer` (mistral-common). HF tokenizer doesn't have this API.

## 12. Granite streaming swallows the first part of reasoning

**Repro.** `--reasoning-parser granite` streaming. Client sees empty delta, empty delta, empty delta, then suddenly a big chunk of reasoning.

**Root cause.** `_get_delta_message_with_no_reasoning_bounds` returns `DeltaMessage(reasoning=None, content=None)` while the phrase "Here is my thought process:" is being built character by character across deltas (`"Here"`, `" is"`, `" my"`, …). When the phrase completes, the deferred content is emitted at once.

**Takeaway.** This is by design — without it, the phrase itself would leak into the output. But it's surprising for clients expecting smooth token streams. Measure TTFT carefully on Granite-style models.

## 13. Implicit reasoning-end not recognized → xgrammar gates wrong

**Repro.** Kimi K2 with tool calls, `--reasoning-parser kimi_k2 --enable-auto-tool-choice`. Model emits `<think>…<|tool_calls_section_begin|>…` (no explicit `</think>`).

**Behavior.** `KimiK2ReasoningParser.is_reasoning_end` explicitly checks `_tool_section_start_token_id`, so xgrammar correctly un-gates. Stream-side `is_reasoning_end_streaming` also checks the delta for that token.

**Takeaway.** If you're authoring a parser for a model that has implicit end markers (tool calls, answer sections, channel changes), encode them explicitly. Single-token `</think>` is the exception, not the rule.

## 14. `--enable-reasoning` is dead

**Repro.** Copy a Stack Overflow answer that uses `--enable-reasoning --reasoning-parser deepseek_r1`.

**Symptom.** `vllm serve: error: unrecognized arguments: --enable-reasoning`.

**Fix.** The `--enable-reasoning` flag was removed circa v0.8 once `--reasoning-parser` became self-enabling. If a parser is specified, reasoning is on. To turn it off, omit the flag. Some vendor docs still reference the old flag — ignore them.

## 15. `reasoning_content` is always null — but parser worked

**Repro.** Current-main vLLM. Client reads `response.choices[0].message.reasoning_content`, always null. `content` looks correct, `</think>` is already stripped from it.

**Root cause.** The response field was renamed from `reasoning_content` to `reasoning` in a refactor (`vllm/entrypoints/openai/chat_completion/protocol.py:64` — `ChatCompletionResponseMessage.reasoning: str | None = None`). Same for `DeltaMessage.reasoning` in `vllm/entrypoints/openai/engine/protocol.py:261`. The string `reasoning_content` does not appear in the chat-completion response path anywhere on current main. Clients (including many OpenAI-SDK-compatible libraries, many tutorials, and older vLLM docs) still read `reasoning_content`, so they see null.

**Fix.**
- Update client to read `.reasoning`. `curl ... | jq '.choices[0].message.reasoning'`.
- If you can't change the client, pin to a pre-rename vLLM version (check `git log --oneline protocol.py` for the rename).
- Confusingly, `--include-reasoning-content` / `include_reasoning` request flag is still spelled with `reasoning` (truncated), so don't confuse the request-side and response-side naming.

**Takeaway.** When someone asks "why is reasoning_content null" — before diving into parser debugging, first run `jq '.choices[0].message | keys'` to see what fields actually exist. If `reasoning` is there, the parser ran fine and this is purely a client-side name mismatch.

## Bonus: `include_reasoning=False` does not disable the parser

Setting `include_reasoning: false` on the request null-ifies the `reasoning_content` field in the response, but `extract_reasoning` / `extract_reasoning_streaming` still run. This matters because:
- The tool parser still receives the *post-reasoning* content (not the full output).
- Structured output still gates on `is_reasoning_end`.

So `include_reasoning: false` is a display-only toggle, not a performance win.
