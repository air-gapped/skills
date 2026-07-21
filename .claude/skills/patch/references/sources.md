# sources.md — external references for `patch` (freshen index)

One row per external reference this skill depends on. `skill-improver freshen`
probes each URL, classifies staleness, and re-stamps `Last verified:`.

Re-run `/skill-improver freshen patch` quarterly or when the upstream harness's
patch ladder changes.

## defending-code reference harness (provenance + execution-verified delegate)

- URL: https://github.com/anthropics/defending-code-reference-harness
- Probe: `gh repo view anthropics/defending-code-reference-harness --json pushedAt,isArchived`
- Note: adapted (Apache-2.0) from that repo's `patch` skill. Static mode is
  self-contained; execution-verified mode delegates to the harness's
  `vuln-pipeline patch` build→reproduce→regress→re-attack ladder. See
  `../vuln-scan/HARNESS.md` for setup/run.
- Last verified: 2026-07-21  (active; not archived; **last push 2026-07-16**; 17 commits since the 2026-06-15 stamp). **The patch ladder itself is unchanged** — `docs/patching.md` still describes the build→reproduce→regress→re-attack tiers, with the regress tier (T2) skipped on targets lacking a `test_command` (only `canary` sets one among the four bundled targets). Four patch-relevant paths moved in the window — `.claude/skills/patch/{README,SKILL}.md`, `docs/patching.md`, `harness/prompts/patch_prompt.py` — but as docs/prompt refinement, not a change to the verification tiers this skill delegates to.

### Delta worth knowing (2026-06-15 → 2026-07-21)

- **Outbound agent API requests now carry a declared usage marker** (PR #22,
  2026-07-11; header renamed the same day). `harness/auth.py` stamps
  `anthropic-cyber-runbook: pipeline` plus
  `User-Agent: cyber-runbook/<version> (claude-cli/<CLAUDE_CODE_VERSION>)` onto
  the agent env via `_with_usage_marker()`. **First-party callers only** — the
  code notes Bedrock/Vertex rewrite the `User-Agent`, so the marker does not
  apply there. Operationally: running the harness against the 1P API now tags
  that traffic identifiably. Documented in the harness's `docs/security.md` and
  `docs/pipeline.md#usage-marker`.
- **New detection & response track** (2026-07-16): `dnr-pipeline`, a `dnrcanary`
  target, and accompanying skills. Out of scope for this skill's patch ladder,
  but it means the harness is no longer only a scan→triage→patch pipeline —
  worth knowing before pointing someone at it.
- **Bedrock guardrail** (2026-07-06): auth now warns on bare Bedrock model IDs
  missing an inference-profile prefix.
- Docs pass (2026-07-16) folded per-skill `Status` sections into prose and
  corrected the model-pin note; the pipeline reference gained a full CLI flag
  tree and batch-sizing guidance.

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
