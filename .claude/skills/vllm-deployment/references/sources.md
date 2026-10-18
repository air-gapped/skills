# Sources — external references probed during `freshen` passes

Freshened: 2026-10-18 — every row probed at vLLM v0.32.0; 138 URLs swept, every cited vLLM repo path checked against the tag. Moved: vLLM v0.32.0, LWS v1.0.0 GA, llm-d v0.10.0 (WVA deprecated), AIBrix v0.8.0, Dynamo v1.5.1, production-stack 0.1.13, Agent Router v1.2.0 (renamed from Envoy AI Gateway), semantic-router v0.4.0 (site vllm-sr.ai), KServe v0.21.0; GAIE unchanged at v1.6.2. `examples/online_serving/` no longer exists (split into `examples/{deployment,disaggregated,ray_serving}/`), P2pNcclConnector gone since v0.24.0, GAIE `InferenceModel` gone since v1.0. All seven dead URLs of the prior pass resolved to replacements.

Records verification of ecosystem refs and versions. Verified via `gh api repos/<owner>/<repo>/releases/latest` and direct content probes.

Last freshen pass: **2026-09-15** (prior: 2026-08-11, 2026-07-21, 2026-05-29, 2026-04-24)

**Two structural changes, not version bumps.** GAIE v1.6.0 moved the full-featured EPP, Body-Based Routing and the latency predictor *out* of the gateway repo and into llm-d, and dropped the alpha `InferenceObjective` / `InferenceModelRewrite` / `EndpointPickerConfig` APIs — while llm-d v0.9.0 still pins GAIE v1.5.0, so the two sides of that split are not yet aligned in any released pair. Separately, `envoyproxy/ai-gateway` is now `theagentrouter/agent-router`: a different owner as well as a different name, so the old URL's 200 is a redirect, not continuity.

## Verified table (2026-10-18 pass)

