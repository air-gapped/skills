# Endpoint Types

Pick `--endpoint-type <name>` to match the inference target's wire format. AIPerf appends the canonical path to `--url` automatically; override via `--custom-endpoint` for non-standard paths.

## Built-in endpoints (15)

| `--endpoint-type` | Default path | Streaming | Wire format / target |
|---|---|---|---|
| `chat` | `/v1/chat/completions` | yes | OpenAI Chat Completions. Multi-modal (text + image + audio + video). Most common. |
| `chat_embeddings` | `/v1/chat/completions` | no | vLLM multimodal embeddings via chat API. |
| `completions` | `/v1/completions` | yes | OpenAI legacy text completion. |
| `responses` | `/v1/responses` | yes | OpenAI Responses API. v0.7.0 added support (PR #695). |
| `embeddings` | `/v1/embeddings` | no | OpenAI Embeddings. Returns vectors. Use `--prompt-batch-size` to batch. |
| `nim_embeddings` | `/v1/embeddings` (NIM) | no | NVIDIA NIM Embeddings. |
| `cohere_rankings` | `/v1/rerank` | no | Cohere Reranking API. |
| `hf_tei_rankings` | `/rerank` | no | HuggingFace TEI Reranker. |
| `nim_rankings` | `/v1/ranking` | no | NVIDIA NIM Rankings. |
| `nim_image_retrieval` | `/v1/retrieval` | no | NVIDIA NIM image search. v0.7.0 (PR #725). |
| `image_generation` | `/v1/images/generations` | no | OpenAI Image Generation. Returns URLs or base64. |
| `video_generation` | varies | async polling | Async job API. AIPerf polls `/v1/videos/{job_id}` (interval `AIPERF_HTTP_VIDEO_POLL_INTERVAL`, default 0.1 s). With `--download-video-content`, latency includes the bytes. |
| `huggingface_generate` | `/generate`, `/generate_stream` | yes | HuggingFace TGI native API. |
| `solido_rag` | varies | yes | SOLIDO RAG pipeline. |
| `template` | configurable | configurable | Custom JSON schema via `--custom-endpoint`. Use this when the target speaks a non-standard variant of OpenAI. |

`aiperf plugins endpoint` lists the live registry. `aiperf plugins endpoint <name>` prints the class path, package, and metadata.

## Streaming → metric availability

The streaming-only metrics (`time_to_first_token`, `time_to_second_token`, `time_to_first_output_token`, `inter_token_latency`, `inter_chunk_latency`, `output_token_throughput_per_user`, `prefill_throughput_per_user`) require BOTH `--streaming` and an endpoint that natively streams (chat / completions / responses / huggingface_generate / solido_rag). For non-streaming endpoints (embeddings / rankings / image), only `request_latency`, throughput, and the API-usage metrics apply.

## Reasoning models

Endpoints that emit `reasoning_content` (DeepSeek-R1, Qwen3 with thinking, GPT-OSS-class) need:

- `--streaming` to pick up incremental TTFT vs TTFO timing.
- `--use-server-token-count` if the server's tokenizer for reasoning differs from the public HF one.

The metric flag `SUPPORTS_REASONING` toggles inclusion of `reasoning_token_count` and the TTFO/TTFT split.

## Custom endpoints — three escape hatches

1. **`--custom-endpoint <path>`** — keep an existing built-in type, but override the URL path. Use for "OpenAI-compat but at `/my-api/chat`".
2. **`--endpoint-type template`** — flexible payload. Configure via the template-endpoint plugin metadata in a local `plugins.yaml`. See `plugins.md`.
3. **Custom plugin** — implement `BaseEndpoint`, register in `plugins.yaml`, add an entry point in `pyproject.toml`. See `plugins.md` for the 4-step recipe.

## Quick recipes by target

### vLLM / SGLang / TensorRT-LLM (OpenAI-compat chat)

```bash
aiperf profile -m my-model -u http://endpoint:8000 \
  --endpoint-type chat --streaming --tokenizer my-model
```

### vLLM video generation

```bash
aiperf profile -m my-video-model -u http://endpoint:8000 \
  --endpoint-type video_generation \
  --request-content-type multipart/form-data \
  --download-video-content \
  --video-batch-size 1 --video-duration 5 --video-fps 24 --video-width 1280 --video-height 720
```

### HuggingFace TGI

```bash
aiperf profile -m my-model -u http://tgi:8080 \
  --endpoint-type huggingface_generate --streaming --tokenizer my-model
```

### NIM Embeddings

```bash
aiperf profile -m nvidia/nv-embedqa-e5-v5 -u http://nim:8000 \
  --endpoint-type nim_embeddings --tokenizer intfloat/e5-large-v2 \
  --prompt-batch-size 16 --concurrency 32 --request-count 5000
```

### Cohere reranker

```bash
aiperf profile -m rerank-english-v3.0 -u https://api.cohere.com \
  --endpoint-type cohere_rankings \
  --api-key $COHERE_API_KEY \
  --prompt-batch-size 8
```

### OpenAI Image Generation

```bash
aiperf profile -m my-img-model -u http://endpoint:8000 \
  --endpoint-type image_generation \
  --image-batch-size 1 --image-width-mean 1024 --image-height-mean 1024 \
  --request-count 100
```
