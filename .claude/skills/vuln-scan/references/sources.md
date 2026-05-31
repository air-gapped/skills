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
- Last verified: 2026-05-31  (active; not archived; last push 2026-05-30)

## claude-code-security-review (category menu + exclusion rules)

- URL: https://github.com/anthropics/claude-code-security-review
- Probe: `gh repo view anthropics/claude-code-security-review --json pushedAt,isArchived`
- Note: the review-brief category menu, DO-NOT-REPORT exclusions, per-finding
  confidence pass, and `exploit_scenario`/`recommendation` fields originate in
  this action's `/security-review` command.
- Last verified: 2026-05-31  (active; not archived)

## "Using LLMs to secure source code" (methodology write-up)

- URL: https://claude.com/blog/using-llms-to-secure-source-code
- Probe: `WebFetch` — expect HTTP 200; the find-and-fix loop framing comes from here.
- Last verified: 2026-05-31  (HTTP 200)

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
