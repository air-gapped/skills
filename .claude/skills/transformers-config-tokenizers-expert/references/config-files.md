# Config file catalogue

Every file a HuggingFace model snapshot can ship, who reads it, what
happens when they drift. Citations are against transformers `main`
(`5.6.0.dev0`) unless otherwise noted.

## Filename constants

Defined in `src/transformers/tokenization_utils_base.py:95-100`:

```
SPECIAL_TOKENS_MAP_FILE = "special_tokens_map.json"   # 95
ADDED_TOKENS_FILE       = "added_tokens.json"         # 96
TOKENIZER_CONFIG_FILE   = "tokenizer_config.json"     # 97
FULL_TOKENIZER_FILE     = "tokenizer.json"            # 100
```

And `src/transformers/utils/hub.py:30-32`:

```
LEGACY_PROCESSOR_CHAT_TEMPLATE_FILE = "chat_template.json"
CHAT_TEMPLATE_FILE                  = "chat_template.jinja"
CHAT_TEMPLATE_DIR                   = "additional_chat_templates"
```

---

## `tokenizer.json`

**Read by:** `TokenizersBackend.__init__` → Rust
`tokenizers.Tokenizer.from_file`. In v5 this is the canonical source.

**Holds:**
- `model` — BPE / WordPiece / Unigram / WordLevel spec + vocab + merges
- `normalizer` — NFC / NFKC / Lowercase / Replace pipeline
- `pre_tokenizer` — byte-level, whitespace, punctuation splitter
- `post_processor` — template-based ID sequencing (BOS/EOS wrapping)
- `decoder` — ByteLevel / Metaspace / Fuse sequence
- `added_tokens` — array of `{id, content, special, lstrip, rstrip,
  normalized, single_word}` per token

**Size:** often large (7.85 MB DeepSeek-V3, 32 MB Gemma-4 LFS).
When stored on HF LFS, `WebFetch` returns an LFS pointer — must
download with `hf_hub_download`.

**Drift with `tokenizer_config.json`:** `tokenizer.json`'s
`added_tokens` array is the Rust-side truth. `tokenizer_config.json`
may re-declare the same tokens under `added_tokens_decoder` for
Python-slow compatibility. In v5 the latter is only serialized when
`tokenizer.json` is absent (PythonBackend path).

---

## `tokenizer_config.json`

**Read by:** `PreTrainedTokenizerBase.from_pretrained` via
`AutoTokenizer`.

**Required fields:**
- `tokenizer_class` — string literal, selects the concrete class.
  Checked against `TOKENIZER_MAPPING_NAMES` in
  `src/transformers/models/auto/tokenization_auto.py`, or against
  `auto_map.AutoTokenizer` when remote code is trusted.

**Role-slot fields (named special tokens):**
- `bos_token`, `eos_token`, `pad_token`, `unk_token`, `cls_token`,
  `sep_token`, `mask_token` — each is either a string or a
  serialized `AddedToken` dict with `content`, `normalized`, `lstrip`,
  `rstrip`, `single_word` keys.

**Extra tokens:**
- `extra_special_tokens` — **list OR dict** (shape varies across
  versions and labs; see `precedence-rules.md#extra-special-tokens-shape`).
- `additional_special_tokens` — older name for the same concept;
  still honored.
- `added_tokens_decoder` — `dict[int_str, AddedToken_dict]`. Only
  serialized when `tokenizer.json` is absent (v5 consolidation).
  Values are JSON objects with `content`, `special`, etc.

**Tokenization behavior:**
- `clean_up_tokenization_spaces` — bool. sglang forces `False` at
  load time (`tokenizer.py:311-317`). vLLM respects the config value.
- `add_bos_token`, `add_eos_token` — bool, auto-prepend/append on
  encode.
- `model_max_length` — int.
- `padding_side`, `truncation_side` — `"left"` / `"right"`.
- `legacy` — bool, controls SentencePiece pre-tokenization behavior
  (affects Llama-2 vs Llama-3 whitespace handling).
- `spaces_between_special_tokens` — bool, controls whether decode
  inserts spaces around added tokens.

**Remote code:**
- `auto_map` — `{"AutoTokenizer": ["module.Class", null]}`. When set
  and `trust_remote_code=True`, loads the custom class from the
  repo.

**Chat template (legacy inline):**
- `chat_template` — string containing the Jinja template. In v5 the
  **preferred** location is the sidecar `chat_template.jinja` file;
  inline form still honored for backward compat.

---

## `generation_config.json`

