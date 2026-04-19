# Reranking & scoring — operator reference

Load when the question is about `/rerank`, `/score`, cross-encoder vs
late-interaction, ColBERT / ColPali / ColQwen, Qwen3-Reranker, or any
"score these documents against this query" workflow.

## 1. Endpoints

| Route | Purpose | Notes |
|---|---|---|
| `/rerank` | Cohere + Jina-compatible rerank | primary |
| `/v1/rerank` | deprecated alias for `/rerank` | emits warning |
| `/v2/rerank` | Cohere v2 shape | primary for v2 clients |
| `/score` | bi-encoder cosine or cross-encoder logit | primary |
| `/v1/score` | deprecated alias | emits warning |

Code: `vllm/entrypoints/pooling/scoring/api_router.py:28-99`.

**The scoring API turns on automatically** whenever the model's
`Pooler.get_supported_tasks()` contains:
- `classify` with `num_labels == 1` → cross-encoder
- `embed` → bi-encoder (cosine)
- `token_embed` → late-interaction (MaxSim)

Gate logic: `vllm/entrypoints/pooling/utils.py:140-154`. There is no flag
to enable or disable this.

## 2. Three score types — pick the model, the engine picks the mode

`ScoreType = Literal["bi-encoder", "cross-encoder", "late-interaction"]`
— defined in `vllm/tasks.py:18`.

### Cross-encoder (joint forward, one logit)

| Model | Invocation notes |
|---|---|
| `BAAI/bge-reranker-v2-m3` | `--runner pooling`. Native classify head. |
| `BAAI/bge-reranker-v2-gemma` | `--runner pooling`. |
| `Qwen/Qwen3-Reranker-0.6B/4B/8B` | **three extras required** — see below |
| `mxbai/mxbai-rerank-large-v2` | `--runner pooling`. |
| `nvidia/llama-nemotron-rerank-1b-v2` | `--runner pooling`. |

**Qwen3-Reranker** is an instruction-tuned causal LM that expects a specific
prompt format — vLLM needs to be told about the classifier head and score
template:

```bash
vllm serve Qwen/Qwen3-Reranker-0.6B \
  --runner pooling --convert classify \
  --chat-template examples/templates/qwen3_reranker.jinja \
  --hf-overrides '{
    "architectures":["Qwen3ForSequenceClassification"],
    "classifier_from_token":["no","yes"],
    "is_original_qwen3_reranker":true
  }'
```

Skipping any of the three produces random-looking scores, not errors.

Score templates (Jinja) apply only to cross-encoder models. Access query
via:
```jinja
{{ (messages | selectattr("role","eq","query") | first).content }}
```
not positional indices (order is not guaranteed).

### Late-interaction (ColBERT family, MaxSim)

Per-token embeddings, MaxSim at scoring time. Higher fidelity than a single
vector on retrieval tasks, at the cost of 10–100× storage per document.

| Model | Notes |
|---|---|
| `ColBERTModernBertModel` via `colbert-ir/*` | base ColBERTv2 family |
| `jinaai/jina-colbert-v2` | `--trust-remote-code` |
| `HF_ColBERT` (registry shim) | for stock ColBERT checkpoints |
| `vidore/colpali-v1.3-hf` | **multimodal** (image + query) |
| `ColQwen3`, `ColQwen3.5` | multimodal, Qwen3 base |
| `ColModernVBertForRetrieval` | multimodal, ModernBERT base |

Serve: `vllm serve jinaai/jina-colbert-v2 --runner pooling --trust-remote-code`.
Runner pick is auto for most; `--runner pooling` is the safe explicit form.

Flash MaxSim is on by default (v0.17–0.19 gave ~14% throughput win). Env
flag `enable_flash_late_interaction: true` — only flip off for debugging.

**Multimodal rerankers** (ColPali, ColQwen, jina-reranker-m0): image input
follows the standard multimodal chat format (`image_url` blocks) but the
endpoint is still `/rerank`. vLLM routes the images through the
multimodal preprocessor.

### Bi-encoder (cosine)

Any embedding model auto-exposes `/score`. No separate config. The engine
embeds both sides and returns cosine similarity.

### Listwise (not late-interaction — separate mode)

