# Improvement Backlog — makefile-best-practices

## Open

- **Extract Color-Output + Target-Specific-Variables blocks to references** (Dim 2) — SKILL.md L184-235 (~45 inline lines). SKILL.md is 374 lines, above the lean <300 band. Not applied in one iteration: a clean move needs a new `references/patterns.md` (or coherent host file) plus pointers plus re-verification of the target file — a multi-step restructure, not a single atomic edit. Deferred to keep the change atomic and avoid muddying ci-integration.md's CI focus.

## Resolved — 2026-07-21 (freshen)

Five refs probed. Two upstream non-events, one URL move, and one genuine
standards change that the skill's portability advice predated.

- **POSIX `make` moved to Issue 8 (IEEE Std 1003.1-2024) and the skill was
  citing Issue 7 (2018).** Issue 8 standardizes `.PHONY`, `.WAIT`,
  `.NOTPARALLEL`, `.POSIX`, and the `::=` / `:::=` / `?=` / `+=` / `!=`
  operators — all of which the skill's GNU-vs-BSD framing implicitly treated as
  extensions. Added a third column to the portability table plus a note. **The
  trap worth naming: plain `:=` is still not standard** — Issue 8 spells
  immediate expansion `::=` and asks implementations to keep `:=` only as a
  compatibility extension. Pattern rules `%` remain unspecified: metarules were
  considered and explicitly rejected, with `%` reserved for future use.
  The two edition URLs differ by one digit (`9699919799` = 7, `9799919799` = 8),
  so both rows are kept and labelled rather than one being silently swapped.
- **GNU Make is still 4.4.1 (Feb 2023)** — no tarball in 3.5 years, no 4.5, no
  5.x. The row now frames this as upstream stability so a future pass does not
  read the absence as a failed probe. Relatedly, the newest NEWS entry is
  **4.4.90 (26 Feb 2023)**, a prerelease toward a 4.5 that never shipped — it is
  not a release and must not be quoted as one.
- **NEWS URL moved.** `git.savannah.gnu.org/cgit/make.git/…` 301s to
  `cgit.git.savannah.gnu.org/cgit/make.git/…`; row updated to the destination.
- **`no-color.org` failed DNS (`ESERVFAIL`) from this sandbox** via both curl and
  WebFetch, while search evidence shows the site live and its registry taking
  entries as recently as 2026-03-10. Verified by search and annotated as such —
  a resolution failure here is a local-network artifact, not a dead domain, and
  the row should not be marked `broken` on that basis next pass.

## Resolved — 2026-05-28

- Created `references/sources.md` with a dated 5-row per-URL table (GNU Make manual, NEWS, FTP release listing, POSIX make, no-color.org), all stamped 2026-05-28 — lifts the Dim 9 staleness cap (absent sources.md was capping Dim 9 at 6).
- Fixed the duplicate-`build`-target defect in `Makefile.gnumake-template`: `BUILD_DIR` default was `build`, so the order-only directory rule `$(BUILD_DIR):` collided with the phony `build` target ("overriding recipe for target 'build'" warnings on `make -n help`). Changed default to `out` and added a guard comment; template now parses warning-free (Dim 7).
- Rewrote Golden Rule 0's scope-confirmation meta-advice ("confirm scope with user first / add them without pushback") as a terse standing rule ("Default to <=10 focused targets; expand only on explicit request") — removes borderline agent-steering (Dim 3).
- Added "recursive make", "tab vs space", and "recursive make" symptom trigger phrases to `when_to_use` (Dim 1), within the 1,536-char listing budget.

## Discarded — 2026-05-28 (rule-ceiling / would-degrade)

- **Delete duplicate -j-correctness from Anti-Patterns** (Dim 6, H4) — discarded. The three -j mentions are not pure duplicates: Golden Rule 2 is canonical (declare real deps + `--shuffle` validation), the recursive-make anti-pattern carries the *distinct* jobserver/parallelism point, and the symptom-table row is a compact diagnostic lookup. No clean one-line deletion exists without losing information.
