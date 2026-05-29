# Improvement backlog — nvidia-nixl

Tracks ceiling findings from `skill-improver` runs that need multi-file
restructure or author judgment. Updated by skill-improver Phase 6.

## Open

(none — all prior Open items resolved this pass.)

## Resolved this pass

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
