# sources.md — external references for `vuln-scan` (freshen index)

One row per external reference this skill depends on. `skill-improver freshen`
probes each URL, classifies staleness, and re-stamps `Last verified:`. Surveys
at use time read this only to surface staleness.

Re-run `/skill-improver freshen vuln-scan` quarterly or when the upstream
security-review tooling changes.

## defending-code reference harness (provenance + execution pipeline)

- URL: https://github.com/anthropics/defending-code-reference-harness
- Probe: `gh repo view anthropics/defending-code-reference-harness --json pushedAt,isArchived`
- Note: the skill is adapted (Apache-2.0) from this repo's `vuln-scan` skill and
  its autonomous `find`/`recon` pipeline prompts. `HARNESS.md` points operators
  here for execution-verified scanning.
- Last verified: 2026-07-21  (active; not archived; **last push 2026-07-16**; 17 commits since the 2026-06-15 stamp).

  **The prompts this skill lifts are unchanged.** `harness/prompts/find_prompt.py`
  appears in a `--since=2026-06-15` commit sweep, but **only** via PR #13 dated
  2026-06-15 itself — the inclusive-boundary artifact of that filter, and the
  same PR the prior pass already reviewed. `recon_prompt.py` does not appear at
  all, and neither does `.claude/skills/vuln-scan/`. The recon pattern and
  memory-safety tiers are intact (10 tier/recon markers still present in
  `find_prompt.py`). *Use `--since=2026-06-16` next pass to avoid re-reviewing
  the boundary commit.*

  **Changed, and reflected in `HARNESS.md`:**
  - **Declared usage marker on outbound agent API requests** (PR #22,
    2026-07-11): `harness/auth.py` stamps `anthropic-cyber-runbook: pipeline`
    plus `User-Agent: cyber-runbook/<version> (claude-cli/<version>)` via
    `_with_usage_marker()`. **First-party callers only** — Bedrock/Vertex
    rewrite the `User-Agent`. Operator-visible, so it belongs in the setup
    pointer rather than only in a sources row.
  - **Detection & response track** (2026-07-16): `dnr-pipeline`, `dnrcanary`
    target, `dnr-hunt` / `dnr-respond` skills. The harness is no longer only
    the find-and-fix loop this group was extracted from.
  - `docs/pipeline.md` gained a full CLI flag tree and batch-sizing guidance;
    a Bedrock guardrail now warns on bare model IDs missing an
    inference-profile prefix (2026-07-06).

## claude-code-security-review (category menu + exclusion rules)

- URL: https://github.com/anthropics/claude-code-security-review
- Probe: `gh repo view anthropics/claude-code-security-review --json pushedAt,isArchived`
- Note: the review-brief category menu, DO-NOT-REPORT exclusions, per-finding
  confidence pass, and `exploit_scenario`/`recommendation` fields originate in
  this action's `/security-review` command.
- Last verified: 2026-07-21  (active; not archived; **still last pushed 2026-02-11** — unchanged for ~5 months, so the category menu, DO-NOT-REPORT exclusions, confidence pass and `exploit_scenario`/`recommendation` fields are stable)

## "Using LLMs to secure source code" (methodology write-up)

- URL: https://claude.com/blog/using-llms-to-secure-source-code
- Probe: `WebFetch` — expect HTTP 200; the find-and-fix loop framing comes from here.
- Last verified: 2026-07-21  (HTTP 200)

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
