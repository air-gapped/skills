# External sources

Load-bearing external references cited in this skill, with verification dates. Probed via `gh api` / `gh release list` / WebFetch / a local clone of `ai-dynamo/nixl`. Refresh via the `freshen` mode of the `skill-improver` skill.

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| NIXL repo (canonical) | https://github.com/ai-dynamo/nixl | 2026-07-21 | Active. Default branch `main`. **Latest tag v1.3.1 (2026-07-08)**; HEAD `pyproject.toml` reports **1.4.0**. |
| NIXL release list | https://github.com/ai-dynamo/nixl/releases | 2026-07-21 | v1.3.1 (2026-07-08, isLatest), v1.3.0 (2026-06-15), v1.2.0 (2026-05-30), v1.1.0 (2026-05-12), v1.0.1 (2026-04-14), v1.0.0 (2026-03-13). |
| NIXL v1.2.0 release notes | https://github.com/ai-dynamo/nixl/releases/tag/v1.2.0 | 2026-07-21 | OS-assigned metadata-listener port (`listen_port=0`, #1439) + port type `int`→`uint16_t`; libfabric EFA `FI_MORE` doorbell batching, **30–58% write-bandwidth gain** on small-message high-descriptor transfers (#1626); `UCX_MAX_HCA_PER_GPU=auto` on UCX ≥ 1.21 (#1637); `nixl_cuda_arch_list` meson option (#1639); `liburing` via meson wrap 2.14 (#1577). |
| NIXL v1.3.0 release notes | https://github.com/ai-dynamo/nixl/releases/tag/v1.3.0 | 2026-07-21 | **AMD ROCm/HIP support** for MI300X/MI325X/MI350X/MI355X incl. `nixlbench` (#1642, #1647); **C++20 required** for source builds (#1571); **DDN Infinia backend plugin** (#1569); path-based file registration for all `FILE_SEG` backends (#1635); obj vendor-backend self-registration (#1550); telemetry `category` field **removed** (#1649); NIXL-EP rank/expert semantics refactor with legacy mask-clean API removed (#1693); GIL released during `makeXferReq` (#1712); batched `remDescList` (#1597). |
| NIXL v1.3.1 release notes | https://github.com/ai-dynamo/nixl/releases/tag/v1.3.1 | 2026-07-21 | Patch. Unique path-mode `devId` per registered `FILE_SEG` file now enforced (`NIXL_ERR_INVALID_PARAM`), fixing a double-free on deregister (#1790, fixes #1766). Multi-PyTorch `nixl_ep` wheels (2.11/2.12/2.13, #1775, #1866); manylinux wheels bundle `libplugin_INFINIA.so` (#1832). |
| `docs/nixl.md` (architecture) | https://github.com/ai-dynamo/nixl/blob/main/docs/nixl.md | 2026-04-25 | Fresh — covers Memory Section, Transfer Backend Interface, Metadata Handler, agent lifecycle, side-channel + central metadata flows. |
| `docs/BackendGuide.md` (SB API) | https://github.com/ai-dynamo/nixl/blob/main/docs/BackendGuide.md | 2026-04-25 | Fresh — canonical SB API spec, plugin manager API, descriptor list abstraction, capability flags. Headers in `src/api/cpp/backend`. |
| `docs/python_api.md` | https://github.com/ai-dynamo/nixl/blob/main/docs/python_api.md | 2026-04-25 | Fresh — points at `src/api/python/_api.py` (1099 lines) for full surface; covers QueryMem, GDS, basic_two_peers, partial_md examples. |
| `docs/telemetry.md` | https://github.com/ai-dynamo/nixl/blob/main/docs/telemetry.md | 2026-04-25 | Fresh — env-var matrix, event categories, cyclic buffer + Prometheus exporter modes. |
| `src/api/python/_api.py` | https://github.com/ai-dynamo/nixl/blob/main/src/api/python/_api.py | 2026-04-25 | 1099 lines. `nixl_agent`, `nixl_agent_config`, `nixl_xfer_handle`, `nixl_prepped_dlist_handle`, all transfer/metadata methods. |
| `pyproject.toml` (NIXL Python pkg) | https://github.com/ai-dynamo/nixl/blob/main/pyproject.toml | 2026-07-21 | Package name `nixl-cu12` / `nixl-cu13`, version **1.4.0** at HEAD, torch==2.11.* build pin, Python ≥ 3.10. |
| `src/plugins/` directory | https://github.com/ai-dynamo/nixl/tree/main/src/plugins | 2026-07-21 | **15 plugins** at tag v1.3.1: azure_blob, cuda_gds, gds_mt, gpunetio, gusli, hf3fs, **infinia**, libfabric, mooncake, obj, posix, telemetry, **tracing**, uccl, ucx. `infinia` added in v1.3.0 (#1569); the skill's "13 plugins" figure was from the v1.0.1/v1.1.0 era. |
| UCX plugin source | https://github.com/ai-dynamo/nixl/tree/main/src/plugins/ucx | 2026-04-25 | Source-of-truth for UCX backend behavior. v1.0.1 PRs #1565 (progress+notif), #1573 (remove indirection), #1527 (EFA-only config). |
| libfabric plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/libfabric/README.md | 2026-04-25 | Multi-rail RDMA, GPU Direct, hwloc topology mapping, AWS EFA validated. v1.21.0+ libfabric, hwloc 2.10+, libnuma. |
| Mooncake plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/mooncake/README.md | 2026-04-25 | Preview status. Own metadata path. `kMaxRequestCount=1024`. No progress-thread support. |
| OBJ (S3) plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/obj/README.md | 2026-04-25 | aws-sdk-cpp 1.11.581, dual-client (S3 + S3 CRT), optional cuobjclient-13.1 acceleration. |
| Azure Blob plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/azure_blob/README.md | 2026-04-25 | azure-sdk-for-cpp at azure-storage-blobs_12.15.0; param-map config; env-var fallback. |
| HF3FS plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/hf3fs/README.md | 2026-04-25 | DeepSeek 3FS integration. mem_config=auto/dram/dram_zc. Page-aligned mem for zero-copy mmap. |
| GUSLI plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/gusli/README.md | 2026-04-25 | NVIDIA GUSLI client. Local shared-mem (recommended) / network / direct-local modes. |
| POSIX plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/posix/README.md | 2026-04-25 | libaio default, opt-in liburing via `use_uring=true`. Docker seccomp blocks io_uring. |
| GDS plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/cuda_gds/README.md | 2026-04-25 | cufile.json with allow_compat_mode. CUFILE_ENV_PATH_JSON env var. |
| DOCA GPUNetIO plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/gpunetio/README.md | 2026-04-25 | GPU-driven RDMA (GDAKI). Stream-attached and stream-pool modes. Single NIC + single GPU per backend. |
| UCCL plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/uccl/README.md | 2026-04-25 | Preview. Internode-only today. PCIe-distance-based NIC discovery. vLLM e731733d30d0aed3252dc60427927768bfc0ca73 has UCCL connector. |
| Telemetry plugin README | https://github.com/ai-dynamo/nixl/blob/main/src/plugins/telemetry/README.md | 2026-04-25 | Custom exporter dev guide. CSV exporter example provided. |
| `examples/python/basic_two_peers.py` | https://github.com/ai-dynamo/nixl/blob/main/examples/python/basic_two_peers.py | 2026-04-25 | Working two-peer READ example. Uses `initialize_xfer` + notifications. CPU/GPU via `--use_cuda True`. |
| `examples/python/expanded_two_peers.py` | https://github.com/ai-dynamo/nixl/blob/main/examples/python/expanded_two_peers.py | 2026-04-25 | Parallel READs + WRITEs + reposting. Uses `prep_xfer_dlist` + `make_prepped_xfer`. `--backend UCX` flag. |
| `examples/python/partial_md_example.py` | https://github.com/ai-dynamo/nixl/blob/main/examples/python/partial_md_example.py | 2026-04-25 | Partial metadata handling, ETCD vs socket via `--etcd` flag, retrying initialize_xfer. |
| `examples/cpp/nixl_etcd_example.cpp` | https://github.com/ai-dynamo/nixl/blob/main/examples/cpp/nixl_etcd_example.cpp | 2026-04-25 | C++ ETCD-mode example. Sets `NIXL_ETCD_ENDPOINTS`. UCX backend. |
| `examples/device/ep/csrc/` (NIXL-EP) | https://github.com/ai-dynamo/nixl/tree/main/examples/device/ep/csrc | 2026-04-25 | NIXL-EP device kernels: `nixl_ep_ll.cu` (low-latency), `nixl_ep_ht.cu` (high-throughput). v1.0.1 #1538 mode guards. |
| NIXLBench README | https://github.com/ai-dynamo/nixl/blob/main/benchmark/nixlbench/README.md | 2026-04-25 | Fresh. ETCD coordination, multi-backend, communication patterns (pairwise/many-to-one/one-to-many/tp), NVSHMEM worker option. v1.0.1 #1502 ETCD-less mode. |
| KVBench dir | https://github.com/ai-dynamo/nixl/tree/main/benchmark/kvbench | 2026-04-25 | Python-based KV-cache-shaped workload generator. Has `commands/`, `models/`, `runtime/`, `docs/`, `examples/`. |
| nixl-cu13 PyPI page | https://pypi.org/project/nixl-cu13/ | 2026-05-28 | Last probed at 1.1.0. Not re-probed this pass — GitHub tags (v1.3.1) are the authority; re-check PyPI before pinning a wheel version. |
| NVIDIA Dynamo repo | https://github.com/ai-dynamo/dynamo | 2026-04-25 | Active. ai-dynamo org. NIXL is one of the data-plane libraries used by Dynamo. |
| NVIDIA Dynamo blog (intro) | https://developer.nvidia.com/blog/introducing-nvidia-dynamo-a-low-latency-distributed-inference-framework-for-scaling-reasoning-ai-models/ | 2026-04-25 | Verified. Dynamo announce, NIXL referenced as its inference transfer library. |
| Dynamo TRT-LLM kv-cache-transfer doc | https://github.com/ai-dynamo/dynamo/blob/main/docs/backends/trtllm/trtllm-kv-cache-transfer.md | 2026-05-28 | RELOCATED: old `docs.nvidia.com/.../kv-cache-transfer.html` is 404 (re-probed); doc renamed to `docs/backends/trtllm/trtllm-kv-cache-transfer.md` in `ai-dynamo/dynamo` (confirmed via repo tree listing). |
| vLLM NixlConnector usage guide | https://docs.vllm.ai/en/stable/features/nixl_connector_usage/ | 2026-04-25 | Verified. `--kv-transfer-config` syntax, `kv_role`, `kv_buffer_device`, `kv_connector_extra_config.backends`. |
| vLLM disagg prefill (experimental) | https://docs.vllm.ai/en/latest/features/disagg_prefill/ | 2026-04-25 | Verified. Cross-references NixlConnector, Mooncake, LMCache. |
| vLLM nixl module API doc | https://docs.vllm.ai/en/latest/api/vllm/distributed/kv_transfer/kv_connector/v1/nixl_connector/ | 2026-04-25 | Verified. Source-doc'd module docs. |
| vLLM `requirements/kv_connectors.txt` | https://github.com/vllm-project/vllm/blob/main/requirements/kv_connectors.txt | 2026-07-21 | At vLLM tag v0.25.1 the pin is **`nixl == 1.3.0`** — exact, not a floor. Also `lmcache >= 0.3.9`, `mooncake-transfer-engine >= 0.3.8`, `cupy-cuda13x < 14.1.0`. Cross-referenced from `vllm-caching` skill. |
| vLLM issue #27055 (LIBFABRIC + NIXL 0.6.1) | https://github.com/vllm-project/vllm/issues/27055 | 2026-04-25 | Open issue. Likely fixed by NIXL v1.0.1 libfabric thread-safety + notif-on-repost work; verify by re-running with bumped NIXL. |
| vLLM PR #18293 (CPU buffer in NixlConnector) | https://github.com/vllm-project/vllm/pull/18293 | 2026-04-25 | By juncgu. Adds CPU-side `kv_buffer_device` support. |
| Spheron NIXL deep-dive blog | https://www.spheron.network/blog/nvidia-nixl-disaggregated-inference-guide/ | 2026-04-25 | External blog. Useful as one-page intro for new users. |
| WEKA + Dynamo + NIXL blog | https://www.weka.io/blog/ai-ml/weka-accelerates-ai-inference-with-nvidia-dynamo-and-nvidia-nixl/ | 2026-04-25 | Storage vendor integration pattern. |
| UCCL KV-transfer deep-dive | https://uccl-project.github.io/posts/kv-transfer-engine/ | 2026-04-25 | UCCL team's blog on KV transfer engines. |
| BARD AI NIXL blog | https://bardai.ai/2026/03/10/enhancing-distributed-inference-performance-with-the-nvidia-inference-transfer-library/ | 2026-04-25 | Third-party overview. |
| Cross-reference: `vllm-caching` skill | local: `~/.claude/skills/vllm-caching/` | 2026-04-25 | Live-lab-verified NIXL recipes for vLLM disagg-prefill on consumer hardware (UCX_TLS, downward API, headless Service, the six P2P env vars, NIXL_ERR_REMOTE_DISCONNECT race). NIXL skill refers to it for vLLM-side connector glue. |

