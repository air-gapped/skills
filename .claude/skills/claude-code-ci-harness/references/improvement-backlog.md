# Improvement Backlog

Open items only. Read before changing the skill.

## Open

- **Subscription-mode live run not done** (Dim 9): blocked on a
  `claude setup-token` token in the secrets file (absent 2026-10-20). Once
  present: smoke + parallel scenarios with `--model sonnet`, then re-check
  `--bare` (expect OAuth refusal) and `--restricted` (`system/init` tools must
  still list `Read`, `Glob`); adopt `--restricted` if it holds.

## Resolved this pass (2026-10-20)

Blind 83 → 84; comparators 3/3 IMPROVED (slight); outcome 0.475 → 0.886 on 8 cases.
- Discard: deleting known-gaps' "Record `claude --version`" line as a duplicate
  of the done condition — it carries the reason (stream-json fields change
  between releases); INTENTIONAL_DETAIL, not deletable.
- Discard: adding "running `claude -p` in a CI job" / "smoke-testing an LLM
  gateway" to `when_to_use` — also matches using Claude Code in CI for real
  work (PR bots); needs a `trigger` measurement before any description change.
- Discard: known-gaps row for stderr `[claude-code:unrecognized_model]` — Δ0,
  no wrong decision traced to it.
- Kept: negative-transfer eval measured (evals/ created, benchmark written).
