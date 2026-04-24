# Per-parser matrix

One row per registered name. Canonical file is `vllm/reasoning/<file>.py`.

| Name | Class | File | Family | Start in prompt? | Thinking-disable switch | Truncation policy |
|---|---|---|---|---|---|---|
| `deepseek_r1` | `DeepSeekR1ReasoningParser` | `deepseek_r1_reasoning_parser.py` | `<think>`/`</think>` (vocab single-token) | Yes (modern templates) | None (always on) | `(all, None)` = all reasoning |
| `deepseek_v3` | `DeepSeekV3ReasoningParser` | `deepseek_v3_reasoning_parser.py` | Delegates → R1 or Identity | — | `chat_template_kwargs.thinking` OR `enable_thinking` (default: **off**) | Inherits from delegate |
| `glm45` / `holo2` | `DeepSeekV3ReasoningWithThinkingParser` | same file | Delegates → R1 or Identity | — | Same as `deepseek_v3` but default **on** | Inherits |
| `qwen3` / `mimo` | `Qwen3ReasoningParser` | `qwen3_reasoning_parser.py` | `<think>`/`</think>` | Yes (Qwen3.5+) — old 2507 template emits it | `chat_template_kwargs.enable_thinking` (default **on**) | Enabled: `(all, None)`. Disabled: `(None, all)` |
| `ernie45` | `Ernie45ReasoningParser` | `ernie45_reasoning_parser.py` | `<think>`/`</think>` + `<response>`/`</response>` | Optional — tolerates both | None | Base behavior |
| `gemma4` | — | `gemma4_reasoning_parser.py` | `<think>`/`</think>` w/ helper `gemma4_utils.py` | — | `chat_template_kwargs` | See file |
| `hunyuan_a13b` | `HunyuanA13BReasoningParser` | `hunyuan_a13b_reasoning_parser.py` | `<think>\n … \n</think>\n<answer>\n … \n</answer>` | No | None | Regex fallback |
| `hy_v3` | `HYV3ReasoningParser` | `hy_v3_reasoning_parser.py` | `<think>`/`</think>` (BaseThinking subclass) with `_identity_parser` delegation | Optional | `chat_template_kwargs.reasoning_effort` (or top-level `reasoning_effort`); value `"no_think"` routes to `IdentityReasoningParser`; default is `"no_think"` when unset | Inherits from delegate (identity when off, base when on) |
| `granite` | `GraniteReasoningParser` | `granite_reasoning_parser.py` | Phrases: "Here is my thought process:" / "Here is my response:" | Phrases in output | None | Falls through as content if phrases absent |
| `kimi_k2` | `KimiK2ReasoningParser` | `kimi_k2_reasoning_parser.py` | `<think>`/`</think>` + implicit end `<\|tool_calls_section_begin\|>` | Optional | `chat_template_kwargs.thinking` | `(remainder, None)` |
| `minimax_m2` | `MiniMaxM2ReasoningParser` | `minimax_m2_reasoning_parser.py` | Only `</think>` (no start) | N/A (no start) | None | `(all, None)` before `</think>` |
| `minimax_m2_append_think` | `MiniMaxM2AppendThinkReasoningParser` | same file | Prepends `<think>` to content; never separates | — | — | Always content |
| `mistral` | `MistralReasoningParser` | `mistral_reasoning_parser.py` | `[THINK]`/`[/THINK]` via `SpecialTokens.begin_think/end_think` | Depends on template | None | Complex: handles all 4 BOT/EOT combinations |
| `nemotron_v3` | `NemotronV3ReasoningParser` | `nemotron_v3_reasoning_parser.py` | R1 base + field swap | — | `chat_template_kwargs.enable_thinking=False` OR `force_nonempty_content=True` swaps reasoning↔content | Inherits R1 |
| `olmo3` | — | `olmo3_reasoning_parser.py` | `<think>`/`</think>` | — | — | — |
| `openai_gptoss` | `GptOssReasoningParser` | `gptoss_reasoning_parser.py` | Harmony `<\|channel\|>analysis<\|message\|>` … `<\|end\|>`; reasoning ends at `<\|channel\|>final<\|message\|>` | Yes (system msg) | — | `extract_reasoning` raises NotImplementedError — harmony branch only |
| `seed_oss` | `SeedOSSReasoningParser` | `seedoss_reasoning_parser.py` | `<seed:think>`/`</seed:think>` | — | — | — |
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

Subclasses: DeepSeek-R1, Qwen3, Ernie45, MiniMaxM2, OLMo3, SeedOSS, Step3, Step3p5, Mistral (via manual init), probably more.

### Delegating wrappers

`DeepSeekV3ReasoningParser` — holds an inner `_parser` that is either `DeepSeekR1ReasoningParser` (thinking on) or `IdentityReasoningParser` (thinking off). Decision made once at `__init__` from `chat_template_kwargs`. All six methods delegate.

`KimiK2ReasoningParser` — similar, holds `_identity_parser` iff `thinking=False`. When set, every method routes to it; otherwise custom thinking-on logic runs.

### Pure-identity

`IdentityReasoningParser` (`identity_reasoning_parser.py`) — `is_reasoning_end` always True, `extract_reasoning` returns `(None, all)`, streaming always returns `DeltaMessage(content=delta_text)`. Building block for delegating wrappers.

### Stateful

`HunyuanA13BReasoningParser` — token-ID state machine with `self.current_state ∈ {"idle", "think", "response"}`, `self.sequence_index`, `self.token_buffer`, `self.text_buffer`. Advances on each `delta_token_ids[0]`. Matches both fast and slow encodings of the state-transition phrases (`think_start_ids` vs `think_start_ids_fast`). Fresh instance per request is mandatory.

`GraniteReasoningParser` — text-phrase state machine for "Here is my thought process:" / "Here is my response:". Buffer-and-emit across deltas when phrases span boundaries. `_is_reasoning_start_substr` / `_is_response_start_substr` check whether partial text could still complete a phrase.

### Harmony

`GptOssReasoningParser` — all other parsers look for string delimiters; this one looks for token-ID prefix-sequences (`self.model_tokenizer.encode("<|channel|>final")`) because the harmony channel markers are multi-token. `reasoning_max_num_between_tokens = 20` — allows up to 20 special tokens to appear between `<|channel|>final` and `<|message|>` (the model may emit `<|constrain|>json` etc. in between). `eom_token_id = <|end|>` — stop looking backward if we hit previous-message boundary (multi-turn safety).

## Non-obvious fields the serving layer reads

From `OpenAIServingChat` (`vllm/entrypoints/openai/chat_completion/serving.py`):

- `prompt_is_reasoning_end_arr[i]` — cached result of `reasoning_parser.is_reasoning_end(prompt_token_ids)`. Only computed once per choice because prompts are immutable per request. If True at prompt time (e.g. Qwen3 chat template with `enable_thinking=False` injected `<think>\n\n</think>\n\n`), streaming skips the parser entirely and routes all deltas to content.

- `reasoning_end_arr[i]` — per-delta latch: once set True, never calls `extract_reasoning_streaming` again for this choice. Set True either by `prompt_is_reasoning_end` or by `is_reasoning_end(previous_token_ids)` returning True.

- `request.include_reasoning` — post-hoc nulls `reasoning` in the final response. Parser still runs; just the emitted field is dropped. Irrelevant for parser logic.

- `reasoning_parser_cls(tokenizer, chat_template_kwargs=chat_template_kwargs)` — the *only* kwarg guaranteed to be passed on instantiation, besides `tokenizer`. Anything else your parser reads from `kwargs` (e.g. `model_config`) may be `None`.
