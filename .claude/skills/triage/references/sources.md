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
- Last verified: 2026-06-15  (active; not archived; last push 2026-06-15; reviewed delta since 2026-05-31 = untrusted_data prompt-isolation, PR #13, + sandbox cgroup-probe fix, PR #2 — PR #13 is a prompt-injection hardening relevant to this skill's verifier/ranker subagent prompts; logged in improvement-backlog.md for an author-judged improve pass)

## CVSS scoring standards (Phase 0 scoring-standard interview option)

- URL: https://www.first.org/cvss/   (v3.1 and v4.0 specifications)
- Probe: `WebFetch` — expect HTTP 200. The Phase-0 interview offers CVSS v3.1 / v4.0
  `severity_label` output; the impact x exploitability HIGH/MEDIUM/LOW is always computed.
- Last verified: 2026-06-15

## OWASP Risk Rating Methodology (Phase 0 scoring-standard option)

- URL: https://owasp.org/www-community/OWASP_Risk_Rating_Methodology
- Probe: `WebFetch` — expect HTTP 200. Likelihood × impact label option.
- Last verified: 2026-06-15

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
