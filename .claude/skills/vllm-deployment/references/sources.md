# Sources — external references probed during `freshen` passes

Records verification of ecosystem refs and versions. Verified via `gh api repos/<owner>/<repo>/releases/latest` and direct content probes.

Last freshen pass: **2026-08-11** (prior: 2026-07-21, 2026-05-29, 2026-04-24)

## Last verified table

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| LWS (LeaderWorkerSet) release | https://github.com/kubernetes-sigs/lws/releases | 2026-08-11 | **v0.9.0** (2026-06-17), up from v0.8.0. **Still pre-GA — no v1.0.** v0.9.0 body is dependency maintenance (K8s deps → v0.35.0, generic webhook API migration, dependabot bumps); not an API-stability milestone. |
| llm-d release | https://github.com/llm-d/llm-d/releases | 2026-08-11 | **v0.8.1** (2026-06-26), up from v0.7.0; v0.8.0 was 2026-06-24. v0.8.0 themes: CI/project-ops hardening, wider accelerator coverage, **multimodal / batch / flow-control graduated to production**, initial RL support. Release notes carry a **per-component version table** — the umbrella tag does not imply every sub-component moved. |
| AIBrix release | https://github.com/vllm-project/aibrix/releases | 2026-08-11 | **v0.7.0** (2026-06-18), up from v0.6.0. |
| GAIE release | https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases | 2026-08-11 | **v1.5.0** (2026-04-19) — unchanged; no release in three months. v1 GA claim still holds. |
| NVIDIA Dynamo release | https://github.com/ai-dynamo/dynamo/releases | 2026-08-11 | **v1.3.1** (2026-08-06) is the newest *stable*, up from v1.2.1 (2026-06-13). **Tag-sorting trap:** the repo publishes model-specific dev prereleases that are newer by date *and* higher by version — `v1.3.0-glm-5.2-dev.1` (2026-07-21), `v1.4.0-inkling-dev.1` (2026-07-17), `v1.3.0-minimax-m3-dev.1`, `v1.3.0-deepseek-v4-dev.1`, `v1.3.0-kimi-k2.6-dev.1`, `v1.3.0-nemotron-super-dev.1`. All carry `isPrerelease=true`; filter on it. |
| vllm-production-stack Helm release | https://github.com/vllm-project/production-stack/releases | 2026-08-11 | **vllm-stack-0.1.12** (2026-07-24), up from 0.1.11 (2026-05-07). 0.1.11 was **missed by the 2026-05-29 pass** — that pass carried this row forward at its 2026-04-24 stamp rather than re-probing, and 0.1.11 had already shipped three weeks earlier. A carried-forward stamp is not a verification. |
| Envoy AI Gateway release | https://github.com/envoyproxy/ai-gateway/releases | 2026-08-11 | **v1.0.0 — GA** (2026-06-23), up from v0.6.0 via v0.7.0 (2026-06-06). Core API (`AIGatewayRoute`, `AIServiceBackend`, `BackendSecurityPolicy`, `GatewayConfig`, `MCPRoute`) declared stable for 1.x; upgrading from v0.7 needs no resource changes. **The API is still served at `v1beta1`** — project GA did not bump the group version. |
| vllm-semantic-router release | https://github.com/vllm-project/semantic-router/releases | 2026-08-11 | **v0.3.0** (2026-06-05), up from v0.2.0 "Athena". |
| vLLM upstream release | https://github.com/vllm-project/vllm/releases | 2026-08-11 | **v0.27.1** (2026-08-11) is latest; **v0.27.0** (2026-08-10) is what this pass probed. Up from v0.25.1 — two minors plus a patch (v0.26.0 was 2026-07-27). v0.27.1 is a one-change patch ("Support quantized DSpark Markov heads", #50424, touching only `vllm/model_executor/models/qwen3_dspark.py`) — nothing deployment-facing, so every v0.27.0 probe below stands. The **`v0.27.1` images are published** — `v0.27.1` (10.53 GB) pushed 10:34:40Z, `-x86_64` 10:24:20Z, `-cu129` 10:41:15Z, `-cu129-ubuntu2404` 10:42:47Z, all *before* the 10:47:49Z release — verified via the Docker Hub tags API; image *contents* were not verified here. PyPI lag is irrelevant to this skill, which deploys the image. The RHAIIS 3.3.0 → v0.13.0 mapping remains RHAIIS-specific and unverifiable without registry.redhat.io access; the gap between RHAIIS and upstream has widened further and `openshift.md` already states this explicitly. |
| vLLM `multi-node-serving.sh` path | https://github.com/vllm-project/vllm/blob/v0.25.1/examples/ray_serving/multi-node-serving.sh | 2026-07-21 | **BROKEN → MOVED.** The previously recorded path `examples/online_serving/multi-node-serving.sh` **404s at v0.25.1 and on `main`**. The script now lives at **`examples/ray_serving/multi-node-serving.sh`** (sha 644bc82, 3798 bytes). Confirmed by upstream's own docs, which use the new path in `docs/deployment/frameworks/lws.md` and `docs/deployment/integrations/kthena.md`. |

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
