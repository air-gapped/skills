# Tokenizers — `tokenizer.json` (HuggingFace) vs `tiktoken.model` (BPE) vs unsupported

The gateway loads a tokenizer via the **`llm-tokenizer` Rust crate (v1.3.2)** — a separate package whose source lives at `github.com/lightseekorg/smg/crates/tokenizer/`, not in the SGLang repo. The gateway re-exports it as `crate::tokenizer` (`src/lib.rs:13: pub use llm_tokenizer as tokenizer;`).

This doc answers two questions operators repeatedly hit:

1. **When does the tokenizer choice actually matter for routing?**
2. **Which tokenizer formats does the gateway accept, and which silently break?**

It also calls out two surprises Kimi-K2 / K2.6 operators run into.

## When the gateway uses a tokenizer (and when it doesn't)

This is the most-misunderstood piece of the gateway. The four cases:

| Code path | Needs tokenizer? | What it does |
|---|---|---|
| **`cache_aware` policy (HTTP)** | **No** | Radix tree of **raw text characters** (`src/policies/cache_aware.rs:22` — comment: *"The tree stores raw text characters"*). `tree.insert(text, worker_url)` + `prefix_match_with_counts(text)`. Tokenizer choice does not affect routing. |
| **`prefix_hash` policy (HTTP or gRPC)** | **Yes** | xxh3 over first N (default 256) **token IDs** against a consistent-hash ring (`src/policies/prefix_hash.rs:107,217`). Needs tokens; in HTTP mode, tokens are produced gateway-side. |
| **gRPC routing path** | **Yes — and only HuggingFace** | Gateway tokenizes locally and sends token IDs to the worker. `process_chat_messages` in `src/routers/grpc/utils.rs:398-505` does an explicit `downcast_ref::<HuggingFaceTokenizer>()` and bails with *"gRPC router requires HuggingFace tokenizer with chat template support"* if the loaded tokenizer is anything else (incl. tiktoken). |
| **`/v1/tokenize`, `/v1/detokenize`** | **Yes** | Gateway-side tokenization exposed to clients (`src/routers/tokenize/handlers.rs`). |

**The "I thought cache_aware was token-based" trap.** `cache_aware` has nothing to do with the worker's KV cache directly — it's **text-prefix routing on the gateway**, designed to make same-prefix requests hit the same replica so that replica's *own* prefix cache builds up. The radix tree key space is UTF-8 strings, not token IDs. This is why operators can run cache_aware with Kimi-K2 / DeepSeek / any tiktoken model perfectly happily even though the gateway can't even fully tokenize those models for gRPC: cache_aware never invokes the tokenizer.

## What the loader accepts — full dispatch matrix

Source: `crates/tokenizer/src/factory.rs` in `lightseekorg/smg`.

The loader function — `factory::create_tokenizer_async_with_chat_template(source, chat_template_path)` — branches on whether `source` is a path or a bare name:

### `source` is a directory path

Priority order (returns the first match):

1. **`tokenizer.json` exists** → `HuggingFaceTokenizer::from_file_with_chat_template`. The fast / preferred path.
2. **`tiktoken.model` or any `*.tiktoken` exists** (`has_tiktoken_file`) → `TiktokenTokenizer::from_dir_with_chat_template`. Loads BPE pairs from the file, reads `tokenizer_config.json` from the same dir for `added_tokens_decoder`, special tokens, and (optionally) `chat_template`.
3. **Neither** → error: *"Directory '{}' does not contain a valid tokenizer file (tokenizer.json, tiktoken.model, *.tiktoken, or vocab.json)"*.

### `source` is a single file path

Dispatched by extension:

- `.json` → `HuggingFaceTokenizer::from_file_with_chat_template`.
- `.model` or `.tiktoken` → `is_tiktoken_file()` check (filename match). If yes → `TiktokenTokenizer::from_file_with_chat_template`. If no (looks like SentencePiece) → **error: *"SentencePiece models not yet supported"***.
- `.gguf` → **error: *"GGUF format not yet supported"***.
- Anything else → magic-byte auto-detect on first 512 bytes:
  - JSON-leading character → `HuggingFaceTokenizer`.
  - GGUF magic → error.
  - SentencePiece magic / `<unk` / `<s>` / `</s>` markers → *"SentencePiece model detected but not yet supported"*.
  - Else → *"Unable to determine tokenizer type"*.

