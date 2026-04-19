# Writing a custom reasoning parser

When the user's thinking model uses delimiters not covered by the shipped parsers, author one. Two paths: **in-tree** (upstream contribution) or **plugin** (local).

## Path A — plugin (fastest)

### 1. Write the parser file

```python
# /srv/vllm-plugins/my_reasoning.py
from collections.abc import Sequence

from vllm.entrypoints.openai.engine.protocol import DeltaMessage
from vllm.reasoning import ReasoningParser, ReasoningParserManager
from vllm.reasoning.basic_parsers import BaseThinkingReasoningParser


@ReasoningParserManager.register_module(["my_model"])
class MyModelReasoningParser(BaseThinkingReasoningParser):
    """My reasoning model uses <|think|>…<|/think|>."""

    @property
    def start_token(self) -> str:
        return "<|think|>"

    @property
    def end_token(self) -> str:
        return "<|/think|>"
```

That's it if your delimiters are single vocab tokens. `BaseThinkingReasoningParser` supplies all five abstract methods + `count_reasoning_tokens`.

### 2. Start vLLM with the plugin

```bash
vllm serve MyOrg/MyModel \
    --reasoning-parser-plugin /srv/vllm-plugins/my_reasoning.py \
    --reasoning-parser my_model
```

Order matters: `--reasoning-parser-plugin` imports the file (runs `@register_module`), then `--reasoning-parser` looks up the registered name. If the file fails to import, vLLM logs the traceback and continues — but `--reasoning-parser my_model` will fail validation with "invalid reasoning parser: my_model (choose from {...})".

### 3. Verify

```bash
curl -s http://localhost:8000/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"MyOrg/MyModel","messages":[{"role":"user","content":"hi"}]}' \
    | jq '.choices[0].message | {reasoning, content}'
```

Both fields should be populated on a thinking-enabled request. (Field is `reasoning` on current main; older clients read `reasoning_content` — see note in SKILL.md.)

## Path B — in-tree

Add the file under `vllm/reasoning/my_model_reasoning_parser.py`, add a line to `_REASONING_PARSERS_TO_REGISTER` in `vllm/reasoning/__init__.py`:

```python
"my_model": ("my_model_reasoning_parser", "MyModelReasoningParser"),
```

Then `--reasoning-parser my_model` just works.

Add tests to `tests/reasoning/test_my_model_reasoning_parser.py`. Pattern matches existing files — parametrize over a corpus of `(input, expected_reasoning, expected_content)` for both streaming and non-streaming.

## When to inherit `BaseThinkingReasoningParser`

- Your delimiters are **single vocab tokens** (resolvable via `self.vocab.get(...)`).
- Start token may or may not appear in generated output (base handles both via `.partition`).
- End token is the sole reasoning-end signal (no implicit ends at tool-call sentinels etc.).
- Truncation policy: "everything before end token is reasoning" works for your model.

Override only the `start_token` / `end_token` properties. Optionally override `extract_reasoning_streaming` to handle your model's oddities (see `deepseek_r1_reasoning_parser.py` which adds a start-token-absent branch, or `qwen3_reasoning_parser.py` which rewrites it entirely for the prompt-side-`<think>` pattern).

## When to inherit `ReasoningParser` directly

- Multi-token delimiters (harmony, `<|channel|>analysis<|message|>`).
- Text-phrase delimiters (Granite "Here is my thought process:").
- Stateful parsing (Hunyuan token-ID state machine).
- Thinking-disabled short-circuit needed (delegate to `IdentityReasoningParser` — see DeepSeekV3 or KimiK2 patterns).

Implement all four required methods. Consider exposing `reasoning_start_str` / `reasoning_end_str` so `ReasoningConfig` can derive IDs automatically for structured-output backends.

## Full minimal custom parser (multi-token delimiter)

