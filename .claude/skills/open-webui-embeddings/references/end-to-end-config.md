# End-to-end working config

Load this file when bootstrapping a new Open WebUI + LiteLLM + TEI deployment. The config is the worked example for BGE-M3 (embed) + BGE-Reranker-v2-m3 (rerank) and generalises to any TEI-served encoder.

## LiteLLM (`config.yaml`)

```yaml
model_list:
  # Embedding via TEI's OpenAI-compat /v1/embeddings (openai driver)
  - model_name: BAAI/bge-m3
    litellm_params:
      model: openai/BAAI/bge-m3
      api_base: http://tei-bge-m3:8080/v1
      api_key: dummy
      encoding_format: float
    model_info:
      max_input_tokens: 8192
      output_vector_size: 1024
      mode: embedding

  # Reranking via TEI's native /rerank with Cohere↔TEI translation (huggingface driver)
  - model_name: BAAI/bge-reranker-v2-m3
    litellm_params:
      model: huggingface/BAAI/bge-reranker-v2-m3
      api_base: http://tei-bge-reranker:8080
      api_key: dummy
    model_info:
      max_input_tokens: 1024     # trained ceiling per HF disc #9
      mode: rerank

litellm_settings:
  drop_params: false             # keep, since encoding_format is explicitly pinned
```

## Open WebUI (env vars)

```
RAG_EMBEDDING_ENGINE=openai
RAG_OPENAI_API_BASE_URL=http://litellm:4000/v1
RAG_OPENAI_API_KEY=<litellm virtual key>
RAG_EMBEDDING_MODEL=BAAI/bge-m3
RAG_EMBEDDING_BATCH_SIZE=32
RAG_EMBEDDING_CONCURRENT_REQUESTS=4

RAG_RERANKING_ENGINE=external
RAG_EXTERNAL_RERANKER_URL=http://litellm:4000/v1/rerank
RAG_EXTERNAL_RERANKER_API_KEY=<litellm virtual key>
RAG_RERANKING_MODEL=BAAI/bge-reranker-v2-m3
```

## TEI manifests (relevant args)

```yaml
# Embedder
args:
  - --model-id=BAAI/bge-m3
  - --port=8080
  - --dtype=float16
  - --max-batch-tokens=32768
  - --max-client-batch-size=64
  - --auto-truncate
  # pooling auto-detected from 1_Pooling/config.json (CLS for BGE-M3)
  # max-input-length auto-detected from config.json max_position_embeddings (8194 → 8192)

# Reranker
args:
  - --model-id=BAAI/bge-reranker-v2-m3
  - --port=8080
  - --dtype=float16
  - --max-batch-tokens=1024              # = trained ceiling, enforced via auto-truncate
  - --max-client-batch-size=128          # cover 2 × Top_K=50 hybrid-search payload
  - --max-concurrent-requests=1024       # raise queue cap above default 512
  - --auto-truncate
```
