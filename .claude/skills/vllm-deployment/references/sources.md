# Sources — external references probed during `freshen` passes

Freshened: 2026-11-09

Every row probed at vLLM v0.33.0; 146 URLs swept; every cited vLLM repo path and line anchor checked against the tag. Moved: vLLM v0.33.0, llm-d v1.0.0, Dynamo v1.6.2, production-stack 0.1.14, Agent Router v1.2.1, Red Hat AI Inference 3.4 (renamed from RHAIIS), KubeRay repo owner. Unchanged: LWS v1.0.0, AIBrix v0.8.0, GAIE v1.6.2, semantic-router v0.4.0, KServe v0.21.0. Two stale teachings corrected from the tag rather than from a release note: the stock image's non-root user (v0.22.0) and the multiprocessing LWS recipe (v0.24.0).

Records verification of ecosystem refs and versions. Verified via `gh release list --json isLatest,isPrerelease` per repo and direct content probes.

Earlier freshen passes: 2026-10-18, 2026-09-15, 2026-08-11, 2026-07-21, 2026-05-29, 2026-04-24.

**2026-09-15 pass — two structural changes, not version bumps.** GAIE v1.6.0 moved the full-featured EPP, Body-Based Routing and the latency predictor *out* of the gateway repo and into llm-d, and dropped the alpha `InferenceObjective` / `InferenceModelRewrite` / `EndpointPickerConfig` APIs. Separately, `envoyproxy/ai-gateway` is now `theagentrouter/agent-router`: a different owner as well as a different name, so the old URL's 200 is a redirect, not continuity. llm-d caught up with the GAIE split at v1.0.0, which pins GAIE v1.6.2.

## Verified table (2026-11-09 pass)