| Ref | URL / path | Notes |
|---|---|---|
| vLLM upstream release | https://github.com/vllm-project/vllm/releases | **v0.32.0** (2026-10-18), via v0.31.0 (2026-10-05). Applied: CORS default `--allowed-origins []` (#61009, `vllm/entrypoints/launchers/cli_args.py:319`); `--enforce-eager` disables JIT warmup (#58197, #58593; v0.31.0); `vllm preload` (#56680), Fast Start DP (#57386) / PP (#55477) / `--weight-cache-health-port` (#58552) / daemon weights charged to `gpu_memory_utilization` (#57298, test `90 GiB budget - 70 GiB external = 20 GiB`); explicit `TRITON_CACHE_DIR` honoured (#58474, v0.31.0, `compiler_interface.py:464-475`). MRV1 still ships at v0.32.0 (`vllm/v1/worker/gpu_model_runner.py`, fallback in `vllm/config/vllm.py` `use_v2_model_runner`) despite the v0.32 removal target; ROCm MRV1 exceptions removed (#56360). Release note says `--enable-shm-tensor-arena` is on by default (#51207) — the tag's `ParallelConfig.enable_shm_tensor_arena = False` and its docstring say opt-in; skill follows the code. Arena = `_ARENA_SLOTS 8 × _ARENA_SLOT_BYTES 256 MiB` (`shm_tensor_arena.py:54-55`). Release note's `vllm preload --preload-autotune` flag does not exist at the tag — #60085 runs FlashInfer autotune in `vllm preload` unless `--no-enable-flashinfer-autotune`; not applied. |
| vLLM image tags | https://hub.docker.com/r/vllm/vllm-openai/tags | v0.32.0: `v0.32.0` (10.3 GB), `-cu129`, `-ubuntu2404`, `-cu129-ubuntu2404`, `-x86_64` (9.2 GB), `-x86_64-zstd` (7.3 GB, #55608 from v0.31.0), `-aarch64*` — Docker Hub tags API, pushed 2026-10-18. |
| vLLM in-repo paths | https://github.com/vllm-project/vllm/tree/v0.32.0 | `examples/online_serving/` absent at v0.30.0, v0.31.0 and v0.32.0 → `examples/deployment/chart-helm/` (`chart-vllm` 0.0.2; no "experimental" marking in chart or `docs/deployment/frameworks/helm.md`), `examples/ray_serving/{run_cluster.sh,ray_serve_deepseek.py}`, `examples/disaggregated/{disaggregated_serving,mooncake_connector,lmcache}/`. `run_cluster.sh` uses `--network host --shm-size 10.24g --gpus all` (no `--ipc=host`). KServe doc is `docs/deployment/integrations/kserve.md`; `kuberay.md`, `llamastack.md`. Dockerfiles live in `docker/` (no `.tpu`, `.nightly_torch`; `.zen`, `.rock` added). `cli_args.py` moved to `vllm/entrypoints/launchers/` (`tool_parser_plugin` :127). Anchors re-measured: `docs/deployment/k8s.md:210,290`, `gpu.cuda.inc.md:242,247,286,298,306`, `envs.py:15,34,37-38`. `VLLM_RPC_TIMEOUT` removed in v0.23.0 (#44128). |
| vLLM `docker/Dockerfile` | https://github.com/vllm-project/vllm/blob/v0.32.0/docker/Dockerfile | Unchanged since v0.27.0: `ARG NCCL_VERSION=2.30.7` (:34, DeepEPv2 comment :31), `DEEPEP_COMMIT_HASH=d4f41e4e93` (:494), `CUDA_VERSION=13.0.3`, `PYTHON_VERSION=3.12`. |
| vLLM `shm_broadcast.py` | https://github.com/vllm-project/vllm/blob/v0.32.0/vllm/distributed/device_communicators/shm_broadcast.py | `check_shm_free_space` still guards `ShmRingBuffer`; `ShmTensorArena` uses the same check. |
| vLLM `multi-node-serving.sh` path | https://github.com/vllm-project/vllm/blob/v0.32.0/examples/ray_serving/multi-node-serving.sh | Present at v0.32.0. |
| P2pNcclConnector | https://github.com/vllm-project/vllm/pull/44854 | Removed 2026-06-08, first in v0.24.0; `kv_connector/factory.py` raises `Unsupported connector type`. |
| LWS release | https://github.com/kubernetes-sigs/lws/releases | **v1.0.0** (2026-10-16), via v0.11.0 (09-23), v0.11.1 (10-01). Urgent upgrade notes: DisaggregatedSet rollout default → maxSurge 0 / maxUnavailable 1 (#1169); slice-less LWS from v0.9.x DisaggregatedSets dropped (#1085). New `maxGroupRestarts` (#877), `restartBackoff` (#1103), `podTerminationPolicy` (#1104), config API v1 (#1094). |
| LWS gang scheduling | https://github.com/kubernetes-sigs/lws/tree/v1.0.0/keps/666-gang-scheduling-in-lws | KEP-666 `stage: alpha`, gate `WorkloadAwareScheduling`, targets Kubernetes 1.37 `scheduling.k8s.io/v1beta1` Workload/PodGroup with `GenericWorkload` gate. Issue #167 closed 2025-04-18 as duplicate of #407, which closed NOT_PLANNED 2025-12-12. |
| llm-d release | https://github.com/llm-d/llm-d/releases | **v0.10.0** (2026-09-29): vLLM base `v0.30.0`, GAIE CRDs v1.5.0, LWS 0.11.0; `llm-d-cuda` image deprecated for `vllm/vllm-openai`; WVA deprecated, KEDA + EPP the autoscaling path (PRs #2490, #2497, merged 2026-09-17). |
| AIBrix release | https://github.com/vllm-project/aibrix/releases | **v0.8.0** (2026-10-13): experimental ModelClaim, ModelWarmup. |
| GAIE release | https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases | **v1.6.2** (2026-09-17), unchanged since the prior pass. CRDs at v1.6.2: `inferencepools` (`inference.networking.k8s.io`) + `inferencepoolimports`; v1.0.0 already had `inferenceobjectives`, no `inferencemodels` (`config/crd/bases` per tag). |
| NVIDIA Dynamo release | https://github.com/ai-dynamo/dynamo/releases | **v1.5.1** (2026-10-07) latest stable, via v1.5.0 (09-21). v1.5.0 bundles vLLM v0.28.0 (#13846), v1beta1 storage, Go EPP removed, KVBM deprecated → v1.7.0. v1.5.1 breaking: `DYN_MM_TRUST_EGRESS_PROXY` (#14474). Dev prereleases (`v1.6.0-*-dev.N`) still outnumber stable tags. |
| vllm-production-stack release | https://github.com/vllm-project/production-stack/releases | **vllm-stack-0.1.13** (2026-09-29). |
| Agent Router release | https://github.com/theagentrouter/agent-router/releases | **v1.2.0** (2026-10-07), first under the Agent Router name (site https://theagentrouter.ai, `aigateway.envoyproxy.io` redirects there); API group unchanged; GAIE v1.6. |
| vllm-semantic-router release | https://github.com/vllm-project/semantic-router/releases | **v0.4.0** (2026-09-27). Repo homepage is now https://vllm-sr.ai (old vllm-semantic-router.com no longer resolves). |
| KServe release | https://github.com/kserve/kserve/releases | **v0.21.0** (2026-09-25), via v0.20.0 (08-06). |
| Replaced URLs | — | thenets post → `/posts/` path; OCP route annotations → `docs.redhat.com/.../4.19/html-single/ingress_and_load_balancing/index#nw-route-specific-annotations_configuring-routes`; OCP 4.17 user-workload monitoring page → monitoring guide single-page (old per-topic URL 404s, no per-topic replacement found); KServe docs → `/website/docs/intro`; ai-on-eks Dynamo → `/framework-guides/GPUs/nvidia-dynamo`. |
| MarkTechPost runtimes article | https://www.marktechpost.com/2025/11/07/comparing-the-top-6-inference-runtimes-for-llm-serving-in-2025/ | 403 to bare curl; live in a browser (title and body confirmed). |

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

## Probes not performed (2026-07-21 — same set as prior passes)

- RHAIIS `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.3.0` tag probe (requires authenticated pull or docs page scraping)
- Individual blog-post 200-OK check (https://blog.vllm.ai/2025/11/22/ray-symmetric-run.html, etc.) — prioritized repo/release freshness over blog URLs
- Individual issue probes (vllm-project/vllm#7466, #18831, #4618, #27321, #8074) — stable issue numbers, skip unless user reports broken links
- Mooncake, LMCache, MORI-IO releases — covered at a higher level by ecosystem refs
- KServe v0.15, OpenShift 4.19/4.20/4.21 doc pages
