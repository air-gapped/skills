# Improvement backlog — nvidia-nixl

Tracks ceiling findings from `skill-improver` runs that need multi-file
restructure or author judgment. Updated by skill-improver Phase 6.

## Open

### Per-plugin READMEs predate the 1.2/1.3 line (new 2026-07-21)

Dim 9. File-set: `references/plugins.md` (all 13 documented plugin entries) + the
`sources.md` plugin-README rows, which still carry `Last verified: 2026-04-25`.

The 2026-07-21 freshen pass updated the plugin **count** (13 → 15, `infinia` and
`tracing` added) and the release-level facts, but did not re-read the 13 individual
`src/plugins/<name>/README.md` files. Three releases have landed since those stamps
and at least two touch plugin internals: libfabric gained `FI_MORE` doorbell batching
(v1.2.0 #1626), and POSIX / HF3FS / CUDA_GDS / GDS_MT all gained path-based file
registration plus the v1.3.1 unique-`devId` constraint. Not a one-edit fix — it is
13 fetches plus a rewrite of each entry's deps/params/gotchas. `infinia` has no
entry at all yet.

### AMD ROCm/HIP path is undocumented in this skill (new 2026-07-21)

Dim 5. File-set: `SKILL.md` audience/prereqs line + `references/deployment.md`
(build + install sections).

v1.3.0 added AMD Instinct support (gfx942 MI300X/MI325X, gfx950 MI350X/MI355X)
including `nixlbench`, but the skill's target-audience line still says
"datacenter-class GPUs (H100/H200/B200/B300) with NVIDIA driver, CUDA 12.8+" and
every build path assumes CUDA wheels. Documenting the ROCm path properly needs the
upstream build instructions read end-to-end and ideally one real build — author work,
not a stamp update.

## Resolved this pass (2026-07-21)

Freshen pass — evidence via `gh release list`, `gh release view` on v1.2.0/v1.3.0/v1.3.1,
`gh api contents/...` for `pyproject.toml` and `src/plugins`, and `git show v0.25.1:...`
in a local vLLM clone:

- **Version drift (Dim 9)**: latest release v1.1.0 → **v1.3.1** (2026-07-08); HEAD
  pyproject 1.2.0 → **1.4.0**. Added v1.2.0 and v1.3.0 rows to the version snapshot
  and to `sources.md`.
- **Plugin count**: 13 → **15** (`infinia` DDN object storage added in v1.3.0 #1569,
  plus `tracing`). Updated the snapshot table, the frontmatter `description`, the
  backend decision tree, and the `plugins.md` header; noted that manylinux wheels
  bundle `libplugin_INFINIA.so` from v1.3.1 while the proprietary DDN runtime is not
  vendored.
- **New API/build constraints surfaced as gotchas**: telemetry `category` field
  removed (#1649); path-mode `FILE_SEG` unique-`devId` enforcement (#1790); C++20
  required for source builds (#1571) with the `nixl_cuda_arch_list` escape hatch;
  OS-assigned listener port via `listen_port=0` (#1439); NIXL-EP rank/expert
  semantics refactor with the legacy mask-clean API removed (#1693).
- **vLLM pin**: `nixl >= 1.1.0` → **`nixl == 1.3.0`** (exact) at vLLM v0.25.1.
  Added the v0.22.1 dual-CUDA-wheel `ImportError: libcudart.so.12` note, the
  `kv_both` deprecation cycle (#43874), and the v0.24.0 NIXL KV-push topology.
- **Drift-watch list extended** with the "NIXL minors can be source-breaking"
  observation and the AMD/HIP churn warning; marked the local-clone and PyPI rows as
  not re-probed this pass rather than silently re-stamping them.

## Resolved earlier (2026-05-28)

- 2026-05-28: SKILL.md version snapshot stale — bumped Latest release v1.0.1→**v1.1.0**
  (2026-05-12), demoted v1.0.1 to a "Previous releases" row, and HEAD pyproject
  **1.1.0→1.2.0**. Verified by `gh release list` + `gh api contents/pyproject.toml`
  on main. Dim 9.
- 2026-05-28: vLLM-pin narrative obsolete — `integrations.md` L84-85 and
  `sources.md` vLLM-pin row rewritten from `nixl <= 0.10.1` / "vLLM not yet on
  ≥1.0.0" to `nixl >= 1.1.0` (verified in `vllm-project/vllm`
  `requirements/kv_connectors.txt`); removed the now-resolved drift-watch bullet.
  Dim 9.
- 2026-05-28: `sources.md` re-stamped to 2026-05-28 — NIXL repo HEAD
  `6cbbfc6`→`3009db5d` (#1630, 2026-05-26), release list (v1.1.0 isLatest),
  pyproject 1.2.0, PyPI nixl-cu12/cu13/meta all 1.1.0; probe-budget note rewritten
  for this pass. Dim 9 freshness restored (oldest date 34 days → 0).
- 2026-05-28: `deployment.md` pin example `nixl-cu12==1.0.1`→`1.1.0` for currency
  (latest released wheel). Dim 9.
- 2026-05-28: **Backlog item #2 (C++/Rust scope-vs-refs) resolved** — chose the
  trim path: SKILL.md audience line + frontmatter `description` no longer promise a
  C++/Rust agent-API reference; C++/Rust demoted to a one-line "consult `src/api/cpp/`
  headers and `examples/{cpp,rust}/` upstream" pointer. Description stays < 1024 chars,
  combined desc+when_to_use stays < 1536. Dim 5 + Dim 8.
- 2026-05-28: **Backlog item #1 (Dynamo TRT-LLM 404) resolved** — the page was
  renamed, not deleted; located the current source at
  `ai-dynamo/dynamo` `docs/backends/trtllm/trtllm-kv-cache-transfer.md` (confirmed
  via repo tree listing). Updated `sources.md` row + `integrations.md` (TensorRT-LLM
  section and the backend-list citation) to the live path; removed the drift-watch
  bullet. Dim 9.
- 2026-05-28: removed untracked `scripts/__pycache__/check_install.cpython-314.pyc`
  build artifact (already gitignored; local cleanup, no committed-tree change). Dim 7.

## Run history

| Date | Mode | Baseline | Final | Delta | Notes |
|---|---|---|---|---|---|
| 2026-04-25 | improve + freshen | 85 (blind) | 93 (blind) | +8 | 4 iterations kept, 0 discards. Stopped at ceiling. |
| 2026-05-28 | improve + freshen | 86 (cold) | 93 (cold self) | +7 | Freshen-led: v1.1.0/1.2.0 bumps, vLLM-pin rewrite, sources re-stamp, C++/Rust trim, Dynamo-doc relocation, pyc cleanup. Backlog #1 + #2 both closed. |
