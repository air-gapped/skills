# Sources

All citations backing the skill. Verify any claim via the linked source.

## vLLM source code + benchmarks

- `benchmarks/kernels/benchmark_moe.py` — [GitHub](https://github.com/vllm-project/vllm/blob/main/benchmarks/kernels/benchmark_moe.py)
- `vllm/model_executor/layers/fused_moe/configs/` — shipped MoE configs
- `vllm/model_executor/layers/fused_moe/prepare_finalize/deepep_ht.py` + `deepep_ll.py` — DeepEP paths
- `vllm/config/compilation.py` — CUDAGraphMode enum
- `vllm/config/scheduler.py` — scheduler knobs
- `vllm/config/parallel.py` — TP/PP/EP/DP config
- `vllm/engine/arg_utils.py` — CLI flag surface
- `vllm/envs.py` — env var catalog
- `benchmarks/auto_tune/auto_tune.sh` — `max_num_seqs × max_num_batched_tokens` sweep

## Community tuned-config repos

- [MissionSquad/vllm-moe-configs](https://github.com/MissionSquad/vllm-moe-configs) — crowd-sourced tuned MoE JSONs
- [Jetson AGX Thor perf thread](https://forums.developer.nvidia.com/t/jetson-agx-thor-vllm-26-02-moe-performance-significantly-below-reference-missing-fused-moe-config/364663)

## Official vLLM docs

- [Optimization & Tuning](https://docs.vllm.ai/en/stable/configuration/optimization/)
- [CUDA graphs design](https://docs.vllm.ai/en/stable/design/cuda_graphs/)
- [torch.compile design](https://docs.vllm.ai/en/latest/design/torch_compile/)
- [CompilationConfig API](https://docs.vllm.ai/en/latest/api/vllm/config/compilation/)
- [V1 User Guide](https://docs.vllm.ai/en/latest/usage/v1_guide/)
- [Expert Parallel Deployment](https://docs.vllm.ai/en/latest/serving/expert_parallel_deployment/)
- [Parallelism scaling](https://docs.vllm.ai/en/stable/serving/parallelism_scaling/)
- [Disaggregated prefill](https://docs.vllm.ai/en/latest/features/disagg_prefill/)
- [NixlConnector usage](https://docs.vllm.ai/en/stable/features/nixl_connector_usage/)
- [Perf benchmarking dashboard](https://docs.vllm.ai/en/latest/benchmarking/dashboard/)

## vLLM recipes (per-model deployment guides)

- [DeepSeek-V3.2](https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-V3_2.html)
- [Qwen3-Coder-480B-A35B](https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3-Coder-480B-A35B.html)
- [Kimi-K2](https://docs.vllm.ai/projects/recipes/en/latest/moonshotai/Kimi-K2.html)
- [GLM-4.X](https://docs.vllm.ai/projects/recipes/en/latest/GLM/GLM.html)

## vLLM blog (headline perf posts)

- [V1 Alpha — 2025-01-27](https://blog.vllm.ai/2025/01/27/v1-alpha-release.html) — 1.7× vs V0
- [Anatomy of vLLM — 2025-09-05](https://vllm.ai/blog/anatomy-of-vllm) — V1 internals
- [Llama-4 serving — 2025-04-05](https://blog.vllm.ai/2025/04/05/llama4.html) — Scout / Maverick recipes
- [torch.compile — 2025](https://vllm.ai/blog/torch-compile) — `-O` levels, fusions
- [DeepSeek-V3.2 — 2025](https://vllm.ai/blog/deepseek-v3-2) — FlashMLA-Sparse recipe
- [Blackwell InferenceMAX — 2025-10-09](https://vllm.ai/blog/blackwell-inferencemax) — Blackwell wins, `--async-scheduling`
- [Wide-EP H200 — 2025-12-17](https://vllm.ai/blog/large-scale-serving) — 2.2k tok/s/GPU DeepSeek-R1
- [Wide-EP GB200 Part I — 2026-02-03](https://vllm.ai/blog/dsr1-gb200-part1) — 26.2K / 10.1K TPGS
- [Speculators v0.3.0 — 2025-12-13](https://blog.vllm.ai/2025/12/13/speculators-v030.html)

## Red Hat posts

- [Performance boosts v0.8.1 V1 — 2025-04-28](https://developers.redhat.com/articles/2025/04/28/performance-boosts-vllm-081-switching-v1-engine)
- [Scaling DeepSeek-style MoEs — 2025-09-08](https://developers.redhat.com/articles/2025/09/08/scaling-deepseek-style-moes-vllm-and-llm-d-using-wide-ep)
- [torch.compile deep-dive — 2025-09-03](https://developers.redhat.com/articles/2025/09/03/vllm-torchcompile-efficient-llm-inference-pytorch)
- [Practical strategies — 2026-03-03](https://developers.redhat.com/articles/2026/03/03/practical-strategies-vllm-performance-tuning)
- [5 steps to triage — 2026-03-09](https://developers.redhat.com/articles/2026/03/09/5-steps-triage-vllm-performance)
- [Red Hat MLPerf v5.1 — 2025](https://www.redhat.com/en/blog/efficient-and-reproducible-llm-inference-red-hat-mlperf-inference-v51-results)

## Cloud + partner posts

- [LMSYS DeepSeek 96× H100 — 2025-05-05](https://www.lmsys.org/blog/2025-05-05-large-scale-ep/) — PD-disagg production numbers
- [Microsoft Azure DeepEP — 2025](https://techcommunity.microsoft.com/blog/azurehighperformancecomputingblog/achieving-optimal-performance-for-deepseek-expert-parallelism-deepep-on-azure/4414699) — NVSHMEM tuning
- [Google Cloud xPU tuning guide](https://cloud.google.com/blog/topics/developers-practitioners/vllm-performance-tuning-the-ultimate-guide-to-xpu-inference-configuration) — `auto_tune.sh`
- [Anyscale Ray Serve LLM](https://www.anyscale.com/blog/ray-serve-llm-anyscale-apis-wide-ep-disaggregated-serving-vllm) — Wide-EP + PD as Pythonic builder
- [LMCache NIXL — 2025-04-11](https://blog.lmcache.ai/en/2025/04/11/shaping-nixl-based-pd-disaggregation-in-vllm-v1) — PD-disagg in vLLM V1
- [PyTorch + vLLM disagg](https://pytorch.org/blog/disaggregated-inference-at-scale-with-pytorch-vllm/)
- [AMD vLLM MoE Playbook](https://rocm.blogs.amd.com/software-tools-optimization/vllm-moe-guide/README.html) — activation density + concurrency crossover
- [AMD MLPerf v5.1](https://rocm.blogs.amd.com/artificial-intelligence/mlperf-inference-v5.1/README.html)
- [NVIDIA Blackwell Ultra MLPerf](https://developer.nvidia.com/blog/nvidia-blackwell-ultra-sets-new-inference-records-in-mlperf-debut/)
- [Lambda HGX B200 MLPerf](https://lambda.ai/blog/lambda-mlperf-inference-v5.1)

## NVIDIA docs

- [GB200 multi-node NCCL tuning](https://docs.nvidia.com/multi-node-nvlink-systems/multi-node-tuning-guide/nccl.html)
- [NCCL env vars](https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/env.html)
- [DCGM field IDs](https://docs.nvidia.com/datacenter/dcgm/latest/dcgm-api/dcgm-api-field-ids.html)

## MLCommons / MLPerf

- [MLPerf v5.0 announcement](https://mlcommons.org/2025/04/llm-inference-v5/) — Llama 3.1 405B added
- [MLPerf v5.1 results](https://www.hpcwire.com/2025/09/10/mlperf-inference-v5-1-results-land-with-new-benchmarks-and-record-participation/)

## Goodput / SLO / inference perf research

- [DistServe paper / goodput blog](https://haoailab.com/blogs/distserve/)
- [Revisiting SLO & Goodput arxiv 2410.14257](https://arxiv.org/html/2410.14257v1)
- [SemiAnalysis InferenceMAX announcement](https://newsletter.semianalysis.com/p/inferencemax-open-source-inference)
- [InferenceX dashboard](https://inferencex.semianalysis.com/)

## Key issues / PRs referenced

### Version-specific regressions
- [#35048](https://github.com/vllm-project/vllm/issues/35048) — v0.14→v0.15.1 MiniMax latency +24%
- [#32547](https://github.com/vllm-project/vllm/issues/32547) — GLM-4.7-GPTQ-Int4 MTP v0.13→v0.14.0rc2
- [#28882](https://github.com/vllm-project/vllm/issues/28882) — H200 DeepSeek-R1 EP 1.5× TTFT regression (DeepGEMM M<128)
- [#29539](https://github.com/vllm-project/vllm/issues/29539) — FULL_AND_PIECEWISE garbage `!!!` output
- [#25538](https://github.com/vllm-project/vllm/issues/25538) — preempt/resume thrashing
- [#19579](https://github.com/vllm-project/vllm/issues/19579) — ROCm V1 piecewise capture size

### Async-scheduling status
- [#27679](https://github.com/vllm-project/vllm/issues/27679) — PP compatibility (still open)
- [#27614](https://github.com/vllm-project/vllm/issues) — default-on landing
- [#28250](https://github.com/vllm-project/vllm/issues) — follow-up
- [#26866](https://github.com/vllm-project/vllm/issues) — structured-output fix
- [#24799](https://github.com/vllm-project/vllm/issues) — spec-dec fix
- [#29821](https://github.com/vllm-project/vllm/issues) — spec-dec follow-up
- [#31679](https://github.com/vllm-project/vllm/issues/31679) — multimodal compatibility

### MoE / DeepEP
- [#17619](https://github.com/vllm-project/vllm/issues/17619) — default-config warning
- [#24112](https://github.com/vllm-project/vllm/issues/24112) — RFC improve MoE tuning
- [#28456](https://github.com/vllm-project/vllm/issues/28456) — config discovery improvements
- [#12408](https://github.com/vllm-project/vllm/pull/12408) — MI300 Mixtral 8x7B/8x22B configs
- [#27513](https://github.com/vllm-project/vllm/issues/27513) — pplx + microbatching incompat
- [#21306](https://github.com/vllm-project/vllm/issues/21306) — DeepEP dp=2,tp=8,ep=16 hang
- [#18343](https://github.com/vllm-project/vllm/pull/18343) — EPLB

### Scheduler
- [#10544](https://github.com/vllm-project/vllm/pull/10544) — `max_num_batched_tokens` 512→2048 default
- [#27869](https://github.com/vllm-project/vllm/pull/27869) — `--stream-interval`
- [#25951](https://github.com/vllm-project/vllm/pull/25951) — CI CUDA-graph size

### Cloud / infra
- [#16992](https://github.com/vllm-project/vllm/pull/16992) — GB200 NCCL env-var defaults

### Vendor-specific
- [#34641](https://github.com/vllm-project/vllm/issues/34641) — MI300X FP4BMM crash
- [#31475](https://github.com/vllm-project/vllm/issues/31475) — MI300X FP8 slower than BF16
- [#34249](https://github.com/vllm-project/vllm/issues/34249) — Hopper FP8 MoE FlashInfer auto-select
- [#38971](https://github.com/vllm-project/vllm/issues/38971) — NVFP4 MoE on SM120
- [#20069](https://github.com/vllm-project/vllm/issues/20069) — MI300X Whisper inaccurate
- [#28362](https://github.com/vllm-project/vllm/issues/28362) — Intel 125H Arc fail
- [#30758](https://github.com/vllm-project/vllm/issues/30758) — gpt-oss B200/GB200 tracker
- [vllm-ascend #4649](https://github.com/vllm-project/vllm-ascend/issues/4649) — async-sched precision
- [pytorch #169857](https://github.com/pytorch/pytorch/issues/169857) — MI325X Qwen2.5-VL 100× slowdown

### Forum threads
- [MoE config on GH200](https://discuss.vllm.ai/t/moe-config-on-gh200/1718)
- [Ascend 910B hang](https://discuss.vllm.ai/t/on-8-card-ascend-910b-with-vllm-serving-qwen3-5-122b-a10b-the-client-freezes-at-8-progress-when-running-accuracy-test-as-the-server-stops-receiving-new-requests-after-running-reqs-and-kv-cache-fall-to-0/2538)
- [v0.9.0.1 vs v0.10.0 regression](https://discuss.vllm.ai/t/performance-degradation-report-0-9-0-1-vs-0-10-0/1368)
- [CUDA-graph capture size](https://discuss.vllm.ai/t/why-is-cuda-graph-capture-sizes-limited-by-max-num-seqs/954)

## Paired vLLM skills

- `vllm-benchmarking` — how to measure (`vllm bench`, goodput)
- `vllm-caching` — KV cache, LMCache, Nixl / Mooncake
- `vllm-nvidia-hardware` — GPU SKUs, GEMM backends
- `vllm-configuration` — env var catalog, YAML
- `vllm-observability` — `/metrics`, DCGM dashboards
- `vllm-speculative-decoding` — EAGLE-3, DFlash
- `vllm-input-modalities` — embeddings / rerank / STT / OCR
- `vllm-omni` — output-side modalities (image / video / TTS)

## Refresh policy

Compiled 2026-04-18 against vLLM v0.19.0. Refresh when:
- v0.20.x stable lands.
- Major regression in referenced issue list closes ([#28882](https://github.com/vllm-project/vllm/issues/28882), [#35048](https://github.com/vllm-project/vllm/issues/35048), [#34641](https://github.com/vllm-project/vllm/issues/34641)).
- Wide-EP GB200 Part II ships — currently Part I only.
- New MLPerf round with vLLM submission.
