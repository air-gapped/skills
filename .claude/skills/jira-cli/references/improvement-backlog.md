# Improvement backlog — jira-cli

Carries ceiling findings across skill-improver runs. Read in Phase 0; updated in Phase 6.

## Open

- **Pitfalls ↔ troubleshooting.md overlap (Dim 6).** The 12-item "Critical pitfalls"
  list in `SKILL.md` (the always-loaded layer) restates several points that also live,
  symptom-keyed, in `references/troubleshooting.md`, and a few notes in the command-map
  table. Both blind scorers flagged this as the sole drag on Simplicity (8 vs 9).
  - File-set: `SKILL.md` "Critical pitfalls" section + `references/troubleshooting.md`.
  - Why not applied: collapsing the inline pitfalls into one-line pointers to
    troubleshooting.md would force a reference-open for the highest-value operational
    gotchas (the `--no-input` hang, value-guessing, append-vs-replace) at the moment
    they matter most. That trades hot-path, trigger-time value for a cosmetic +1 — a
    progressive-disclosure layering decision that needs author judgment, not a
    mechanical dedup. Left intentionally redundant. Revisit only if SKILL.md length
    becomes a real budget problem.

- **Live-verification gaps (residual from the 2026-06-07 completion pass).** Three
  commands could not be exercised on the test instance; verify on a suitable instance
  in a future run.
  - `epic add` / `epic remove` (the `epic` subcommand): not cleanly run — `epic create`
    fails non-interactively on the test instance (next-gen), so there was no valid epic
    to add to *via that subcommand*. The underlying `-P/--parent` linking IS verified.
    Retest on a classic (company-managed) project, or against an epic made with
    `issue create -tEpic`.
  - `sprint add` / `sprint close`: the test board has no sprint and the CLI can't create
    one. Retest on a project/board with an active sprint. (`sprint list` flags are
    verified.)
  - `init`: not run — would overwrite the live config. Verify against a scratch config
    via `JIRA_CONFIG_FILE=/tmp/...` so the real `~/.config/.jira/.config.yml` is untouched.

## Resolved this pass

(2026-06-07, improve + freshen run — baseline self 83 / blind 86 → final self 90 / blind 91)

- **Dim 1 (Trigger Precision) 7→9.** Combined `description`+`when_to_use` was 1737 chars,
  truncating the `NOT for the Jira REST API / web UI / Confluence` false-positive guards
  past the 1536 listing cutoff. Trimmed to 1435 (description 648, when_to_use 786); the
  exclusions now survive. Also dropped the lingering `ankitpokhrel` token from the
  trigger surface.
- **Dim 3 (Writing Style) 6/7→9/10.** Converted 9 second-person constructs in the body
  ("your project keys", "you get gibberish", "wants your password", "if you pass both",
  etc.) to imperative/declarative. Body now has zero second-person occurrences.
- **Dim 6 (Simplicity) 8→9 (self).** Collapsed the 8-bullet output-flag list in the
  "automation contract" section (verbatim duplication of `commands.md`) into 4 bullets,
  grouping the `--plain` modifiers under `--plain` where they actually apply — tighter
  and more accurate, no flag names lost.
- **Dim 9 (Domain Accuracy) — live-verification corrections.** Ran a full read + write
  round-trip against a real (team-managed) Jira Cloud instance (2026-06-07), exercising
  the entire command surface except `sprint add`/`close` (no sprint on the board) and
  `init` (destructive). Two errors `--help` review and both blind scorers missed:
  (1) `project list`/`board list`/`release list` take **no output flags** (`--plain`/
  `--raw`/`--columns` error) — fixed 5 usages in `SKILL.md`/`config-auth.md` + the
  `commands.md` claim; (2) **[later retracted — see below]** a claim that `epic create
  --no-input` prompts/fails on next-gen.
  Everything else (assign/comment/worklog/watch/link/unlink/clone/move/delete, the
  `--label` append-vs-minus-remove asymmetry, all `--raw` jq paths) verified correct
  as written.
- **Source review (2026-06-07) — retraction + refinements.** Reading the local clone
  caught a self-inflicted error: the earlier "`epic create` prompts `Epic Key` / fails
  on next-gen" claim was wrong. `epic create -n -s [-b] --no-input` works on next-gen
  (verified live, CPG-20/21); the `? Epic Key` EOF in the original run came from a
  downstream `epic add` with an empty key (the real `epic create` issue was just that it
  has no `--raw` flag). Corrected SKILL.md pitfall 5, commands.md, troubleshooting.md,
  known-issues.md, sources.md. Also from source: #935 is an `edit`-only asymmetry
  (`create`/`comment` convert); `--custom` requires fields configured under
  `issue.fields.custom`; #621 (body drop) is fixed on v1.7.0; #948/#984 stems from
  `StdinHasData()` meaning "stdin not a TTY".
- **Upstream issue sweep — known bugs folded in (2026-06-07).** Searched the repo's
  issues/discussions (earlier runs only checked the release tag). Added verified,
  in-scope gotchas with citations: pagination `startAt` removal on Cloud v1.7.0 (#898,
  also confirmed live — corrected 4 files), `epic create --no-input` fragility +
  root-cause/workarounds (#621), the `--no-input` socket/subprocess stdin hang with the
  `</dev/null` fix (#948/#984), and two ADF rendering bugs (#941 `___`, #974 URL-in-code).
  Open feature requests and non-reproducible reports were intentionally not folded in.
- **Freshen: all fresh, no mutations.** v1.7.0 confirmed still the latest release
  (`gh release list` → Latest, 2025-08-31); installed binary = 1.7.0; `sources.md` rows
  dated 2026-06-07 (0 days old, no staleness cap). Skill authored same day, so no drift
  to apply.
