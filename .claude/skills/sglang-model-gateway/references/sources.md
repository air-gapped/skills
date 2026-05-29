# Source citations — sgl-model-gateway

Dated index of every external claim in this skill. The `Last verified` column tracks when the source was last cross-checked against upstream. `freshen` mode (per `skill-improver`) reads and stamps these dates. Manual updates from improve-mode runs are also valid as long as the citation was actually re-verified, not just date-bumped.

## Upstream project

| Source | Claim in skill | Last verified | Pinned |
|---|---|---|---|
| https://github.com/sgl-project/sglang | Project home (was `sgl-router`, renamed to `sgl-model-gateway` Dec 2025). Local clone at `~/projects/github.com/sgl-project/sglang/`. | 2026-05-28 | branch: main; release tag `gateway-v0.3.1`, crate v0.3.2 |
| https://github.com/sgl-project/sglang/tree/main/sgl-model-gateway | Gateway crate root. | 2026-05-28 | |
| https://docs.sglang.io/docs/advanced_features/sgl_model_gateway.md | Upstream operator docs. "Load Balancing Policies" table documents `random`, `round_robin`, `power_of_two`, `cache_aware` (default), `bucket` as `--policy` values; the skill's six `--policy`-selectable + two factory-only split is sourced from `src/policies/factory.rs:77-91` (see cli-flags.md). | 2026-05-28 | |
| https://github.com/sgl-project/sglang/pull/14283 | Crate rename `sglang-router` → `sgl-model-gateway`. | 2026-05-28 | merged 2025-12-02 |
| https://github.com/sgl-project/sglang/pull/14312 | Source dir rename `sgl-router/` → `sgl-model-gateway/`. | 2026-05-28 | merged 2025-12-05 |
| https://github.com/sgl-project/sglang/pull/13120 | First-class vLLM gRPC backend (`RuntimeType::Vllm`). PD with vLLM not supported per limitation matrix. | 2026-05-28 | merged 2025-11-12 |
| https://github.com/sgl-project/sglang/issues/20184 | Service discovery only watches one port per pod. | 2026-05-09 | |
| https://github.com/sgl-project/sglang/issues/17623 | Operator repro: cache_aware ≈ k8s round-robin with abundant KV memory. | 2026-05-09 | |

## Tokenizer crate (separate repo)

| Source | Claim in skill | Last verified | Pinned |
|---|---|---|---|
| https://crates.io/crates/llm-tokenizer | `llm-tokenizer = "=1.3.2"` in gateway Cargo.toml; repository = `lightseekorg/smg`. crates.io newest_version = 1.3.2. | 2026-05-28 | version 1.3.2 |
| https://github.com/lightseekorg/smg | Source repo for `llm-tokenizer` crate (and the broader sgl-model-gateway alternate distribution). | 2026-05-09 | pushed_at 2026-05-07 |
| `lightseekorg/smg::crates/tokenizer/src/factory.rs` | `create_tokenizer_async_with_chat_template` dispatch matrix: directory scan picks `tokenizer.json` first, falls back to `tiktoken.model`/`*.tiktoken`; SentencePiece `.model` returns "not yet supported"; GGUF returns "not yet supported"; `is_likely_openai_model` triggers built-in tiktoken; otherwise HF Hub download. | 2026-05-09 | |
| `lightseekorg/smg::crates/tokenizer/src/tiktoken.rs` | `CL100K_BASE_PATTERN` hardcoded for ALL tiktoken-loaded models incl. Kimi K2 / DeepSeek; comment acknowledges Kimi K2's native `\p{Han}` regex differs but BPE roundtrip-safe. `find_tiktoken_file` / `has_tiktoken_file` / `is_tiktoken_file` semantics. | 2026-05-09 | |

## Gateway source (cited file:line refs in SKILL.md / references/)

