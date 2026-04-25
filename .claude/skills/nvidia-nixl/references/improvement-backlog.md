# Improvement backlog — nvidia-nixl

Tracks ceiling findings from `skill-improver` runs that need multi-file
restructure or author judgment. Updated by skill-improver Phase 6.

## Open

### 1. Dynamo TRT-LLM `kv-cache-transfer` URL returns 404
- **Affects**: Dim 9 (Domain Accuracy)
- **Files**: `references/sources.md` row "Dynamo TRT-LLM kv-cache-transfer doc";
  `references/integrations.md` "TensorRT-LLM" section
- **Why deferred**: requires probe of NVIDIA Dynamo doc-site map / `ai-dynamo/dynamo`
  repo to find current path of the document. Not auto-fixable in one iteration —
  needs verification + rewrite.
- **Action when fixed**: replace URL with current path, re-stamp `Last verified`,
  remove "drift watch" entry from sources.md.

### 2. Rust / C++ agent API claimed in scope but no reference file
- **Affects**: Dim 5 (Completeness)
- **Files**: `SKILL.md` audience line ("plugin authors writing new backends, developers
  using the agent API directly from Python/C++/Rust"), `references/sources.md`
  Rust example row
- **Why deferred**: SKILL.md asserts C++ + Rust support; only `references/python-api.md`
  exists. Either add `references/cpp-api.md` + `references/rust-api.md` (substantial
  authoring against `src/api/cpp/` headers + `examples/rust/src/single_process_example.rs`),
  or trim the audience claim to Python-only and demote C++ / Rust to a "see
  upstream" pointer. Author choice.
- **Action when fixed**: pick one path. If adding refs: each ~150–250 lines mapping
  to in-tree headers and the Rust example. If trimming: remove "C++/Rust" from
  the audience line and add a one-line "C++/Rust developers: consult `src/api/cpp/`
  headers and `examples/rust/src/single_process_example.rs` directly" pointer.

## Resolved this pass

- 2026-04-25: oversized `description` + `when_to_use` (combined 2450 chars vs 1536
  cap) — trimmed to 1472 chars, dropped paraphrase variants and "Also implicit"
  prose triggers. Dim 1 7→9.
- 2026-04-25: 2 second-person slips in SKILL.md body (lines 36, 90) — converted
  to imperative. Dim 3 9→10.
- 2026-04-25: no `scripts/` despite operational skill — added
  `scripts/check_install.py` (215 lines, 7 sanity checks tied to gotchas.md
  top-10) plus diagnostic-flow + References pointers. Dim 7 7→9.
- 2026-04-25: "Authoritative sources" section in SKILL.md duplicated
  `references/sources.md` — collapsed to one paragraph + pointer. Dim 6 minor
  cleanup, no score change but removes redundancy.
- 2026-04-25: freshen pass — NIXL latest release (v1.0.1, 2026-04-14), HEAD commit
  `6cbbfc6` (2026-04-24), nixl-cu13 PyPI 1.0.1 — all `fresh` (1 day old). No
  content updates required.

## Run history

| Date | Mode | Baseline | Final | Delta | Notes |
|---|---|---|---|---|---|
| 2026-04-25 | improve + freshen | 85 (blind) | 93 (blind) | +8 | 4 iterations kept, 0 discards. Stopped at ceiling. |