## Notes on probe budget

Probes used (2026-07-21 freshen): `gh release list` (v1.3.1 latest), `gh release view` on v1.2.0 / v1.3.0 / v1.3.1, `gh api contents/pyproject.toml` on main (1.4.0), `gh api contents/src/plugins` on main and at `?ref=v1.3.1` (15 entries), `git show v0.25.1:requirements/kv_connectors.txt` in the local vLLM clone (`nixl == 1.3.0`), plus vLLM v0.22.1–v0.25.0 release notes for NIXL-side integration changes. Not re-probed: PyPI wheel pages, the per-plugin READMEs (2026-04-25 stamps stand), the third-party blog rows.

Probes used (2026-05-28 freshen): `gh release list` + `gh api releases/latest` (v1.1.0), `gh api contents/pyproject.toml` on main (1.2.0), `gh api commits/main` (HEAD `3009db5d`, #1630), `gh api vllm-project/vllm contents/requirements/kv_connectors.txt` (`nixl >= 1.1.0`), PyPI `/pypi/<pkg>/json` for nixl-cu12/cu13/meta (all 1.1.0), `curl -L` Dynamo TRT-LLM doc (still 404). Prior pass (2026-04-25): NIXL v1.0.1, HEAD `6cbbfc6`.

## Drift watch list

- Mooncake transfer engine refactor in progress — Mooncake plugin README explicitly notes this. Re-probe per minor NIXL release.
- NIXL-EP elastic mode is new (v1.0.0–v1.0.1); expect API churn through 1.x.
- Prometheus telemetry exporter is beta — expect interface changes; pin exact NIXL version when wiring into ops dashboards. The event schema already lost `category` in v1.3.0 (#1649) and timestamps in v1.0.0 (#1522).
- The 1.3.x line broke two API surfaces in a minor: NIXL-EP rank/expert semantics (#1693, legacy mask-clean API removed) and path-mode `FILE_SEG` `devId` uniqueness (#1790). Treat NIXL minors as potentially source-breaking for plugin and EP code, not just for ops config.
- AMD ROCm/HIP support is one release old (v1.3.0). Expect churn on the HIP path; the per-plugin READMEs were last read at 2026-04-25 and predate it.
