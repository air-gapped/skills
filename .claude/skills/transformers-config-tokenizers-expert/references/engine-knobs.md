# Engine tokenizer-adjacent knobs — vLLM + sglang

Every flag and lifecycle hook a preflight tool must understand to
predict how vLLM and sglang will *use* the tokenizer state. Not the
chat-template layer (covered by `chat-template-contract.md`) — the
runtime knobs.

Primary sources:
- vLLM `main` (~v0.19.1, 2026-04-18)
- sglang `main` (snapshot 2026-04-21)

File:line citations are against `main`; line numbers drift
release-to-release but symbol names are stable.

---

## vLLM `chat_template_kwargs` plumbing {#chat-template-kwargs-allowlist}

Flow:

```
CLI --default-chat-template-kwargs  (vllm/entrypoints/openai/cli_args.py:109-128)
  ↓
OpenAIServingChat.__init__          (chat_completion/serving.py:102-177)
  stores self.default_chat_template_kwargs
  ↓
create_chat_completion              (chat_completion/serving.py:281)
  calls _prepare_extra_chat_template_kwargs(
    request.chat_template_kwargs,
    self.default_chat_template_kwargs,
  )
  ↓
_prepare_extra_chat_template_kwargs (engine/serving.py:426-433)
  return default_kwargs | request_kwargs   # dict-union, REQUEST WINS
  ↓
renderer.preprocess_chat
  ↓
safe_apply_chat_template            (renderers/hf.py:379-424)
  ↓
resolve_chat_template_kwargs        (renderers/hf.py:352-377)  ← ALLOWLIST
  ↓
tokenizer.apply_chat_template(**resolved)
```

### The allowlist {#pr-27622}

`vllm/renderers/hf.py:352-377`:

```python
def resolve_chat_template_kwargs(
    tokenizer, chat_template, chat_template_kwargs,
    raise_on_unexpected=True,
):
    unexpected_vars = {"chat_template", "tokenize"}
    fn_kw = {k for k in chat_template_kwargs
             if supports_kw(tokenizer.apply_chat_template, k,
                            allow_var_kwargs=False)}
    template_vars = _cached_resolve_chat_template_kwargs(chat_template)
    hf_base_params = _get_hf_base_chat_template_params()
    accept_vars = (fn_kw | template_vars | hf_base_params) - unexpected_vars
    return {k: v for k, v in chat_template_kwargs.items() if k in accept_vars}
```

Unknown kwargs are filtered silently. No raise.

**HF base params inspection** at `renderers/hf.py:334-347`:

```python
@lru_cache
def _get_hf_base_chat_template_params():
    sig = inspect.signature(PreTrainedTokenizer.apply_chat_template)
    return set(sig.parameters.keys())
```

Uses `inspect.signature` on `PreTrainedTokenizer` base class. This is
the fix from PR #27622 (merged 2025-10-28).

### Version gate

- PR #27622 merged 2025-10-28
- v0.11.0 shipped 2025-10-02 (pre-fix)
- **v0.11.1 shipped 2025-11-18** (first release with fix)

Pre-v0.11.1: `supports_kw(..., allow_var_kwargs=False)` excludes any
tokenizer whose `apply_chat_template` signature uses `**kwargs`.
Kimi-K2's custom `TikTokenTokenizer` uses `**kwargs`, so `add_generation_prompt`,
`enable_thinking`, `tools` were silently dropped. Symptom: empty tool
calls, `finish_reason: stop`, no error.

---

## sglang `chat_template_kwargs` plumbing

`python/sglang/srt/entrypoints/openai/serving_chat.py:524-527`:

```python
extra_template_kwargs = {}
if request.reasoning_effort is not None:
    extra_template_kwargs["reasoning_effort"] = request.reasoning_effort
if request.chat_template_kwargs:
    extra_template_kwargs.update(request.chat_template_kwargs)
```

**No allowlist.** Literal `dict.update`. Any key reaches
`apply_chat_template`. Matches pre-PR-27622 vLLM in looseness, but
for a different reason: sglang never filtered, while vLLM filtered
wrongly and was fixed.

