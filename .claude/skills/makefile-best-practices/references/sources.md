# Sources

External references underpinning this skill's GNU Make claims. Re-verify the
listed facts and stamp the date when you re-confirm a row online.

| Source | URL | Last verified | Notes |
|---|---|---|---|
| GNU Make Manual | https://www.gnu.org/software/make/manual/make.html | 2026-07-21 | Authoritative reference for variables, automatic variables, pattern rules, `.PHONY`, `.DELETE_ON_ERROR`, order-only prerequisites, grouped targets. |
| GNU Make NEWS (release notes) | https://cgit.git.savannah.gnu.org/cgit/make.git/tree/NEWS | 2026-07-21 | Host moved: `git.savannah.gnu.org/cgit/…` now 301s to `cgit.git.savannah.gnu.org/cgit/…`; URL updated. Per-version feature gates: `--shuffle` added in 4.4, grouped targets `&:` added in 4.3, `.RECIPEPREFIX` added in 3.82. Newest NEWS entry is still **4.4.90 (26 Feb 2023)** — a prerelease toward 4.5 that never shipped, so do not read it as a release. |
| GNU Make FTP release listing | https://ftp.gnu.org/gnu/make/ | 2026-07-21 | Latest stable release is still **make-4.4.1 (Feb 2023)** — no new tarball in 3.5 years, and no 4.5 or 5.x. "GNU Make 4.x" targeting remains current; the silence is upstream stability, not a failed probe. |
| POSIX `make` — **Issue 8 (2024), current** | https://pubs.opengroup.org/onlinepubs/9799919799/utilities/make.html | 2026-07-21 | IEEE Std 1003.1-2024. Standardizes `.PHONY`, `.WAIT`, `.NOTPARALLEL`, `.POSIX`, and the `::=` / `:::=` / `?=` / `+=` / `!=` operators. **Plain `:=` is still NOT standard** (`::=` is the specified spelling); pattern rules `%` remain unspecified and were explicitly considered-and-rejected, with `%` reserved. |
| POSIX `make` — Issue 7 (2018), superseded | https://pubs.opengroup.org/onlinepubs/9699919799/utilities/make.html | 2026-07-21 | Still live (200) but superseded. This skill cited Issue 7 through 2026-05-28, which predates the `.PHONY` standardization. Kept only so the two edition URLs are not confused: `9699919799` = Issue 7, `9799919799` = Issue 8 — one digit apart. |
| NO_COLOR convention | https://no-color.org/ | 2026-07-21 | Convention behind the color-output `ifdef NO_COLOR` guard: any *presence* of the variable disables color, regardless of value. Verified via search, not direct fetch — `no-color.org` failed DNS resolution (`ESERVFAIL`) from this sandbox on 2026-07-21 while the site is demonstrably live and maintained (registry entries added 2026-03-10). Treat a resolution failure here as a local-network artifact, not a dead domain. |
