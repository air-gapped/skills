# Special-token discovery precedence

Five sources exist for "is this token structural?" They disagree in
scope and in timing of population. This document pins each down with
file:line and explains the precedence for preflight code.

Primary reference: `src/transformers/tokenization_utils_base.py`
(v5.0.0). Class `PreTrainedTokenizerBase` starts at line 1029;
`__init__` at line 1058.

---

## The seven named role slots

`SPECIAL_TOKENS_ATTRIBUTES` at `tokenization_utils_base.py:1040-1047`:

```python
SPECIAL_TOKENS_ATTRIBUTES = [
    "bos_token",
    "eos_token",
    "unk_token",
    "sep_token",
    "pad_token",
    "cls_token",
    "mask_token",
]
```

These are the **only** slots exposed via `tokenizer.special_tokens_map`.
Everything else (tool markers, turn primers, thinking delimiters,
reserved tokens) lives outside this list.

---

## Source 1 — `backend_tokenizer.get_added_tokens_decoder()` (Rust truth)

**Available on:** `TokenizersBackend` only.

**Shape:** `dict[int, AddedToken]`. Every added token, keyed by
integer ID.

**`AddedToken` fields:** `content`, `special` (bool), `lstrip`,
`rstrip`, `normalized`, `single_word`.

**Source:** the Rust `tokenizers.Tokenizer` instance, populated from
`tokenizer.json["added_tokens"]` at load time.

**Completeness:** **all** added tokens, including those registered
with `special=False`. DeepSeek-V3's 128000+ ID range is fully
visible here.

**Preflight code:**

```python
decoder = tokenizer.backend_tokenizer.get_added_tokens_decoder()
# dict[int, AddedToken]
all_ids = set(decoder.keys())
structural_ids = {i for i, t in decoder.items() if t.special}
reserved_ids = {i for i, t in decoder.items() if not t.special}
```

---

## Source 2 — `tokenizer.added_tokens_decoder` (Python mirror)

**Available on:** both backends.

### For TokenizersBackend

`tokenization_utils_tokenizers.py:488-495`:

```python
@property
def added_tokens_decoder(self) -> dict[int, AddedToken]:
    """Returns the added tokens in the vocabulary as a dictionary of index to AddedToken."""
    return self._tokenizer.get_added_tokens_decoder()
```

Literal passthrough to Source 1. Always agrees.

### For PythonBackend

Populated from `tokenizer_config.json["added_tokens_decoder"]` during
`__init__`. Shape: `dict[int, AddedToken]`.

**Shape landmine:** some older repos or broken configs serialize the
decoder as a **list** instead of a dict. Gemma-4 under transformers
4.57 was reported as list-shaped (user premise). Verified on
2026-04-21: Gemma-4 E4B and 26B-A4B-it **do not** ship
`added_tokens_decoder` in `tokenizer_config.json` at all — added
tokens live in `tokenizer.json` (LFS). The list-shape claim is
consequently unconfirmed against current repos; the v4.57
list-shape bug may have been patched upstream.

---

## Source 3 — `tokenizer.all_special_tokens` / `all_special_ids`

`tokenization_utils_base.py:1406` and `1421`:

```python
@property
def all_special_tokens(self) -> list[str]:
    """All unique special tokens (named + extra) as strings"""

@property
def all_special_ids(self) -> list[int]:
    """IDs of tokens listed in all_special_tokens"""
```

**Scope:** union of
- The seven role-slot values (`bos_token`, `eos_token`, ...)
- `self._extra_special_tokens` (list, see Source 5)

**Excludes:** any added token registered with `special=False`.

**Why this matters:**
- **DeepSeek-V3/R1** registers hundreds of reserved tokens into
  `added_tokens_decoder` with `special=True` for some, but the
  DSML-adjacent markers are registered with `special=False`. An
  engine using `all_special_ids` as its skip-decode set lets raw
  `<｜…｜>` strings leak into chat responses.
- **GLM-5.1** registers `<|user|>` and `<|observation|>` in
  `extra_special_tokens` (list shape) — they reach `all_special_ids`.
  But engines that override `skip_special_tokens=False` (to keep
  `<think>` visible) get the turn primers rendered into output.

