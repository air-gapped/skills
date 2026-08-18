# Per-parser matrix

One row per registered name. **29 registered names** at v0.27.0.

**Two implementation paths now — check which one a name is on before reading its
source.** A refactor has moved several parsers into a new top-level
**`vllm/parser/`** package, where one class per model (e.g. `Qwen3Parser`) is
split by `make_adapters()` into *both* a reasoning adapter and a tool adapter:

```python
# vllm/parser/engine/registered_adapters.py
(Qwen3ParserReasoningAdapter, Qwen3ParserToolAdapter) = make_adapters(Qwen3Parser)
```

The `vllm/reasoning/*_engine_reasoning_parser.py` files are now **three-line
re-export shims** — the logic is in `vllm/parser/<model>.py`. This is the
unified reasoning+tool parser design from RFC
[#32713](https://github.com/vllm-project/vllm/issues/32713), which the stale
bot auto-closed as `NOT_PLANNED` on 2026-07-24 — a closure for inactivity, not
a completion — even though the code has landed. Read the tree, not the tracker.

| Path | Names | Where the logic lives |
|---|---|---|
| **Adapter** | `deepseek_v4`, `gemma4`, `glm45`, `glm47`, `inkling`, `kimi_k2`, `mimo`, `minimax_m2`, `mistral`, `nemotron_v3`, `qwen3`, `seed_oss` (12) | `vllm/parser/<model>.py`, adapters built in `vllm/parser/engine/registered_adapters.py` |
| **Legacy** (standalone) | the other 17 | `vllm/reasoning/<file>.py` as before |

**Membership is decided by the import, not the filename.** Only some shims are
named `*_engine_reasoning_parser.py`; `kimi_k2_reasoning_parser.py`,
`minimax_m2_reasoning_parser.py`, `glm47_moe_reasoning_parser.py` and
`mistral_reasoning_parser.py` are ordinary names that are nonetheless a few
lines subclassing an adapter. The authoritative test:

```bash
grep -l "registered_adapters import" vllm/reasoning/*.py
```

An earlier revision of this file claimed `kimi_k2` and `minimax_m2` still had
legacy *reasoning* implementations. **That was wrong** — both were already on
the adapter path at v0.25.1; only the filenames misled. `mistral` joined at
v0.27.0 ([#48947](https://github.com/vllm-project/vllm/pull/48947)).
`minimax_m2_append_think` is the one genuinely-legacy class in a shim file:
`minimax_m2_reasoning_parser.py` holds `MiniMaxM2ReasoningParser` (adapter
subclass) *and* `MiniMaxM2AppendThinkReasoningParser` (plain `ReasoningParser`).
`vllm/parser/deepseek_v32.py` exists but has no *reasoning* registry entry at
all. Read `_REASONING_PARSERS_TO_REGISTER`.

| Name | Class | File | Family | Start in prompt? | Thinking-disable switch | Truncation policy |
|---|---|---|---|---|---|---|
| `deepseek_r1` | `DeepSeekR1ReasoningParser` | `deepseek_r1_reasoning_parser.py` | `<think>`/`</think>` (vocab single-token) | Yes (modern templates) | None (always on) | `(all, None)` = all reasoning |
| `deepseek_v3` | `DeepSeekV3ReasoningParser` | `deepseek_v3_reasoning_parser.py` | Delegates → R1 or Identity | — | `chat_template_kwargs.thinking` OR `enable_thinking` (default: **off**) | Inherits from delegate |
| `deepseek_v4` | `DeepSeekV4ParserReasoningAdapter` | `deepseek_v4_engine_reasoning_parser.py` (shim) → `vllm/parser/deepseek_v4.py` | **No longer an alias of `deepseek_v3`** — as of v0.25.1 it has its own `DeepSeekV4Parser` on the adapter path | — | See `vllm/parser/deepseek_v4.py` | See file |
| `poolside_v1` | `PoolsideV1ReasoningParser` | `poolside_v1_reasoning_parser.py` | Subclass of `DeepSeekV3ReasoningParser` (`<think>`/`</think>`); scopes the backward `</think>` scan to the current assistant turn (`<assistant>` token) so a stray `</think>` in history/few-shot doesn't false-positive `prompt_is_reasoning_end` | — | Same as `deepseek_v3` | Inherits from delegate |
| `cohere_command3` | `CohereCommand3ReasoningParser` | `cohere_command_reasoning_parser.py` (shared, 716 lines at v0.27.1) | **`<\|START_THINKING\|>` / `<\|END_THINKING\|>`** vocab tokens (also tracks `<\|CHATBOT_TOKEN\|>`); both classes derive from `BaseCohereCommandReasoningParser` | — | None — the subclass only selects a filter profile, `PyFilterOptions().cmd3()` streaming / `.cmd3().no_tools()` unary | Base class behaviour |
| `cohere_command4` | `CohereCommand4ReasoningParser` | `cohere_command_reasoning_parser.py` (shared) | Same delimiters and base class as `cohere_command3` | — | None — differs from `cohere_command3` **only** by `PyFilterOptions().cmd4()` / `.cmd4().no_tools()` | Base class behaviour |
| `glm45` / `glm47` | `Glm47MoeParserReasoningAdapter` | `glm47_moe_reasoning_parser.py` (shim) → `vllm/parser/glm47_moe.py` | **`glm45` moved off the DeepSeek-V3 class onto the adapter path and now shares with the new `glm47` name** — it no longer behaves identically to `holo2` | — | See `vllm/parser/glm47_moe.py` | See file |
| `holo2` | `DeepSeekV3ReasoningWithThinkingParser` | `deepseek_v3_reasoning_parser.py` (shared) | Delegates → R1 or Identity | — | Same as `deepseek_v3` but default **on** | Inherits |
| `qwen3` / `mimo` | `Qwen3ParserReasoningAdapter` | `qwen3_engine_reasoning_parser.py` (shim) → `vllm/parser/qwen3.py` (`mimo` aliases the same class/file) | `<think>`/`</think>` | Yes (Qwen3.5+) — old 2507 template emits it | `chat_template_kwargs.enable_thinking` (default **on**) | Enabled: `(all, None)`. Disabled: `(None, all)` |
| `ernie45` | `Ernie45ReasoningParser` | `ernie45_reasoning_parser.py` | `<think>`/`</think>` + `<response>`/`</response>` | Optional — tolerates both | None | Base behavior |
| `gemma4` | `Gemma4ParserReasoningAdapter` | `gemma4_engine_reasoning_parser.py` (shim) → `vllm/parser/gemma4.py` | `<think>`/`</think>` | — | `chat_template_kwargs` | See file |
| `hunyuan_a13b` | `HunyuanA13BReasoningParser` | `hunyuan_a13b_reasoning_parser.py` | `<think>\n … \n</think>\n<answer>\n … \n</answer>` | No | None | Regex fallback |
| `hy_v3` | `HYV3ReasoningParser` | `hy_v3_reasoning_parser.py` | `<think>`/`</think>` (BaseThinking subclass) with `_identity_parser` delegation | Optional | `chat_template_kwargs.reasoning_effort` (or top-level `reasoning_effort`); value `"no_think"` routes to `IdentityReasoningParser`; default is `"no_think"` when unset | Inherits from delegate (identity when off, base when on) |
| `granite` | `GraniteReasoningParser` | `granite_reasoning_parser.py` | Phrases: "Here is my thought process:" / "Here is my response:" | Phrases in output | None | Falls through as content if phrases absent |
| `kimi_k2` | `KimiK2ReasoningParser` = `KimiK2ParserReasoningAdapter` | `kimi_k2_reasoning_parser.py` (8-line shim) → `vllm/parser/kimi_k2.py` | `<think>`/`</think>` + implicit end `<\|tool_calls_section_begin\|>`. **Adapter path** despite the ordinary filename | Optional | `chat_template_kwargs.thinking` | `(remainder, None)` |
| `kimi_k3` | `KimiK3ReasoningParser` | `kimi_k3_reasoning_parser.py` | **New at v0.27.0**, legacy shape. XTML `<\|open\|>think<\|sep\|>` … `<\|close\|>think<\|sep\|>` — each marker is a **3-token sequence**, so the token-id helpers do subsequence search, not single-id lookup (contrast Kimi-K2's single `<think>` token) | In thinking mode the serving layer may feed `<\|open\|>think<\|sep\|>` as the generation prefix, so output can begin *inside* the think channel — a missing open marker is treated as "reasoning starts at offset 0" | `chat_template_kwargs.thinking=False` or `enable_thinking=False` (instruct mode) → every delta returned as content | See file |
| `inkling` | `InklingParserReasoningAdapter` | `inkling_reasoning_parser.py` (3-line shim) → `vllm/parser/inkling.py` | **New at v0.27.0.** Not a delimiter pair — typed blocks: `<\|message_model\|>` + `<\|content_thinking\|>` … `<\|end_message\|>`, repeatable in any order, sharing `<\|end_message\|>` with text and tool blocks. The engine keys `is_reasoning_end` / `count_reasoning_tokens` on `THINK_START`/`THINK_END` *labels*; the transition table carries the semantics, not the label | — | See file | See file |
| `minimax_m2` | `MiniMaxM2ReasoningParser` (subclass of `MinimaxM2ParserReasoningAdapter`) | `minimax_m2_reasoning_parser.py` → `vllm/parser/minimax_m2.py` | Only `</think>` (no start). **Adapter path** despite the ordinary filename | N/A (no start) | None | `(all, None)` before `</think>` |
| `minimax_m2_append_think` | `MiniMaxM2AppendThinkReasoningParser` | same file | Prepends `<think>` to content; never separates | — | — | Always content |
| `mistral` | `MistralParserReasoningAdapter` | `mistral_reasoning_parser.py` (3-line shim) → `vllm/parser/mistral.py` | **Moved onto the adapter path at v0.27.0** ([#48947](https://github.com/vllm-project/vllm/pull/48947)) — one `MistralParser` now serves reasoning *and* tool calls. `[THINK]`/`[/THINK]` via `SpecialTokens.begin_think/end_think`; also handles text-based reasoning. The old `ValueError: The tokenizer must be an instance of MistralTokenizer.` is gone — `is_mistral_tokenizer()` selects a code path and a non-Mistral tokenizer falls back to the generic `adjust_request` | Depends on template | None | Handles all 4 BOT/EOT combinations |
| `nemotron_v3` | `NemotronV3ParserReasoningAdapter` | `nemotron_v3_engine_reasoning_parser.py` (shim) → `vllm/parser/nemotron_v3.py` | R1 base + field swap | — | `chat_template_kwargs.enable_thinking=False` OR `force_nonempty_content=True` swaps reasoning↔content | Inherits R1 |
| `olmo3` | `Olmo3ReasoningParser` | `olmo3_reasoning_parser.py` | `<think>`/`</think>` | — | — | — |
| `openai_gptoss` | `GptOssReasoningParser` | `gptoss_reasoning_parser.py` | Harmony. **Reduced to a stub at v0.27.0** ([#45560](https://github.com/vllm-project/vllm/pull/45560)): `is_reasoning_end` and `is_reasoning_end_streaming` `return True` unconditionally; the backward-scan fields are gone. All real work is in `HarmonyParser` (`vllm/parser/harmony.py`) | Yes (system msg) | — | `extract_reasoning`, `extract_reasoning_streaming`, `extract_content_ids` all raise `NotImplementedError` with "Use HarmonyParser for output parsing" |
| `seed_oss` | `SeedOssParserReasoningAdapter` | `seed_oss_engine_reasoning_parser.py` (shim) → `vllm/parser/seed_oss.py` | `<seed:think>`/`</seed:think>` | — | — | — |
| `minimax_m3` | `MiniMaxM3ReasoningParser` | `minimax_m3_reasoning_parser.py` | MiniMax M3 — own file/class, **new since the 2026-05-28 sweep** (separate from the two `minimax_m2*` names) | — | See file | See file |
| `step3` / `step3p5` | `Step3ReasoningParser` / `Step3p5ReasoningParser` | `step3_reasoning_parser.py` / `step3p5_reasoning_parser.py` | `<think>`/`</think>` | — | — | — |

## Families

### `BaseThinkingReasoningParser` subclasses (simple two-token)

`basic_parsers.py:18`. Subclass only needs `start_token` / `end_token` string properties. Get for free:
- Init-time vocab lookup + raise if token missing.
- `is_reasoning_end` via reverse scan (depth-safe wrt nested pairs).
- `extract_content_ids` via `input_ids.index(end_token_id) + 1 :`.
- `extract_reasoning_streaming` handling all four start-in-{prev,delta} × end-in-{prev,delta} cases.
- `extract_reasoning` via `.partition`.
- `count_reasoning_tokens` via depth counter.

Subclasses: DeepSeek-R1, Ernie45, OLMo3, Step3, Step3p5, and others — verify per file. **Not** Mistral, Qwen3, MiniMaxM2 or SeedOSS any more: those names now resolve through the adapter path (see the Path table above), so the `BaseThinkingReasoningParser` freebies below do not describe their behaviour.

### Delegating wrappers

`DeepSeekV3ReasoningParser` — holds an inner `_parser` that is either `DeepSeekR1ReasoningParser` (thinking on) or `IdentityReasoningParser` (thinking off). Decision made once at `__init__` from `chat_template_kwargs`. All six methods delegate.

`KimiK2ReasoningParser` — similar, holds `_identity_parser` iff `thinking=False`. When set, every method routes to it; otherwise custom thinking-on logic runs.

### Pure-identity

`IdentityReasoningParser` (`identity_reasoning_parser.py`) — `is_reasoning_end` always True, `extract_reasoning` returns `(None, all)`, streaming always returns `DeltaMessage(content=delta_text)`. Building block for delegating wrappers.

### Stateful

`HunyuanA13BReasoningParser` — token-ID state machine with `self.current_state ∈ {"idle", "think", "response"}`, `self.sequence_index`, `self.token_buffer`, `self.text_buffer`. Advances on each `delta_token_ids[0]`. Matches both fast and slow encodings of the state-transition phrases (`think_start_ids` vs `think_start_ids_fast`). Fresh instance per request is mandatory.

`GraniteReasoningParser` — text-phrase state machine for "Here is my thought process:" / "Here is my response:". Buffer-and-emit across deltas when phrases span boundaries. `_is_reasoning_start_substr` / `_is_response_start_substr` check whether partial text could still complete a phrase.

### Harmony

`GptOssReasoningParser` **is no longer a parser** as of v0.27.0 ([#45560](https://github.com/vllm-project/vllm/pull/45560)) — it is 60 lines of stub whose `is_reasoning_end`/`is_reasoning_end_streaming` return `True` and whose three extraction methods raise `NotImplementedError`. The token-ID prefix-sequence machinery it used to carry (`reasoning_end_token_ids_prefix` from `encode("<|channel|>final")`, `reasoning_max_num_between_tokens = 20` for interposed specials like `<|constrain|>json`, `eom_token_id = <|end|>` for multi-turn backward-scan safety) was **deleted** — `git grep reasoning_end_token_ids_prefix v0.27.0` returns nothing. Read `vllm/parser/harmony.py` instead. For a live multi-token-marker example, read `kimi_k3_reasoning_parser.py`.

## Non-obvious fields the serving layer reads

From `OpenAIServingChat` (`vllm/entrypoints/openai/chat_completion/serving.py`):

- `prompt_is_reasoning_end_arr[i]` — cached result of `reasoning_parser.is_reasoning_end(prompt_token_ids)`. Only computed once per choice because prompts are immutable per request. If True at prompt time (e.g. Qwen3 chat template with `enable_thinking=False` injected `<think>\n\n</think>\n\n`), streaming skips the parser entirely and routes all deltas to content.

- `reasoning_end_arr[i]` — per-delta latch: once set True, never calls `extract_reasoning_streaming` again for this choice. Set True either by `prompt_is_reasoning_end` or by `is_reasoning_end(previous_token_ids)` returning True.

- `request.include_reasoning` (default `True`) — suppresses `reasoning` from the response without changing inference. **No longer serving-layer-only**: [#44301](https://github.com/vllm-project/vllm/pull/44301) (v0.26.0) extended it to the Responses API and to the unified `Parser` interface, so at v0.27.0 the drop also happens inside `vllm/parser/abstract_parser.py`, `vllm/parser/engine/parser_engine.py` and `vllm/parser/harmony.py` (`if delta_message and not request.include_reasoning`). If you write an engine-path parser, `parse_delta` sees the flag; a legacy `ReasoningParser` still does not.

- `reasoning_parser_cls(tokenizer, chat_template_kwargs=chat_template_kwargs)` — the *only* kwarg guaranteed to be passed on instantiation, besides `tokenizer`. Anything else your parser reads from `kwargs` (e.g. `model_config`) may be `None`.
