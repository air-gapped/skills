# Hall of shame — verified 2026 tokenizer/config pathologies

Every incident in this file is backed by a citable source: the repo
file itself on HF Hub, or an upstream issue/PR. Claims the author of
the skill could not verify are flagged explicitly.

The pattern: labs ship tokenizer/config states that engines read
differently. Drift between `generation_config.json`,
`tokenizer_config.json`, `config.json`, and the chat template is the
norm, not the exception.

---

## GLM-5.1 — three-ID EOS including turn primers {#glm-5-1-three-id-eos}

**Repo:** `zai-org/GLM-5.1` and `zai-org/GLM-5.1-FP8`
**Tokenizer class:** `TokenizersBackend` (requires transformers ≥5.0)
**Files involved:** `generation_config.json`, `config.json`,
`tokenizer_config.json`

### The EOS triple

`generation_config.json`:

```json
"eos_token_id": [154820, 154827, 154829],
"pad_token_id": 154820
```

`config.json` (same): `[154820, 154827, 154829]`.

`tokenizer_config.json`:

```json
"eos_token": "<|endoftext|>",  // resolves to 154820 only
```

| ID | Token | Role |
|---|---|---|
| 154820 | `<|endoftext|>` | canonical terminator |
| 154827 | `<|user|>` | next-turn primer |
| 154829 | `<|observation|>` | tool-result-turn primer |

### Consequence

- vLLM + sglang union-merge the three-ID list into `stop_token_ids`.
  Engines stop whenever the template emits any of the three —
  including at turn boundaries where 154827 / 154829 are written as
  role primers.
- Any client forcing `skip_special_tokens=False` (to keep `<think>`
  visible, or for reasoning parser compatibility) sees
  `<|user|>` / `<|observation|>` leak into output.
- Transformers-based renderers that read only `tokenizer.eos_token_id`
  see **154820 only** and produce runaway completions that never
  stop at turn boundaries.

### extra_special_tokens list shape

```json
"extra_special_tokens": [
  "<|endoftext|>", "[MASK]", "[gMASK]", "[sMASK]",
  "<sop>", "<eop>", "<|system|>", "<|user|>",
  "<|assistant|>", "<|observation|>",
  "<|begin_of_image|>", ...
]
```

Crashes transformers `<5.0` readers with `AttributeError: 'list'
object has no attribute 'keys'`.

### Missing files

- `special_tokens_map.json` — absent (v5 consolidation; confirmed
  against repo tree).
- `added_tokens.json` — absent.
- `tokenizer.model` — absent (uses `tokenizer.json` only).

### Pad == EOS

`"pad_token_id": 154820` = `eos_token_id[0]`. Classic footgun for
batched training (padding collapses to EOS).

**Sources:**
- `huggingface.co/zai-org/GLM-5.1/blob/main/tokenizer_config.json`
- `huggingface.co/zai-org/GLM-5.1/blob/main/generation_config.json`
- `huggingface.co/zai-org/GLM-5.1-FP8/blob/main/tokenizer_config.json`

---

## GLM-5.1-FP8 — orphan-commit trap {#glm-5-1-ap-45}

Critical audit risk pattern.

Commit `6ad52ee1b15cd57ab3cc4dda698313579a47536e` (2026-04-10,
"Update chat_template.jinja") on `zai-org/GLM-5.1-FP8` contains the
proper list-handling branch. Users reading vLLM issues assume it
shipped on main. **It did not.** The commit is unreachable from
`refs/heads/main`. HF API `/refs` shows `refs/heads/main` at
`a92f8155`.

### Symptom

- A preflight run against the post-patch SHA still returns
  `template_bug` with critical exceptions at `File "<template>", line 89`.
- Users manually commit-pick the fix via `git fetch <sha>` and
  apply locally — but automated HF loaders see the unpatched `main`.

### Preflight rule

Always check `/refs` on the HF API before trusting a commit SHA:

