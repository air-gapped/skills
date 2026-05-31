# sources.md — external references for `triage` (freshen index)

One row per external reference this skill depends on. `skill-improver freshen`
probes each URL, classifies staleness, and re-stamps `Last verified:`.

Re-run `/skill-improver freshen triage` quarterly or when the scoring standards
or upstream harness change.

## defending-code reference harness (provenance + ingestible pipeline output)

- URL: https://github.com/anthropics/defending-code-reference-harness
- Probe: `gh repo view anthropics/defending-code-reference-harness --json pushedAt,isArchived`
- Note: adapted (Apache-2.0) from that repo's `triage` skill; Phase 1 ingests
  its pipeline `results/<target>/<ts>/` output. `../vuln-scan/HARNESS.md` points here.
- Last verified: 2026-05-31  (active; not archived; last push 2026-05-30)

## CVSS scoring standards (Phase 0 scoring-standard interview option)

- URL: https://www.first.org/cvss/   (v3.1 and v4.0 specifications)
- Probe: `WebFetch` — expect HTTP 200. The Phase-0 interview offers CVSS v3.1 / v4.0
  `severity_label` output; the precondition-derived HIGH/MEDIUM/LOW is always computed.
- Last verified: 2026-05-31

## OWASP Risk Rating Methodology (Phase 0 scoring-standard option)

- URL: https://owasp.org/www-community/OWASP_Risk_Rating_Methodology
- Probe: `WebFetch` — expect HTTP 200. Likelihood × impact label option.
- Last verified: 2026-05-31

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
