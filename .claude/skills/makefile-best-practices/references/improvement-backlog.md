# Improvement Backlog — makefile-best-practices

## Open

- **Extract Color-Output + Target-Specific-Variables blocks to references** (Dim 2) — SKILL.md L184-235 (~45 inline lines). SKILL.md is 374 lines, above the lean <300 band. Not applied in one iteration: a clean move needs a new `references/patterns.md` (or coherent host file) plus pointers plus re-verification of the target file — a multi-step restructure, not a single atomic edit. Deferred to keep the change atomic and avoid muddying ci-integration.md's CI focus.

## Resolved this pass

- Created `references/sources.md` with a dated 5-row per-URL table (GNU Make manual, NEWS, FTP release listing, POSIX make, no-color.org), all stamped 2026-05-28 — lifts the Dim 9 staleness cap (absent sources.md was capping Dim 9 at 6).
- Fixed the duplicate-`build`-target defect in `Makefile.gnumake-template`: `BUILD_DIR` default was `build`, so the order-only directory rule `$(BUILD_DIR):` collided with the phony `build` target ("overriding recipe for target 'build'" warnings on `make -n help`). Changed default to `out` and added a guard comment; template now parses warning-free (Dim 7).
- Rewrote Golden Rule 0's scope-confirmation meta-advice ("confirm scope with user first / add them without pushback") as a terse standing rule ("Default to <=10 focused targets; expand only on explicit request") — removes borderline agent-steering (Dim 3).
- Added "recursive make", "tab vs space", and "recursive make" symptom trigger phrases to `when_to_use` (Dim 1), within the 1,536-char listing budget.

## Discarded this pass (rule-ceiling / would-degrade)

- **Delete duplicate -j-correctness from Anti-Patterns** (Dim 6, H4) — discarded. The three -j mentions are not pure duplicates: Golden Rule 2 is canonical (declare real deps + `--shuffle` validation), the recursive-make anti-pattern carries the *distinct* jobserver/parallelism point, and the symptom-table row is a compact diagnostic lookup. No clean one-line deletion exists without losing information.
