# skills

Claude Code plugin marketplace — 20+ installable reference skills for vLLM, Kubernetes, release engineering, and skill authoring.

## Install

```
/plugin marketplace add air-gapped/skills
/plugin install <plugin>@air-gapped-marketplace
```

Plugins are either single-skill (e.g. `jinja-expert`, `helm`, `keda`) or grouped suites (e.g. `vllm` — bundles all 14 vLLM reference skills into one plugin). See `.claude-plugin/marketplace.json` for the full list.

Versioning scheme per plugin: `0.YYYYMMDD.N` where `YYYYMMDD` is the UTC date of the most recent content change across member skills and `N` is the unique commit count touching any member skill directory. Run `/plugin update` to pick up new bumps.

<!-- skills-start -->
| Skill | Description |
|---|---|
| [`aiperf`](.claude/skills/aiperf/SKILL.md) | NVIDIA AIPerf — vendor-neutral generative-AI inference benchmarking (genai-perf successor). Covers `aiperf profile` with concurrency / request-rate / fixed-schedule trace replay / user-centric / multi-run confidence, 15 endpoint types (chat,… |
| [`autoresearch`](.claude/skills/autoresearch/SKILL.md) | Karpathy-pattern autoresearch — autonomous hill-climbing over a measurable metric, deep multi-agent research, or research-then-optimize. Three modes: Optimize (keep/discard ratchet), Research (STORM multi-perspective), Improve. |
| [`baml-expert`](.claude/skills/baml-expert/SKILL.md) | BAML (Boundary ML) expert for projects defining LLM calls as typed functions in .baml files with a generated Python client. Use whenever the repo contains baml_src/, baml_client/, baml-cli commands, or imports from baml_py / baml_client. Covers… |
| [`helm`](.claude/skills/helm/SKILL.md) | Author and maintain Helm charts: create chart, write templates, values.yaml patterns, _helpers.tpl, Chart.yaml, values.schema.json, helm-docs, library charts. Helm 4 (SSA, WASM, OCI digest). Chart CI/CD (lint, helm-unittest, chart-testing,… |
| [`jinja-expert`](.claude/skills/jinja-expert/SKILL.md) | Author, read, and debug Jinja2 templates across the three places Jinja lives in 2026 — HuggingFace `chat_template.jinja` (rendered by `apply_chat_template` for vLLM / sglang), Ansible playbooks + `.j2` files, and Jinja-adjacent Kubernetes workflows… |
| [`keda`](.claude/skills/keda/SKILL.md) | Configure, operate, and master KEDA (Kubernetes Event-driven Autoscaling) — ScaledObject, ScaledJob, TriggerAuthentication CRDs, 70+ scalers, HPA behavior tuning, scale-to-zero, the KEDA HTTP Add-on, production hardening, multi-trigger semantics,… |
| [`lmcache-mp`](.claude/skills/lmcache-mp/SKILL.md) | LMCache multiprocess (MP) mode — standalone LMCache server in its own pod/process that vLLM connects to over ZMQ. Provides process isolation, no GIL contention on the inference path, one cache shared by multiple vLLM pods on the same node, and… |
| [`makefile-best-practices`](.claude/skills/makefile-best-practices/SKILL.md) | Makefile best practices, patterns, and templates for GNU Make 4.x — dependency graphs, task-runner workflows, parallel-safe recipes, self-documenting help targets, and language-specific patterns (Go, Python, Node, Docker, Helm, POSIX). |
| [`nvidia-nixl`](.claude/skills/nvidia-nixl/SKILL.md) | NVIDIA Inference Xfer Library (NIXL) operator + developer reference. Point-to-point KV-cache and tensor transport for distributed inference (Dynamo, vLLM, SGLang). Covers the C++/Python/Rust agent API, all 13 backend plugins (UCX, GDS, GDS_MT,… |
| [`openshift-app`](.claude/skills/openshift-app/SKILL.md) | Package applications for OpenShift deployment: container images (UBI, arbitrary UID, multi-stage builds), packaging formats (Helm, Kustomize, Operators, OLM v1), CI/CD (Tekton, ArgoCD, Shipwright, Conforma), security (SCC, PSA, supply chain, image… |
| [`prometheus-mimir-grafana`](.claude/skills/prometheus-mimir-grafana/SKILL.md) | Query Prometheus and Grafana Mimir, write and debug PromQL, and build or fix Grafana dashboards — for agents solving problems from metrics. Covers the Prometheus HTTP API (`/api/v1/query`, `query_range`, `series`, `labels`, `metadata`), Mimir… |
| [`sglang-hicache`](.claude/skills/sglang-hicache/SKILL.md) | SGLang HiCache (hierarchical KV cache) — three-tier prefix cache: GPU HBM (L1) → pinned host DRAM (L2) → distributed L3 (Mooncake / 3FS / NIXL / AIBrix / EIC / SiMM / file / LMCache). Covers `--enable-hierarchical-cache`, all `--hicache-*` flags,… |
| [`sglang-model-gateway`](.claude/skills/sglang-model-gateway/SKILL.md) | SGLang Model Gateway (`sgl-model-gateway`, formerly `sgl-router`) — Rust router fronting vLLM/SGLang inference workers on Kubernetes. Trigger on "sgl-model-gateway", "sgl-router", "sglang router", "smg", "amg", "model gateway", "inference gateway",… |
| [`skill-improver`](.claude/skills/skill-improver/SKILL.md) | Autoresearch loop for Claude Code skills — greedy keep/discard hill climbing on a 10-dimension quality rubric, with blind subagent validation for self-scoring bias, plus a `freshen` mode that probes external references (release notes, docs,… |
| [`transformers-config-tokenizers-expert`](.claude/skills/transformers-config-tokenizers-expert/SKILL.md) | Preflight reference for HuggingFace snapshots — what vLLM, sglang, and transformers.generate see at runtime. Covers config-file precedence (tokenizer.json, tokenizer_config.json, generation_config.json, chat_template.jinja), transformers v5… |
| [`vllm-benchmarking`](.claude/skills/vllm-benchmarking/SKILL.md) | Run production vLLM benchmarks — `vllm bench` (serve, throughput, latency, sweep, startup, mm-processor), request-rate vs max-concurrency semantics, TTFT/TPOT/ITL/E2EL percentiles, goodput SLO measurement, prefix-cache workloads, air-gapped… |
| [`vllm-caching`](.claude/skills/vllm-caching/SKILL.md) | vLLM tiered KV cache configuration for production H100/H200 clusters. Native CPU offload, LMCache (CPU+NVMe+GDS), NixlConnector (disaggregated prefill), MooncakeConnector (RDMA), MultiConnector composition. Version gates, sizing math (flag total… |
| [`vllm-chat-templates`](.claude/skills/vllm-chat-templates/SKILL.md) | vLLM chat-template (prompt-side Jinja) operator reference. Template resolution precedence (`--chat-template` → AutoProcessor → tokenizer default → bundled fallback), `chat_template_kwargs` allowlist silently dropping… |
| [`vllm-configuration`](.claude/skills/vllm-configuration/SKILL.md) | Configure vLLM completely — YAML config file format, CLI arg precedence, full VLLM_*/HF_*/TRANSFORMERS_* env-var catalog, end-to-end recipe for air-gapped environments (internal HF mirrors, hf-mirror.com, ModelScope, HF_HUB_OFFLINE with pre-seeded… |
| [`vllm-deployment`](.claude/skills/vllm-deployment/SKILL.md) | Use this skill when authoring, reviewing, or fixing a vLLM Kubernetes manifest, Docker/Podman pod, or OpenShift ServingRuntime — even when the user does not say "vllm". Triggers on: lab cluster performance practices, cache mount + survival across… |
| [`vllm-gemma-4-31b`](.claude/skills/vllm-gemma-4-31b/SKILL.md) | Operating-point reference for serving Gemma 4 31B on vLLM — TP sizing, max_model_len, max_num_seqs, gpu_memory_utilization, kv_cache_dtype, EAGLE3 spec-dec, chat_template choice. |
| [`vllm-input-modalities`](.claude/skills/vllm-input-modalities/SKILL.md) | vLLM non-chat inference surfaces — text embeddings (`/v1/embeddings`, `/v2/embed`), reranking/scoring (`/rerank`, `/score`), speech-to-text (`/v1/audio/transcriptions`, `/v1/audio/translations`), document OCR via VLMs. Covers 2026 `--runner pooling`… |
| [`vllm-nvidia-hardware`](.claude/skills/vllm-nvidia-hardware/SKILL.md) | NVIDIA AI-hardware + vLLM-platform reference covering Hopper (H100/H200), Blackwell (B100/B200/B300) and Blackwell Ultra, Grace-Blackwell superchips and NVL72 racks (GB200, GB300), Vera Rubin (R100/R300) with VR200 NVL144 and Kyber NVL576, Dell… |
| [`vllm-observability`](.claude/skills/vllm-observability/SKILL.md) | Observe production vLLM — `/metrics` Prometheus surface (V1 engine), SLO-driven alerting on TTFT/ITL/queue/KV/preemption/aborts/corrupted-logits, shipping Grafana dashboards in `examples/observability/`, OTLP tracing with `--otlp-traces-endpoint`… |
| [`vllm-omni`](.claude/skills/vllm-omni/SKILL.md) | vLLM-Omni output-side multimodal generation — image (FLUX.1/2, Qwen-Image, GLM-Image, BAGEL, SD3.5, HunyuanImage-3.0), video (Wan2.1/2.2, LTX-2, HunyuanVideo-1.5), TTS (Qwen3-TTS, CosyVoice3, Voxtral-TTS), any-to-any omni (Qwen3-Omni, Qwen2.5-Omni,… |
| [`vllm-performance-tuning`](.claude/skills/vllm-performance-tuning/SKILL.md) | vLLM performance-tuning operator reference — tuning workflow (baseline → bottleneck → knob → re-bench), fused-MoE kernel autotune (`benchmark_moe.py` generates `E=N,N=M,device_name=X.json` configs), DeepEP all-to-all + expert parallelism + EPLB,… |
| [`vllm-quantization`](.claude/skills/vllm-quantization/SKILL.md) | vLLM datacenter-GPU quantization — picking, configuring, troubleshooting NVFP4, FP8, MXFP4, MXFP8, AWQ, GPTQ, INT8, compressed-tensors, modelopt, quark on H100/H200/B200/B300/GB200/GB300. 29 `--quantization` flag values, KV-cache dtypes (fp8_e4m3,… |
| [`vllm-reasoning-parsers`](.claude/skills/vllm-reasoning-parsers/SKILL.md) | vLLM reasoning-parser operator + developer reference. `--reasoning-parser` CLI wiring, `ReasoningParser` contract (non-streaming `extract_reasoning` + per-delta `extract_reasoning_streaming`), `is_reasoning_end` xgrammar gating,… |
| [`vllm-speculative-decoding`](.claude/skills/vllm-speculative-decoding/SKILL.md) | Pick, configure, tune, monitor vLLM speculative decoding in production. Eleven SpeculativeMethod options (ngram, ngram_gpu, medusa, mlp_speculator, draft_model, suffix, eagle, eagle3, dflash, mtp, extract_hidden_states), `--speculative-config` JSON… |
| [`vllm-tool-parsers`](.claude/skills/vllm-tool-parsers/SKILL.md) | vLLM tool-calling operator reference — picking `--tool-call-parser` per model family, writing custom parsers via `--tool-parser-plugin`, navigating vLLM source + GitHub tracker to debug any specific tool-call question. Pointer map, not source… |
<!-- skills-end -->

MIT licensed.