```python
from huggingface_hub import HfApi
api = HfApi()
refs = api.list_repo_refs("zai-org/GLM-5.1-FP8")
main_sha = next(b.target_commit for b in refs.branches if b.name == "main")
assert main_sha == expected_sha, "Orphan-commit trap"
```

### Tool-call string vs dict shape

Unfixed. Assistant tool-call path line 89 of the template:

```jinja
{% set _args = tc.arguments %}{% for k, v in _args.items() %}…
```

When `tc.arguments` is a JSON **string** (OpenAI wire shape),
`.items()` raises `UndefinedError` under
`ImmutableSandboxedEnvironment`. Template has no JSON-parse filter
(`fromjson` doesn't exist in transformers' Jinja env). The GLM
per-key `<arg_key>/<arg_value>` format cannot be produced from
string-shape arguments without parsing.

Requires engine-side pre-parse or parser redesign.

### None-content leak (line 64)

```jinja
{%- set content = visible_text(m.content) %}
```

When `m.content is none`, `visible_text()` returns `None`. Without a
`content is none` guard, line 80's `content.strip()` emits the
literal string `"None"` into the prompt.

**Source:** HF repo tree + `/refs` API on `zai-org/GLM-5.1-FP8`

---

## Gemma-4-26B-A4B-it — multi-ID EOS {#gemma-4-ap-45}

**Repo:** `google/gemma-4-26B-A4B-it` (verified), not `gemma-4-31B-it`
(SKU not found on HF Hub as of 2026-04-21).
**Tokenizer class:** `GemmaTokenizer` + `Gemma3Processor` (multimodal)
**Files involved:** `tokenizer_config.json`, `generation_config.json`,
separate `chat_template.jinja`

### EOS list

`generation_config.json`:

```json
"eos_token_id": [1, 106, 50]
```

`config.json`: `[1, 106]` (two-element).

`tokenizer.json` (LFS-stored, not readable inline via WebFetch) —
per the project's finding documents, the IDs resolve to:
- 1 = `<eos>`
- 106 = `<turn|>` (turn-close marker)
- 50 = `<|tool_response>` (tool-response marker)

**Caveat:** direct tokenizer.json content verification blocked by
LFS. IDs are as-claimed in finding docs; preflight should decode
against loaded tokenizer at runtime.

### Consequence — EOS mismatch

Token 50 (`<|tool_response>`) only stops generation on code paths
reading `generation_config.json`. Paths reading `config.json` miss it.

### Scalar-null bug

Stock `format_argument` macro in `chat_template.jinja` (lines 118-147)
has no branch for Python `None`. Jinja's `str(None)` renders literal
`"None"` instead of JSON `null`:

```
# Stock (broken):
nullable_field:None

# Fixed:
nullable_field:null
```

Fix: add `is none → null` branch in `format_argument` (6 lines).

### System message list-content leak

Line 189 of `chat_template.jinja`:

```jinja
{{ messages[0]['content'] | trim }}
```

When `content` is OpenAI-format list `[{"type": "text", "text": "..."}]`,
`trim` filter stringifies and emits Python repr:

```
[{'type': 'text', 'text': 'You answer in one sentence.'}]
```

In-loop handler (lines 227-254) correctly checks `is string` vs
`is sequence` — but system-message header path was missed.

### Chat-template sidecar not loaded (issue #45205)

`google/gemma-4-E2B-it`, `gemma-4-E4B-it` on transformers 5.5.0:
`chat_template.jinja` ships as separate file but isn't auto-loaded.
`tokenizer.chat_template` is `None`. Workaround: manual
`hf_hub_download`.

Open as of 2026-04-21.

### added_tokens_decoder absent

`tokenizer_config.json` has no `added_tokens_decoder` key. Added
tokens live in `tokenizer.json` (LFS). Preflight tools scanning
tokenizer_config alone see an empty structural set.