**Read by:** `GenerationConfig.from_pretrained` via
`src/transformers/generation/configuration_utils.py`.

**Token fields:**
- `eos_token_id` — `Union[int, list[int]]` per
  `configuration_utils.py:595-597`. Llama-3 ships a list (`[128001,
  128008, 128009]`); GLM-5.1 ships `[154820, 154827, 154829]`;
  Kimi-K2.6 ships a single int (163586).
- `bos_token_id`, `pad_token_id`, `decoder_start_token_id`,
  `forced_bos_token_id`, `forced_eos_token_id` — all `Union[int,
  list[int], None]`.

**Sampling defaults:**
- `temperature`, `top_p`, `top_k`, `typical_p`, `min_p`, `repetition_penalty`
- `do_sample` (bool), `num_beams` (int)
- `max_length`, `max_new_tokens`, `min_length`, `min_new_tokens`
- `stop_strings` — `Union[str, list[str], None]`. New-ish; not
  universally populated.

**Framework hints:**
- `transformers_version` — hint for forward-compat.
- `_from_model_config: true` — flag indicating this was auto-generated
  from `config.json` fields, not hand-maintained. GLM-5.1 sets this
  (`"transformers_version": "5.4.0"`).

**v5 breaking change:** non-generative models (BERT encoders, etc.)
no longer expose `model.generation_config` — attribute access raises
`AttributeError`. Gate on `hasattr`.

---

## `config.json`

**Read by:** `PretrainedConfig.from_pretrained`.

**Architecture fields:**
- `model_type` — lowercase string; selects the model class.
- `architectures` — list of class names (e.g. `["Gemma3ForCausalLM"]`).
- `torch_dtype` — initial load dtype.

**Token-ID fields** (same keys as `generation_config.json`, often
duplicated):
- `bos_token_id`, `eos_token_id`, `pad_token_id`,
  `decoder_start_token_id`.
- Under v5 these are primarily for architecture initialization —
  `generation_config.json` is the authoritative source for
  `.generate()`.

**v5 rope consolidation:**
- Old: `config.rope_theta`, `config.rope_scaling`.
- New: `config.rope_parameters = {"rope_theta": ..., "rope_type": ...}`.
  Direct access on old attribute **raises** `AttributeError`
  (breaking change per `MIGRATION_GUIDE_V5.md`).

---

## `special_tokens_map.json`

**Read by:** `PreTrainedTokenizerBase.from_pretrained` (legacy path).

**Holds:** the seven named role slots (`bos_token`, `eos_token`, ...)
and `additional_special_tokens`. Enables loading without
`tokenizer_config.json` (rare).

**v5 status:** per `MIGRATION_GUIDE_V5.md`, *"Special tokens are now
stored in `tokenizer_config.json`. The files `special_tokens_map.json`
and `added_tokens.json` are consolidated"*. Only written for
back-compat with `<5.0` readers. Several 2026 repos (GLM-5.1) omit it
entirely.

---

## `added_tokens.json`

**Read by:** legacy PythonBackend path.

**Holds:** flat `dict[str, int]` — `token_content -> id`.

**v5 status:** consolidated into `tokenizer_config.json["added_tokens_decoder"]`.
Only honored if `tokenizer.json` is absent (no Rust tokenizer).

---

## `processor_config.json`

**Read by:** `ProcessorMixin.from_pretrained` via
`src/transformers/processing_utils.py`.

**Multimodal processor config.** Holds image/audio preprocessor
settings and references to the tokenizer class:

- `image_processor_type`, `feature_extractor_type`
- `processor_class` — e.g. `"Gemma3Processor"`, `"Qwen2VLProcessor"`
- `image_size`, `patch_size`, `num_image_tokens` (VLM-specific)
- `tokenizer` — sometimes a nested object pointing at a
  sub-tokenizer class

**Gemma-4 clarification:** there is **no `Gemma4Processor` class**
in transformers v5.5.4. Gemma-4 multimodal uses `Gemma3Processor`;
text-only Gemma-4 uses plain `GemmaTokenizer`. The user's premise
that Gemma-4 has a dedicated processor is wrong.

---

## `chat_template.jinja`

**Read by:** `PreTrainedTokenizerBase.from_pretrained` via the
`CHAT_TEMPLATE_FILE` constant.

**Holds:** pure Jinja template string.

**v5 status:** the **preferred** location. Inline
`tokenizer_config.json["chat_template"]` still honored for backward
compat, but new models (Gemma-4, Llama-3.x recent) ship only the
sidecar file.