**Preflight rule:** never trust `all_special_ids` alone. For the
full structural-ID set, use Source 1 filtered by `t.special`.

---

## Source 4 — `tokenizer.special_tokens_map`

`tokenization_utils_base.py:1387`:

```python
@property
def special_tokens_map(self) -> dict[str, str]:
```

**Scope:** only the seven named role slots as `dict[str, str]`.
No extras, no added_tokens.

**Example:**
```python
{"bos_token": "<s>", "eos_token": "</s>", "pad_token": "<pad>",
 "unk_token": "<unk>"}
```

**Use case:** legacy code, back-compat shims, quick sanity check on
role-slot presence. **Not** a general structural-ID source.

---

## Source 5 — `tokenizer.extra_special_tokens` {#extra-special-tokens-shape}

### Internal shape (list)

`tokenization_utils_base.py:1074`:

```python
self._extra_special_tokens = []  # List of extra model-specific special tokens
```

Internally a **list**. Overridden via `__setattr__`/`__getattr__` at
lines 1151–1161 and 1176–1179.

### Serialized shape (list OR dict — lab-dependent)

The canonical reference is the
[NVIDIA Nemotron commit e707da7](https://huggingface.co/nvidia/nemotron-colembed-vl-4b-v2/commit/e707da79538edf17c86abd24d42d603eaec9b3cb):

> extra_special_tokens was serialized as a list by transformers 5.0.0rc0.
> Versions <5.0 call .keys() on it, causing AttributeError. Changed to
> {} since all tokens are already registered in tokenizer.json
> added_tokens.

**Consequence:**
- `zai-org/GLM-5.1-FP8` ships `extra_special_tokens` as a **list**:
  ```json
  "extra_special_tokens": [
    "<|endoftext|>", "[MASK]", "[gMASK]", "[sMASK]",
    "<sop>", "<eop>", "<|system|>", "<|user|>",
    "<|assistant|>", "<|observation|>", "<|begin_of_image|>", ...
  ]
  ```
- `zai-org/GLM-4.6` ships it as a **dict**: `"extra_special_tokens": {}`.
- Transformers `<5.0` readers crash on the list form with
  `AttributeError: 'list' object has no attribute 'keys'`.
- Transformers `>=5.0` readers accept both.

**Preflight rule:**
```python
value = tokenizer_config.get("extra_special_tokens")
if isinstance(value, list):
    # Coerce to dict for cross-version safety
    value = {tok: tok for tok in value}
```

---

## Precedence chain for preflight code

When answering "is X structural?" or "what are all the structural
IDs?", walk the sources in this order:

### 1. Rust truth (TokenizersBackend only) {#backend-fallback}

```python
if hasattr(tokenizer, "backend_tokenizer") and tokenizer.backend_tokenizer:
    decoder = tokenizer.backend_tokenizer.get_added_tokens_decoder()
    return {i for i, t in decoder.items() if t.special}
```

### 2. Python mirror on tokenizer

```python
decoder = getattr(tokenizer, "added_tokens_decoder", None)
if isinstance(decoder, dict):
    return {i for i, t in decoder.items()
            if getattr(t, "special", False)}
```

### 3. Raw config file fallback (for no-tokenizer-loaded case)

```python
with open(snapshot_dir / "tokenizer_config.json") as f:
    cfg = json.load(f)
decoder = cfg.get("added_tokens_decoder", {})
if isinstance(decoder, dict):
    ids = {int(k) for k, v in decoder.items()
           if isinstance(v, dict) and v.get("special") is True}
elif isinstance(decoder, list):
    # Rare/broken shape; fall through to tokenizer.json
    ids = set()
```

### 4. tokenizer.json raw scan (for no-tokenizer_config case)

```python
with open(snapshot_dir / "tokenizer.json") as f:
    tok_json = json.load(f)
added = tok_json.get("added_tokens", [])
ids = {int(t["id"]) for t in added if t.get("special") is True}
```

### 5. Union with role slots for "anything declared structural"

```python
# Add named role-slot IDs for the "named slot" view
role_ids = set()
for slot in SPECIAL_TOKENS_ATTRIBUTES:
    val = cfg.get(slot)
    if isinstance(val, str):
        role_ids |= set(tokenizer.convert_tokens_to_ids([val]))
    elif isinstance(val, dict) and "content" in val:
        role_ids |= set(tokenizer.convert_tokens_to_ids([val["content"]]))
```

---

## The "turn marker as EOS" cross-check

Preflight question: "does `generation_config.eos_token_id` contain
tokens that are turn primers (i.e. things the template emits at the
start of a role section)?"

Algorithm:

```python
def is_turn_marker_eos(snapshot_dir):
    tokenizer_config = json.load(open(snapshot_dir / "tokenizer_config.json"))
    generation_config = json.load(open(snapshot_dir / "generation_config.json"))
    template_path = snapshot_dir / "chat_template.jinja"

    eos = generation_config.get("eos_token_id")
    if isinstance(eos, int):
        eos_ids = {eos}
    elif isinstance(eos, list):
        eos_ids = set(eos)
    else:
        return set()

    # Resolve each EOS ID to its string
    decoder = tokenizer_config.get("added_tokens_decoder", {})
    id_to_str = {}
    if isinstance(decoder, dict):
        for k, v in decoder.items():
            if isinstance(v, dict) and "content" in v:
                id_to_str[int(k)] = v["content"]

    # Scan chat_template.jinja for each EOS string
    if not template_path.exists():
        return set()
    template = template_path.read_text()
    import re
    turn_markers = set()
    for eos_id in eos_ids:
        s = id_to_str.get(eos_id)
        if not s:
            continue
        # A turn marker appears BEFORE the content it primes
        # Heuristic: appears adjacent to a role tag in the template
        pattern = rf"{re.escape(s)}\s*(?:\\n)?(?:\{{\%|\{{\{{|\[)"
        if re.search(pattern, template):
            turn_markers.add((eos_id, s))

    return turn_markers
```

Canonical hit: GLM-5.1 `generation_config.json` lists
`[154820, 154827, 154829]`. 154827 = `<|user|>`, 154829 =
`<|observation|>`. The template emits both at role-tag positions.
The function returns `{(154827, "<|user|>"), (154829, "<|observation|>")}`.

---

## Cross-reference summary table

| Source | Dict shape | Includes `special=False`? | Cross-version safe? |
|---|---|---|---|
| `backend_tokenizer.get_added_tokens_decoder()` | `dict[int, AddedToken]` | Yes | v5 only |
| `tokenizer.added_tokens_decoder` | `dict[int, AddedToken]` | Yes (passthrough on TokenizersBackend) | v5 only |
| `tokenizer.all_special_ids` | `list[int]` | **No** | Both |
| `tokenizer.special_tokens_map` | `dict[str, str]` (role slots only) | **No** | Both |
| `tokenizer.extra_special_tokens` | list internally; varies serialized | Yes (when present) | **List form crashes <5.0** |
| `tokenizer_config.json["added_tokens_decoder"]` | `dict[str_id, AddedToken_dict]` OR absent | Yes | Both (dict form) |
| `tokenizer.json["added_tokens"]` | `list[AddedToken_dict]` | Yes | Rust-era; universal |

---

## Primary sources

- `src/transformers/tokenization_utils_base.py:1029-1421` —
  `PreTrainedTokenizerBase` class, property accessors
- `src/transformers/tokenization_utils_tokenizers.py:488-495` —
  `added_tokens_decoder` passthrough
- `src/transformers/tokenization_utils_base.py:1040-1047` —
  `SPECIAL_TOKENS_ATTRIBUTES`
- `src/transformers/tokenization_utils_base.py:1074` —
  `self._extra_special_tokens = []` list initialization
- [NVIDIA Nemotron commit e707da7](https://huggingface.co/nvidia/nemotron-colembed-vl-4b-v2/commit/e707da79538edf17c86abd24d42d603eaec9b3cb) —
  list-vs-dict serialization landmine
