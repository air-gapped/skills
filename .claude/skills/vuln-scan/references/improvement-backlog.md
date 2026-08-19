# improvement-backlog — vuln-scan

Carries ceiling findings across `skill-improver` runs. Read in Phase 0;
updated in Phase 6.

## Resolved — 2026-08-19 (Visa §3.2 evidence, §1.4 threat tagging, §2.3 lenses)

- **Six `--focus` specialist lenses (§2.3):** `crypto`, `logic-bug`,
  `access-control`, `deserialization`, `batch-etl`, `iac` are reserved
  names meaning "the whole target through one vulnerability class", not a
  subsystem — reserved only when the name is the entire argument. The lens
  bodies live in the `vuln-area-reviewer` agent definition (one cached
  prefix per wave, not one per spawn; the tail passes the bare name), and
  the transferable part of each is its **cite-or-drop gate**, which is
  stricter than the general reporting bar and replaces it for that pass.
  Step 1 skips a lens with no material in the tree and says so rather than
  spending a reviewer to be told nothing is there. Follows the harness's
  `SPECIALIST_HINTS` set; note it defines six but default-activates five
  (`deserialization` is opt-in there — here all six are opt-in by
  definition, since nothing runs without `--focus`).

- **Focus areas and findings carry their threat rows (§1.4).** Step 1 tags
  each THREAT_MODEL.md-derived focus area with the section-4 `id`s whose
  `surface` names its entry point, and rule 5 turns any unmapped or
  unscanned row into its own focus area (skipped under `--focus`, which
  means "scan only this"; section 5 "Deprioritized" rows stay out). The
  spawn tail carries the rows as a prior to confirm or refute, never as a
  bound on what to report. `threat_ids` is inherited mechanically at
  collate — the reviewer is never asked which threat its finding
  instantiates. `threat_coverage` lists **every** row including the
  zero-finding ones, and Step 5 names those out loud: "found nothing for
  T2, T6" is a result, and it is invisible if only matched rows are
  listed. Mirrors the harness's s3 `threat_id` chunk tagging.

- **`source_ref` / `sink_ref` are structured fields now**, not prose. The
  `vuln-area-reviewer` emits both in its `<finding>` block (equal refs for
  context-free findings, `null` rather than a guess when it cannot name
  one); `VULN-FINDINGS.json` carries them verbatim and `VULN-FINDINGS.md`
  renders a `**Flow:**` line. Step 3a gained a third rule — a finding with
  neither ref is annotated `prefilter: "unproven_flow"` and counted
  separately in `summary`, but is NOT gated: it still gets a confidence
  read. The orchestrator never synthesizes a ref. Adapted (Apache-2.0)
  from `visa/visa-vulnerability-agentic-harness` s4/s5, whose
  `require_evidence` gate *drops* such findings — incompatible with this
  skill's never-drop invariant, so it became an annotation.

## Resolved — 2026-08-16 (Visa-harness review adoptions)

- **Step 3a deterministic pre-filter added** (from
  `visa/visa-vulnerability-agentic-harness` s5, Apache-2.0; verified in its
  source before porting). Hallucinated-path and test/fixture-path findings
  get a mechanical confidence + reason and skip the 3b subagent round;
  committed-credential findings are exempt from the test-path gate; nothing
  is dropped (`prefilter` field + `prefiltered` summary count). Rationale:
  the harness's measured "model ignores the prompt rule ~10%" — a check a
  script can run must never cost a subagent.
- **Call-graph context for reviewers** (§2.2, second wave, same day): when
  `<target-dir>/.codegraph/` exists, the orchestrator runs one
  `codegraph explore` per focus area and appends a trimmed excerpt to that
  reviewer's tail; the agent body instructs "starting point, not evidence
  — trace flows by reading code". Absent index → block omitted, behavior
  unchanged; the skill never indexes the target itself.
  `Bash(codegraph:*)` added to allowed-tools.
- Deferred from the same review (see `.research/visa-harness.md`): nothing
  outstanding. §2.3, §3.2, and §1.4 all landed 2026-08-19 — see above.

## Resolved — 2026-08-16 (operator-directed restructure)

- **Fan-out cache discipline (improvement-patterns 7.3).** The Step 2 review
  brief and Step 3b scoring brief moved verbatim into the
  `vuln-area-reviewer` / `vuln-confidence-scorer` agent definitions
  (`.claude/agents/`, shipped with the plugin). Their bodies are the
  subagents' system prompts — one cached prefix shared across every spawn in
  a wave instead of a full inline brief per spawn — and their `tools:` lists
  make the read-only constraint structural. SKILL.md now carries only the
  per-spawn variable tails plus a read-the-agent-file fallback (also the
  `--single` path). No behavioral change to the briefs themselves.

## Resolved — 2026-07-21 (freshen)

Last of the four security skills sharing the `defending-code-reference-harness`
upstream. All three sources re-probed.

