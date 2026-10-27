# sources.md — external references for `patch` (freshen index)

Freshened: 2026-10-27 — every row probed (gh, local clones at `d3bea6b` / `0e6f00d`, live Claude Code docs); the harness's D&R run dirs and Claude Code's background-by-default subagents changed SKILL.md.

One row per external reference this skill depends on. `skill-improver freshen`
probes every row and writes the single `Freshened:` header stamp above.

Re-run `/skill-improver freshen patch` quarterly or when the upstream harness's
patch ladder changes.

## defending-code reference harness (provenance + execution-verified delegate)

- URL: https://github.com/anthropics/defending-code-reference-harness
- Probe: `gh repo view anthropics/defending-code-reference-harness --json pushedAt,isArchived`
- Note: adapted (Apache-2.0) from that repo's `patch` skill. Static mode is
  self-contained; execution-verified mode delegates to the harness's
  `vuln-pipeline patch` build→reproduce→regress→re-attack ladder. See
  `../vuln-scan/HARNESS.md` for setup/run.
- D&R layout (Phase 0b stop rule): `dnr_harness/cli.py` writes
  `results/<target>/<ts>/run_NNN/{result.json,INCIDENTS.json}`, so the
  `run_*/result.json` exec-mode marker also matches D&R runs; `harness/`
  (the vuln pipeline) never writes `INCIDENTS.json`. Upstream's own patch skill
  carries the same exception since anthropics/defending-code-reference-harness#23
  (2026-07-16). Checked at `d3bea6b` on 2026-10-27.
- Status: active, not archived, no GitHub releases or tags. Last push
  2026-08-06 (anthropics/defending-code-reference-harness#44, Bedrock launch
  preflights) — nothing after it. The ladder in `docs/patching.md` and
  `harness/patch_grade.py` is T0 build → T1 PoC stops → T2 tests (skipped
  without a `test_command`) → re-attack; `vuln-pipeline patch <results_dir>
  --model M [--bug N]` writes `reports/bug_NN/{patch.diff,patch_result.json}`
  with `verdict.passed`.

### Delta worth knowing (2026-06-15 → 2026-07-21)

- **Outbound agent API requests now carry a declared usage marker** (anthropics/defending-code-reference-harness#22,
  2026-07-11; header renamed the same day). `harness/auth.py` stamps
  `anthropic-cyber-runbook: pipeline` plus
  `User-Agent: cyber-runbook/<version> (claude-cli/<CLAUDE_CODE_VERSION>)` onto
  the agent env via `_with_usage_marker()`. **First-party callers only** — the
  code notes Bedrock/Vertex rewrite the `User-Agent`, so the marker does not
  apply there. Operationally: running the harness against the 1P API now tags
  that traffic identifiably. Documented in the harness's `docs/security.md` and
  `docs/pipeline.md#usage-marker`.
- **New detection & response track** (2026-07-16): `dnr-pipeline`, a `dnrcanary`
  target, and accompanying skills. Its run dirs share the `run_*/result.json`
  exec-mode marker — hence the Phase 0b stop rule (row above).
- **Bedrock guardrail** (2026-07-06): auth now warns on bare Bedrock model IDs
  missing an inference-profile prefix.
- Docs pass (2026-07-16) folded per-skill `Status` sections into prose and
  corrected the model-pin note; the pipeline reference gained a full CLI flag
  tree and batch-sizing guidance.

## visa-vulnerability-agentic-harness (reviewer gate structure lineage)

- URL: https://github.com/visa/visa-vulnerability-agentic-harness
- Probe: `gh repo view visa/visa-vulnerability-agentic-harness --json pushedAt,isArchived`
- Note: the Phase 3 reviewer's four-gate structure (root-cause /
  instance-coverage / no-new-vulns / best-practices, skip counted as
  abstention, qualified accepts surfaced) and its anti-manipulation
  prologue are adapted (Apache-2.0) from this repo's s11 validation
  personas (`vvaharness/validation/subagents/`, `constants/scoring.py`).
- Latest release v1.5.1 (2026-10-22; v1.5.0 2026-10-09). Read at `0e6f00d`:
  `vvaharness/validation/constants/scoring.py` `GATE_WEIGHTS` still keys
  `root_cause` / `instance_coverage` / `no_new_vulnerabilities` /
  `security_best_practices`, `SKIP` weight-neutral, root-cause and
  no-new-vulns the critical gates. v1.4.0→v1.5.1 touched that file's comments
  only; of the persona files only `cross-repo-analyzer.md` changed.

## Claude Code skills docs (`allowed-tools` semantics, SKILL.md "Tools")

- URL: https://code.claude.com/docs/en/skills (section "Pre-approve tools for a skill")
- Note: `allowed-tools` "grants permission for the listed tools during the
  turn that invokes the skill ... It does not restrict which tools are
  available: every tool remains callable". SKILL.md's Bash limits are
  therefore skill rules, not runtime-enforced (corrected 2026-10-27 from
  "permission filter, not a loader").

## Claude Code subagent docs (Phase 2B/3 spawn + async recovery)

- URLs: https://code.claude.com/docs/en/sub-agents ("Which subagents run in
  the background", "Tools, permissions, and results of background subagents",
  "Available tools"); https://code.claude.com/docs/en/tools-reference
  ("Agent tool behavior")
- Note: `Agent` is the subagent tool (`Agent(Explore)` permission form).
  "With nothing configured, a subagent that Claude spawns from your main
  conversation starts in the background"; its "results reach Claude as a
  completion notification in a later turn". Background subagents keep `Read`,
  `Grep`, `Glob`, so the read-only author/reviewer tool sets survive.
- Guard rail "Always set `subagent_type`; never fork": an Agent call that
  omits `subagent_type` falls back to `general-purpose` (errors.md, "subagent_type
  is required"); a fork "inherits the entire conversation so far" (sub-agents,
  "Fork the current conversation"). Omission does not fork.

---

## Markers

- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
