# Improvement Backlog — aiperf

Prior skill-improver runs and ceiling findings.

## Open

*(the carried v0.8.0 audit item below is now closed — see the 2026-07-21 section)*

## Resolved — 2026-07-21 (freshen)

Three minors of drift closed (v0.8.0 → **v0.11.0**, 2026-07-08). Also closes the
carried "audit v0.8.0 release notes flag-by-flag" item, superseded by auditing
v0.9/v0.10/v0.11 against the `v0.11.0` CLI reference rather than release prose.

- **`--endpoint-type` enum corrected against `docs/cli-options.md` @ `v0.11.0`:**
  17 values, not 15. Added `image_edit` (v0.9.0, PR #906, FLUX.2 image-to-image)
  and `raw`. **`nim_image_retrieval` was wrong — the enum value is
  `image_retrieval`.** A user copying the old name would have hit a CLI
  validation error.
- **SPEED-Bench was in the wrong category.** `datasets.md` listed the
  `speed_bench_*` names under `--public-dataset`; at v0.11.0 they are
  `--custom-dataset-type` values. `--public-dataset speed_bench_math` is
  rejected. Corrected, and the public-dataset table gained the missing
  `spec_al_*` (speculative-decoding acceptance length) and speech/ASR
  (`librispeech`, `voxpopuli`, `gigaspeech`, `ami`, `spgispeech`) groups.
- **Custom dataset formats: 6 → 10 core** — added `dag_jsonl` (v0.9.0, PR #891,
  conversation DAGs with FORK/SPAWN), `raw_payload`, `inputs_json`,
  `sagemaker_data_capture`, plus the SPEED-Bench family documented as
  custom-dataset-type values.
- **Frontmatter counts corrected** (15→17 endpoints, 6→10 formats, "40+ public
  datasets"→"20+" since the 40+ figure was counting SPEED-Bench variants that
  are not public datasets). Trigger phrases left intact.
- **New capability section in SKILL.md** for v0.9–v0.11: adaptive sweep
  orchestrator + YAML-native v2 config (BO + search recipes), multi-tier SLO
  search, the seven-benchmark accuracy suite, OTel/MLflow and W&B exporters,
  AMD ROCm telemetry via `amdsmi`, `network_adjusted_*` latency metrics, power
  metrics, and the v0.11.0 warmup fix that invalidates prefix-cache-skewed
  baselines from ≤v0.10.x.
- **Python bound is now `>=3.10,<3.14`** (was recorded as `>=3.10`); Windows is
  a first-class port with blocking CI since v0.11.0; `aiperf-nightly` wheel
  published since v0.10.0.

**Marked as inferred, not documented:** the `image_edit` and `raw` default
paths are absent from the CLI reference — both rows now say so explicitly and
tell the reader to confirm with `--help`, rather than asserting OpenAI's
conventional path as fact.

### Bundle helper scripts to lift Dim 7 (Resource Quality)
- **Dim:** 7
- **Where:** new `scripts/` directory; would also require pointer table additions in `SKILL.md` "What to read next" and `references/output-artifacts.md`.
- **Why ceiling-bound:** plugin authoring (rerank shim, custom dataset loader) and `profile_export.jsonl` percentile/correlation analysis are scriptable. But: (a) which scripts are most valuable depends on author intent — operator-side (analysis helpers) vs developer-side (plugin scaffolds); (b) the official aiperf repo already provides Pydantic models for output parsing, so a script would be duplicative without a focused use case the author wants to standardize on. Skip until the author signals the workflow.
- **Score impact if resolved:** Dim 7 7→9 (~+2 total).

### Quick-recipe / timing-modes overlap (intentional design)
- **Dim:** 6
- **Where:** `SKILL.md` "Quick recipes" overlaps with `references/timing-modes.md` "Worked examples".
- **Why not fixed:** different audiences. SKILL.md recipes are entry-points (smoke test, ShareGPT, Mooncake+goodput, NIM, multi-turn KV-cache, multi-run CI, accuracy) — pattern-by-task. timing-modes.md examples are scheduling-mode-by-scheduling-mode, intentionally illustrating compatibility-matrix rules. Removing either degrades the corresponding navigation path. Carrying as a known-non-issue rather than open work.

### Audit v0.8.0 release notes for new flags / endpoints / dataset types (carried 2026-05-28)
- **Dim:** 9
- **Where:** `SKILL.md` Decision-tree + scheduling-mode tables; `references/{cli,endpoints,datasets,metrics}.md`.
- **Why not fixed this pass:** the version pin was bumped v0.7.0 → v0.8.0 (verified), but the v0.8.0 release-notes body was not diffed flag-by-flag against the skill within this pass's budget. Pull https://github.com/ai-dynamo/aiperf/releases/tag/v0.8.0 and reconcile any new/renamed flags, endpoint types, or dataset formats. The per-feature PR attributions already in endpoints.md/datasets.md ("v0.7.0 added X via PR #Y") are historical and correct — do not bump those.

## Resolved this pass (2026-05-28)

- **Version freshen v0.7.0 → v0.8.0 (Dim 9).** Verified against PyPI (`pypi.org/pypi/aiperf/json` → info.version 0.8.0, uploaded 2026-05-16, requires-python >=3.10) and GitHub releases (`gh release view v0.8.0` → published 2026-05-16). Updated SKILL.md "Versions": stable PyPI v0.7.0 (2026-04-07) → v0.8.0 (2026-05-16); repo `main` 0.8.0-dev → 0.9.0-dev. Re-stamped 4 sources.md rows (repo, releases, release-notes, PyPI) to Last verified 2026-05-28 and pointed the release-notes row at the v0.8.0 tag.
- **Recon/disk mismatch identified (process note).** The recon findings fed to this APPLY stage targeted a stale v0.6.x checkout (claimed v0.6.4 latest with a single `profile` subcommand, 6 endpoint types, a 6-row "Subcommands" table, and workflows.md/telemetry-and-plugins.md reference files). None of that matches the on-disk skill (v0.7.0 rewrite, "Decision tree — which subcommand" table, cli.md/timing-modes.md/metrics.md references). The recon's "v0.6.4 is latest" claim was also self-contradictory — v0.8.0 is the true latest (2026-05-16). The recon's downgrade hypotheses were therefore NOT applied; doing so would have corrupted a coherent, more-current skill.

## Prior run — Resolved 2026-04-25

- **Trigger Precision (Dim 1) char-cap fix.** Combined `description` + `when_to_use` reduced from 2188 chars (truncated at 1536) to 1455 chars (81-char margin). Tail-truncated triggers no longer lost.
- **Writing Style (Dim 3).** Six second-person slips removed (2 in SKILL.md, 4 in references). Zero "you/your" remaining.
- **Stale instruction in cli.md.** `--isl-block-size` "Match server's block size" rewritten to the correct divisibility rule (points at SKILL.md pitfall 5).
- **Pitfall redundancy (Dim 6).** Pitfall 12 (server-side reasoning-parser config) folded into pitfall 2.

### Score trajectory (2026-04-25 run)

| iter | self | blind | delta | status | description |
|------|------|-------|-------|--------|-------------|
| 0    | 85   | 82    | —     | baseline |  |
| 1    | 86   |       | +1    | keep   | trim desc+when_to_use to 1532/1536 |
| 2    | 87   |       | +1    | keep   | 2 SKILL.md you/your → imperative + 1 cli.md stale instruction |
| 3    | 88   |       | +1    | keep   | merge pitfall 12 → pitfall 2 |
| 4    | 90   | 90    | +2    | keep   | 4 reference you/your fixes + tighten margin to 81 chars |

Final blind agreed with self. No bias flags ≥2. Run converged at 90/100 with no dimension below 8.