```python
from collections.abc import Iterable, Sequence
from transformers import PreTrainedTokenizerBase

from vllm.entrypoints.openai.engine.protocol import DeltaMessage
from vllm.reasoning import ReasoningParser, ReasoningParserManager


@ReasoningParserManager.register_module(["my_channels"])
class MyChannelsReasoningParser(ReasoningParser):
    def __init__(self, tokenizer: PreTrainedTokenizerBase, *args, **kwargs):
        super().__init__(tokenizer, *args, **kwargs)
        self._start_ids = tokenizer.encode("<|think|>", add_special_tokens=False)
        self._end_ids = tokenizer.encode("<|answer|>", add_special_tokens=False)

    @property
    def reasoning_start_str(self) -> str:
        return "<|think|>"

    @property
    def reasoning_end_str(self) -> str:
        return "<|answer|>"

    def is_reasoning_end(self, input_ids: Sequence[int]) -> bool:
        end = self._end_ids
        for i in range(len(input_ids) - len(end), -1, -1):
            if list(input_ids[i:i + len(end)]) == end:
                return True
        return False

    def is_reasoning_end_streaming(self, input_ids, delta_ids) -> bool:
        # Cheap check — may miss cases where end sequence spans boundary.
        # Call the full check as fallback.
        return self.is_reasoning_end(input_ids)

    def extract_content_ids(self, input_ids: list[int]) -> list[int]:
        end = self._end_ids
        for i in range(len(input_ids) - len(end), -1, -1):
            if list(input_ids[i:i + len(end)]) == end:
                return list(input_ids[i + len(end):])
        return []

    def extract_reasoning(self, model_output, request):
        start, end = "<|think|>", "<|answer|>"
        body = model_output.partition(start)[2] or model_output
        if end not in body:
            return body, None
        reasoning, _, content = body.partition(end)
        return reasoning, content or None

    def extract_reasoning_streaming(self, prev_text, cur_text, delta_text,
                                    prev_ids, cur_ids, delta_ids):
        end = "<|answer|>"
        if end in cur_text:
            # End has happened somewhere; determine if in this delta.
            if end in prev_text:
                return DeltaMessage(content=delta_text)
            # End is spanning into this delta.
            end_pos_in_cur = cur_text.find(end)
            # Carve the delta.
            start_of_delta_in_cur = len(cur_text) - len(delta_text)
            if end_pos_in_cur >= start_of_delta_in_cur:
                carve = end_pos_in_cur - start_of_delta_in_cur
                reasoning = delta_text[:carve]
                content = delta_text[carve + len(end):]
                return DeltaMessage(
                    reasoning=reasoning or None,
                    content=content or None,
                )
        return DeltaMessage(reasoning=delta_text)
```

Note the awkwardness of `extract_reasoning_streaming` when the delimiter spans multiple tokens — you can't simply check `end_token_id in delta_token_ids`. This is why `BaseThinkingReasoningParser` is preferred when it fits.

## Testing checklist

Cover both paths:

### Non-streaming (`extract_reasoning`)

- [ ] Normal: `<start>think<end>answer` → `("think", "answer")`.
- [ ] Start missing (prompt-side): `think<end>answer` → `("think", "answer")`.
- [ ] End missing (truncation): `<start>think` → parser's documented policy.
- [ ] Empty content after end: `<start>think<end>` → `("think", None)`.
- [ ] Empty reasoning: `<start><end>answer` → `("", "answer")` or `(None, "answer")`.
- [ ] Nested: `<start>a<start>b<end>c<end>d` — first `<end>` splits; document the behavior.

### Streaming (`extract_reasoning_streaming`)

- [ ] Delta is only `<start>` token → returns None.
- [ ] Delta is only `<end>` token → returns None.
- [ ] End token spans two deltas → reasoning on first, content on second (and possibly an empty-ish delta in between).
- [ ] Both start and end in same delta → single `DeltaMessage` with both fields set.
- [ ] End token arrived previously, new delta is pure content → `DeltaMessage(content=delta_text)`.
- [ ] `is_reasoning_end(previous_token_ids)=True` should route subsequent deltas as content.

### Integration

- [ ] With `--guided-json` + streaming: xgrammar starts enforcing after `is_reasoning_end` flips.
- [ ] With `--tool-call-parser X --enable-auto-tool-choice`: tool calls in content half are extracted.
- [ ] With `chat_template_kwargs={"enable_thinking": False}` (if applicable): parser short-circuits to content-only.
- [ ] Two concurrent streaming requests: no state bleeds between them (test with class-level `id(self)` assertions if paranoid).

## Shape checklist

Before shipping:

- Single vocab-token delimiter? → `BaseThinkingReasoningParser`.
- Thinking-disable switch needed? → Delegating wrapper around Identity + thinking parser.
- Delimiters multi-token, text-phrase, or channel-based? → Direct `ReasoningParser` subclass.
- Model stops reasoning implicitly at some other token? → Add that token to `is_reasoning_end` / `is_reasoning_end_streaming` / `extract_content_ids` / `extract_reasoning` / `extract_reasoning_streaming`. Five places. Miss one and it will bite.
- State on `self`? → Assert fresh instance per request by logging `id(self)` at `__init__`.