| Source | Claim in skill | Last verified | Pinned |
|---|---|---|---|
| `sgl-model-gateway/src/lib.rs:13` | `pub use llm_tokenizer as tokenizer;` re-export. | 2026-05-09 | |
| `sgl-model-gateway/src/policies/cache_aware.rs:22` | "The tree stores raw text characters" — cache_aware is text-based, not token-based. | 2026-05-09 | |
| `sgl-model-gateway/src/policies/cache_aware.rs:67,324,428,453` | Tree insert/remove ops sync via mesh CRDT. | 2026-05-09 | |
| `sgl-model-gateway/src/policies/prefix_hash.rs:107,217` | xxh3 over first N (default 256) token IDs against consistent-hash ring. | 2026-05-09 | |
| `sgl-model-gateway/src/routers/grpc/utils.rs:398-505` | gRPC path requires `HuggingFaceTokenizer` via `downcast_ref`; tiktoken-only models error with *"gRPC router requires HuggingFace tokenizer with chat template support"*. | 2026-05-09 | |
| `sgl-model-gateway/src/core/steps/worker/local/discover_metadata.rs:237-298` | HTTP service discovery falls through gracefully on `/server_info`+`/model_info` 404s, registers worker with empty labels. | 2026-05-09 | |
| `sgl-model-gateway/src/server.rs:753-759` | Rate-limit window counters synced via mesh CRDT. | 2026-05-09 | |
| `sgl-model-gateway/src/main.rs:903` | Default mesh peer-discovery annotation `sglang.ai/ha-port` (NOT `sglang.ai/mesh-port`). | 2026-05-09 | |
| `sgl-model-gateway/src/main.rs:1099-1102` | `--mesh-peer-urls` parsed as `IP:port` SocketAddr; only `first()` used as bootstrap peer. | 2026-05-09 | |
| `sgl-model-gateway/Cargo.toml` | `crdts = "7.3"` for CRDT mesh sync; `llm-tokenizer = "=1.3.2"`. Crate version v0.3.2. | 2026-05-28 | version 0.3.2 |

## vLLM cross-references

| Source | Claim in skill | Last verified | Pinned |
|---|---|---|---|
| `vllm/entrypoints/cli/serve.py:64-104` | DP load-balancer modes: internal (default), external (`--data-parallel-external-lb`), hybrid. | 2026-05-09 | |
| `vllm/config/parallel.py:135-146` | "useful for a 'one-pod-per-rank' wide-EP setup in Kubernetes". | 2026-05-09 | |

## Container images

| Source | Claim in skill | Last verified | Pinned |
|---|---|---|---|
| `lmsysorg/sgl-model-gateway:v0.3.2` (Docker Hub) | Current operator image; old `lmsysorg/sglang-router:*` deprecated post Dec 2025 rename. `v0.3.2` + `latest` both last_updated 2026-05-27 (then `v0.3.1` 2026-01-11, `v0.3.0` 2026-01-05). Note: the git release tag is `gateway-v0.3.1` — the image/crate `v0.3.2` legitimately trails the release-tag scheme, do not churn this. | 2026-05-28 | image v0.3.2 / release tag gateway-v0.3.1 |

## HuggingFace model references

| Source | Claim in skill | Last verified | Pinned |
|---|---|---|---|
| https://huggingface.co/moonshotai/Kimi-K2.6 | Ships `tiktoken.model`, `tokenizer_config.json`, `chat_template.jinja`, `tokenization_kimi.py`, `kimi_k25_processor.py`, `kimi_k25_vision_processing.py`, `media_utils.py`, `preprocessor_config.json`, `configuration_*.py`, `modeling_*.py`, `tool_declaration_ts.py`. NO `tokenizer.json`. Multimodal (vision). | 2026-05-09 | |
| https://huggingface.co/moonshotai/Kimi-K2-Instruct | Reference: same tiktoken-only file shape. | 2026-05-09 | |

## Metric and naming history

| Source | Claim in skill | Last verified | Pinned |
|---|---|---|---|
| Dec 2025 rename | `sgl_router_*` → `smg_*` Prometheus prefix (upstream docs metric table uses `smg_http_*`, `smg_router_*`, `smg_worker_*`, `smg_db_*`, `smg_discovery_*`, `smg_mcp_*`); binary names `sgl-model-gateway` / `smg` / `amg`; release tags `gateway-vX.Y.Z`. Python launcher module `sglang_router` *not* renamed. | 2026-05-28 | event date Dec 2025 |

## How to refresh

Run `skill-improver freshen sglang-model-gateway` to re-probe these references and stamp fresh `Last verified:` dates. Manual freshening is acceptable when the verifier (operator) has already cross-checked against upstream within the same session — record the date honestly.