**Sources:**
- `huggingface.co/google/gemma-4-E4B/blob/main/tokenizer_config.json`
- `huggingface.co/google/gemma-4-E4B/blob/main/generation_config.json`
- `huggingface.co/google/gemma-4-26B-A4B-it/blob/main/generation_config.json`
- transformers issue #45205

---

## Kimi-K2.6 — half-fix EOS split-brain {#kimi-k2-6-half-fix}

**Repo:** `moonshotai/Kimi-K2.6` (2b2b88e3, lastModified 2026-04-20)
**Tokenizer class:** Custom `TikTokenTokenizer` via `trust_remote_code`
**Backend:** `PythonBackend` (slow)
**Files involved:** `tokenizer_config.json`, `config.json`,
`generation_config.json`, `chat_template.jinja`

### The half-fix

K2.5 had a known EOS mismatch: `config.json` + `generation_config.json`
listed 163585 (`[EOS]`); `tokenizer_config.json` declared
`eos_token: "[EOS]"` (also 163585). Template emitted `<|im_end|>`
(163586) — neither matched.

K2.6 flipped `config.json` + `generation_config.json` to **163586**
(`<|im_end|>`) but **did not update `tokenizer_config.json`**. Result:

| Engine / tool | Reads | Stops on |
|---|---|---|
| vLLM | `tokenizer_config.json` | 163585 (`[EOS]`) — template never emits this |
| sglang | `generation_config.json` + `config.json` | 163586 (`<|im_end|>`) — correct |
| `transformers.apply_chat_template` render | `tokenizer_config.json` | Renders `[EOS]` literal |

### Absent tokenizer.json

Kimi ships no `tokenizer.json`. Engines fall back to slow custom-code
path via `trust_remote_code=True`. Preflight must:
- Require `trust_remote_code=True`
- `pip install tiktoken`
- Know that `tokenizer.backend_tokenizer` is unavailable (no Rust
  backend)

### Discussion #31 on HF — the EOS ambiguity thread

`huggingface.co/moonshotai/Kimi-K2-Instruct/discussions/31` records
that `tokenization_kimi.py`, `tokenizer_config.json`, and `config.json`
all say `[EOS]`, while only `generation_config.json` signals
`163586`. Still open.

### Tool-call ID format — vLLM parser mismatch

`vllm/tool_parsers/kimi_k2_tool_parser.py:66`:

```python
r"(?P<tool_call_id>[^<]+:\d+)"
```

Regex **requires** `something:N` shape. OpenAI SDK generates IDs like
`call_abc123` — no colon, no digits. Parser silently drops those
tool calls. Same unfixed issue since K2.5 issues #106 and #22.

### Reasoning kwarg: `preserve_thinking`

K2.6 added `preserve_thinking` kwarg (new, defaults `false`).

K2.6 template reads `message.reasoning` first, falls back to
`reasoning_content`. K2.5 read only `reasoning_content`. Engine
integrations that haven't updated to emit `reasoning` lose thinking
persistence on K2.6.

### Special-token flag — deliberately special=False

Finding `SPECIAL_TOKEN_FLAG_WRONG` fires on six tokens (`<think>`,
`<|tool_call_begin|>`, etc.) declared `special=False`. This is
**intentional** — vLLM's parser uses literal-text regex on decoded
strings; if these were `special=True`, they'd be filtered by
`skip_special_tokens=True` (default), and the parser would fail.

**Preflight rule:** don't auto-flag all `special=False` structural
markers. Cross-reference against the engine's parser source.

**Sources:**
- `huggingface.co/moonshotai/Kimi-K2-Instruct/blob/main/tokenization_kimi.py`
- `huggingface.co/moonshotai/Kimi-K2-Instruct/discussions/31`
- `huggingface.co/moonshotai/Kimi-K2.6/blob/main/tokenizer_config.json`
- vLLM `tool_parsers/kimi_k2_tool_parser.py:66`

