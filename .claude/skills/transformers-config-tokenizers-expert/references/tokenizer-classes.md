# Tokenizer class taxonomy (transformers v5)

The v5 refactor (GA 2026-01-26) consolidated the v4 tokenizer zoo.
This document maps every class a 2026 lab repo is likely to ship,
which file selects it, which backend actually runs, and what
compatibility aliases exist for `<5.0` readers.

## Version timeline

| Version | Date | Notes |
|---|---|---|
| v4.56.0 | 2025-08-29 | Last v4 mainline feature release |
| v4.57.0 | 2025-10-03 | Yanked |
| v4.57.1–v4.57.6 | 2025-10-14 → 2026-01-16 | Patch line parallel to v5 RCs |
| v5.0.0rc0 | 2025-12-01 | First v5 RC (extra_special_tokens list serialization lands) |
| v5.0.0 | 2026-01-26 | GA; weekly minor cadence begins |
| v5.5.4 | 2026-04-13 | Current stable |
| 5.6.0.dev0 | main | As of 2026-04-21 |

Tags 4.58, 4.59, 4.60 **do not exist** — v5 replaced them. Gate on
`parse(transformers.__version__) >= Version("5.0")` before using any
v5-only class name.

---

## The five backends

### 1. TokenizersBackend (Rust-backed primary) {#tokenizers-backend}

Path: `src/transformers/tokenization_utils_tokenizers.py:89`.

```python
class TokenizersBackend(PreTrainedTokenizerBase):
```

Alias for back-compat at line 1373:

```python
PreTrainedTokenizerFast = TokenizersBackend
```

**Wraps:** `tokenizers.Tokenizer` (Rust). Stored on `self._tokenizer`.
Exposed via `backend_tokenizer` property at lines 542–545.

**Selected when:**
- Model ships `tokenizer.json`, OR
- A concrete class (`LlamaTokenizer`, `GPT2Tokenizer`, `GemmaTokenizer`,
  `Qwen2Tokenizer`, ...) inherits from it via a single
  `tokenization_<model>.py` file (v5 eliminated the `_fast.py` split).

**`added_tokens_decoder` shape:** `dict[int, AddedToken]`.
Implementation at `tokenization_utils_tokenizers.py:488-495`:

```python
@property
def added_tokens_decoder(self) -> dict[int, AddedToken]:
    return self._tokenizer.get_added_tokens_decoder()
```

Literal Rust passthrough. Python-side property and
`backend_tokenizer.get_added_tokens_decoder()` return identical
values.

**Used by:** everything with a `tokenizer.json` — most 2026 repos.
Qwen3, GLM-5.1, Gemma-4, DeepSeek-V3, Phi-4, Mistral-Small.

---

### 2. PythonBackend (pure-Python slow) {#python-backend}

Path: `src/transformers/tokenization_python.py:297`.

```python
class PythonBackend(PreTrainedTokenizerBase):
```

Alias at line 1064:

```python
PreTrainedTokenizer = PythonBackend
```

**Selected when:**
- Model's `tokenizer_config.json` explicitly names a class that
  subclasses `PythonBackend`, AND
- No Rust-fast path exists (no `tokenizer.json`, no auto-derivable
  fast variant).

**Uses:** internal `Trie` / `ExtensionsTrie` (lines 47, 208) for
vocab lookup.

**2026 usage:** rare for new models. Kimi-K2 family is the notable
holdout (see below).

---

### 3. SentencePieceBackend (SP models) {#sentencepiece-backend}

