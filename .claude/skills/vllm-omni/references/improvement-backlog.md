# Improvement backlog — vllm-omni

Tracking for the skill-improver loop. "Open" is work attempted but not applied in one
iteration; "Resolved this pass" is changes the metric registered.

## Open

- **Frontmatter `description` still advertises now-historical pitfall specifics** (Dim 1 / Dim 9, SKILL.md frontmatter `description`): the description ends with "release pitfalls (v0.19.0rc1 FLUX regression, GLM-Image transformers>=5.0, Qwen3-TTS enforce-eager)". The FLUX regression is fixed in v0.20.0 and the enforce-eager mandate is lifted, so these are no longer current *features* — but they remain valuable *trigger phrases* (an operator hitting the v0.19.0rc1 FLUX bug or searching "enforce-eager" should still match). Not applied: rewording risks lowering Trigger Precision (Dim 1=9) for a marginal Dim 9 gain, and it is a taste trade-off rather than a clean one-iteration win. Revisit on the next freshen once these symptoms are old enough that no operator searches them.
- **GLM-Image `transformers>=5.0` requirement on v0.20.0 not definitively confirmed** (Dim 9, SKILL.md pitfall + references/models.md GLM-Image row): v0.20.0 release notes list "Transformers 5.x compatibility fixes", so the manual upgrade is *likely* unnecessary now, but this was not verified against the actual v0.20.0 wheel's `transformers` pin. Edited to "verify whether still needed" rather than deleted. Resolving needs a probe of the v0.20.0 wheel metadata (`pip download vllm-omni==0.20.0` → inspect `Requires-Dist`).
- **v0.21.0rc1 contents not surveyed** (Dim 9, references/sources.md release row): added as the latest pre-release row but its release notes were not read, so any new models/endpoints/fixes it introduces are not reflected in models.md / endpoints.md. Survey on next freshen. **(2026-07-21: partly moot — no v0.21.0 stable was ever cut. Superseded by the larger model-roster gap below.)**
- **Model roster is four minors behind** (Dim 5/9, `references/models.md`): v0.22.0 and v0.24.0 between them added Cosmos3, DreamZero, MiniCPM-o 4.5, MOSS-TTS, GLM-TTS, Higgs Audio v2 and V3, HiDream-I1-Full, SenseNova U1, IndexTTS2, Step-Audio2, SDXL, GR00T-N1.7, Lance, Covo-Audio-Chat, Ming-flash-omni-2.0, soulx-singer, Aura, Stable-Audio-Open and more. Not applied this pass: syncing the roster means re-reading `docs/models/supported_models.md` and rewriting a table across `models.md` — a multi-row content import, not a one-line freshen edit, and the release notes alone are not an authoritative capability list (they say "added or improved" without distinguishing). Should lead the next pass.

## Resolved — 2026-08-11 (freshen, rebaseline v0.24.x → v0.26.0)

