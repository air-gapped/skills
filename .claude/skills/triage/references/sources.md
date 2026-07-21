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
- Last verified: 2026-07-21  (active; not archived; **last push 2026-07-16**; 17 commits since the 2026-06-15 stamp).

  **The ingest contract this skill depends on is unchanged.** `docs/triage.md`
  still documents `results/<target>/<timestamp>/` as the pipeline input and
  `TRIAGE.md` + `TRIAGE.json` as the outputs — matching this skill's Phase 1
  ingest (`SKILL.md:41`) and its `TRIAGE.json`/`TRIAGE.md` writers
  (`SKILL.md:117`, `SKILL.md:649`).

  Three triage paths moved upstream — `.claude/skills/triage/README.md`,
  `.claude/skills/triage/SKILL.md`, `docs/triage.md`. **Unlike the
  `threat-model` sibling, the upstream `SKILL.md` is among them**, so it was
  checked rather than assumed: both touching commits are the 2026-07-16
  detection-&-response-track addition and the same-day docs pass folding
  per-skill `Status` sections into prose. Neither changes the triage
  methodology or the output schema.

  **Harness-wide deltas that apply here too** (shared upstream with `patch`,
  `threat-model`, `vuln-scan` — full detail in
  `../patch/references/sources.md`): a declared usage marker is now stamped on
  outbound agent API requests (`anthropic-cyber-runbook: pipeline`, first-party
  callers only); and the harness gained a **detection & response track**
  (`dnr-pipeline`, `dnrcanary`), so it is no longer only scan→triage→patch.

## CVSS scoring standards (Phase 0 scoring-standard interview option)

- URL: https://www.first.org/cvss/   (v3.1 and v4.0 specifications)
- Probe: `WebFetch` — expect HTTP 200. The Phase-0 interview offers CVSS v3.1 / v4.0
  `severity_label` output; the impact x exploitability HIGH/MEDIUM/LOW is always computed.
- Last verified: 2026-07-21  (HTTP 200; v3.1 and v4.0 both still published)

## OWASP Risk Rating Methodology (Phase 0 scoring-standard option)

- URL: https://owasp.org/www-community/OWASP_Risk_Rating_Methodology
- Probe: `WebFetch` — expect HTTP 200. Likelihood × impact label option.
- Last verified: 2026-07-21  (HTTP 200)

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