Per `MIGRATION_GUIDE_V5.md` and the
[Tokenization blog](https://huggingface.co/blog/tokenizers):
*"SentencePieceBackend inherits from PythonBackend and provides
integration with Google's SentencePiece library."*

**Selected when:** Gemma/Llama-style models whose Rust fast path is
unavailable OR user passes `use_fast=False`. In practice Gemma and
Llama both auto-derive fast tokenizers from their SentencePiece
`.model` files, so `SentencePieceBackend` is mostly a fallback.

**Known divergence:** issue #41870 (transformers 4.57.1) — `GemmaTokenizerFast`
introduces its own BOS/EOS rather than honoring the SentencePiece
file's. Unknown tokens mis-map to ID 3. Still open as of 2026-04. A
preflight tool should compare fast vs slow output when custom
`.model` files are present.

---

### 4. MistralCommonBackend (Mistral-AI) {#mistral-common-backend}

Path: `src/transformers/tokenization_mistral_common.py:271`.

```python
class MistralCommonBackend(PreTrainedTokenizerBase):
```

Alias at EOF: `MistralCommonTokenizer = MistralCommonBackend`.

**Wraps:** the external `mistral-common` Python package. Supports
both `spm` (SentencePiece) and `tekken` (Mistral's own BPE).

**Selected when:** `tokenizer_config.json` names `MistralCommonBackend`
or `MistralCommonTokenizer`, OR the engine forces
`tokenizer_mode=mistral`.

**Engine interaction:**
- vLLM: `tokenizer_mode="mistral"` loads `vllm/tokenizers/mistral.py`
  which imports `mistral_common.tokens.tokenizers.tekken.Tekkenizer`.
  This is a **separate** integration — not transformers' built-in
  `MistralCommonBackend`. vLLM does not require transformers >= 5.x
  for Mistral models.
- sglang: uses HF's `MistralCommonBackend` when the repo ships a
  `tekken.json` or `tokenizer.model.v*`.

**Auto-detection logic in vLLM:** `vllm/tokenizers/registry.py:87-111`
looks for `"tekken.json"` or `"tokenizer.model.v*"` filenames in the
HF repo file list. Matches flip `tokenizer_mode` to `"mistral"`
automatically under `tokenizer_mode="auto"`.

---

### 5. TikTokenTokenizer — not a first-class class {#tiktoken-path}

The prompt's taxonomy puts `TikTokenTokenizer` as a first-class
transformers class. It isn't. The upstream class is defined
**in the model repo** (not in transformers):

```python
# moonshotai/Kimi-K2-Instruct/tokenization_kimi.py
import tiktoken
from tiktoken.load import load_tiktoken_bpe

class TikTokenTokenizer(PreTrainedTokenizer):  # = PythonBackend in v5
```

**Selection mechanism:** `tokenizer_config.json` sets

```json
"tokenizer_class": "TikTokenTokenizer",
"auto_map": {"AutoTokenizer": ["tokenization_kimi.TikTokenTokenizer", null]}
```

`AutoTokenizer.from_pretrained(repo, trust_remote_code=True)` then
imports the class from the repo's Python file and instantiates it.

**Requirements:**
- `trust_remote_code=True`
- `pip install tiktoken`
- The repo ships `tiktoken.model` as the vocab file (NOT
  `tokenizer.json`).

**Labs using this path:** moonshotai/Kimi-K2-Instruct, Kimi-K2.6.
Kimi-K2 and Kimi-K2.5 tree listings 401 on public HF (gated or
pulled).

**Kimi-K2.5 slow tokenizer issue:** per
`https://huggingface.co/moonshotai/Kimi-K2.5/discussions/7`, the
Kimi family ships as slow (PythonBackend) tokenizers because
tiktoken's BPE isn't the Rust `tokenizers` BPE. Inference is
noticeably slower per-token on the tokenizer path.

**Transformers' own `TikTokenConverter`:** `src/transformers/convert_slow_tokenizer.py`
has a `TikTokenConverter` class, but it's a **build-side helper** for
converting tiktoken BPE into the Rust `tokenizers` format at fast-
tokenizer construction time — not a runtime tokenizer class.

---

## Processor-shaped tokenizers

### ProcessorMixin

Path: `src/transformers/processing_utils.py` → `ProcessorMixin`.

**Wraps:** `{image_processor, feature_extractor, tokenizer}` as a
compound object. The `.tokenizer` attribute is still a regular
`TokenizersBackend` or `PythonBackend`.

**Common subclasses in 2026:**
- `Gemma3Processor` (used by Gemma-3 and Gemma-4 multimodal)
- `Qwen2VLProcessor`, `Qwen2AudioProcessor`
- `LlavaProcessor`, `PaliGemmaProcessor`

**There is NO `Gemma4Processor`.** The user-level premise is wrong —
Gemma-4 multimodal reuses `Gemma3Processor`. Gemma-4 text-only uses
plain `GemmaTokenizer`.

**Preflight rule:** inspect `processor.tokenizer`, not `processor`
directly. Tokenizer-class discovery on a processor-shaped model
requires one unwrap step.

---

## Class-selection dispatcher

Path: `src/transformers/models/auto/tokenization_auto.py`.

Dispatch order:
1. Read `tokenizer_config.json["tokenizer_class"]`. Resolve against
   `TOKENIZER_MAPPING_NAMES`. Hit → instantiate.
2. Read `tokenizer_config.json["auto_map"]["AutoTokenizer"]`. If set
   AND `trust_remote_code=True`, import the custom class from the
   repo. (This is the Kimi path.)
3. Fall back to `config.json["model_type"]` → `TOKENIZER_MAPPING_NAMES`
   lookup.
4. If none match: raise `ValueError("Unrecognized tokenizer")`.

---

## Version-alias table {#version-aliases}

| v5 class | v4 alias still exported |
|---|---|
| `TokenizersBackend` | `PreTrainedTokenizerFast` |
| `PythonBackend` | `PreTrainedTokenizer` |
| `MistralCommonBackend` | `MistralCommonTokenizer` |
| `SentencePieceBackend` | (no v4 alias; was always `PreTrainedTokenizer` subclass) |

**Preflight rule:** a `tokenizer_config.json` declaring
`"tokenizer_class": "TokenizersBackend"` will fail to load under
transformers `<5.0` with:

```
AttributeError: module 'transformers' has no attribute 'TokenizersBackend'
```

Gate accordingly. GLM-5.1 and GLM-5.1-FP8 are the current canonical
case.

---

## Decoder-shape regression (v5 landmine)

**Issue #43066** / PR #43104 — DeepSeek-R1-Distill tokenizer's
`backend_tokenizer.decoder` shape changed between v4.57.3 and v5.0.0rc1:

```
v4.57.3:
  ByteLevel(add_prefix_space=True, trim_offsets=True, use_regex=True)

v5.0.0rc1+:
  Sequence(decoders=[
    Replace(..."▁"..., " "),
    ByteFallback(),
    Fuse(),
    Strip(...)
  ])
```

Functional decoding unchanged. Code that introspected
`decoder.__class__` or walked `decoder.decoders` **broke**. PR #43104
is open as of 2026-04 — documents the change, no functional reversal.

**Preflight rule:** do not assume a flat decoder shape. Use
`isinstance(tokenizer.backend_tokenizer.decoder, tokenizers.decoders.Sequence)`
and unwrap the sequence when present.

---

## Kimi-K2.5 `</think>` regression (v5.3 → v5.4)

**Issue #45356** / PR #45359.

Between transformers 5.3.0 and 5.4.0, special token ID 163607
(`</think>`) started decoding to empty string. Transformers emits a
warning suggesting `fix_mistral_regex=True`, but applying that flag
crashes with `AttributeError: 'tokenizers.Tokenizer' object has no
attribute 'backend_tokenizer'`.

PR #45359 closed; fix version not explicitly documented in the issue
but landed after 5.4. Any preflight tool hitting this should pin
transformers 5.3.x or check decoded output against expected string.

---

## Decision tree

```
Is tokenizer_config.json["tokenizer_class"] == "TikTokenTokenizer"?
├─ Yes → Kimi path. Require trust_remote_code=True, tiktoken pkg.
│        Backend = PythonBackend. No tokenizer.json.
│
├─ No → Is auto_map.AutoTokenizer set?
│  ├─ Yes → Remote code. Require trust_remote_code=True.
│  │        Backend = whatever the custom class inherits from.
│  │
│  └─ No → Is tokenizer.json present?
│     ├─ Yes → TokenizersBackend (Rust).
│     │        added_tokens_decoder = Rust passthrough.
│     │        Works on any v5.x (and v4 via PreTrainedTokenizerFast alias).
│     │
│     └─ No → Is tokenizer.model (SP) present?
│        ├─ Yes → SentencePieceBackend.
│        │        PythonBackend subclass.
│        │
│        └─ No → Check tekken.json / tokenizer.model.v* for MistralCommonBackend.
│                Else: fail.
```

---

## Primary sources

- `src/transformers/tokenization_utils_tokenizers.py` — TokenizersBackend
- `src/transformers/tokenization_python.py` — PythonBackend
- `src/transformers/tokenization_mistral_common.py` — MistralCommonBackend
- `src/transformers/models/auto/tokenization_auto.py` — dispatcher
- `src/transformers/convert_slow_tokenizer.py` — TikTokenConverter (build-side)
- `MIGRATION_GUIDE_V5.md` — v5 consolidation notes
- [Tokenization in Transformers v5 blog](https://huggingface.co/blog/tokenizers)
- [Release Transformers v5.0.0](https://github.com/huggingface/transformers/releases/tag/v5.0.0)
- Issue #41870 — GemmaTokenizerFast SP inconsistency
- Issue #43066 / PR #43104 — v5 decoder shape change
- Issue #45205 — Gemma-4 chat_template not loaded
- Issue #45356 / PR #45359 — Kimi-K2.5 `</think>` regression
- [Kimi-K2.5 discussion #7 — Slow Tokenizer](https://huggingface.co/moonshotai/Kimi-K2.5/discussions/7)