**Issue #45205** (open, transformers 5.5.0, 2026): Gemma-4 E2B/E4B
ship only the sidecar file; `AutoTokenizer` fails to wire it into
`tokenizer.chat_template`. Symptom: *"Cannot use chat template
functions because tokenizer.chat_template is not set and no template
argument was passed!"* Workaround: manual
`hf_hub_download("google/gemma-4-E2B-it", "chat_template.jinja")`.

**Issue #42914** (open, transformers 4.57.3, 2025-12-16): with
`HF_HUB_OFFLINE=1`, `AutoTokenizer.from_pretrained` still tries to
hit `huggingface.co/api/models/...` to resolve `chat_template.jinja`.
For air-gapped preflight: pre-seed the cache in an online phase, or
inline the chat template in `tokenizer_config.json` at snapshot time.

---

## `additional_chat_templates/*.jinja`

**Read by:** `PreTrainedTokenizerBase.from_pretrained` via
`CHAT_TEMPLATE_DIR`.

**Holds:** named alternate templates. Request via
`apply_chat_template(..., chat_template="tool_use")` (or similar
name).

**Example:** Mistral-Small-24B-Instruct ships separate templates for
tool-calling vs plain chat.

---

## Drift matrix — which file wins for which consumer

### `eos_token_id` drift {#eos-drift}

The canonical drift: `generation_config.json` lists `[A, B, C]`,
`tokenizer_config.json` declares `eos_token: "<X>"` which resolves to
just `A`.

| Consumer | Effective EOS set |
|---|---|
| `model.generate()` (transformers) | `{A, B, C}` — generation_config wins |
| `apply_chat_template` Jinja render (`{{ eos_token }}`) | `"<X>"` (= just A) |
| vLLM stop-matching (`sampling_params.py:540-560`) | `{A, B, C}` ∪ request stops |
| sglang stop-matching (`model_config.py:580-598`) | `hf_config.eos_token_id ∪ hf_generation_config.eos_token_id` |
| Any tool that reads only `tokenizer.eos_token_id` | Just A — **WRONG** |

Canonical example: GLM-5.1's `generation_config.json` lists
`[154820, 154827, 154829]` but `tokenizer_config.json` declares
`eos_token: "<|endoftext|>"` (= 154820 only). IDs 154827/154829 are
`<|user|>` and `<|observation|>` — turn primers that vLLM and sglang
stop on but transformers-based renderers miss.

### `tokenizer.json` vs `tokenizer_config.json` added_tokens drift {#v5-consolidation}

- **v5 canonical**: `tokenizer.json["added_tokens"]` is truth; 
  `tokenizer_config.json["added_tokens_decoder"]` is often absent or
  stale.
- **Common failure**: a patch updates `tokenizer.json` but leaves
  stale entries in `tokenizer_config.json["added_tokens_decoder"]`.
  For `TokenizersBackend`, Python-side `tokenizer.added_tokens_decoder`
  is a passthrough to Rust — so the stale dict is silently ignored,
  but preflight tools that only read the JSON file see the wrong
  state.

### `chat_template` sidecar vs inline drift

- v5: sidecar file wins if present; inline in tokenizer_config
  falls back.
- Pre-v5: inline wins; sidecar is optional secondary.
- Landmine: a repo that ships **both** and edits only one (usually
  the sidecar, leaving the inline stale). Preflight should emit a
  drift warning if both exist and differ.

---

## Which files a preflight MUST open

Minimum set to answer "what does this model look like at runtime":

```
tokenizer.json              # Rust source of truth for added_tokens
tokenizer_config.json       # role slots, tokenizer_class, chat_template (maybe)
generation_config.json      # authoritative EOS/stop set for .generate()
config.json                 # architecture, fallback token IDs
chat_template.jinja         # sidecar template (v5 preferred)
```

Optional (if present):
```
special_tokens_map.json     # legacy; flag as drift if inconsistent
added_tokens.json           # legacy; flag as drift if inconsistent
processor_config.json       # multimodal
additional_chat_templates/*.jinja  # named alternates
```

---

## Primary sources

- `src/transformers/tokenization_utils_base.py` — filename constants,
  `PreTrainedTokenizerBase`
- `src/transformers/utils/hub.py:30-32` — chat-template file constants
- `src/transformers/generation/configuration_utils.py:595-597` — EOS
  `Union[int, list[int]]` docstring
- `MIGRATION_GUIDE_V5.md` — consolidation notes
- `src/transformers/models/auto/tokenization_auto.py` — dispatcher
- [Tokenization in Transformers v5 blog](https://huggingface.co/blog/tokenizers)
