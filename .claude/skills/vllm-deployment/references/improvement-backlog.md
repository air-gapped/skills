# Improvement backlog — vllm-deployment

Work-not-done log for the skill-improver loop. `## Open` lists issues attempted as
hypotheses that could not be applied (or safely verified) in a single iteration.
`## Resolved this pass` lists changes the metric actually registered.

## Resolved — 2026-09-15 (v0.28/v0.29 sweep)

- Recorded the four v0.28/v0.29 changes that touch a manifest or a rollout plan:
  `python -m vllm.entrypoints.openai.api_server` deprecated for `vllm serve`
  (#52131); **Model Runner V2 now default with MRV1 removal targeted at v0.32**
  (#53183), while MRV1 still runs for some ROCm models and unsupported features,
  so a fleet can split across both without anyone choosing that; FlashInfer
  all-reduce on by default (#52998) with `VLLM_ALLREDUCE_USE_FLASHINFER=0` as
  the opt-out; and the new `--max-num-queued-reqs` / `--max-num-queued-tokens`
  admission-control flags (#49445).
- Added an explicit warning **not** to read v0.28.0's
  "`max_num_batched_tokens` raised from 8192 to 16384" as a change to the
  serving default. It is not — see `vllm-performance-tuning` for the
  entrypoint-gated table.

## Resolved — 2026-08-11 (freshen)

vLLM shipped **two** minors since the last pass (v0.26.0 2026-07-27, v0.27.0
2026-08-10), so the drift spanned both. The ecosystem, by contrast, barely moved:
only two of nine release feeds changed, the inverse of the previous pass.

- **`/dev/shm` fact #1 was right but incomplete — and the missing half is the
  expensive one.** The skill taught "segfault on the first all-reduce," which is
  the *absent*-volume case. The *undersized*-volume case (the 64 MiB Docker/k8s
  default) behaves completely differently: tmpfs allocation is lazy, so the pod
  boots, passes probes, serves text-only traffic, and then dies under multimodal
  load with an uncatchable `SIGBUS` surfacing as an opaque `EngineDeadError`.
  Added the mechanism, the sizing math (`MessageQueue` = 24 MiB × 10 ≈ 240 MiB at
  TP ≥ 2, already 3.75× the default), and the v0.27.0 fail-fast (#48879,
  `check_shm_free_space()`, error string read verbatim from the v0.27.0 blob).
- **DeepEPv2 is image-only.** v0.27.0 (#45321) raised the `vllm/vllm-openai`
  image's NCCL to 2.30.7; verified in `docker/Dockerfile` at the tag
  (`ARG NCCL_VERSION=2.30.7`, comment "DeepEPv2 requires NCCL >= 2.30.4 (GIN
  backend)"). The load-bearing half is the negative: the PyPI wheel is unchanged
  because DeepEP is not shipped in it, so a pip-installed vLLM in a custom image
  gains nothing from the version bump alone.
- **`resources.limits.memory` was silently ignored before v0.27.0** (#49966) —
  vLLM read host RAM inside a Pod, so its own memory heuristics sized against the
  node, not the container. New `pod-shape.md` subsection.
- **DP+EP external-LB fault tolerance** (#44428) — one dead DP rank blocks the EP
  all-to-all on every survivor and hangs the cluster; v0.27.0 adds detection,
  in-flight abort, and `POST /fault_tolerance/apply`. External-LB topology only.
- **Two ecosystem bumps:** production-stack 0.1.11 → **0.1.12** (2026-07-24),
  Dynamo stable v1.2.1 → **v1.3.1** (2026-08-06). LWS, llm-d, AIBrix, GAIE, Envoy
  AI Gateway and semantic-router all re-probed and unchanged — recorded as
  verified non-events rather than left unstamped.
- **Closed the carried Dim 8 item.** `ecosystem.md` had mixed verification-date
  labels; all nine are now stamped 2026-08-11 because all nine were actually
  re-probed this pass.
- **Four hard removals checked, none applicable.** `max_num_partial_prefills` /
  `max_long_partial_prefills` (#49244) and the Plamo2 / Ouro / TeleChat /
  Persimmon / Fuyu model removals all grep to zero hits in this skill. Likewise
  the PyTorch 2.13.0 / Triton 3.7.1 "breaking environment change" (#48155) — this
  skill pins image tags, not Python dependencies. Recorded in `sources.md` so the
  next pass doesn't re-litigate them.
- **One near-miss recorded deliberately:** #48992 adds `grpc.health.v1.Health` to
  the **Rust frontend's gRPC listener**, not to the HTTP `/health` endpoint the
  k8s probes hit. Probe guidance unchanged. Written down because it reads like a
  probe-contract change and isn't.

## Resolved — 2026-07-21 (freshen)

Ran three days ahead of the "URGENT: freshen by 2026-07-24" deadline the
2026-07-18 pass filed. That item is closed — and it was right to be urgent, for
a reason it didn't anticipate.

- **A cited path is broken, not merely stale.**
  `examples/online_serving/multi-node-serving.sh` **404s at v0.25.1 and on
  `main`**. The script moved to **`examples/ray_serving/multi-node-serving.sh`**
  (sha 644bc82, 3798 bytes), confirmed against upstream's own
  `docs/deployment/frameworks/lws.md` and `docs/deployment/integrations/kthena.md`.
  Fixed in six places across `SKILL.md`, `multi-node.md` and `ecosystem.md` —
  **two of them inside the container `command:` of LWS manifests**, which is the
  damaging case: a stale path does not fail at `kubectl apply`, it fails when
  the pod starts, as a bare missing-file error from `bash`.
- **Seven of nine ecosystem refs moved in under two months.**
  - **Envoy AI Gateway v0.6.0 → v1.0.0 GA** (2026-06-23) — first project in this
    set with an explicit 1.x API-stability promise; upgrading from v0.7 needs no
    resource changes. Recorded the non-obvious part: the API is **still served
    at `v1beta1`**, so project GA did not bump the group version and manifests
    must not be rewritten to `v1`.
  - LWS v0.8.0 → **v0.9.0**, still pre-GA; both recent releases are maintenance
    in character, so nothing signals an imminent v1.0.
  - llm-d v0.7.0 → **v0.8.1**; v0.8.0 graduated multimodal / batch /
    flow-control **to production**.
  - AIBrix v0.6.0 → **v0.7.0**; semantic-router v0.2.0 → **v0.3.0**;
    production-stack 0.1.10 → **0.1.11**; vLLM upstream v0.21.0 → **v0.25.1**.
  - GAIE unchanged at v1.5.0 — recorded as a verified non-event.
- **Dynamo tag-sorting trap documented.** Stable is **v1.2.1** (2026-06-13), but
  the repo continuously publishes model-specific dev prereleases
  (`v1.3.0-glm-5.2-dev.1` dated *today*, `v1.4.0-inkling-dev.1`, …) that are
  newer by date **and** higher by semver while flagged `isPrerelease=true`. Any
  "latest Dynamo" answer that sorts by either date or version without filtering
  is wrong.
- **Process finding: a carried stamp is not a verification.**
  `vllm-production-stack` sat at 0.1.10 with a 2026-04-24 stamp and was carried
  unchanged through the 2026-05-29 pass — but **0.1.11 shipped 2026-05-07**,
  three weeks before that pass ran. The row was accurate when written and simply
  wasn't re-probed, which preserved the staleness invisibly. Added a note to
  `sources.md`: when a pass declares a probe budget, spend it on the rows most
  likely to have moved rather than re-confirming recently-stamped ones.

## Open

_None._ Nothing here is waiting on an absent ruling, credential, release, or
measurement nobody can run.

## Unblocked — actionable

- **OCP Route 60s timeout taught in three places** (Dim 6) — SKILL.md pitfall 6,
  `routing.md` §OpenShift Route, `openshift.md` §Routes. Keep the pitfall
  one-liner plus one canonical treatment and point the other at it. Multi-file,
  but nothing is absent.
- **Body still feature-list / pointer-map shaped, not operator-workflow ordered**
  (Dim 2) — `SKILL.md` top third (~L16-98). Lead with the operator workflow
  (audit → cache mount → HF_TOKEN → probes → serve_args → autoscale) before the
  vendor-named decision table. A structural rewrite that must preserve every
  pointer, keep SKILL.md under 500 lines, and not disturb trigger-relevant
  keyword placement — work, not a blocker. (carried 2026-05-29)
- **Trigger measurement for this skill and its vLLM siblings** (Dim 1) — the
  eval-set mining and the cross-skill over-trigger batch (e.g. "without
  restarting" stealing from spec-decode) are both a `trigger`-mode run away. The
  over-trigger case needs a batched run across the vLLM family, not an isolated
  edit here.

## Resolved — 2026-09-15

- **Tables of contents added to all eight >100-line reference files** (Dim 2/7)
  — `pod-shape.md` (12 entries), `disagg.md` (13), `openshift.md` (11),
  `docker-lab.md` (10), `autoscaling.md` (10), `multi-node.md` (10),
  `routing.md` (10), `ecosystem.md` (5). Every anchor checked against a real
  heading. Carried since 2026-07-18, displaced by other work each pass; nothing
  was ever blocking it.
- **The `probe-trigger.py` all-zero blocker was stale by three months.** The
  entry claimed trigger precision "cannot be measured/tuned for this skill until
  the harness probe returns non-zero scores", carried since 2026-05-29. That
  probe was repaired on **2026-06-07** — the `jira-cli` pass fixed it (it had
  installed a non-auto-invoked slash command, bailed on the first non-Skill
  tool, and shared a project root between concurrent workers) and then ran a
  real 13/15 measurement with it. Nothing has blocked trigger work here since.
  **This is drain duty failing, not a blocker**: the absent thing arrived, no
  pass noticed, and it held two further trigger items behind it.
- **`ecosystem.md` verification-label drift** (Dim 8) — already struck through
  as closed on 2026-08-11 but still sitting under Open; moved here.

## Resolved this pass (2026-07-18 — improve run, post-SkillLens rubric)

Baseline self 89 → **83 corrected** after grep-verifying the baseline blind's
Dim 5 flag (self-score had missed that four description-promised topics had
zero body coverage — the SkillLens fluency trap in miniature) / baseline
blind **83** → final self **90** (stop condition: 90+ with no dim <7) /
final blind **87**. 7 keeps, 0 discards, 7 iterations. Neither Boris nor
SkillLens caps fired at baseline or final — mechanism+remedy density and
blacklists confirmed by both blind agents.

- **iter 1 (keep, simplification):** SKILL.md 163→148 lines — deleted the
  ad-hoc smoke-command block (covered by deployment-smoke.sh) and the
  commented NCCL env dupes (in pod-shape template). Dim 2 8→9.
- **iters 2–4 (keep ×3, noise-confirmed):** landed the four
  description-promised topics that had no body coverage — compile-cache
  survival (`VLLM_CACHE_ROOT`; vLLM redirects TORCHINDUCTOR/TRITON cache
  dirs itself, verified at `vllm/compilation/compiler_interface.py:477-480`),
  serve-args review (`--enforce-eager` trade-off, MoE
  `--enable-expert-parallel` / ep2-dp2 layout-vs-GPU-count check), and the
  parser-plugin ConfigMap mount (`--tool-parser-plugin`,
  `cli_args.py:115`) — all in pod-shape.md with SKILL.md pointers extended
  in-line. All flag/env claims probed against the local vLLM clone
  (752a3a5044, 2026-07-12). Dim 5 6→9.
- **iter 5 (keep, noise-confirmed):** deployment-smoke.sh check 6 dead code
  fixed — TP is a CLI arg, invisible to `printenv`; now parsed from the pod
  spec args with a GPU-limit fallback; both arg formats tested, shellcheck
  clean. Dim 7 8→9. (Baseline-blind finding.)
- **iter 6 (keep, noise-confirmed):** sources.md prose note contradicted its
  own table (llm-d "v0.6.0 latest" vs verified v0.7.0 row). Dim 8.
- **iter 7 (keep, noise-confirmed):** pitfall 2 reconciled with pod-shape's
  startupProbe recommendation ("fixed at 600 s" → both options named).
  Dim 8 → 10.

## Resolved this pass (2026-05-29)

- llm-d version bump v0.6.0 → v0.7.0 (2026-05-12) in `references/ecosystem.md`; sources.md row re-stamped. (Dim 9)
- NVIDIA Dynamo version bump v1.0.2 → v1.1.1 (2026-05-09) in `references/ecosystem.md`; sources.md row re-stamped. (Dim 9) — note: `references/disagg.md` carries no Dynamo version string, so no edit needed there (recon hypothesis assumed one that does not exist).
- Envoy AI Gateway version bump v0.5.0 → v0.6.0 (2026-05-05) in `references/ecosystem.md`; sources.md row re-stamped. (Dim 9)
- vLLM upstream v0.21.0 (2026-05-15) note added to `references/openshift.md` RHAIIS mapping (reinforces "pin the RHAIIS tag, roll forward with release notes"; RHAIIS↔upstream pin still flagged unverifiable); sources.md upstream row re-stamped. (Dim 9)
- Gateway-API-on-OpenShift version-gate table deduplicated: removed the verbatim copy from `references/routing.md`, replaced with a one-line pointer to `references/openshift.md`. (Dim 6)
- `references/sources.md` re-stamped all rows to 2026-05-29 (4 bumped via direct `gh api` release probes: llm-d, Dynamo, Envoy AI Gateway, vLLM; 4 re-confirmed current: LWS, AIBrix, GAIE, semantic-router); Classifications + freshen-pass header updated. (Dim 9 staleness ceiling refreshed)