### `source` is a bare name (not a path on disk)

1. **`is_likely_openai_model(name)` matches** (`gpt-` + digit, `chatgpt-`, `o<digit>` reasoning models, `davinci`/`curie`/`babbage`/`ada` families, `text-davinci-*`, `code-davinci-*`, `code-cushman-*`, `text-embedding-ada-*`) → built-in tiktoken via `tiktoken_rs`: `cl100k_base` / `p50k_base` / `p50k_edit` / `r50k_base`. **No network**.
2. **Otherwise** → `download_tokenizer_from_hf(name)` (HF Hub fetch via `crates/tokenizer/src/hub.rs`). After download, re-enter directory-scan logic.

The `is_likely_openai_model` check is name-prefix-only: `openai/gpt-oss-20b` correctly does **not** match (the `4` after `gpt-` test catches OpenAI naming, "oss" doesn't start with a digit).

### Formats explicitly not supported in 1.3.2

- **SentencePiece** (`.model` with SP magic) — explicit error.
- **GGUF** — explicit error.
- **Custom Python tokenizers** (`tokenization_*.py`, `trust_remote_code=True`) — silently ignored. The Rust gateway never executes Python; if a model's "real" tokenizer lives in a Python class (Qwen-old, some Yi variants, Kimi's `tokenization_kimi.py`), the gateway falls back to whatever HF/tiktoken file is present, and behavior is determined by that file alone.

## The Kimi-K2 / K2.6 case (and any other cl100k_base-style model)

Kimi-K2.6 (`moonshotai/Kimi-K2.6`) ships **a lot more than just tokenizer files** — and several are Python that the Rust gateway flatly cannot use. Inspect repo contents with the `hf` CLI (see the `hf-cli` skill):

```bash
hf models info moonshotai/Kimi-K2.6 --json | jq -r '.siblings[].rfilename'
```

Relevant non-weight files in K2.6:

| File | Loaded by gateway? | What it is |
|---|---|---|
| `tiktoken.model` | **Yes** | BPE pairs in tiktoken format. The only tokenizer file the Rust gateway actually reads. |
| `tokenizer_config.json` | **Yes** | Special tokens, `added_tokens_decoder`, optional inline `chat_template`. |
| `chat_template.jinja` | **Yes** (auto-discovered if `tokenizer_config.chat_template` is absent) | Jinja chat template. |
| `config.json`, `generation_config.json` | **Partially** (EOS IDs only via `crates/tokenizer/src/eos.rs`) | Model architecture / generation defaults. |
| `preprocessor_config.json` | **No** | Multimodal preprocessor config. |
| `tokenization_kimi.py` | **No — silently ignored** | Python tokenizer class. Gateway never executes Python; if the model's "real" tokenizer logic lives here, the gateway's `tiktoken.model`-based path is an *approximation* (see cl100k_base regex caveat below). |
| `kimi_k25_processor.py`, `kimi_k25_vision_processing.py`, `media_utils.py` | **No** | Multimodal request processor. The Rust gateway has no multimodal path of its own — image preprocessing is the worker's job (vLLM/SGLang, with `trust_remote_code=True` at the worker). |
| `configuration_deepseek.py`, `configuration_kimi_k25.py`, `modeling_deepseek.py`, `modeling_kimi_k25.py` | **No** | Inference-time custom code, used by the worker via `trust_remote_code`, irrelevant to the gateway. |
| `tool_declaration_ts.py` | **No** | Tool-declaration helper, irrelevant to the gateway. |
| `tokenizer.json` | — | **Not present.** This is the file `HuggingFaceTokenizer` would prefer; without it, the directory-scan path falls through to `tiktoken.model`. |

