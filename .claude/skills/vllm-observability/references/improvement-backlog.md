# Improvement Backlog — vllm-observability

Work-not-done log from skill-improver passes. Open = attempted-but-not-applied or deferred verification; not a wishlist.

## Open

- **Re-probe non-GitHub sources online** (Dim 9) — `references/sources.md` rows for the production metrics doc (docs.vllm.ai), ebpfchirp incident article, DCGM dashboard 15117, and the canonical design doc were NOT re-probed this pass (probe budget spent on the accuracy-gating GitHub refs: PRs #24245/#25392, loggers.py, examples/observability tree). They remain stamped 2026-04-24 (34 days old, within the 90-day no-cap window). Verify each URL resolves and content matches on the next freshen pass.

## Resolved this pass (2026-05-28)

- Deleted editorializing sentence "This table is the skill's single most valuable line. Everything else is how to read the underlying metrics." in `SKILL.md` core-diagnostic section (Dim 6) — the queue-depth x TPOT table stands on its own; no instruction lost.
- Trimmed PR-number/date forensics out of the frontmatter `description` block scalar in `SKILL.md` (Dim 1, 644 -> 627 chars; combined desc+when_to_use 1389, under the 1536 listing cap). Kept the `gpu_->kv_ rename saga` trigger keyword; the PR #24245/#25392 forensics still live verbatim in the Version notes section.
- Restamped 4 re-confirmed GitHub source rows in `references/sources.md` to 2026-05-28 (PR #24245 MERGED 2025-09-16; PR #25392 CLOSED-unmerged 2025-09-23; loggers.py emits all cited names with `gpu_cache_usage_perc` absent; examples/observability tree intact) — Dim 9 staleness reset on the version-sensitive refs.
- Annotated the `references/sources.md` "Next freshen triggers" bullet: observed current latest release is v0.21.0 (2026-05-15), still below the ">v0.22" re-probe trigger, so no version-drift mutation is due.
- Restamped the `references/metrics-catalog.md` "Last verified" header from 2026-04-24 to 2026-05-28 with a re-probe note.

## Process note

An intermittent tool-output channel outage struck twice this session (Bash/Read returning empty or stale results). The first APPLY attempt produced a StructuredOutput based on stale file-state context that claimed edits which had NOT landed (notably a "stray fence removal" that was never real — all files have balanced fence parity, confirming the recon's retraction of the earlier hallucinated fence defect). That output is superseded. The edits recorded above are the ones whose Edit calls returned explicit success-with-integrity-check confirmations against freshly-Read file content.