| Ref | URL / path | Notes |
|---|---|---|
| vLLM upstream release | https://github.com/vllm-project/vllm/releases | **v0.33.0** (2026-11-02), via v0.32.0 (2026-10-18). The GitHub Release object is named `v0.33.0` and targets `releases/v0.33.0` but is attached to tag `v0.33.0rc3`, so a `tag_name` listing shows an rc; tag `v0.33.0` is the same commit (`4ba787ec99`), PyPI `vllm` 0.33.0 uploaded 2026-11-02, Docker Hub `v0.33.0` pushed 2026-11-02. Applied from the notes: CUDA 12.9 images dropped (#62575), `-efa` image (#58768), `vllm/vllm` alias, `VLLM_USE_RAY_*` env vars removed (#61712, #62228), NIXL ≥ 1.5 (#61032), Fast Start EP + EPLB rejection (#55490), watchdog (#55700). MRV1 still ships (`vllm/v1/worker/gpu_model_runner.py`, fallback log `vllm/config/vllm.py:754,761`). `enable_shm_tensor_arena` still defaults `False` (`vllm/config/parallel.py:244`). Read, not applied (no deploy-layer action): PyTorch 2.14, concurrent TP worker startup (#60028, automatic), paused-generation HTTP 503 (#51488), Medusa/MLP speculator removal, `--mamba-cache-mode` / `--ir-op-priority` / LM Format Enforcer deprecations (zero hits in this skill). |
| vLLM issue sweep | https://github.com/vllm-project/vllm/issues | Issues opened 2026-10-18 → 2026-11-09, non-PR, by comment count plus deploy keywords. Applied: #66493 (boolean env parsing; `VLLM_NO_USAGE_STATS=true` silently False, `vllm/envs.py:842`), #64391 (`/invocations` outside `--api-key`; closed as documented, `docs/usage/security.md:152,191-195,260`). Logged, not applied: #62677 (v0.32.0 image, `deepep_v2` `ZeroDivisionError` after `ibstat` cannot run — one report, no maintainer reply), #63667 (`/health` stops answering while detokenization stalls the API-server event loop — open, no fix), #64103 (cgroup limit read only at `/sys/fs/cgroup`; PR #64104 unmerged), #65155 (Rust frontend: new connections hang during `--shutdown-timeout` — open), #65440 (request for CUDA 12 wheels on v0.33.x). |
| vLLM image tags | https://hub.docker.com/r/vllm/vllm-openai/tags | v0.33.0 (Docker Hub tags API, pushed 2026-11-02): `v0.33.0` (10.9 GB), `-aarch64`, `-x86_64` (9.7 GB), `-x86_64-zstd` (7.7 GB), `-efa`, `-aarch64-efa`, `-x86_64-efa`. No `-cu129`, no `-ubuntu2404`. `vllm/vllm:v0.33.0` (+ `-efa`, `-rocm`, `-rocm100`, `-rocm72`, `-cpu`, `-xpu`) exists. No tag matching `nonroot`. v0.32.0 tags unchanged. |
| vLLM in-repo paths | https://github.com/vllm-project/vllm/tree/v0.33.0 | Every path in the SKILL.md cheat sheet present at the tag. `cli_args.py` moved again: `vllm/entrypoints/common/cli_args.py` (`tool_parser_plugin` :134, `allowed_origins` default empty list :329). Anchors: `docs/deployment/k8s.md:211,291`, `gpu.cuda.inc.md:242,247,292,304,312`, `nginx.md:95,105`, `parallelism_scaling.md:175,181-182`, `run_cluster.sh:120,127`, `envs.py:15,35,38-39`, `compiler_interface.py:29-42`, `health.py:22-33`, `shm_tensor_arena.py:54-55`, `shm_broadcast.py:242` (`check_shm_free_space`). `chart-vllm` 0.0.2. `docs/features/disagg_prefill.md:1,6` still "experimental". `kv_connector/v1/` adds `hisparse/`; `weight_cache/protocol.py` present. |
| vLLM `docker/Dockerfile` | https://github.com/vllm-project/vllm/blob/v0.33.0/docker/Dockerfile | `CUDA_VERSION=13.0.3` (:25), `PYTHON_VERSION=3.12` (:26), `UBUNTU_VERSION=24.04` (:27), `NCCL_VERSION=2.31.2` (:35; was 2.30.7 through v0.32.0), `DEEPEP_COMMIT_HASH=d4f41e4e93` (:495). `docker/` at the tag: `Dockerfile`, `.cpu`, `.efa`, `.ppc64le`, `.rocm`, `.rocm_72`, `.rocm_72_base`, `.rocm_base`, `.rocm_base_gfx1250`, `.rocm_gfx1250`, `.s390x`, `.xpu`, `.zen`, `docker-bake.hcl`, `versions.json` (`.rock*` gone). |
| vLLM non-root support | https://github.com/vllm-project/vllm/pull/40275 | Merged 2026-05-25, first in v0.22.0; closes #31959. `docker/Dockerfile:874-903` (user `vllm` UID 2000 GID 0, `/home/vllm` group-0-writable, default target stays root), `:1361-1365` (`vllm-openai-nonroot`), `docs/deployment/docker.md:52-108`. |
| vLLM LWS recipe | https://github.com/vllm-project/vllm/blob/v0.33.0/docs/deployment/frameworks/lws.md | "Multiprocessing (default)" tab since #39400 (merged 2026-06-10, first in v0.24.0): `--nnodes` / `--node-rank` / `--master-addr`, workers `--headless`. "Ray" tab chains `multi-node-serving.sh` with `vllm serve --distributed-executor-backend ray`. |
| vLLM `multi-node-serving.sh` | https://github.com/vllm-project/vllm/blob/v0.33.0/examples/ray_serving/multi-node-serving.sh | Present. Exits 1 without `--ray_cluster_size` (leader) / `--ray_address` (worker); does not start `vllm serve`. |
| vLLM security doc | https://github.com/vllm-project/vllm/blob/v0.33.0/docs/usage/security.md | `--api-key` covers only `/v1`, `/v2`, `/inference`, `/cohere` (:152). |
| P2pNcclConnector | https://github.com/vllm-project/vllm/pull/44854 | Merged 2026-06-08, first in v0.24.0; unchanged. |
| LWS release | https://github.com/kubernetes-sigs/lws/releases | **v1.0.0** (2026-10-16) still `isLatest`. Injected env names at the tag: `LWS_LEADER_ADDRESS`, `LWS_GROUP_SIZE`, `LWS_WORKER_INDEX` (`api/leaderworkerset/v1/leaderworkerset_types.go:82-90`). |
| LWS gang scheduling | https://github.com/kubernetes-sigs/lws/tree/v1.0.0/keps/666-gang-scheduling-in-lws | Unchanged (no release since). Issue #167 closed 2025-04-18, #407 closed NOT_PLANNED 2025-12-12. |
| llm-d release | https://github.com/llm-d/llm-d/releases | **v1.0.0** (2026-10-20): all components version-aligned; `vllm/vllm-openai` v0.30.0 (component table says vLLM v0.31.0 "varies per accelerator"), GAIE CRDs v1.6.2, LWS + DisaggregatedSet v1.0.0; P/D guide needs LWS ≥ v0.11.1 with `enableDisaggregatedSet=true`; `llm-d-rocm` builds deprecated. WVA deprecation PRs #2497 (merged 2026-09-17) and #2490 (merged 2026-09-23); WVA doc now `docs/architecture/autoscaling/wva.md`. `llm-d/llm-d-deployer` and `llm-d-incubation/llm-d-infra` both archived. |
| AIBrix release | https://github.com/vllm-project/aibrix/releases | **v0.8.0** (2026-10-13), unchanged. |
| GAIE release | https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases | **v1.6.2** (2026-09-17), unchanged. `config/crd/bases` at the tag: `inferencepools` + `inferencepoolimports` only. |
| NVIDIA Dynamo release | https://github.com/ai-dynamo/dynamo/releases | **v1.6.2** (2026-11-05) `isLatest`, via v1.6.0 (10-22), v1.6.1 (10-27). Bundles vLLM v0.31.0, NIXL v1.4.1 on the vLLM image. v1.6.0 breaking list read in full; applied: #9848, #13990, #15374/#15704, #15202; v1.6.1 #17108. Dev prereleases now reach `v1.7.0-*-dev.N`. |
| vllm-production-stack release | https://github.com/vllm-project/production-stack/releases | **vllm-stack-0.1.14** (2026-11-07). Release body is one line; content read from `compare/vllm-stack-0.1.13...vllm-stack-0.1.14` (#1071, #1044, #1142, #1185). |
| Agent Router release | https://github.com/theagentrouter/agent-router/releases | **v1.2.1** (2026-11-06): no API changes; Envoy Gateway v1.9.2, GAIE v1.6.2. |
| vllm-semantic-router release | https://github.com/vllm-project/semantic-router/releases | **v0.4.0** (2026-09-27), unchanged; https://vllm-sr.ai 200. |
| KServe release | https://github.com/kserve/kserve/releases | **v0.21.0** (2026-09-25), unchanged. |
| KubeRay repo | https://github.com/kuberay-project/kuberay | Moved from `ray-project/kuberay` (old URL redirects). |
| Red Hat AI Inference | https://docs.redhat.com/en/documentation/red_hat_ai_inference/3.4/html-single/release_notes/index | 3.4.0 / 3.4.1 → vLLM v0.18.0; renamed from Red Hat AI Inference Server; image `registry.redhat.io/rhaii/vllm-cuda-rhel9:3.4.1`. 3.3 release notes: 3.3.0 → v0.13.0. 3.2 release notes: 3.2.3, 3.2.4 → v0.11.0; 3.2.5 → v0.11.2. `docs.redhat.com` answers 403 to bare curl; all eight cited pages load in a browser (titles confirmed), including the OCP 4.19 route-annotations anchor. |
| Issue / PR states | — | vllm-project/vllm #7466, #4618 closed COMPLETED; #18831, #27321, #8074 closed NOT_PLANNED; #15359 closed 2025-03-24; #31959 closed 2026-05-25 by #40275. ai-dynamo/dynamo #331, #3724 closed COMPLETED. NVIDIA/nvidia-container-toolkit #434, #85 closed COMPLETED (2025-11). All are cited as symptom references, none as open. |
| URL sweep | — | 146 URLs, bare curl: 137 × 200, 9 × 403 (eight `docs.redhat.com`, MarkTechPost) — all nine load in a browser. Working redirects left as written: `blog.vllm.ai/YYYY/MM/DD/<slug>.html` → `vllm.ai/blog/YYYY-MM-DD-<slug>`; `vllm.ai/blog/moriio-kv-connector` → dated slug; `docs.nvidia.com/networking/...` → `networking-docs.nvidia.com`; `lws.sigs.k8s.io/docs/` → `/stable/docs/`; `keda.sh/docs/latest/` → `/docs/2.21/`; `redhat.com/en/products/ai/inference-server` → `/inference`. |
| MarkTechPost runtimes article | https://www.marktechpost.com/2025/11/07/comparing-the-top-6-inference-runtimes-for-llm-serving-in-2025/ | 403 to bare curl; live in a browser (title, byline date 2025-11-07 and body confirmed). |

