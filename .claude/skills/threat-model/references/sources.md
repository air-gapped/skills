# sources.md — external references for `threat-model` (freshen index)

One row per external reference this skill depends on. `skill-improver freshen`
probes each URL, classifies staleness, and re-stamps `Last verified:`.

Re-run `/skill-improver freshen threat-model` quarterly or when the threat-model
frameworks or upstream harness change.

## Shostack four-question framework (interview mode)

- URL: https://shostack.org/files/papers/The_Four_Question_Framework.pdf
- Probe: `WebFetch` — expect HTTP 200. Interview mode walks the four questions.
- Last verified: 2026-05-31  (HTTP 200)

## OWASP Threat Modeling Cheat Sheet

- URL: https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html
- Probe: `WebFetch` — expect HTTP 200. Cross-reference for STRIDE gap-fill.
- Last verified: 2026-05-31  (HTTP 200)

## GitHub Security Advisories API (bootstrap advisory fetcher)

- URL: https://docs.github.com/en/rest/security-advisories
- Probe: `gh api /repos/{owner}/{repo}/security-advisories` (used by the Stage-1 swarm).
- Note: the bootstrap mode's Advisory fetcher relies on this endpoint when the
  target has a GitHub remote and `gh` is on PATH.
- Last verified: 2026-05-31

## defending-code reference harness (provenance)

- URL: https://github.com/anthropics/defending-code-reference-harness
- Probe: `gh repo view anthropics/defending-code-reference-harness --json pushedAt,isArchived`
- Note: this skill is adapted (Apache-2.0) from that repo's `threat-model` skill.
- Last verified: 2026-05-31  (active; not archived; last push 2026-05-30)

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