So the gateway's view of K2.6 is essentially `tiktoken.model + tokenizer_config.json + chat_template.jinja + EOS IDs`. Everything else (the Python tokenizer logic, the multimodal preprocessor, the modeling code) lives only on the worker.

**Multimodal implication for `cache_aware`.** K2.6 is a vision-language model; clients send image data inline (base64 in `messages[*].content[*].image_url.url` for OpenAI-format chat). The radix tree hashes whatever string the request builder feeds it. Identical text prompts with different images may collide on prefix; identical images with different prompts won't. Verify what the gateway actually feeds the tree before assuming cache_aware behaves well for your workload — for pure text-prompt traffic it's fine; for mixed image/text traffic the routing is "best-effort text prefix" and the cache hit rate is empirical, not guaranteed.

What the gateway does when pointed at the snapshot dir:

1. Directory scan finds no `tokenizer.json`, finds `tiktoken.model` → `TiktokenTokenizer::from_dir_with_chat_template`.
2. Loads BPE encoder, reads `tokenizer_config.json` for special tokens and `chat_template`, falls back to `chat_template.jinja` if config has no inline template.
3. Loads EOS token IDs by merging `config.json::eos_token_id` and `generation_config.json::eos_token_id` (`crates/tokenizer/src/eos.rs::load_eos_token_ids`).
4. **Constructs `CoreBPE` with the hardcoded `CL100K_BASE_PATTERN` regex.**

That last point is the surprise. The source comment (`crates/tokenizer/src/tiktoken.rs:21-27`) is explicit:

> *This pattern is correct for OpenAI models and most open-source tiktoken models (e.g. DeepSeek, Kimi K2). Some models use a different regex — for example, Kimi K2's native regex includes `\p{Han}` for Chinese character splitting — but encode/decode roundtrips still work correctly because BPE vocab handles tokenization; the regex only affects exact token boundary placement.*

In practice this means:

- **Roundtrip-safe**: `decode(encode(text)) == text` for any reasonable input.
- **Not byte-for-byte identical token IDs vs. the worker's native tokenizer** for inputs containing Chinese characters (or any other script the regex partitions differently). Two consecutive Chinese characters might land in one token slot via the gateway's cl100k_base regex but in two separate BPE merge slots via Kimi's native `\p{Han}` regex (or vice versa).
- **For `cache_aware`**: irrelevant. Tree stores text, never looks at IDs.
- **For `prefix_hash`**: matters. The hash is computed over gateway-tokenized IDs; KV-cache benefits assume the worker would have produced the same IDs. With drift on multilingual prompts, the hash-to-replica steering is still consistent (every gateway gets the same drift), but two-stage cache predictions get fuzzier.
- **For `/v1/tokenize` clients**: the IDs returned are cl100k_base-derived, not Kimi-native. Don't feed these IDs back to a Kimi worker as `prompt_token_ids` expecting them to round-trip identically — they will *roundtrip text* but not necessarily *match the worker's tokenization* of that same text.

If exact ID parity matters, run `cache_aware` (text-based) and let each worker tokenize natively. That's the configuration the user already runs in production for K2.6.

## Routing-mode + tokenizer compatibility matrix

| Worker model ships | gRPC mode | HTTP + `cache_aware` | HTTP + `prefix_hash` | `/v1/tokenize` |
|---|---|---|---|---|
| `tokenizer.json` (most HF models) | ✅ | ✅ (no tokenizer needed) | ✅ | ✅ |
| `tiktoken.model` only (Kimi K2/K2.6, DeepSeek-V3 family, GPT-OSS-style) | ❌ explicit error: HF tokenizer required | ✅ (no tokenizer needed) | ✅ but cl100k_base boundaries — see warning above | ✅ but cl100k_base IDs |
| SentencePiece-only `.model` (rare today; older Llama/Mistral variants, some Indic models) | ❌ load fails | ✅ if you don't pass `--tokenizer-path` (cache_aware doesn't need one) | ❌ token loading fails | ❌ token loading fails |
| GGUF | ❌ load fails | ✅ if you don't pass `--tokenizer-path` | ❌ load fails | ❌ load fails |
| Python-only custom tokenizer (`tokenization_*.py`, `trust_remote_code`) | ❌ unless an HF/tiktoken sibling file is also shipped | ✅ no tokenizer needed | ❌ unless sibling file present | ❌ unless sibling file present |