- **The prompts this skill lifts are unchanged.** `find_prompt.py` shows up in a
  `--since=2026-06-15` sweep, but only through PR #13 dated 2026-06-15 itself —
  an **inclusive-boundary artifact** of the filter, and the same PR the prior
  pass already reviewed and logged. `recon_prompt.py` never appears, nor does
  `.claude/skills/vuln-scan/`. Recon pattern and memory-safety tiers intact.
  Recorded the fix in `sources.md`: use `--since=<stamp+1d>` next pass so the
  boundary commit isn't re-investigated.
- **`claude-code-security-review` unchanged for ~5 months** (last push
  2026-02-11) — the category menu, DO-NOT-REPORT exclusions, confidence pass
  and `exploit_scenario`/`recommendation` fields are stable, not merely
  unverified.
- **Two harness changes promoted into `HARNESS.md`, not just logged.** This
  skill owns the setup pointer the other three link to, so operator-visible
  facts belong in the doc itself:
  - the harness now **tags its own API traffic** with a declared usage marker
    (`anthropic-cyber-runbook: pipeline`, first-party callers only — Bedrock/
    Vertex rewrite the `User-Agent`). Someone running this where outbound
    request attribution matters should know before, not after;
  - the harness **is no longer only find-and-fix** — a detection & response
    track (`dnr-pipeline`, `dnrcanary`, `dnr-hunt`, `dnr-respond`) landed
    2026-07-16, outside the seven stages `HARNESS.md` documents.

**Family note.** Across all four skills the pattern held: probe the shared
upstream once, then ask per-skill *which paths under my adapted surface moved*.
Result — `threat-model`: README/docs only; `triage`: upstream `SKILL.md` moved
(opened, benign); `patch`: prompt + docs (benign); `vuln-scan`: nothing beyond
the boundary artifact. A repo-level `pushed_at` check would have flagged all
four identically and told us nothing.


## Open

- **Inline review briefs could move to `references/` (Dim 2).** (carried
  2026-07-05; body grew 294 → 319 lines with the asset/deployment-facts
  additions — blind final scored Dim 2 at 6 for it. Still under the ~350
  revisit threshold, but the margin is shrinking; next content addition
  should trigger the extraction to `references/prompts.md`.)
- **`allowed-tools: Task` vs canonical `Agent` (Dim 8/9).** (carried
  2026-07-05) SKILL.md:17 lists `Task`; body uses `Task`/`subagent_type`.
  Cross-cutting rename shared with the other three defending-code skills —
  see threat-model backlog for the rationale and the one-pass plan.
  Deferred (regression risk + multi-location).

## Resolved — 2026-07-05 (improve, operator feedback)

Applied FEEDBACK-impact-on-asset.md §2 in 2 kept iterations plus one
blind-flagged fix (self 79→81; blind baseline 79, final 77 — the final
credits Dim 5 up to 9 for deployment-facts calibration but docks Dim 2
for the line growth, now an updated Open item).

- **Asset-anchored severity rubric (Dim 9 7→8).** Review-brief SEVERITY
  block: HIGH requires a high-value asset actually present in the
  deployment, never inferred from the vuln class (XSS = what the origin
  protects; file-read = what the filesystem holds; SSRF = what is
  reachable / allowlist influence). Reporting bar unchanged — severity
  decoupled from report-or-not.
- **ASSETS + DEPLOYMENT FACTS into every focus-area agent (Dim 5 8→9).**
  Step 1 parses THREAT_MODEL.md section 2 + section 1 (or collects
  deployment facts from deploy manifests during recon); the brief carries
  both blocks.
- **Blind-flagged Dim 8 fix:** Constraints "No Bash" contradicted the
  read-only Bash whitelist (pre-existing since baseline); now scoped to
  "no Bash beyond the read-only whitelist".

## Resolved — 2026-06-15 (freshen)

- **sources.md re-stamped; harness delta reviewed.** All three refs re-probed
  live (harness + claude-code-security-review repos active; "Using LLMs to
  secure source code" write-up HTTP 200); `Last verified` advanced 2026-05-31 →
  2026-06-15. Harness pushed 2026-05-30 → 2026-06-15 — reviewed delta =
  `untrusted_data` prompt-isolation (PR #13) + sandbox cgroup-probe fix
  (PR #2). PR #13's `find_prompt.py` change only wrapped the dup-bugs list; the
  recon pattern + memory-safety tiers this skill lifts, and `recon_prompt.py`,
  are unchanged, so no mutation beyond the re-stamp. No new Open item.

## Resolved this pass (2026-05-31)

- **Dim 9 staleness cap lifted.** Created `references/sources.md`
  (defending-code reference harness, claude-code-security-review, the
  "Using LLMs to secure source code" write-up) — all probed live,
  `Last verified: 2026-05-31`. Was capped at 6 by the absent-sources.md rule.
