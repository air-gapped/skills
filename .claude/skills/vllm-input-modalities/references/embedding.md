# Embedding — operator reference

Load when the question is about serving a text or multi-modal embedding
model, Matryoshka / dimension reduction, pool-type overrides, or the
`/v1/embeddings` + `/v2/embed` endpoints.

## 1. Endpoints

| Route | Spec | When to use |
|---|---|---|
| `/v1/embeddings` | OpenAI-compatible | default; any OpenAI-SDK client works |
| `/v2/embed` | Cohere v2 compatible | client expects `input_type`, `embedding_types`, per-request `truncate` |

Both endpoints are live whenever the loaded model's supported tasks include
`embed`. No flag to toggle. Code: `vllm/entrypoints/pooling/embed/api_router.py:23-61`.

## 2. Pooling types

`SequencePoolingType` enum: `CLS`, `LAST`, `MEAN`, `ALL` (token-wise), `STEP`
(with `returned_token_ids`). Defined in `vllm/config/pooler.py:13`.

Default is picked per-model from:

1. Model's `Pooler.get_supported_tasks()` + `default_seq_pooling_type`
2. Sentence-Transformers `modules.json` if present
3. `--pooler-config` override (wins over both)

| Model family | Default | Override if… |
|---|---|---|
| BGE-M3, BGE-base/large (XLM-Roberta / BERT) | CLS | never |
| E5, GTE (BERT-family) | CLS or MEAN per config | mean-pool variants need `"pooling_type":"MEAN"` |
| Qwen3-Embedding (causal LM) | LAST | never |
| Jina v3 (XLM-Roberta) | MEAN | never (Sentence-Transformers config correct) |
| Jina v4 `-vllm-retrieval` | ALL (multi-vector) | never (this IS the pool config) |
| ssmits/Qwen2-7B-Instruct-embed-base | broken in ST config | force `"pooling_type":"MEAN"` |

Override syntax:

```bash
vllm serve <model> --runner pooling \
  --pooler-config '{"pooling_type":"MEAN"}'
```

## 3. Matryoshka / MRL

Native: model config must have `is_matryoshka: true` **or**
`matryoshka_dimensions: [256, 512, 768]`. `vllm/config/model.py:1591-1598`.

Forcing on for a model that supports MRL but lacks config:

```bash
--hf-overrides '{"is_matryoshka": true}'
--hf-overrides '{"matryoshka_dimensions":[256,512,768]}'
```

Per-request:

```python
client.embeddings.create(model="...", input=[...], dimensions=512)
```

Non-MRL models return 400 for `dimensions` — deliberate. BGE-M3 is a common
example of a well-loved model that simply doesn't support MRL; that's not a
bug to chase.

## 4. The four+ embedding families an operator encounters

### BGE — BAAI

- `BAAI/bge-m3` — XLM-Roberta, CLS pool, 8192-tok context, multi-lingual,
  no MRL.
- `BAAI/bge-base-en-v1.5`, `bge-large-en-v1.5` — BERT, CLS, 512 tok.
- Command: `vllm serve BAAI/bge-m3 --runner pooling`. Nothing else needed.

### E5 / GTE (Microsoft, Alibaba)

- `intfloat/e5-large-v2`, `intfloat/multilingual-e5-large-instruct`.
- `Alibaba-NLP/gte-Qwen2-*-instruct` needs `--trust-remote-code`.
- Instruction-aware: clients prepend `"query: "` / `"passage: "` as needed
  (not enforced server-side).

### Qwen3-Embedding (Qwen team)

- Sizes: 0.6B, 4B, 8B. Base is Qwen3 causal LM.
- **Do not use `--convert embed` any more.** Qwen3-Embedding's config
  registers the right pooling; `--runner pooling` alone works. Older
  cheat-sheet advice that says `--convert embed` is from the pre-runner era.
- Context length: up to 32K on the 4B variant.
- MRL: 4B / 8B support MRL per model card; activate with
  `--hf-overrides '{"is_matryoshka": true}'` if the config doesn't advertise.