## Picking `--tokenizer-path` / `--model-path` correctly

The CLI accepts either a HuggingFace repo ID or a local directory. In an air-gapped cluster:

- **Always pass a local path.** The Rust gateway does not honor `HF_ENDPOINT` (verified — zero hits in the gateway source; `crates/tokenizer/src/hub.rs` uses raw `hf-hub` semantics, not `HF_ENDPOINT`-aware code). A repo ID will fail to download.
- **Point at the snapshot directory**, not the symlink layer. Standard HF cache layout:
  ```
  /models/huggingface/hub/
    models--moonshotai--Kimi-K2.6/
      snapshots/<sha>/
        tiktoken.model
        tokenizer_config.json
        chat_template.jinja
        config.json
        generation_config.json
        ...
  ```
  Pass `--tokenizer-path /models/huggingface/hub/models--moonshotai--Kimi-K2.6/snapshots/<sha>/`.
- **For cache_aware-only deployments, you can omit `--tokenizer-path` entirely.** The gateway still routes correctly because the policy is text-based. The only thing you lose is `/v1/tokenize` and the chat-template-applied request handling on the gRPC path — both of which you weren't using anyway.

When in doubt:

```bash
docker run --rm \
  -v /models/huggingface/hub/models--moonshotai--Kimi-K2.6/snapshots/<sha>:/m:ro \
  lmsysorg/sgl-model-gateway:v0.3.2 \
  --tokenizer-path /m --policy cache_aware --worker-urls http://example:8000 \
  --host 0.0.0.0 --port 8080
```

If the boot log shows `Successfully loaded tokenizer 'X' (id: Y) with vocab_size: Some(Z)`, the load worked. If it shows the *"does not contain a valid tokenizer file"* error, the snapshot dir is wrong (or this is a SentencePiece / GGUF model not yet supported).

## Quick decision flow for new models

```
Does the model ship tokenizer.json?
├── Yes → use it, all gateway features work.
└── No
    ├── Does it ship tiktoken.model or *.tiktoken?
    │   ├── Yes → tiktoken path; HTTP routing fine, gRPC mode unsupported, watch for cl100k_base regex drift on multilingual.
    │   └── No
    │       ├── Does it ship a SentencePiece .model?
    │       │   └── Yes → not supported in llm-tokenizer 1.3.2. Either run HTTP + cache_aware (no tokenizer needed) or wait for SP support.
    │       └── Does it ship only Python tokenization_*.py?
    │           └── Yes → not loadable by the Rust gateway. Same fallback: HTTP + cache_aware works, anything tokenizer-touching does not.
```

For the typical 2026 deployment (HTTP + cache_aware), the answer almost always reduces to "you don't need a working tokenizer, just point `--worker-urls` at the workers and skip `--tokenizer-path`." The exception is when you specifically need `prefix_hash` (KV-locality routing on token IDs) or `/v1/tokenize` for clients.

## Source pins

- Gateway re-export: `sgl-model-gateway/src/lib.rs:13`.
- Tokenizer registration workflow: `sgl-model-gateway/src/core/steps/tokenizer_registration.rs`.
- gRPC HuggingFace-only enforcement: `sgl-model-gateway/src/routers/grpc/utils.rs:398-505`.
- cache_aware text-only tree: `sgl-model-gateway/src/policies/cache_aware.rs` (line 22 comment, lines 320-435 for tree ops).
- prefix_hash token-based hash: `sgl-model-gateway/src/policies/prefix_hash.rs:107,217`.
- Tokenizer factory: `lightseekorg/smg::crates/tokenizer/src/factory.rs`.
- Tiktoken loader + cl100k_base regex caveat: `lightseekorg/smg::crates/tokenizer/src/tiktoken.rs:14-30, 216-275, 343-413`.
- Crate version: `Cargo.toml: llm-tokenizer = "=1.3.2"`.
