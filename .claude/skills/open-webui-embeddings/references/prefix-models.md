# Prefix models — asymmetric embedders in Open WebUI

Load this file when the embedding model is anything other than BGE-M3, or when
retrieval quality dropped after an embedding-model swap with no errors in any log.

## Why this file exists

BGE-M3 — this skill's worked example — is **symmetric**: text in, vector out, no
decoration. Its model card is explicit: *"The only difference is that the BGE-M3
model no longer requires adding instructions to the queries."* Its
`config_sentence_transformers.json` carries no `prompts` block at all.

**Every mainstream alternative is asymmetric.** Queries and documents must be
labelled with different prefix strings, because that is how the model was trained
to tell "someone is asking" from "this is corpus text". Feed an asymmetric model a
bare string and it does not error — it returns a well-formed vector of the right
dimensionality that is simply *worse*. Nothing logs a complaint. Retrieval just
quietly degrades.

So migrating off BGE-M3 always means taking on prefix configuration. BGE-M3 is the
comfortable spot, not the baseline.

## Symmetric vs asymmetric — the model matrix

| Model | Type | Query prefix | Document prefix |
|---|---|---|---|
| `BAAI/bge-m3` | **symmetric** | — none — | — none — |
| `intfloat/multilingual-e5-large` | asymmetric | `query: ` | `passage: ` |
| `nvidia/Nemotron-3-Embed-1B-BF16` | asymmetric | `query: ` | `passage: ` |
| `intfloat/multilingual-e5-large-instruct` | asymmetric + instruction | `Instruct: {task}\nQuery: ` | *(none)* |
| `google/embeddinggemma-300m` | asymmetric | `task: search result \| query: ` | `title: none \| text: ` |
| `Qwen/Qwen3-Embedding-{0.6,4,8}B` | asymmetric + instruction | `Instruct: {task}\nQuery:` | *(none)* |

Three distinct shapes hide in that table:

- **Both sides prefixed** — e5-large, Nemotron-3-Embed, EmbeddingGemma. Nemotron
  reuses e5's exact `query: ` / `passage: ` pair, so the two are drop-in
  interchangeable as far as *this file* is concerned (the vector dimension is not —
  see trap 6).
- **Query side only** — Qwen3 and e5-instruct ship `"document": ""` in their
  configs. Documents genuinely go in bare; omitting the content prefix is correct,
  not an oversight.
- **Fixed vocabulary vs free text** — EmbeddingGemma's task label comes from a
  closed menu (below); Qwen3's instruction is yours to write.

### EmbeddingGemma's task menu

`config_sentence_transformers.json` defines the full set. Retrieval uses `query` /
`document`; the rest exist for other task types:

| Prompt name | String |
|---|---|
| `query`, `Retrieval-query`, `Retrieval`, `Reranking`, `BitextMining` | `task: search result \| query: ` |
| `document`, `Retrieval-document` | `title: none \| text: ` |
| `Clustering` | `task: clustering \| query: ` |
| `Classification`, `MultilabelClassification` | `task: classification \| query: ` |
| `PairClassification`, `STS` | `task: sentence similarity \| query: ` |
| `InstructionRetrieval` | `task: code retrieval \| query: ` |
| `Summarization` | `task: summarization \| query: ` |

Pooling is `MEAN` with `include_prompt: true` (`1_Pooling/config.json`) — the prefix
tokens are pooled into the output vector, which is exactly why they change the result.

### Qwen3's instruction is a tunable

The default, verbatim from its config:

```
Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:
```

Qwen's guidance: task-specific instructions buy 1–5% on downstream tasks, and
should be **written in English even for non-English corpora**, because the training
instructions were English. Since Open WebUI takes `RAG_EMBEDDING_QUERY_PREFIX` as a
free-form string, swapping in a corpus-specific instruction needs no code:

```
Instruct: Given a question about internal infrastructure runbooks, retrieve the relevant runbook passages\nQuery:
```

### The adjacent silent failure: post-transformer modules

Prefixes are not the only thing that can go missing without an error. What the
sentence-transformers wrapper does *after* the transformer differs per model, and a
runtime that skips a step returns a well-formed vector of the right dimension that
is simply wrong — the same failure signature as a missing prefix.

| Model | `modules.json` stack | Risk |
|---|---|---|
| `bge-m3` | Transformer → Pooling → Normalize | none |
| `multilingual-e5-large` | Transformer → Pooling → Normalize | none |
| `Nemotron-3-Embed-1B` | Transformer → Pooling (MEAN) → Normalize | none |
| `Qwen3-Embedding-*` | Transformer → Pooling (last-token) → Normalize | pooling mode must be read correctly |
| `embeddinggemma-300m` | Transformer → Pooling (MEAN) → **Dense 768→3072** → **Dense 3072→768** → Normalize | projector must be applied |