### Jina embeddings v3 / v4 / v5

- **v3** (`jinaai/jina-embeddings-v3`, XLM-Roberta): `--trust-remote-code`.
  vLLM currently merges only the `text-matching` LoRA — if another task
  (retrieval, classification) is needed, run the official Jina HF endpoint.
- **v4 base is NOT vLLM-compatible.** Use the pre-merged variant:
  ```bash
  vllm serve jinaai/jina-embeddings-v4-vllm-retrieval --runner pooling \
    --pooler-config '{"pooling_type":"ALL"}' --dtype float16
  ```
  Output is multi-vector per token — client-side normalization required.
- **v5** (`JinaEmbeddingsV5Model`) is first-class. Select adapter at serve
  time:
  ```bash
  --hf-overrides '{"jina_task":"retrieval"}'     # or text-matching,
                                                 # classification, clustering
  ```

## 5. Generative-model adaptation (`--convert embed`)

For a `*ForCausalLM` that doesn't have its own pooling head, vLLM can adapt
it by hooking a `LAST`-token pooler. Command:

```bash
vllm serve <causal-lm> --runner pooling --convert embed
```

This is rarely needed in 2026 because the popular embedding-from-LM models
(Qwen3-Embedding, GTE-Qwen2) already register pooling in their config.
Reserve `--convert embed` for custom checkpoints.

## 6. Client-side patterns

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")

# Standard
r = client.embeddings.create(model="BAAI/bge-m3", input=["hello", "world"])

# MRL
r = client.embeddings.create(
    model="Qwen/Qwen3-Embedding-4B",
    input=["hello"],
    dimensions=256,
)

# Cohere v2 shape
import requests
r = requests.post("http://localhost:8000/v2/embed", json={
    "model": "jinaai/jina-embeddings-v5",
    "texts": ["hello"],
    "input_type": "search_document",
    "output_dimension": 256,
    "truncate": "END",
    "embedding_types": ["float", "binary"],
})
```

## 7. Performance notes

- Pooling models run in **PIECEWISE** CUDA graph mode, not full. Don't force
  `--enforce-eager` for production.
- vLLM docs explicitly note pooling is "primarily for convenience" and not
  always faster than Sentence-Transformers; benchmark against your alt path
  before committing.
- v0.16+ shipped mean-pooling optimisation via `index_add` — ~5.9% throughput
  win on mean-pool models.
- Chunked prefill + prefix caching: both work on embedding models; leave
  defaults on.
- Tensor parallel is supported: `--tensor-parallel-size 2`. Hidden-dim
  divisibility applies.

## 8. Common configuration gotchas

- **Local path loading** — some embedding models (notably older BGE-M3
  checkpoints) refuse to load from a local directory. Use the HF ID and let
  the resolver handle download to `$HF_HUB_CACHE`.
- **Precision differences vs HF Transformers** — ~1e-4 expected from
  attention-kernel + activation differences. Don't chase.
- **`--max-model-len`** — set explicitly for long-context embedders
  (8192 BGE-M3, 32 k Qwen3-Embedding-4B); auto-detection picks the HF
  config's `max_position_embeddings`, which may be smaller than the model
  actually supports.
- **HF gated models** — set `HF_TOKEN` even in offline mode (known quirk,
  issue #9255).

## 9. Source anchors

- `vllm/entrypoints/pooling/embed/api_router.py` — route definitions
- `vllm/entrypoints/pooling/factories.py:38-100` — IO processor registration
- `vllm/config/pooler.py:41-150` — `PoolerConfig` schema (pool type,
  dimensions, chunked processing, Platt scaling)
- `vllm/config/model.py:1591-1598` — `is_matryoshka` detection
- `vllm/model_executor/models/bert.py`, `jina.py` — embedding model
  definitions
- Docs: `docs/models/pooling_models/embed.md` in the repo