---

## Qwen3 family — `<|im_end|>` dual role + base flip

**Verified repos:** `Qwen/Qwen3-0.6B`, `Qwen/Qwen3.5-35B-A3B-Base`

### Qwen3-0.6B (Instruct-like): `<|im_end|>` = EOS AND turn terminator

`tokenizer_config.json`:

```json
"eos_token": "<|im_end|>",
"pad_token": "<|endoftext|>",
"151645": {"content": "<|im_end|>", "special": true},
"additional_special_tokens": ["<|im_start|>", "<|im_end|>", ...]
```

ID 151645 is simultaneously:
- EOS (stop token)
- Turn terminator (emitted at every assistant/user/system turn close)
- Listed in `additional_special_tokens`

Deduplication matters: counting it twice or dropping it once breaks
generation.

### Qwen3.5-Base: flips EOS to `<|endoftext|>`

`tokenizer_config.json`:

```json
"eos_token": "<|endoftext|>",
"pad_token": "<|endoftext|>"
```

**Base variant differs from chat-tuned Qwen3.** Preflight that
hardcodes `<|im_end|>` for all Qwen3-family stops generates runaway
completions on base variants.

Related: QwenLM/Qwen3 issue #927 documents `config.json` vs
`tokenizer_config.json` inconsistency on Qwen2.5-Base — pattern
propagates to Qwen3.5.

### Date grounding (Qwen3.6-family)

Without a date anchor in the system prompt, Qwen3.6 refuses to fabricate
ISO dates from relative references ("tomorrow", "next week"). Inject:

```jinja
{{- '<|im_start|>system\nToday is ' + strftime_now("%-d %B %Y") + '.\n\n' }}
```

**Not a model bug** — model correctly asks for clarification when
required params are missing. BFCL distinguishes this case via
`multi_turn_miss_param` category (asking IS pass).

**Sources:**
- `huggingface.co/Qwen/Qwen3-0.6B/blob/main/tokenizer_config.json`
- `huggingface.co/Qwen/Qwen3.5-35B-A3B-Base/blob/main/tokenizer_config.json`
- `github.com/QwenLM/Qwen3/issues/927`

---

## DeepSeek — added tokens in tokenizer.json only

**Repos:** `deepseek-ai/DeepSeek-V3`, `deepseek-ai/DeepSeek-R1`
**Tokenizer class:** `LlamaTokenizerFast` → `TokenizersBackend`

### V3: added_tokens NOT in tokenizer_config.json

`tokenizer_config.json`:

```json
"tokenizer_class": "LlamaTokenizerFast",
"eos_token": {"content": "<｜end▁of▁sentence｜>", ...},
"bos_token": {"content": "<｜begin▁of▁sentence｜>", ...}
```

`added_tokens_decoder` **absent**. Added tokens live exclusively in
`tokenizer.json` (7.85 MB).

### User premise — 818 special=false tokens

The project's hall-of-shame claims "818 non-role-assigned added
tokens with special=False". Direct verification against the shipped
tokenizer.json (sampling via WebFetch, 2026-04-21): all ~398 visible
entries have `special: true`. IDs 0-128397 with
`<｜place▁holder▁no_N｜>` pattern running to 397.

**Status:** user premise **unverified** against current main.
Either:
- The 818-count is from a different DeepSeek variant (V2.5?)
- The pattern was patched in a more recent push
- The sampling window missed the relevant ID range

Preflight should verify at runtime via:

```python
decoder = tokenizer.backend_tokenizer.get_added_tokens_decoder()
non_special = [i for i, t in decoder.items() if not t.special]
```

Do NOT hardcode the 818 count in skill logic.

### R1: `<think>` in chat_template, not added_tokens

```json
"tokenizer_class": "LlamaTokenizerFast",
"bos_token": {"content": "<｜begin▁of▁sentence｜>"},
"eos_token": {"content": "<｜end▁of▁sentence｜>"}
```