## Classifications (2026-08-11 pass)

Probed all nine ecosystem release feeds plus three vLLM v0.27.0 source blobs.
**Only two of nine ecosystem refs moved** — the opposite of the 2026-07-21 pass,
where seven of nine did. The churn this cycle was in vLLM itself (two minors).

| Classification | Refs |
|---|---|
| fresh | LWS v0.9.0, llm-d v0.8.1, AIBrix v0.7.0, GAIE v1.5.0, Envoy AI Gateway v1.0.0, semantic-router v0.3.0 — all re-probed, all unchanged |
| version-drift | production-stack 0.1.11 → **0.1.12** (2026-07-24); Dynamo v1.2.1 → **v1.3.1** (2026-08-06); vLLM upstream v0.25.1 → **v0.27.1** (2026-08-11; probed at v0.27.0, 2026-08-10) |
| new-feature | `/dev/shm` pre-flight check (#48879); NCCL 2.30.7 → DeepEPv2 in the image (#45321); cgroup memory limits honoured (#49966); DP+EP external-LB fault tolerance (#44428) — all v0.27.0, all applied |
| unverifiable | RHAIIS 3.3.0 → vLLM v0.13.0 mapping (still needs a registry.redhat.io probe; unchanged reasoning from prior passes) |
| broken | none |
| deprecation | none detected in this pass |

**New source rows probed this pass.**

| Ref | URL | Notes |
|---|---|---|
| vLLM `shm_broadcast.py` | https://github.com/vllm-project/vllm/blob/v0.27.0/vllm/distributed/device_communicators/shm_broadcast.py | `check_shm_free_space()` called from `ShmRingBuffer.__init__`; raises `RuntimeError("Insufficient space in /dev/shm: N MiB required, M MiB free. Increase /dev/shm (e.g. --shm-size or --ipc=host).")`. Read verbatim from the v0.27.0 blob. |
| vLLM `docker/Dockerfile` | https://github.com/vllm-project/vllm/blob/v0.27.0/docker/Dockerfile | `ARG NCCL_VERSION=2.30.7` with in-file comment *"DeepEPv2 requires NCCL >= 2.30.4 (GIN backend)"*, plus `ARG DEEPEP_COMMIT_HASH=d4f41e4e93`, `ARG CUDA_VERSION=13.0.3`, `ARG PYTHON_VERSION=3.12`. |

**Verified non-events (checked, no edit needed).** v0.27.0 removed
`max_num_partial_prefills` / `max_long_partial_prefills` (#49244) and the Plamo2,
Ouro, TeleChat, Persimmon and Fuyu models — `grep` across this skill returns zero
hits for all of them, so no text describes a removed feature. The PyTorch 2.13.0 /
torchvision 0.28.0 / Triton 3.7.1 bump (#48155, called a breaking environment change
upstream) likewise touches nothing here: this skill pins no Python-side dependency
versions, only image tags. #48992 adds `grpc.health.v1.Health` to the **Rust
frontend's gRPC listener** — it is *not* the HTTP `/health` endpoint the k8s probes
hit, so the probe guidance in `pod-shape.md` is unaffected. Recorded so a later pass
does not mistake it for a probe-contract change.

## Classifications (2026-07-21 pass)

**Seven of the nine probed refs moved.** This ecosystem does not hold still for
two months; treat any version in this skill older than ~6 weeks as suspect.

| Classification | Refs |
|---|---|
| fresh | GAIE v1.5.0 (no release in 3 months) |
| **maturity milestone** | **Envoy AI Gateway v0.6.0 → v1.0.0 GA** (2026-06-23) — API stability promise for 1.x, no resource changes needed from v0.7, but still served at `v1beta1` |
| version-drift | LWS v0.8.0 → v0.9.0, llm-d v0.7.0 → v0.8.1, AIBrix v0.6.0 → v0.7.0, Dynamo v1.1.1 → v1.2.1, production-stack 0.1.10 → 0.1.11, semantic-router v0.2.0 → v0.3.0, vLLM upstream v0.21.0 → v0.25.1 |
| version-added | none this pass |
| unverifiable | RHAIIS 3.3.0 → vLLM v0.13.0 mapping (requires registry.redhat.io probe; upstream vLLM is now v0.21.0 as of 2026-05-15, so the RHAIIS doc trails upstream by ~8 minors — openshift.md now states this explicitly; "Pin the exact RHAIIS tag; roll forward with release notes" remains correct guidance) |
| broken | none |
| deprecation | none detected in this pass |

## Ecosystem-project state notes (2026-07-21)

- **Envoy AI Gateway reached 1.0 GA** — the first project in this set to make an
  explicit API-stability commitment. Two details worth carrying: upgrading from
  v0.7 needs **no resource changes**, and the group version stayed at
  **`v1beta1`**, so "GA" here is a project-maturity statement, not a CRD version
  bump. Don't rewrite manifests to `v1` expecting it to exist.
- **LWS is still pre-GA at v0.9.0** despite being the substrate under llm-d,
  vllm-production-stack and AIBrix. Two releases in six months, both maintenance
  in character — nothing signals an imminent v1.0.
- **llm-d** still CNCF Sandbox, now v0.8.1, cutting roughly monthly. v0.8.0
  graduated multimodal, batch and flow-control **to production** — a maturity
  step, not just a version bump. Its release notes carry a per-component version
  table; the umbrella tag does not mean every sub-component moved.
- **AIBrix** v0.6.0 → v0.7.0 continues the fast Q1-onwards cadence — keep
  watching for StormService / KVCache breaking changes.
- **NVIDIA Dynamo** stable is v1.2.1, but the repo publishes a continuous stream
  of **model-specific dev prereleases** (`v1.3.0-<model>-dev.N`,
  `v1.4.0-inkling-dev.1`) that are both newer-dated and higher-versioned than
  the stable tag. Any "what's the latest Dynamo" answer that sorts by date or by
  semver without filtering `isPrerelease` will be wrong.
- **vllm-semantic-router** shipped v0.3.0; Milvus integration still current.

## Process note — a carried stamp is not a verification

`vllm-production-stack` was recorded at **vllm-stack-0.1.10** with a 2026-04-24
stamp and carried unchanged through the 2026-05-29 pass. But **0.1.11 shipped
2026-05-07**, three weeks *before* that pass. The row was not wrong when written
and was not re-probed when it could have been; carrying a row forward with its
old date preserved the staleness invisibly. When a pass declares a probe budget,
prefer re-probing the rows most likely to have moved over re-confirming ones
already stamped recently.