Template invocation at `serving_chat.py:538-550`:

```python
prompt_ids = self.tokenizer_manager.tokenizer.apply_chat_template(
    openai_compatible_messages,
    tokenize=True,
    add_generation_prompt=True,
    tools=tools,
    return_dict=False,
    **extra_template_kwargs,
)
```

### sglang has no `trust_request_chat_template`

Request kwargs are always accepted. For multi-tenant deployments
where request kwargs need gating, add the filter at a reverse proxy
or gateway layer — not in sglang.

---

## `trust_request_chat_template` (vLLM only)

CLI field at `vllm/entrypoints/openai/cli_args.py:118-120`. Default
`False`.

Enforced at `vllm/entrypoints/openai/engine/serving.py:415-425`:
`_validate_chat_template` returns a 4xx error if the flag is False
AND the request carries `chat_template` or `chat_template_kwargs`.

Set to `True` only in deployments where every caller is already
trusted (e.g. behind an auth-gated gateway).

---

## `skip_special_tokens`

### vLLM

- Field at `vllm/entrypoints/openai/chat_completion/protocol.py:208`.
- Default `True`.
- Threaded through `to_sampling_params` at line 516.
- Consumed by the incremental detokenizer (see below).

### sglang

- Field at `python/sglang/srt/sampling/sampling_params.py:102`.
- Default `True`.
- Hard overrides to `False` at three sites in
  `serving_chat.py`:
  - Line 306: `if is_gpt_oss or is_gemma4`
  - Line 315: `if request.tools and tool_choice != "none"`
  - Line 397: Mistral reasoning parser with non-"none" `reasoning_effort`

These three sites are sglang's equivalent of vLLM's per-parser
`adjust_request` hooks — hardcoded instead of extensible.

---

## `include_stop_str_in_output` (vLLM)

Field at `protocol.py:212`. Default `False`. When `True`, engine
appends the matched stop substring to the final output.

sglang has no direct equivalent exposed on the OpenAI endpoint;
internal handling is similar but surface differs.

---

## vLLM `adjust_request` lifecycle

Abstract contract at `vllm/parser/abstract_parser.py:216-227`:

```python
def adjust_request(self, request):
    """Modify request parameters (e.g., setting structured output
    schemas for tool calling)"""
    return request
```

Subclass contracts:
- Reasoning parser base: `vllm/reasoning/abs_reasoning_parsers.py:157-160`
  — no-op default.
- Tool parser base: `vllm/tool_parsers/abstract_tool_parser.py:80-106`
  — on requests with `tools`, extracts each tool's JSON schema and
  sets `request.structured_outputs` / `request.text`; clears
  `response_format`. Does NOT modify `tools`, `stop`, or
  `chat_template_kwargs`.

### Call site

`vllm/entrypoints/serve/render/serving.py:372-383`:

```python
request = reasoning_parser(tokenizer, model_config=...).adjust_request(request=request)
request = tool_parser(tokenizer, request.tools).adjust_request(request=request)
```

Order: **reasoning first, then tool.** Tool parser can override what
reasoning parser set.

### Per-model overrides

- `vllm/tool_parsers/hermes_tool_parser.py`
- `vllm/tool_parsers/kimi_k2_tool_parser.py`
- `vllm/tool_parsers/gemma4_tool_parser.py`
- `vllm/tool_parsers/deepseekv32_tool_parser.py`
- `vllm/tool_parsers/glm4_moe_tool_parser.py`

Each can mutate any request field before `to_sampling_params`.
Common mutations: stop strings (to include `</tool_call>`),
structured-output grammar, response format.

### sglang has no analog

Closest is `custom_logit_processor` (logit-level, not request-level).

---

## Stop-token merge {#stop-token-merge}

### vLLM

`vllm/v1/engine/input_processor.py:282-295`:

```python
sampling_params.update_from_generation_config(
    self.generation_config_fields,
    self.renderer.get_eos_token_id(),
)
if self.tokenizer is not None:
    sampling_params.update_from_tokenizer(self.tokenizer)
```

