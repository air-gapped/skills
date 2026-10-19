# Sources

Freshened: 2026-09-22 — every row probed at v0.12.0, still the latest release. Two counts re-derived from the CLI source rather than carried forward: 12 custom dataset formats (baseten_trace and weka_trace landed in v0.12.0) and 42 public datasets, not "20+". The 18 endpoint types reproduce exactly.

Per-row `Last verified:` dates for the external claims in this skill. `freshen` mode reads + updates this file. The header stamp is authoritative: every row above was probed on that date.

| Source | URL | Last verified | Pinned |
|---|---|---|---|
| AIPerf repo | https://github.com/ai-dynamo/aiperf | 2026-09-15 | |
| AIPerf releases | https://github.com/ai-dynamo/aiperf/releases | 2026-10-20 | latest stable **v0.13.0 (2026-09-24)**, up from v0.12.0; no newer tag on 2026-10-20 |
| AIPerf v0.9.0 release notes | https://github.com/ai-dynamo/aiperf/releases/tag/v0.9.0 | 2026-09-15 | v0.9.0 |
| AIPerf v0.10.0 release notes | https://github.com/ai-dynamo/aiperf/releases/tag/v0.10.0 | 2026-09-15 | v0.10.0 |
| AIPerf v0.11.0 release notes | https://github.com/ai-dynamo/aiperf/releases/tag/v0.11.0 | 2026-09-15 | v0.11.0 |
| AIPerf v0.12.0 release notes | https://github.com/ai-dynamo/aiperf/releases/tag/v0.12.0 | 2026-10-20 | v0.12.0 |
| AIPerf v0.13.0 release notes | https://github.com/ai-dynamo/aiperf/releases/tag/v0.13.0 | 2026-10-20 | v0.13.0 — kube (beta, PR #1379), `--per-chunk-usage` (#1279), `--reset-kv-cache` / `--server-profiler` (#1163), `--system-prompt[-file]` (#1268), `--random-range-ratio` (#850), `tracelab` (#1262), `audio_transcription` (#1247), session-affinity header default (#1312) |
| Session-affinity env vars | https://github.com/ai-dynamo/aiperf/blob/v0.13.0/docs/environment-variables.md | 2026-10-20 | `AIPERF_HTTP_X_SESSION_AFFINITY_FROM_CORRELATION_ID` default `True`; Dynamo / SMG / X-Session-ID variants default `False` (PR #1312 sends `X-Session-Affinity`) |
| AIPerf on PyPI | https://pypi.org/project/aiperf/ | 2026-10-20 | latest **0.13.0** (2026-09-24), `requires-python` **>=3.11**,<3.14 — the floor moved 3.10 → 3.11 at v0.12.0 (PR #1107), a breaking install gate; `aiperf-nightly` 0.13.0.dev20261019 |
| AIPerf docs index (Fern) | https://github.com/ai-dynamo/aiperf/blob/main/docs/index.md | 2026-09-15 | |
| CLI options doc | https://github.com/ai-dynamo/aiperf/blob/main/docs/cli-options.md | 2026-10-20 | read at tag `v0.13.0` — authoritative for subcommands (adds `kube *`, `proxy`) and the `--endpoint-type` (19, `audio_transcription` added), `--custom-dataset-type` (13 core + SPEED-Bench, `tracelab` added) and `--public-dataset` (42) enum values |
| `synthesize` command source | https://github.com/ai-dynamo/aiperf/blob/v0.13.0/src/aiperf/cli_commands/synthesize.py | 2026-10-20 | `target: Literal["agentic-code"]` — the only target; no trace input |
| Prefix-synthesis tutorial | https://github.com/ai-dynamo/aiperf/blob/v0.13.0/docs/tutorials/prefix-synthesis.md | 2026-10-20 | trace scaling runs inside `aiperf profile` with `--synthesis-*` flags |
| Endpoint registry (`plugins.yaml`) | https://github.com/ai-dynamo/aiperf/blob/v0.13.0/src/aiperf/plugin/plugins.yaml | 2026-10-20 | `audio_transcription`: `/v1/audio/transcriptions`, non-streaming, multipart (PR #1247) |
| Synthetic audio vs real speech | https://github.com/ai-dynamo/aiperf/issues/1524 | 2026-10-20 | open — white-noise default audio gives unrealistic latency/RTFx for ASR |
| TraceLab tutorial | https://github.com/ai-dynamo/aiperf/blob/v0.13.0/docs/tutorials/tracelab-trace.md | 2026-10-20 | `tracelab` type (PR #1262); corpus at uw-syfi/TraceLab release v0.0.2; auto fixed-schedule, `--no-fixed-schedule` for capped pauses |
| Synthetic prompt reuse across runs | https://github.com/ai-dynamo/aiperf/issues/1579 | 2026-10-20 | open (filed against 0.13.0) — default `--num-dataset-entries 100` + fixed seed → prefix-cache hits (SGLang 1024/1024 cached tokens, vLLM 91% hit rate). Mechanism confirmed in `docs/cli-options.md` v0.13.0 (`--num-dataset-entries` default 100, reused; `--set-consistent-seed` default True; `--vary-seed-per-trial` default False) |
| Watchdog reaps services during raw export | https://github.com/ai-dynamo/aiperf/issues/1467 | 2026-10-20 | open, 0.13.0 regression (dead-component detection, PR #1325); fix PR #1468 open, unmerged on 2026-10-20 |
| Truncated raw export with exit 0 | https://github.com/ai-dynamo/aiperf/issues/1532 | 2026-10-20 | open; observed 0.12.0, force-kill path still in 0.13.0; reporter's 0.13.0 run with `AIPERF_SERVICE_HEARTBEAT_MISSED_THRESHOLD=24` exited 0 with a complete file. Env var documented in docs/environment-variables.md at v0.13.0 (default 3, range 1–100) |
| Throughput denominator | https://github.com/ai-dynamo/aiperf/issues/1492 | 2026-10-20 | open; reproduced on main by a second reporter (200 req: 7.89 s phase window vs 7.79 s benchmark_duration) |
| Metrics reference | https://github.com/ai-dynamo/aiperf/blob/main/docs/metrics-reference.md | 2026-09-15 | |
| Architecture | https://github.com/ai-dynamo/aiperf/blob/main/docs/architecture.md | 2026-09-15 | |
| Migrating from GenAI-Perf | https://github.com/ai-dynamo/aiperf/blob/main/docs/migrating.md | 2026-09-15 | |
| Plugin system doc | https://github.com/ai-dynamo/aiperf/blob/main/docs/plugins/plugin-system.md | 2026-09-15 | |
| Environment variables | https://github.com/ai-dynamo/aiperf/blob/main/docs/environment-variables.md | 2026-09-15 | |
| Comprehensive LLM benchmarking | https://github.com/ai-dynamo/aiperf/blob/main/docs/comprehensive-llm-benchmarking.md | 2026-09-15 | |
| Timing modes reference | https://github.com/ai-dynamo/aiperf/blob/main/docs/benchmark-modes/timing-modes-reference.md | 2026-09-15 | |
| Working with profile exports | https://github.com/ai-dynamo/aiperf/blob/main/docs/tutorials/working-with-profile-exports.md | 2026-09-15 | |
| Mooncake KV-cache traces | https://github.com/kvcache-ai/Mooncake | 2026-09-15 | FAST25-release |
| Mooncake arxiv trace JSONL | https://raw.githubusercontent.com/kvcache-ai/Mooncake/refs/heads/main/FAST25-release/arxiv-trace/mooncake_trace.jsonl | 2026-09-15 | |
| BurstGPT trace paper | https://arxiv.org/abs/2401.17644 | 2026-10-20 | "BurstGPT: A Real-world Workload Dataset to Optimize LLM Serving Systems" (title confirmed on the abs page). The ID previously cited here, 2401.17286, is an unrelated astrophysics paper. |
| DistServe / goodput paper | https://arxiv.org/pdf/2401.09670 | 2026-09-15 | |
| Hao-AI DistServe blog | https://hao-ai-lab.github.io/blogs/distserve | 2026-09-15 | |
| GenAI-Perf (predecessor) | https://github.com/triton-inference-server/perf_analyzer/tree/main/genai-perf | 2026-09-15 | |
| AIPerf DeepWiki | https://deepwiki.com/ai-dynamo/aiperf | 2026-09-15 | |
| AIPerf Discord | https://discord.gg/D92uqZRjCZ | 2026-09-15 | |