EmbeddingGemma is the outlier: its real output depends on a two-layer bottleneck
projector that lives in the ST wrapper, not the transformer. vLLM implements it
(PR #24318, `tests/models/language/pooling/test_st_projector.py`) — but any runtime
that only loads the transformer will not.

So when validating a *new* backend, check the numbers, not just that requests
return 200. The recipe in §Verifying below catches missing prefixes; comparing
against the model card's own published reference scores catches missing modules.

## How Open WebUI delivers a prefix — two modes, one switch

Three env vars, and the third is not what its name suggests:

```
RAG_EMBEDDING_QUERY_PREFIX      ← a string: the query label
RAG_EMBEDDING_CONTENT_PREFIX    ← a string: the document label
RAG_EMBEDDING_PREFIX_FIELD_NAME ← NOT a value. A mode switch.
```

`RAG_EMBEDDING_PREFIX_FIELD_NAME` decides *how the prefix reaches the server*:

| Value | Mode | Behaviour |
|---|---|---|
| **unset** | A — glue | Prefix is string-prepended to the text |
| any string | B — sidecar field | Text untouched; prefix sent as a separate JSON field under that name |

`retrieval/utils.py:1192-1196` (v0.11.0) — mode A:

```python
if prefix is not None and RAG_EMBEDDING_PREFIX_FIELD_NAME is None:
    if isinstance(text, list):
        text = [f'{prefix}{text_element}' for text_element in text]
    else:
        text = f'{prefix}{text}'
```

`retrieval/utils.py:871-873` (`generate_openai_batch_embeddings`) — mode B:

```python
json_data = {'input': texts, 'model': model}
if isinstance(RAG_EMBEDDING_PREFIX_FIELD_NAME, str) and isinstance(prefix, str):
    json_data[RAG_EMBEDDING_PREFIX_FIELD_NAME] = prefix
```

The same mode-B block is repeated in the ollama, azure_openai, and sync/async
variants (`utils.py:905, 943, 985, 1024, 1060`).

**Mode B exists for Ollama**, whose native embed API accepts a sibling field.
`/v1/embeddings` — vLLM, LiteLLM, TEI, OpenAI — has no such field. With
`RAG_EMBEDDING_ENGINE=openai`, mode B is always wrong.

### On the wire

Query *"How do I reset my password?"*, chunk *"To reset your password, click Forgot
Password on the login screen."*, EmbeddingGemma.

**Mode A — `PREFIX_FIELD_NAME` unset (correct):**

```json
POST http://litellm:4000/v1/embeddings
{"input": ["task: search result | query: How do I reset my password?"],
 "model": "embeddinggemma"}
```

```json
POST http://litellm:4000/v1/embeddings
{"input": ["title: none | text: To reset your password, click Forgot Password on the login screen."],
 "model": "embeddinggemma"}
```

**Mode B — `PREFIX_FIELD_NAME: prompt` (broken on any OpenAI-compat backend):**

```json
POST http://litellm:4000/v1/embeddings
{"input": ["How do I reset my password?"],
 "model": "embeddinggemma",
 "prompt": "task: search result | query: "}
```

`input` is naked. LiteLLM strips the unknown param or vLLM 400s on it. Either way
the label never reaches the model — the failure mode is a quality regression with
no error anywhere.

## Configuration per model

`RAG_EMBEDDING_PREFIX_FIELD_NAME` stays **unset** in every one of these.

**BGE-M3** — nothing to set.

**multilingual-e5-large — and `nvidia/Nemotron-3-Embed-1B-BF16`, same strings:**

```yaml
- name: RAG_EMBEDDING_QUERY_PREFIX
  value: "query: "
- name: RAG_EMBEDDING_CONTENT_PREFIX
  value: "passage: "
```

**EmbeddingGemma:**

```yaml
- name: RAG_EMBEDDING_QUERY_PREFIX
  value: "task: search result | query: "
- name: RAG_EMBEDDING_CONTENT_PREFIX
  value: "title: none | text: "
```

**Qwen3-Embedding** — query only:

```yaml
- name: RAG_EMBEDDING_QUERY_PREFIX
  value: "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery:"
# RAG_EMBEDDING_CONTENT_PREFIX — omit the entry entirely
```

## Traps

**1. `RAG_EMBEDDING_PREFIX_FIELD_NAME: ""` is the worst possible value.** In
Kubernetes, a bare `- name: RAG_EMBEDDING_PREFIX_FIELD_NAME` with no `value:` also
yields an empty string. `os.getenv(..., None)` then returns `""` — a `str`, not
`None` — so `utils.py:1192` skips the prepend *and* `utils.py:872` fires, injecting
a JSON key with an empty name. Prefixes silently vanish. **Omit the variable
entirely; never set it empty.** (`RAG_EMBEDDING_CONTENT_PREFIX: ""` is harmless by
contrast — an empty prepend is a no-op. The two variables do not behave alike.)

**2. Trailing whitespace is load-bearing, and inconsistent between models.** The
code does `f'{prefix}{text}'` with no separator. `query: ` and
`task: search result | query: ` end in a space. Qwen3's `Query:` **does not** — its
config string ends flush. Copy each string exactly; do not normalise. YAML strips
unquoted trailing whitespace, so quoting is mandatory.

**3. Qwen3 and e5-instruct contain a real newline.** YAML double-quoted scalars
interpret `\n` as a newline, so the block above is correct. Single quotes
(`'...\n...'`) and `|` block scalars keep it **literal**, shipping the two
characters `\` and `n` to the model. If templating through Helm, check the
rendered manifest, not the values file.

**4. Set both sides or neither.** Query prefix is applied at search time
(`utils.py:739`, `retrieval.py:2777`, `retrieval/external.py:107,156,233`,
`tools/builtin.py:3245`); content prefix at ingestion (`retrieval.py:1799`,
`knowledge.py:77`, `memories.py:152,213,414,512`). A half-configured pair labels
queries and documents inconsistently — worse than labelling neither. The exception
is the query-only models, where the document side is *specified* as empty.

**5. These are plain `os.getenv`, not PersistentConfig** (`config.py:1009-1013`).
They do not appear in the admin UI, cannot be set through the REST API, and take
effect only on pod restart. Env is the only lever — unlike most other RAG settings.

**6. Changing a prefix invalidates the index.** Everything already in the vector DB
was embedded under the old prefix (or none). Changing the string means a full
re-ingest, same as changing the model. Switching models additionally changes the
vector dimension (BGE-M3 1024 → EmbeddingGemma 768 → Qwen3-4B 2560), which forces
collection recreation regardless.

## Verifying the prefix is actually applied

The `ENV=dev` debug endpoint (`retrieval.py:2987-2991`) embeds a string through
Open WebUI's own function with `RAG_EMBEDDING_QUERY_PREFIX` applied. Compare it
against two direct backend calls:

```bash
# 1. what Open WebUI computes
curl -s -H "Authorization: Bearer $JWT" \
  "$OWUI/api/v1/retrieval/ef/hello" | jq -c '.result[:5]'

# 2. the prefixed string, straight from the backend
curl -s -X POST http://litellm:4000/v1/embeddings \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"embeddinggemma","input":["task: search result | query: hello"]}' \
  | jq -c '.data[0].embedding[:5]'

# 3. the bare string, for contrast
curl -s -X POST http://litellm:4000/v1/embeddings \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"embeddinggemma","input":["hello"]}' \
  | jq -c '.data[0].embedding[:5]'
```

(1) must match (2). If (1) matches (3), the prefix is not reaching the model —
check that `RAG_EMBEDDING_PREFIX_FIELD_NAME` is genuinely absent from the pod env
rather than set to `""` (trap 1).

This is the same cross-engine numerical-identity idiom as
`references/performance.md`; it works because embedding is deterministic.

## Reranking is unaffected

Cross-encoder rerankers (`Qwen3-Reranker-*`, `bge-reranker-v2-m3`) take the
(query, document) pair directly and apply no prefixes. None of this file applies to
`RAG_RERANKING_*`.

## Sources

| Claim | Source | Verified |
|---|---|---|
| EmbeddingGemma prompt strings + full task menu | `google/embeddinggemma-300m` → `config_sentence_transformers.json` (gated repo; needs `HF_TOKEN`) | 2026-08-05 |
| EmbeddingGemma MEAN pooling, `include_prompt: true` | same repo → `1_Pooling/config.json` | 2026-08-05 |
| Qwen3 query prompt, empty document prompt | `Qwen/Qwen3-Embedding-0.6B` → `config_sentence_transformers.json` | 2026-08-05 |
| Qwen3 instruction guidance (1–5%, write in English) | `Qwen/Qwen3-Embedding-0.6B` → `README.md` | 2026-08-05 |
| e5 `query: ` / `passage: `, required even for non-English | `intfloat/multilingual-e5-large` → `README.md` FAQ | 2026-08-05 |
| Nemotron `query: ` / `passage: `; MEAN pooling, 2048d, 32768 max_seq_length, no Dense module | `nvidia/Nemotron-3-Embed-1B-BF16` → `config_sentence_transformers.json`, `modules.json`, `1_Pooling/config.json`, `sentence_bert_config.json` | 2026-08-05 |
| Nemotron vLLM support is unregistered + version-bounded | `Ministral3Model` absent from vLLM main's `registry.py`; model card validates `vllm serve` on v0.20.0–v0.24.0 and `/v2/embed` on v0.25.0 (latest release v0.26.0); [vLLM #48621](https://github.com/vllm-project/vllm/issues/48621) YaRN bug still OPEN | 2026-08-05 |
| e5-instruct `Instruct: {task}\nQuery: ` | `intfloat/multilingual-e5-large-instruct` → `README.md` (`get_detailed_instruct`) | 2026-08-05 |
| BGE-M3 needs no instructions | `BAAI/bge-m3` → `README.md`; no `prompts` in its ST config | 2026-08-05 |
| Mode A / mode B dispatch | open-webui v0.11.0 `retrieval/utils.py:871-873, 1192-1196` | 2026-08-05 |
| Prefix vars are not PersistentConfig | open-webui v0.11.0 `config.py:1009-1013` | 2026-08-05 |
