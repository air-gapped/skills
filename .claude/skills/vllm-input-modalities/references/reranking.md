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

Code: `vllm/entrypoints/pooling/scoring/api_router.py:37-111`.

**The scoring API turns on automatically** whenever the model's
`Pooler.get_supported_tasks()` contains:
- `classify` with `num_labels == 1` → cross-encoder
- `embed` → bi-encoder (cosine)
- `token_embed` → late-interaction (MaxSim)

Gate logic: `vllm/entrypoints/pooling/utils.py:220-238`. There is no flag
to enable or disable this.

## 2. Three score types — pick the model, the engine picks the mode

`ScoreType = Literal["bi-encoder", "cross-encoder", "late-interaction"]`
— defined in `vllm/tasks.py:33`.

### Cross-encoder (joint forward, one logit)

| Model | Invocation notes |
|---|---|
| `BAAI/bge-reranker-v2-m3` | `--runner pooling`. Native classify head. |
| `BAAI/bge-reranker-v2-gemma` | causal LM — `--hf-overrides '{"architectures":["GemmaForSequenceClassification"],"classifier_from_token":["Yes"],"method":"no_post_processing"}'` plus `--chat-template examples/pooling/score/template/bge-reranker-v2-gemma.jinja` |
| `Qwen/Qwen3-Reranker-0.6B/4B/8B` | **three extras required** — see below |
| `mixedbread-ai/mxbai-rerank-base-v2` / `-large-v2` | causal LM — `--hf-overrides '{"architectures":["Qwen2ForSequenceClassification"],"classifier_from_token":["0","1"],"method":"from_2_way_softmax"}'` plus `--chat-template examples/pooling/score/template/mxbai_rerank_v2.jinja` |
| `nvidia/llama-nemotron-rerank-1b-v2` | `--runner pooling --trust-remote-code --chat-template examples/pooling/score/template/nemotron-rerank.jinja` |
| `polaria-tech/zerank-2-reranker-vllm` | v0.32.0+ (#60415): `--runner pooling --chat-template examples/pooling/score/template/zerank2.jinja`. A `Qwen3ForSequenceClassification` conversion of `zeroentropy/zerank-2-reranker`. |

Only encoder cross-encoders with a native classification head (BERT,
RoBERTa, XLM-RoBERTa, ModernBERT — e.g. `bge-reranker-v2-m3`) need nothing
beyond `--runner pooling`. Every LLM-based reranker above needs its score
template, and the original (non-`seq-cls`) checkpoints also need the
`--hf-overrides`; without them the server starts and returns plausible wrong
scores.

**Qwen3-Reranker** is an instruction-tuned causal LM that expects a specific
prompt format — vLLM needs to be told about the classifier head and score
template:

```bash
vllm serve Qwen/Qwen3-Reranker-0.6B \
  --runner pooling --convert classify \
  --chat-template examples/pooling/score/template/qwen3_reranker.jinja \
  --hf-overrides '{
    "architectures":["Qwen3ForSequenceClassification"],
    "classifier_from_token":["no","yes"],
    "is_original_qwen3_reranker":true
  }'
```

Skipping any of the three produces random-looking scores, not errors.
**v0.30.0+ catches the missing-template case at startup**: serving a model
with `is_original_qwen3_reranker=true` and no chat template now logs a
warning naming `qwen3_reranker.jinja` (#56017,
`vllm/entrypoints/pooling/scoring/io_processor.py`) instead of silently
producing bad scores.

**The other cause of "random-looking scores" — engine version, not config.**
PR #48901 (merged 2026-07-17, shipped **v0.26.0**) fixed a bug in which any
LAST-pooling model returned wrong scores when a query+document pair was long
enough for chunked prefill to split it, *and* `torch.compile` was on (the
default). The PR's own repro: a matching pair scores ~0.83 when it fits in one
chunk and collapses to ~0.01–0.36, varying run-to-run, when chunked. Neither
condition alone reproduces it — `--enforce-eager` was always correct, and the
offline batch path happened not to chunk. Root cause was a buffer-lifetime
race in the compiled forward, so the wrong value is plausible, not garbage:
no NaN, no zeros, cosine similarity ~0.47 against the eager hidden state.

Operational consequence: on **< v0.26.0**, ranking quality silently degraded
as documents got longer, and the degradation is not reproducible run to run.
Re-score anything ranked by an older engine on long inputs — an upgrade alone
does not repair the index. Diagnostic on an old engine: re-run the same pair
with `--enforce-eager`; if the score jumps, this is the bug and not the
`--hf-overrides`.

Score templates (Jinja) apply only to cross-encoder models. Access query
via:
```jinja
{{ (messages | selectattr("role","eq","query") | first).content }}
```
not positional indices (order is not guaranteed).

**v0.33.0+ applies a checkpoint's own score template** when the checkpoint is
a Sentence Transformers (v5.4+) `CrossEncoder` whose `sentence_bert_config.json`
declares the `message` modality (#60877) — e.g.
`nvidia/llama-nemotron-rerank-vl-1b-v2` at revisions from October 2026. No
`--chat-template` needed; passing one still wins; the template in use is
logged at startup, and a declared template the checkpoint lacks fails startup.
Below v0.33.0 (or with an older revision) pass
`--chat-template examples/pooling/score/template/nemotron-vl-rerank.jinja`.
Truncate these models with `max_tokens_per_doc`, not `truncate_prompt_tokens`
— the template suffix is not restored after truncation.

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
| `athrael-soju/ColUltraVBERT` | v0.33.0+ (#62237), `ColUltraVBertForRetrieval`: multimodal, 768-d token vectors. Clients must send the trained prompts — page: `User:<image>Describe the image.<end_of_utterance>\nAssistant:` plus the image; query: the text followed by ten `<end_of_utterance>` |

Serve: `vllm serve jinaai/jina-colbert-v2 --runner pooling --trust-remote-code`.
Runner pick is auto for most; `--runner pooling` is the safe explicit form.

Flash MaxSim is on by default (v0.17–0.19 gave ~14% throughput win). It is a
server CLI flag, not an env var: `--no-enable-flash-late-interaction` turns it
off — only for debugging. From v0.32.0 the flag is mirrored into
`PoolerConfig.enable_flash_late_interaction` and also selects the engine-side
flash-maxsim Triton kernel (#40337).

**Multimodal rerankers** (ColPali, ColQwen, jina-reranker-m0): image input
follows the standard multimodal chat format (`image_url` blocks) but the
endpoint is still `/rerank`. vLLM routes the images through the
multimodal preprocessor. If `jinaai/jina-reranker-m0` fails to load its
checkpoint weights, upgrade to ≥v0.31.0 (#57347, JinaVL text-config
`num_labels` fix).

**`jinaai/jina-reranker-m0` scores are wrong under truncation below v0.33.0**
(#62783). Whenever `truncate_prompt_tokens` binds — or `-1` is used on a pair
longer than `--max-model-len` — truncation cut off the model's score token and
the classifier read an ordinary prompt token: irrelevant documents score as
high as relevant ones, with no error. Upgrade, then re-score every pair that
was truncated.

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
    "max_tokens_per_doc": 512,  # added v0.20.0 (PR #38827), truncates long docs
})
```

`top_n` semantics: `0` means "return all results"; values larger than the
document count are accepted and clamped. **Negative values are rejected as of
v0.24.0** (PR #46119, merged 2026-06-22) — `top_n=-1` used to be silently
treated as `0`, i.e. it also returned everything, so a client sentinel of `-1`
"worked" by accident and now 400s.

**`max_tokens_per_doc` changed scores even when it did not truncate — below
v0.31.0** (#57666). For non-separator rerankers (e.g. Qwen3-Reranker and its
`-seq-cls` conversions) any positive limit re-tokenized the prompt differently.
Separator-based cross-encoders (BGE-reranker) were unaffected. Re-score if an
older engine ranked with this field set.

**HTTP 500 with `max_tokens_per_doc` on BERT-style cross-encoders — below
v0.33.0** (#61871). When the query alone fills the token limit
(`truncate_prompt_tokens` at or below the query length, or a query longer than
the model context), `/rerank` and `/score` fail with `Truncation error:
Sequence to truncate too short to respect the provided max_length`. v0.33.0
truncates the query as usual, or returns the normal 400 "maximum context
length". On older engines drop `max_tokens_per_doc` for long-query
("find similar") requests.

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

Renamed from the old `logit_bias` / `logit_scale` fields in v0.20.0
(PR #39530). The deprecated names still work with a warning.

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

## 7. Source anchors (line numbers at v0.33.0)

- `vllm/entrypoints/pooling/scoring/api_router.py` — routes
- `vllm/entrypoints/pooling/scoring/serving.py` — dispatch + flash
  late-interaction selector
- `vllm/entrypoints/pooling/scoring/io_processor.py` — per-score-type IO
  processors (`BiEncoder…`, `LateInteraction…`, `FlashLateInteraction…`,
  `CrossEncoder…`, `JinaRanking…IOProcessor`)
- `vllm/entrypoints/pooling/utils.py:220-238` — scoring API auto-enable
- `vllm/tasks.py:33` — `ScoreType` enum
- `vllm/model_executor/models/colbert.py`, `colpali.py`, `colqwen3*.py` —
  late-interaction models
- `vllm/model_executor/models/jina.py:44-96` — `JinaForRanking`
- Docs: `docs/models/pooling_models/scoring.md`

## 8. Recent PRs worth knowing (all merged; v0.20.0 unless marked)

- **#38800** (merged 2026-04-10) — jina-reranker-v3 (listwise).
- **#38827** (merged 2026-04-13) — `max_tokens_per_doc` in `/rerank` body.
- **#34539** (merged 2026-03-31) — **Generative Scoring** (experimental) —
  scoring via generate path for models without a classify head.
- **#39530** (merged 2026-04-13, **breaking**) — `logit_bias`/`logit_scale`
  renamed to `logit_mean`/`logit_sigma` in `PoolerConfig`. Old names still
  accepted with a deprecation warning. Update any calibration YAML using
  the old keys.
- **#36818** — ColPali (v0.18.0).
- **#33686** — ColBERT (v0.18.0).