`update_from_generation_config` at `vllm/sampling_params.py:540-560`:
- Sets `_eos_token_id` from renderer-supplied id (unless `ignore_eos=True`)
- Adds primary EOS to `_all_stop_token_ids` (line 548)
- Reads `generation_config.eos_token_id` (often a list), dedupes,
  **appends** to `stop_token_ids` (lines 558-559) when
  `ignore_eos=False`

`update_from_tokenizer` at `sampling_params.py:562-603` handles
bad-words only; does NOT re-add tokenizer EOS (already handled by
generation_config).

**Ignore-EOS semantics**: `ignore_eos=True` suppresses the entire
EOS merge. Request-level `stop=[...]` still applies.

### sglang

`python/sglang/srt/configs/model_config.py:580-598`:

```python
def _get_hf_eos_token_id(self):
    eos_ids = getattr(self.hf_config, "eos_token_id", None)
    if eos_ids is not None:
        eos_ids = {eos_ids} if isinstance(eos_ids, int) else set(eos_ids)
    if eos_ids is None:
        eos_ids = set()
    if self.hf_generation_config:
        generation_eos_ids = getattr(self.hf_generation_config, "eos_token_id", None)
        if generation_eos_ids:
            ...
            eos_ids = eos_ids | generation_eos_ids
    return eos_ids
```

Strict union of `hf_config.eos_token_id` and `hf_generation_config.eos_token_id`.
Neither source wins. Cached as `self.hf_eos_token_id`.

Request-level merge at `serving_chat.py:614-623`:

```python
stop = copy.copy(conv.stop_str or [] if not request.ignore_eos else [])
if request.stop:
    if isinstance(request.stop, str):
        stop.append(request.stop)
    else:
        stop.extend(request.stop)
```

**`ignore_eos=True` divergence**: sglang also drops template `stop_str`
under this flag; vLLM only drops EOS, not template stops.

---

## Incremental detokenizer {#incremental-detokenizer}

### vLLM — fast path

`vllm/v1/engine/detokenizer.py:82`:

```python
class FastIncrementalDetokenizer:
    ...
    self.stream = DecodeStream(skip_special_tokens=self.skip_special_tokens)
```

Uses `tokenizers.DecodeStream` directly. Added/special-ID dict at
lines 87-101 suppresses auto-space insertion between consecutive
specials when `spaces_between_special_tokens=True`.

### vLLM — slow path

`vllm/tokenizers/detokenizer_utils.py:98-167`:

```python
def detokenize_incrementally(
    tokenizer, all_input_ids, prev_tokens,
    prefix_offset, read_offset,
    skip_special_tokens, spaces_between_special_tokens,
):
    ...
    # lines 149-157: byte-fallback guard
    if new_text.endswith("�") or not new_text:
        return prev_tokens, prefix_offset, read_offset, ""
```

Word-boundary mechanism:
- `prefix_offset` / `read_offset` lag window over `prev_tokens`
- Decode `prev_tokens[prefix_offset:read_offset]` and
  `prev_tokens[prefix_offset:]`, diff strings
- U+FFFD or shrinking-diff → return empty (defer flush)

`INITIAL_INCREMENTAL_DETOKENIZATION_OFFSET = 5` at line 57.

### Why `skip_special_tokens=False` can break word boundaries

With `skip_special_tokens=True`, a special token is dropped before
the `convert_tokens_to_string` diff. The `▁` word-start marker on
the following real token converts to a space correctly.

With `skip_special_tokens=False`, the special is kept. Depending on
the tokenizer's `added_tokens_decoder` handling, the diff can collapse
or auto-spacing misses the boundary:

```
Expected: hello<|im_end|> world
Actual:   hello<|im_end|>world
```

`spaces_between_special_tokens=True` re-inserts those spaces — but
only via the added/special-id dict at `detokenizer.py:87-101`,
which does not cover every edge case in the fast path.

### sglang — separate process

`python/sglang/srt/managers/detokenizer_manager.py:19`:

