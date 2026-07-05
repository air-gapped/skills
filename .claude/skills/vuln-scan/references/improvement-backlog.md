# improvement-backlog — vuln-scan

Carries ceiling findings across `skill-improver` runs. Read in Phase 0;
updated in Phase 6.

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
