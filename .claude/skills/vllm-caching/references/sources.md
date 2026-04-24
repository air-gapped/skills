# External sources

Load-bearing external references cited in this skill, with verification dates. Probed via `gh api` / `gh release list` / WebFetch. Only refreshed when the skill-improver `freshen` mode runs — not meant to be exhaustive.

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| vLLM release list (v0.11.0 – v0.19.1 stable, v0.20.0 pre-release) | https://github.com/vllm-project/vllm/releases | 2026-04-24 | Confirmed v0.11.0 (2025-10-02), v0.11.1 (2025-11-18), v0.14.0 (2026-01-20), v0.19.0 (2026-04-03), v0.19.1 (2026-04-18) all exist. Latest stable: v0.19.1. v0.20.0 is still pre-release. |
| `vllm/v1/kv_offload/` source tree | https://github.com/vllm-project/vllm/tree/main/vllm/v1/kv_offload | 2026-04-24 | Fresh — contains `abstract.py`, `cpu/`, `factory.py`, `mediums.py`, `reuse_manager.py`, `spec.py`, `worker/`. |
| `requirements/kv_connectors.txt` pins | https://github.com/vllm-project/vllm/blob/main/requirements/kv_connectors.txt | 2026-04-24 | Fresh — current pins: `lmcache>=0.3.9`, `nixl-cu12/cu13>=0.7.1,<=0.10.1`, `mooncake-transfer-engine>=0.3.8`. |
| `docs/features/disagg_prefill.md` | https://github.com/vllm-project/vllm/blob/main/docs/features/disagg_prefill.md | 2026-04-24 | Fresh — file exists (~7.8 KB). |
| `docs/features/nixl_connector_compatibility.md` | https://github.com/vllm-project/vllm/blob/main/docs/features/nixl_connector_compatibility.md | 2026-04-24 | Fresh — file exists (~5.4 KB). |
| `docs/features/mooncake_connector_usage.md` | https://github.com/vllm-project/vllm/blob/main/docs/features/mooncake_connector_usage.md | 2026-04-24 | Fresh — file exists (~3.2 KB). |
| `tests/v1/kv_connector/nixl_integration/run_accuracy_test.sh` | https://github.com/vllm-project/vllm/blob/main/tests/v1/kv_connector/nixl_integration/run_accuracy_test.sh | 2026-04-24 | Fresh — file exists (~9.4 KB). |
| `examples/.../mooncake_connector/run_mooncake_connector.sh` | https://github.com/vllm-project/vllm/blob/main/examples/online_serving/disaggregated_serving/mooncake_connector/run_mooncake_connector.sh | 2026-04-24 | Fresh — file exists (~7.9 KB). |
| LMCache config reference | https://docs.lmcache.ai/api_reference/configurations.html | 2026-04-24 | Fresh — 200 OK, page title "Configuring LMCache", no explicit version pinned. |
| NVIDIA GPU Operator GDS + RDMA docs | https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-operator-rdma.html | 2026-04-24 | **Drift** — Helm value `driver.useOpenKernelModules=true` is stale; current docs use `driver.kernelModuleType=open`. Fix applied in `connectors.md`. Page also recommends GPU Operator v26.3.1+ with `gds.enabled=true`. |
| `--calculate-kv-scales` deprecation in `vllm/config/cache.py` | https://github.com/vllm-project/vllm/blob/main/vllm/config/cache.py | 2026-04-24 | **Drift** — Skill previously claimed flag was "removed in v0.19". Probe shows flag is still present as of `main` (after v0.19.1 / v0.20.0rc), emits a deprecation warning, accepts but has no real effect. Wording fixed in `SKILL.md`. |

## Notes on probe budget

This freshen pass used 8/8 probes (6 `gh api` + 1 `gh release list` + 2 `WebFetch` + 1 `gh search code`). All top-tier refs covered. Not probed (lower signal): individual v0.11.0/v0.14.0 release notes (covered by release list), LMCache GitHub repo pins (covered by `kv_connectors.txt`).
