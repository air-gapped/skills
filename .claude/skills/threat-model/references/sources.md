# sources.md — external references for `threat-model` (freshen index)

Freshened: 2026-09-22 — every row probed; all 6 URLs 200 and neither cited repo is archived. This skill cites no versioned framework, so no version drift applies.

One row per external reference this skill depends on. `skill-improver freshen`
probes each URL, classifies staleness, and re-stamps `Last verified:`.

**Freshened: 2026-09-15 — every URL probed and every cited repo checked for archival.** All resolve; none is archived. One URL moved: OWASP's risk-rating methodology now serves from `community.owasp.org`, not `owasp.org/www-community/` — it still returns 200 at the old address, so only the effective URL shows it.

Re-run `/skill-improver freshen threat-model` quarterly or when the threat-model
frameworks or upstream harness change.

## Shostack four-question framework (interview mode)

- URL: https://shostack.org/files/papers/The_Four_Question_Framework.pdf
- Probe: `WebFetch` — expect HTTP 200. Interview mode walks the four questions.
- Last verified: 2026-09-15  (HTTP 200, re-probed)

## OWASP Threat Modeling Cheat Sheet

- URL: https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html
- Probe: `WebFetch` — expect HTTP 200. Cross-reference for STRIDE gap-fill.
- Last verified: 2026-09-15  (HTTP 200, re-probed)

## GitHub Security Advisories API (bootstrap advisory fetcher)

- URL: https://docs.github.com/en/rest/security-advisories
- Probe: `gh api /repos/{owner}/{repo}/security-advisories` (used by the Stage-1 swarm).
- Note: the bootstrap mode's Advisory fetcher relies on this endpoint when the
  target has a GitHub remote and `gh` is on PATH.
- Global advisories: https://docs.github.com/en/rest/security-advisories/global-advisories
  — `GET /advisories`, `affects` = "only return advisories that affect any of
  package or package@version"; `ecosystem` enum (from the 422 error, 2026-10-27):
  rubygems, npm, pip, maven, nuget, composer, go, rust, erlang, actions, pub,
  other, swift. Default `type` is `reviewed`.
- Why the fetcher queries both (2026-10-27): `pallets/jinja` repo advisories = 5;
  global `ecosystem=pip affects=jinja2` = 10, five of them with
  `repository_advisory_url: null` (e.g. CVE-2020-28493, CVE-2019-10906).
  `mackron/dr_libs` repo advisories = 0 while CVE-2026-29022 and CVE-2025-14369
  exist only as `type: unreviewed` global records with no package mapping
  (`vulnerabilities: []`), so no GitHub query by repo or package finds them.

## Worked-example CVEs (schema.md example table, bootstrap.md Stage 2)

- CVE-2026-29022 — https://nvd.nist.gov/vuln/detail/CVE-2026-29022 — dr_libs
  `dr_wav.h` ≤ 0.14.4, heap buffer overflow in
  `drwav__read_smpl_to_metadata_obj()` via crafted WAV (CWE-122/787), fixed in
  commit 8a7258c. Published 2026-03-03.
- CVE-2025-14369 — https://nvd.nist.gov/vuln/detail/CVE-2025-14369 — dr_libs
  `dr_flac`, integer overflow from trusting `totalPCMFrameCount` before sizing a
  buffer; NVD states DoS. Published 2026-01-20.
- Probe: NVD API `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=<id>`.

## defending-code reference harness (provenance)

- URL: https://github.com/anthropics/defending-code-reference-harness
- Probe: `gh repo view anthropics/defending-code-reference-harness --json pushedAt,isArchived`
- Note: this skill is adapted (Apache-2.0) from that repo's `threat-model` skill.
- Last verified: 2026-09-15  (active; not archived; **last push 2026-08-06**, up from 2026-07-16).

  **This skill's adapted surface is unchanged.** Only two threat-model paths
  moved upstream in the window — `.claude/skills/threat-model/README.md` and
  `docs/threat-model.md` — and **not** the upstream `SKILL.md`. Both changes
  came from the 2026-07-16 detection-&-response-track commit (adding the new
  track's cross-references) and the same-day docs pass that folded per-skill
  `Status` sections into prose. The bootstrap/interview methodology this skill
  adapts is untouched.

  **Harness-wide deltas that apply here too** (shared upstream with `patch`,
  `triage`, `vuln-scan` — full detail in `../patch/references/sources.md`):
  outbound agent API requests now carry a declared usage marker
  (`anthropic-cyber-runbook: pipeline` + a `cyber-runbook/<version>` User-Agent,
  first-party callers only — Bedrock/Vertex rewrite it); and the harness gained
  a **detection & response track** (`dnr-pipeline`, `dnrcanary` target, skills),
  so it is no longer only scan→triage→patch.

---

## Markers

- `<!-- ignore-freshen -->` on a row excludes it from `freshen` probes.
- `Pinned: <ref>` under a row tells freshen not to advance past that ref.
