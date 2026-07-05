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

## Resolved — 2026-07-05 (improve, operator feedback)

Applied FEEDBACK-impact-on-asset.md §3 in 4 kept iterations (self 84→87,
one metric-neutral keep; blind baseline 82, final 84 — the final's Dim 10
now cites severity-gating open questions as differentiating value).

- **Impact binding to the named asset (Dim 9 8→9).** schema.md scoring
  guide: every section-4 impact must be justifiable in one clause against
  its asset cell + environment; absent-asset threats cap at `low` and move
  to section 5 with "asset not present".
- **Asset finder answers "what does this actually gate?" (Dim 5 8→9).**
  Bootstrap swarm brief requires stating what is behind each candidate
  asset; empty gates get sensitivity `low` with the emptiness stated.
- **Severity-gating questions first-class (Dim 8 8→9).** schema section 6
  + bootstrap Stage 5: gating questions name threat id(s) + direction
  (`— gates T4: low→high if a secret is mounted`); declared as the input
  `/triage` Phase 0d ingests. Both ends of the wire match.
- **Impact companion to the untrusted-input default.** Stage 3c: the
  externally-reachable-is-untrusted default is a reachability rule, not an
  impact rule; stateless/anonymous/secret-less/single-tenant caps
  origin-XSS / auth-bypass / disclosure threats at `low`.

The Open item below is carried (2026-07-05).

## Resolved — 2026-06-15 (freshen)

- **sources.md re-stamped; harness delta reviewed.** All four refs re-probed
  live (Shostack PDF, OWASP threat-modeling cheat sheet, GitHub
  security-advisories API docs — HTTP 200; harness repo active); `Last verified`
  advanced 2026-05-31 → 2026-06-15. Harness pushed 2026-05-30 → 2026-06-15 —
  reviewed delta = `untrusted_data` prompt-isolation (PR #13, find/grade/judge/
  patch/report prompts) + sandbox cgroup-probe fix (PR #2). Neither overlaps
  this skill's adapted bootstrap/interview content; no mutation beyond the
  re-stamp. No new Open item.

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