`jinaai/jina-reranker-v3` is listwise. Jina describes it as "last but not
late interaction" — `JinaForRanking`, `token_embed` task, custom scoring.
Same `/rerank` endpoint, but ranks a full list jointly rather than scoring
pairs independently.

## 3. Request shapes

### `/rerank`

```python
r = requests.post("http://localhost:8000/rerank", json={
    "model": "BAAI/bge-reranker-v2-m3",
    "query": "what is vLLM",
    "documents": [
        "vLLM is an LLM serving engine",
        "Redis is an in-memory KV store",
        "vLLM supports continuous batching"
    ],
    "top_n": 3,
    "max_tokens_per_doc": 512,  # added late-2025, truncates long docs
})
```

### `/score`

```python
r = requests.post("http://localhost:8000/score", json={
    "model": "BAAI/bge-reranker-v2-m3",
    "text_1": "what is vLLM",
    "text_2": ["vLLM is …", "Redis is …"],
})
```

Accepts `text_1: str | list[str]` and `text_2: str | list[str]`. Returns
per-pair score.

## 4. Platt-scaling (affine) calibration

Raw cross-encoder logits aren't well-calibrated probabilities. vLLM bakes
affine calibration into `PoolerConfig`:

```bash
--pooler-config '{"logit_mean": -0.5, "logit_sigma": 1.2}'
```

Renamed from the old `logit_bias` / `logit_scale` fields (late 2025). The
deprecated names still work with a warning.

Use this when clients compare scores across reranker models and need
comparable ranges.

## 5. Choosing between modes

| Need | Pick |
|---|---|
| Lowest-latency, one pair at a time | bi-encoder (pre-computed embeddings + client cosine) |
| Highest quality on short docs | cross-encoder |
| Highest quality on long docs with token-level reasoning | late-interaction (ColBERT) |
| Multimodal (image + query) rerank | ColPali / ColQwen / jina-reranker-m0 |
| Listwise with small N (e.g. top-20 rerank) | jina-reranker-v3 |
| Multilingual cross-encoder | BGE-reranker-v2-m3 |

**Quality vs cost rule of thumb:** cross-encoder ≫ bi-encoder on accuracy,
late-interaction wins on long contexts where a single vector can't capture
token-level detail. Late-interaction costs more storage (one vector per
token) but scoring is cheap once indexed.

## 6. Common mistakes

1. **Calling `/score` on a generative-only model.** Expected: 404 on the
   route. If the server responds but with `NotImplemented`, the runner is
   probably wrong — check `--runner pooling` was set.
2. **`--enable-scoring-api`.** Doesn't exist. Don't add it.
3. **Qwen3-Reranker without the score template.** Scores will look random.
   The three `--hf-overrides` + `--chat-template` are all mandatory.
4. **ColBERT with `--enforce-eager`.** Loses the flash-late-interaction win.
   The default (PIECEWISE graphs + flash MaxSim) is the performant path.
5. **Mixing `/rerank` and raw cross-encoder endpoints across reranker
   families.** Different vendors expect different score ranges (some 0–1
   probabilities, some raw logits). Use Platt scaling to normalise, or
   wrap the client to rescale per model.

## 7. Source anchors

- `vllm/entrypoints/pooling/scoring/api_router.py` — routes
- `vllm/entrypoints/pooling/scoring/serving.py` — dispatch + flash
  late-interaction selector
- `vllm/entrypoints/pooling/scoring/io_processor.py:259-300` — per-model
  score-type configuration
- `vllm/entrypoints/pooling/utils.py:140-154` — scoring API auto-enable
- `vllm/tasks.py:18` — `ScoreType` enum
- `vllm/model_executor/models/colbert.py`, `colpali.py`, `colqwen3*.py` —
  late-interaction models
- `vllm/model_executor/models/jina.py:33-83` — `JinaForRanking`
- Docs: `docs/models/pooling_models/scoring.md`

## 8. Recent PRs worth knowing

- **#38800 (2025-12)** — jina-reranker-v3 (listwise).
- **#38827 (2025-12)** — `max_tokens_per_doc` in `/rerank` body.
- **#34539 (2025-11)** — **Generative Scoring** (experimental) — scoring
  via generate path for models without a classify head. Early days; keep
  an eye on release notes if a deployment needs it.
- **#36818** — ColPali.
- **#33686** — ColBERT.
