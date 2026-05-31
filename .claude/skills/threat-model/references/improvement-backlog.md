# improvement-backlog — threat-model

Carries ceiling findings across `skill-improver` runs. Read in Phase 0;
updated in Phase 6.

## Open

- **`allowed-tools: Task` vs canonical `Agent` (Dim 8/9).** SKILL.md:26
  permits `Bash(... )` + `Task`; the body says "spawn a Task subagent" /
  `subagent_type` throughout. Blind scorers flagged `Agent` as the canonical
  tool name since Claude Code v2.1.63 (`Task` still works as an alias). NOT
  applied this pass: it's a cross-cutting rename (frontmatter + ~every body
  reference) shared across all four defending-code skills, and the source
  (anthropics/defending-code-reference-harness, active) deliberately uses
  `Task`, so renaming risks a regression if `Agent` isn't accepted in the
  operator's CC version. Verify `Agent` is a valid `allowed-tools`/spawn name
  in the target version, then rename consistently across all 4 skills in one
  pass.

## Resolved this pass (2026-05-31)

- **Dim 9 staleness cap lifted.** Created `references/sources.md` (Shostack
  four-question framework, OWASP threat-modeling cheat sheet, GitHub
  security-advisories API, defending-code reference harness) — all probed
  live, `Last verified: 2026-05-31`. Dim 9 was mechanically capped at 6 by the
  absent-sources.md rule; now scored on content accuracy.
- **Dim 3 second-person → imperative.** Converted 7 instructional slips in
  SKILL.md (context-durability notes, schema-read instruction, authorization
  framing) to imperative/third-person. Remaining `you` is owner-dialogue and
  the "if the user asks you to" idiom (legitimate).
- **Dim 8 consistency.** README.md intro said "Two modes" while the skill has
  three; corrected to "Three modes" naming bootstrap-then-interview.
