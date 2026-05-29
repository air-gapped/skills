# Improvement backlog — vllm-omni

Tracking for the skill-improver loop. "Open" is work attempted but not applied in one
iteration; "Resolved this pass" is changes the metric registered.

## Open

- **Frontmatter `description` still advertises now-historical pitfall specifics** (Dim 1 / Dim 9, SKILL.md frontmatter `description`): the description ends with "release pitfalls (v0.19.0rc1 FLUX regression, GLM-Image transformers>=5.0, Qwen3-TTS enforce-eager)". The FLUX regression is fixed in v0.20.0 and the enforce-eager mandate is lifted, so these are no longer current *features* — but they remain valuable *trigger phrases* (an operator hitting the v0.19.0rc1 FLUX bug or searching "enforce-eager" should still match). Not applied: rewording risks lowering Trigger Precision (Dim 1=9) for a marginal Dim 9 gain, and it is a taste trade-off rather than a clean one-iteration win. Revisit on the next freshen once these symptoms are old enough that no operator searches them.
- **GLM-Image `transformers>=5.0` requirement on v0.20.0 not definitively confirmed** (Dim 9, SKILL.md pitfall + references/models.md GLM-Image row): v0.20.0 release notes list "Transformers 5.x compatibility fixes", so the manual upgrade is *likely* unnecessary now, but this was not verified against the actual v0.20.0 wheel's `transformers` pin. Edited to "verify whether still needed" rather than deleted. Resolving needs a probe of the v0.20.0 wheel metadata (`pip download vllm-omni==0.20.0` → inspect `Requires-Dist`).
- **v0.21.0rc1 contents not surveyed** (Dim 9, references/sources.md release row): added as the latest pre-release row but its release notes were not read, so any new models/endpoints/fixes it introduces are not reflected in models.md / endpoints.md. Survey on next freshen.

## Resolved this pass (2026-05-28)

- Rebased central mental model: dropped the removed `patch.py` early-import / entrypoint-hijack claim, replaced with the v0.20.0 plugin-registration integration path (#3232/#3393). [Dim 9]
- Rebased "current stable" from v0.18.0 to v0.20.0 across SKILL.md (mental model, install pins, ROCm wheel index, Docker tag, key-numbers table, source policy) and reference headers (models.md, endpoints.md). [Dim 9]
- FLUX pitfall: deleted obsolete "pin v0.18.0 until next release" advice; noted #2730 fixed in v0.20.0 (PR #2760). [Dim 9]
- Qwen3-TTS enforce-eager: re-scoped to v0.18-only; noted #2866 CLOSED 2026-04-29 and v0.20.0 code2wav CUDA-graph capture (PR #2690); dropped `--enforce-eager` from v0.20-era serve commands. [Dim 9]
- GLM-Image transformers>=5.0: re-scoped to v0.18; noted v0.20.0 Transformers 5.x compat fixes. [Dim 9]
- sources.md: added v0.20.0rc1 / v0.20.0 / v0.21.0rc1 release rows; corrected #2866 and #2730 to CLOSED; added PR rows #2690 (VoxCPM2 TTS perf, cited in v0.20.0 TTS-CUDA-graph group) / #3232 (rebase to vllm 0.20.0); cited the release-notes PR group (#3232/#3082/#3352/#3393/#2306) for the entrypoint-hijack removal rather than mislabeling a single PR; annotated the patch.py anchor as removed in v0.20.0; restamped re-confirmed rows (Repo, PyPI, Docker/Release index) to 2026-05-28. [Dim 9]
- Converted the 10-item numbered "top operator mistakes" list to a bulleted catalog, dropping body numbered-list count to 0 and lifting the Boris Dim-6 strict-workflow cap. [Dim 6]
- Added a one-line "Contents:" TOC to the four reference files over 100 lines (endpoints, diffusion, stage-config, realtime-tts). [Dim 2]