`<think>` / `</think>` do **not** appear in `added_tokens_decoder` on
R1. They're referenced only inside `chat_template` Jinja:

```jinja
{% if '</think>' in content %}...split('</think>')[-1]...
```

**Preflight rule:** scanning `added_tokens_decoder` for "think"
markers returns empty on R1. Extraction logic must also parse
`chat_template.jinja`.

**Sources:**
- `huggingface.co/deepseek-ai/DeepSeek-V3/blob/main/tokenizer_config.json`
- `huggingface.co/deepseek-ai/DeepSeek-V3/raw/main/tokenizer.json`
- `huggingface.co/deepseek-ai/DeepSeek-R1/blob/main/tokenizer_config.json`

---

## Phi-4 — inverted BOS/EOS

**Repo:** `microsoft/phi-4`
**Tokenizer class:** `GPT2Tokenizer`

```json
"eos_token": "<|im_end|>",
"bos_token": "<|endoftext|>"
```

Opposite of Qwen3-Base (where `<|endoftext|>` is EOS). Preflight
must not regex on string to decide role — read the explicit field.

**Source:** `huggingface.co/microsoft/phi-4/blob/main/tokenizer_config.json`

---

## Mistral-Small — LlamaTokenizer + INST wrappers

**Repo:** `mistralai/Mistral-Small-24B-Instruct-2501`
**Tokenizer class:** `LlamaTokenizer`

```json
"tokenizer_class": "LlamaTokenizer",
"eos_token": "</s>",
"add_bos_token": true,
"add_eos_token": false
```

`[INST]` and `[/INST]` at IDs 3 and 4 are structural wrappers, not
added_tokens. Preflight stop-token heuristics keyed on `<|im_end|>`
or ChatML patterns miss these entirely.

**Source:** `huggingface.co/mistralai/Mistral-Small-24B-Instruct-2501/blob/main/tokenizer_config.json`

---

## Pattern summary

| Pattern | Example | Layer |
|---|---|---|
| Three-ID EOS with turn primers | GLM-5.1 `[154820, 154827, 154829]` | generation_config |
| Half-fix EOS split-brain | Kimi K2.6 (163586 in gen_config, 163585 in tok_config) | Multiple files |
| Scalar-null template bug | Gemma-4 `format_argument` → `None` | chat_template |
| Orphan commit trap | GLM-5.1-FP8 SHA `6ad52ee` unreachable from main | HF git state |
| Absent tokenizer.json | Kimi K2.x | Class selection |
| added_tokens only in tokenizer.json LFS | DeepSeek-V3, Gemma-4 | Config file presence |
| `<think>` only in chat_template | DeepSeek-R1 | Template vs added_tokens |
| EOS = turn terminator | Qwen3-0.6B `<|im_end|>` | Dual role |
| Base flips EOS | Qwen3.5-Base | Variant mismatch |
| Inverted BOS/EOS | Phi-4 | Role assignment |
| extra_special_tokens list | GLM-5.1 | Cross-version crash |
| Intentional `special=False` | Kimi K2.x `<think>` etc. | Parser compatibility |

---

## Primary sources

**HF Hub (verified 2026-04-21):**
- All repo URLs listed per-section above

**Upstream issues/PRs:**
- transformers #45205 (Gemma-4 chat_template not loaded)
- transformers #42914 (offline chat_template cache)
- transformers #43066 / #43104 (DeepSeek-R1-Distill decoder shape)
- transformers #45356 / #45359 (Kimi-K2.5 `</think>` regression)
- QwenLM/Qwen3 #927 (config.json inconsistency)
- vLLM #25401 (mistral mode silent `--chat-template`)
- vLLM #27622 (chat_template_kwargs allowlist fix, shipped v0.11.1)
- sglang #22510 / #22549 (streaming double-slice, not tokenizer)