- **Rebased to v0.26.0 (2026-08-03, on vLLM 0.26.0 via #5443)** across the
  mental model, install pins, ROCm wheel index (`rocm700` → `rocm723`), Docker
  tags, key-numbers table and `sources.md` release rows.
- **Last pass's headline finding is now moot — and saying so is the point.**
  The GitHub/PyPI/Docker mismatch is resolved: all three serve v0.26.0, and
  the v0.24.1 Qwen-Image fix rides along by descent, so the `git+…@v0.24.1`
  install form is deleted. Two things were kept rather than celebrated:
  Docker `latest` now resolves to `v0.26.0post1.20260811` (a post-release
  build, so pin exact tags), and the refresh policy still says re-check all
  three channels — parity today is not parity next release.
- **Two v0.26.0 breaking changes captured.** (1) LTX registry renames
  (#5148): `LTX2Pipeline` unified for LTX-2/2.3 × T2V/I2V; five old names
  removed; distilled path is `LTX2DistilledPipeline`. Verified against
  `vllm_omni/diffusion/registry.py` at the v0.26.0 tag rather than trusting
  the release note, which is how the extra `LTX2T2VDMD2Pipeline` /
  `LTX2I2VDMD2Pipeline` entries surfaced. (2) GGUF diffusion moved out of
  tree (#4769) to `vllm-project/vllm-gguf-plugin` — `diffusion.md`'s quant
  table advertised an in-core path that no longer exists.
- **Three Open items closed against source, not inference:**
  - **`guidance_scale=0` sentinel** — was documented as a permanent design
    gotcha; it was a *bug* (#4998), fixed by #4999 in v0.26.0. The old text
    also mis-described the failure: an explicit `0` was not "coerced to 1.0",
    it was replaced by the **pipeline's own default**, which for
    HunyuanImage-3.0 is `5.0` and turns CFG on.
  - **GLM-Image `transformers>=5.0`** — the wheel-metadata probe this backlog
    asked for, done: v0.26.0 `requirements/common.txt` floors transformers at
    `>= 5.5.3`. Hedge deleted from SKILL.md and models.md.
  - **`flashinfer<0.6.7`** — traced to upstream vLLM #38729 (GB300/SM103
    only; **SM100 never affected**, so the skill's "SM100/SM103" overstated
    it), fixed in-tree by #38730 on 2026-04-01 and upstream in FlashInfer
    #2939. The pin is now also *unsatisfiable*, since vLLM 0.26.0 hard-pins
    `flashinfer-python==0.6.14`. Replaced with the provenance and a "this
    would be a new bug" instruction.
- **Recorded the dependency-line boundary explicitly** (`sources.md`): this
  stack is PyTorch 2.11.0 / FlashInfer 0.6.14 because it rides vLLM 0.26.0.
  Upstream vLLM v0.27.0's 2.13.0 / 0.6.16.post3 is *not* this stack, and the
  strict minor-alignment rule means it cannot be until vllm-omni v0.27.x —
  worth stating because the obvious mistake is to read upstream pins as
  current.
- **New surface noted, in scope:** experimental full-duplex realtime for
  MiniCPM-o 4.5 — `/v1/duplex` and `/v1/realtime?duplex=1` (#3907) — added to
  the router with its preview caveats (no persistent KV leases, no
  multi-session admission/recovery, not byte-for-byte Realtime-compatible).

**Carried forward / still Open:** the model-roster re-sync (now five minors
behind, and the largest remaining gap — v0.26.0 alone adds MiniMax H3, Krea 2,
Boogu Image, Nemotron Audex, LingBot Video, MammothModa2-Dev, Cosmos3
Edge/Distilled, MOSS-TTS-Local v1.5). `models.md` now carries an explicit
"this is a floor" banner naming those, so a reader is warned even before the
table is fixed. The frontmatter-description item below is also untouched —
but note `transformers>=5.0` in that description is now doubly historical.

## Resolved — 2026-07-21 (freshen)

- **Found a distribution-channel mismatch — the pass's most actionable finding.**
  GitHub's "Latest" is **v0.24.1** (2026-07-10), but PyPI's newest is **0.24.0**
  and `0.24.1` is absent from its release index entirely (never uploaded, not
  yanked), and Docker Hub's newest versioned tag is also **v0.24.0** with
  `latest` pointing at it. v0.24.1 is a single-PR patch (#5017) fixing the
  Qwen-Image performance regression in #4964 — so `pip install vllm-omni` and
  `vllm/vllm-omni:latest` both still carry that regression. Added a
  channel-comparison table to SKILL.md and `sources.md` plus the
  `git+…@v0.24.1` install form. Reinforces the general rule: **a tag is not a
  wheel**; check the artifact, not the release page.
- **Rebased v0.20.0 → v0.24.0/v0.24.1** across the SKILL.md mental model,
  install pins, ROCm wheel index, Docker tag, and key-numbers table, plus all
  `sources.md` release rows. Recorded that **v0.21.0 and v0.23.0 never got
  stables** (rc1 only) so a future reader doesn't treat the gaps as withdrawals.
- **§3.0 sweep on the tracked issues — five live caveats saved.** Six issues
  flipped to `CLOSED`/`COMPLETED` since the last pass; only **#4964** closed
  against a named fix PR. Reading the state field alone would have retired:
  - **#2768** (orphan procs after Wan2.2 crash) — closed `COMPLETED`
    2026-05-16, but the last comment four days earlier is a **fresh
    reproduction by a different reporter** with no fix referenced. Mitigation
    kept, with the closure explicitly annotated as bookkeeping.
  - **#2562** (Qwen3-TTS streaming audio gaps) — closed verbatim *"as no
    response over 1 month"*. Inactivity, not a fix.
  - **#2595** — closed on a **workaround** (`VLLM_ALLOW_LONG_MAX_MODEL_LEN=1`,
    PR #2508), promoted into SKILL.md as an operator pitfall since it is
    actionable and likely still needed.
  - **#2683**, **#2635**, **#2880** — root-caused in-thread but with no fix
    confirmation; marked "fix unconfirmed, re-test before relying on it".
  - **#2898** — genuinely *answered* rather than patched: multi-stage
    deployment means `--dtype` / `--max-model-len` / `--served-model-name`
    don't propagate from the CLI, so they belong in the YAML stage config.
    That is real operator guidance and is now recorded as such.
- **Captured the v0.22.0/v0.24.0 architecture deltas** in `sources.md`:
  `OmniCoordinator` integrated into the stage engine pipeline (#3569 — the
  shape RFC #984 was tracking), Cosmos3 world-model day-0 support, DreamZero +
  OpenPI robot serving, the stage-runtime + distributed replica control-plane
  refactor (#3855), diffusion **request-level batching** (#4079), and async
  output materialization (#4476).
- **Added a refresh-policy rule:** re-check the distribution channels, not just
  the release list — this pass's headline finding is invisible to a
  release-list-only probe.

**Not done this pass:** the model roster (now an explicit Open item above), the
doc-page rows (still 2026-04-18), the arXiv paper, and the open RFC list. The
GLM-Image `transformers>=5.0` wheel-metadata probe also remains Open — it needs
a `pip download` + `Requires-Dist` inspection that was out of scope here.

## Resolved this pass (2026-05-28)

- Rebased central mental model: dropped the removed `patch.py` early-import / entrypoint-hijack claim, replaced with the v0.20.0 plugin-registration integration path (#3232/#3393). [Dim 9]
- Rebased "current stable" from v0.18.0 to v0.20.0 across SKILL.md (mental model, install pins, ROCm wheel index, Docker tag, key-numbers table, source policy) and reference headers (models.md, endpoints.md). [Dim 9]
- FLUX pitfall: deleted obsolete "pin v0.18.0 until next release" advice; noted #2730 fixed in v0.20.0 (PR #2760). [Dim 9]
- Qwen3-TTS enforce-eager: re-scoped to v0.18-only; noted #2866 CLOSED 2026-04-29 and v0.20.0 code2wav CUDA-graph capture (PR #2690); dropped `--enforce-eager` from v0.20-era serve commands. [Dim 9]
- GLM-Image transformers>=5.0: re-scoped to v0.18; noted v0.20.0 Transformers 5.x compat fixes. [Dim 9]
- sources.md: added v0.20.0rc1 / v0.20.0 / v0.21.0rc1 release rows; corrected #2866 and #2730 to CLOSED; added PR rows #2690 (VoxCPM2 TTS perf, cited in v0.20.0 TTS-CUDA-graph group) / #3232 (rebase to vllm 0.20.0); cited the release-notes PR group (#3232/#3082/#3352/#3393/#2306) for the entrypoint-hijack removal rather than mislabeling a single PR; annotated the patch.py anchor as removed in v0.20.0; restamped re-confirmed rows (Repo, PyPI, Docker/Release index) to 2026-05-28. [Dim 9]
- Converted the 10-item numbered "top operator mistakes" list to a bulleted catalog, dropping body numbered-list count to 0 and lifting the Boris Dim-6 strict-workflow cap. [Dim 6]
- Added a one-line "Contents:" TOC to the four reference files over 100 lines (endpoints, diffusion, stage-config, realtime-tts). [Dim 2]
