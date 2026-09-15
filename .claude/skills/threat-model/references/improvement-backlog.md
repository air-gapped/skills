# improvement-backlog — threat-model

Carries ceiling findings across `skill-improver` runs. Read in Phase 0;
updated in Phase 6.

## Resolved — 2026-09-15 (least privilege: dropped an unused tool grant)

- **`Agent` was in `allowed-tools` and this skill never spawns a subagent.**
  Verified before removing: zero occurrences of `subagent_type`, `spawn`,
  `delegate`, `in parallel` or "Agent tool" anywhere in `SKILL.md` or any
  `references/` file. The only hits in the whole skill directory are in this
  backlog, discussing the historical `Task` to `Agent` rename. Removed.
- **Why it is worth doing rather than noting.** `allowed-tools` is a permission
  filter, as this family's own skills say. A grant the skill never exercises is
  capability without a caller, and this skill's entire job is reading a target's
  source to enumerate exactly that shape of over-permission. Leaving it would be
  the thing the skill exists to flag.
- **Scope, so this is easy to reverse.** One line removed from frontmatter, no
  body change. If a future revision does delegate — a parallel bootstrap pass
  over a large repo is the obvious candidate — add it back at that point, when
  there is a call site to justify it.
- Found by sweeping the four defending-code skills for consistent
  `untrusted_data` isolation. Three spawn attacker-influenced text and needed
  the guard; this one turned out not to spawn at all, which answered the
  isolation question and raised this one instead.

## Resolved — 2026-09-15

- **`allowed-tools: Task` renamed to the canonical `Agent`** (Dim 8/9), in the
  frontmatter and in every body reference, across all four defending-code
  skills in one pass. The entry's own blocker was "verify `Agent` is a valid
  `allowed-tools`/spawn name in the target version" — that is now settled by
  direct evidence rather than by documentation alone:
  - The official tools reference lists **`Agent`** as the subagent tool and
    shows `Agent(Explore)` as an `allowed-tools` entry. No current doc lists
    `Task`.
  - The installed Claude Code binary (2.1.271) contains a guard reading
    `if (e !== "Agent" && e !== "Task") return;` on the subagent
    permission path, so **both names are still handled** — the rename does not
    strand the skills on this version, and `Task` was not silently dead before
    it either.
  - `allowed-tools` is validated only as "a string or array of strings" with
    no per-name whitelist, so an unrecognised entry would be accepted and
    simply match nothing. That is precisely why the undocumented spelling was
    worth removing: the failure mode is silent.

  The residual risk the entry named — "renaming risks a regression if `Agent`
  isn't accepted" — is therefore inverted. `Agent` is the documented name and
  is accepted; `Task` is the undocumented one.

## Resolved — 2026-08-19 (Visa §1.2 baselines, §1.4 downstream contract)

- **Repo-kind baseline table in interview Q2 (§1.2).** Five kinds — `web-api`,
  `native`, `mobile`, `iac`, `library` (default) — each with recognition
  signals taken from section 1 rather than asked, and a concrete class list.
  Kinds are a **union**, not a choice: a Rust service with a Helm chart is
  three of them. The rule that makes it safe is the harness's: a class with
  a matching surface and no row covering it is a gap to raise; a class with
  no surface here is **dropped silently**, and the table is never shown to
  the owner as a list to answer. Q2 also gained a per-entry-point-kind
  STRIDE mapping (network → all six; IPC → T/I/E; file → T/I/D; CLI and
  deserialization → T/E; else T/I) so the owner is not asked about
  repudiation on a CLI flag. `bootstrap.md` Stage 4 cross-references the
  same table — past-vuln clustering is biased toward what has been found,
  and this is the cheapest correction, but only while it stays a recall aid.

- Section-4 `id` stability now has a named downstream consumer: `/vuln-scan`
  tags focus areas and findings with these ids and reports per-row
  coverage, so renumbering silently re-points every reference. Noted on the
  `id` bullet in `schema.md`.

## Checked, no change — 2026-08-16 (Visa-harness review)

- An external review against `visa/visa-vulnerability-agentic-harness`
  (`.research/visa-harness.md` §1.1) recommended requiring a `controls`
  column and an "every trust boundary is the surface of ≥1 threat"
  coverage rule. **Both already exist** — `schema.md` §4 mandates
  `controls` (Q3 fills it, `[Code-verified]` vs `[Owner-states]`),
  `interview.md` Q4 checks boundary coverage verbatim-name-match, and
  `bootstrap.md` enforces the same invariant at emit time. Do not
  re-propose. Deferred from the same review: repo-kind baseline table for
  the interview backbone (§1.2), threat-id tagging of vuln-scan focus
  areas (§1.4).

## Resolved — 2026-07-21 (freshen)

All four sources re-probed; **nothing in this skill needed correcting.**

- **Shostack four-question framework PDF, OWASP Threat Modeling Cheat Sheet,
  GitHub Security Advisories API docs — all HTTP 200.** The advisory endpoint
  shape the Stage-1 bootstrap swarm depends on is unchanged.
- **The adapted surface is unchanged upstream.** Of 17 harness commits since the
  last stamp, only two touched threat-model paths —
  `.claude/skills/threat-model/README.md` and `docs/threat-model.md` — and
  notably **not** the upstream `SKILL.md`. Both came from the 2026-07-16
  detection-&-response-track commit (cross-references to the new track) and the
  same-day docs pass folding `Status` sections into prose. The
  bootstrap/interview methodology is untouched.
- **Two harness-wide facts recorded here as well**, since they apply to every
  skill that delegates to or derives from this upstream: the new declared usage
  marker on outbound agent API requests (first-party only), and the new
  detection & response track. Full detail lives once in
  `../patch/references/sources.md` rather than being duplicated four times.

**Method note:** for a family of skills sharing one upstream, probe the repo
once and then ask a *per-skill* question — "which paths under my adapted surface
moved?" That distinguishes "the harness changed" from "my skill is stale", which
a repo-level `pushed_at` check cannot.


## Open

## Unblocked — actionable

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
