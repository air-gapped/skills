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
- Last verified: 2026-05-31  (active; not archived; last push 2026-05-30)

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
