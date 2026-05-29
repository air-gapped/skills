# Sources — external references probed during `freshen` passes

Records verification of ecosystem refs and versions. Verified via `gh api repos/<owner>/<repo>/releases/latest` and direct content probes.

Last freshen pass: 2026-05-29 (prior: 2026-04-24)

## Last verified table

| Ref | URL | Last verified | Notes |
|---|---|---|---|
| LWS (LeaderWorkerSet) release | https://github.com/kubernetes-sigs/lws/releases | 2026-05-29 | v0.8.0 (published 2026-01-26) — still latest, matches skill. Pre-GA, still no v1.0 cut. |
| llm-d release | https://github.com/llm-d/llm-d/releases | 2026-05-29 | v0.7.0 (published 2026-05-12) — bumped from v0.6.0. Latest, non-draft. |
| AIBrix release | https://github.com/vllm-project/aibrix/releases | 2026-05-29 | v0.6.0 (published 2026-03-03) — still latest, matches skill. |
| GAIE release | https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases | 2026-05-29 | v1.5.0 (published 2026-04-19) — still latest, v1 GA claim confirmed. |
| NVIDIA Dynamo release | https://github.com/ai-dynamo/dynamo/releases | 2026-05-29 | v1.1.1 (published 2026-05-09) — bumped from v1.0.2. Latest stable. |
| vllm-production-stack Helm release | https://github.com/vllm-project/production-stack/releases | 2026-04-24 | vllm-stack-0.1.10 (published 2026-02-27) — added explicit chart version. |
| Envoy AI Gateway release | https://github.com/envoyproxy/ai-gateway/releases | 2026-05-29 | v0.6.0 (published 2026-05-05) — bumped from v0.5.0. Latest. |
| vllm-semantic-router release | https://github.com/vllm-project/semantic-router/releases | 2026-05-29 | v0.2.0 "Athena" (published 2026-03-10) — still latest, matches skill. |
| vLLM upstream release | https://github.com/vllm-project/vllm/releases | 2026-05-29 | v0.21.0 (published 2026-05-15) — upstream advanced two minors (v0.19.1 → v0.20.x → v0.21.0). RHAIIS 3.3.0 → v0.13.0 mapping remains RHAIIS-specific and unverifiable without registry.redhat.io access — still flagged; openshift.md now notes the gap explicitly. |
| vLLM `multi-node-serving.sh` path | https://github.com/vllm-project/vllm/blob/main/examples/online_serving/multi-node-serving.sh | 2026-04-24 | SHA d2823bb, 3763 bytes — path confirmed present. |

## Classifications

Classifications below are from the 2026-05-29 pass (prior-pass detail retained in the table Notes column).

| Classification | Refs |
|---|---|
| fresh | LWS v0.8.0, AIBrix v0.6.0, GAIE v1.5.0, vllm-semantic-router v0.2.0 Athena, vllm-production-stack vllm-stack-0.1.10, multi-node-serving.sh |
| version-drift | llm-d v0.6.0 → v0.7.0 (2026-05-12), NVIDIA Dynamo v1.0.2 → v1.1.1 (2026-05-09), Envoy AI Gateway v0.5.0 → v0.6.0 (2026-05-05), vLLM upstream v0.19.1 → v0.21.0 (2026-05-15) |
| version-added | none this pass |
| unverifiable | RHAIIS 3.3.0 → vLLM v0.13.0 mapping (requires registry.redhat.io probe; upstream vLLM is now v0.21.0 as of 2026-05-15, so the RHAIIS doc trails upstream by ~8 minors — openshift.md now states this explicitly; "Pin the exact RHAIIS tag; roll forward with release notes" remains correct guidance) |
| broken | none |
| deprecation | none detected in this pass |

## Ecosystem-project state notes

- **llm-d** still CNCF Sandbox (Mar 2026) — `references/ecosystem.md` already reflects this accurately. v0.6.0 is the latest release (was v0.5.1).
- **AIBrix** moved from v0.4.x to v0.6.0 over Q1 2026 — this is a significant cadence; watch release notes for StormService / KVCache breaking changes.
- **NVIDIA Dynamo** cut v1.0 during Q1 2026 and is now at v1.0.2 — major-version stability achieved since the skill was authored.
- **Envoy AI Gateway** progressed v0.3 → v0.5 over ~6 months — indicates active development pace.
- **vllm-semantic-router** shipped v0.2 "Athena" — successor to v0.1 "Iris"; Milvus integration still current.
- **LWS** still pre-GA at v0.8.0 — consolidation / breaking-change note #2 in ecosystem.md is still accurate.

## Probes not performed (budget exhausted at 10/10)

- RHAIIS `registry.redhat.io/rhaiis/vllm-cuda-rhel9:3.3.0` tag probe (requires authenticated pull or docs page scraping)
- Individual blog-post 200-OK check (https://blog.vllm.ai/2025/11/22/ray-symmetric-run.html, etc.) — prioritized repo/release freshness over blog URLs
- Individual issue probes (vllm-project/vllm#7466, #18831, #4618, #27321, #8074) — stable issue numbers, skip unless user reports broken links
- Mooncake, LMCache, MORI-IO releases — covered at a higher level by ecosystem refs
- KServe v0.15, OpenShift 4.19/4.20/4.21 doc pages