> DetokenizerManager is a process that detokenizes the token ids.

`DecodeStatus` dataclass at lines 57-63:

```python
@dataclasses.dataclass
class DecodeStatus:
    decoded_text: str
    decode_ids: List[int]
    surr_offset: int
    read_offset: int
    sent_offset: int = 0
```

Four offsets (one fewer than vLLM — the surrounding-offset trick
collapses the prefix offset). Same U+FFFD guard at lines 274-285.

### Issue #22510 — the red herring

Reporter: `solitude-alive`, 2026-04-10. Initial symptom: Gemma-4-31B-it
with `--incremental-streaming-output` and `--reasoning-parser gemma4`
produced word-fragment streaming output. The sampling params log
showed `skip_special_tokens=False` (forced by `--reasoning-parser gemma4`).

**Actual root cause (PR #22549, merged 2026-04-12, commit `9e7dfcc`)**:
double-delta-slicing bug in `serving_chat.py`. Issue #21037 added
incremental streaming to `tokenizer_manager.py`, but `serving_chat.py`
still sliced by the accumulated buffer length, re-stripping the
already-incremental delta.

Fix at `python/sglang/srt/entrypoints/openai/serving_chat.py:736-740`:

```python
if self.tokenizer_manager.server_args.incremental_streaming_output:
    # content["text"] is already the incremental delta
    delta = content["text"]
else:
    delta = content["text"][len(stream_buffer):]
```

**Lesson:** `skip_special_tokens=False` was NOT the cause. It was
the first visible server-log field, which led reporters and
first-pass diagnosers astray. Detokenizer itself is fine.

---

## MTP speculative decoding × tokenization

### sglang

`python/sglang/srt/speculative/spec_info.py:14-18`:

```python
class SpeculativeAlgorithm(enum.Enum):
    DFLASH = ...
    EAGLE = ...
    EAGLE3 = ...
    STANDALONE = ...
    NGRAM = ...
    NONE = ...
```

**No `MTP` enum value.** MTP in sglang is a model-architecture pattern
(files like `qwen3_5_mtp.py`, `mimo_mtp.py`, `step3p5_mtp.py`,
`nemotron_h_mtp.py`, `qwen3_next_mtp.py`, `exaone_moe_mtp.py`) —
six MTP-head variants.

MTP-enabled models run via `--speculative-algorithm EAGLE`. Draft
tokens from the MTP head are emitted as **integer IDs**, verified by
the target model as IDs, and reach `DetokenizerManager` as an
ordinary `BatchTokenIDOutput`. The tokenizer is NOT re-invoked per
draft.

**Preflight-relevant claim:** MTP cannot introduce tokenization-layer
bugs. Any apparent tokenization regression under MTP is caused
elsewhere (detokenizer, serving_chat, stop-token mismatch, template).

### vLLM

Similar architecture — draft tokens are IDs. No tokenizer re-invocation.

---

## Mistral / tekken path (vLLM)

`vllm/tokenizers/mistral.py:128`:

```python
class MistralTokenizer(TokenizerLike):
    IS_MISTRAL_TOKENIZER = True
```

Delegates to `MistralCommonBackend.from_pretrained` at line 130-144.

Auto-detection at `vllm/tokenizers/registry.py:87-111`:

```python
def resolve_tokenizer_args(tokenizer_mode, ...):
    # "auto" mode
    for pattern in ("tekken.json", "tokenizer.model.v*"):
        if any(re.match(pattern, f) for f in repo_files):
            return "mistral"
    return "hf"
```

**`tokenizer-mode mistral` silently ignores `--chat-template`.**
Warning only. Tracked in vllm-project/vllm#25401.

---

## Gemma4Processor — not a special branch

vLLM registry has no dedicated `Gemma4Processor` branch. The
processor is loaded via the generic `AutoProcessor.from_pretrained`
path (`vllm/transformers_utils/processor.py`). Underlying tokenizer
is still a standard HF AutoTokenizer chosen via the normal registry
path.

---

## `/tokenize` and `/detokenize` endpoints (vLLM)

`vllm/entrypoints/serve/tokenize/serving.py:29-125`. Chat-mode
tokenize honors:
- `add_generation_prompt`
- `continue_final_message`
- `chat_template`
- `chat_template_kwargs`
- `tools`

Shares preprocessing with `/v1/chat/completions` (including
`adjust_request`). `/detokenize` takes only `model` + `tokens`; does
NOT accept `skip_special_tokens` per-request. To control
special-token rendering in detokenize, configure server-side.

**Side effect:** `/tokenize` with `tools=[...]` runs the tool
parser's `adjust_request`, which may mutate
`request.structured_outputs` / `request.text`. If callers reuse the
same request object across `/tokenize` → `/v1/chat/completions`, the
second call sees the mutation.

---

## Quick reference — divergence summary

| Concern | vLLM | sglang |
|---|---|---|
| Chat-template kwargs allowlist | Yes (post PR #27622, v0.11.1+) | No — literal dict update |
| Trust request chat template | `--trust-request-chat-template` flag | No equivalent |
| Bundled templates dir | `vllm/transformers_utils/chat_templates/` | No direct equivalent (FastChat `conversation.py` registry) |
| `adjust_request` hook | Per-parser (reasoning + tool), extensible | Hardcoded three sites |
| EOS merge | `generation_config.eos_token_id` appended to `stop_token_ids` | Union of `hf_config` + `hf_generation_config` EOS sets |
| `ignore_eos` scope | Drops EOS merge only | Drops EOS merge AND template `stop_str` |
| Detokenizer location | In-engine process | Separate DetokenizerManager process |
| Detokenizer offsets | `prefix_offset` + `read_offset` | `surr_offset` + `read_offset` + `sent_offset` |
| Tool choice affects tokenizer | No (passed through to parser) | Yes — forces `skip_special_tokens=False` at serving_chat.py:315 |

---

## Primary sources

**vLLM:**
- `vllm/entrypoints/openai/cli_args.py:109-128, 334-337`
- `vllm/entrypoints/openai/chat_completion/serving.py:102-177, 281`
- `vllm/entrypoints/openai/chat_completion/protocol.py:208, 212, 279-284, 516`
- `vllm/entrypoints/openai/engine/serving.py:415-425, 426-433`
- `vllm/renderers/hf.py:334-347, 352-377, 379-424`
- `vllm/entrypoints/serve/render/serving.py:372-383`
- `vllm/tool_parsers/abstract_tool_parser.py:80-106`
- `vllm/sampling_params.py:540-603`
- `vllm/v1/engine/input_processor.py:282-295`
- `vllm/v1/engine/detokenizer.py:82-101, 149-189`
- `vllm/tokenizers/detokenizer_utils.py:98-167`
- `vllm/tokenizers/registry.py:87-157`
- `vllm/tokenizers/mistral.py:128-165`
- `vllm/entrypoints/serve/tokenize/serving.py:29-125`
- vLLM PR #27622 (merged 2025-10-28, shipped v0.11.1 2025-11-18)
- vLLM issue #25401 (`tokenizer-mode mistral` silent `--chat-template`)

**sglang:**
- `python/sglang/srt/entrypoints/openai/serving_chat.py:306, 315, 397,
  524-527, 538-550, 614-623, 736-740`
- `python/sglang/srt/sampling/sampling_params.py:80-170`
- `python/sglang/srt/managers/detokenizer_manager.py:19, 57-63, 164-181, 250-310`
- `python/sglang/srt/configs/model_config.py:580-598`
- `python/sglang/srt/utils/hf_transformers/tokenizer.py:165-171, 292, 311-317`
- `python/sglang/srt/speculative/spec_info.py:14-18`
- `python/sglang/srt/parser/reasoning_parser.py:436-451`
- `python/sglang/srt/parser/conversation.py:57-58`
- sglang issue #22510, PR #22549 (merged 2026-04-12, commit `9e7dfcc`)
- sglang issue #21037 (introduced incremental streaming mode)
