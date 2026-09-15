# Debugging and Portability Reference

Lookup material for diagnosing a misbehaving Makefile and for writing one that
runs outside GNU Make. Loaded on demand; the decision content stays in SKILL.md.

## Table of Contents

- [Debugging Makefile Issues](#debugging-makefile-issues)
- [Portability Notes](#portability-notes)

---

## Debugging Makefile Issues

### Essential Flags

| Flag | Purpose |
|------|---------|
| `make -n` | Dry run (print commands, don't execute) |
| `make -B` | Force rebuild all targets |
| `make -d` | Debug output (why did it rebuild?) |
| `make --trace` | Print each target as it runs |
| `make -p` | Print database (all rules and variables) |
| `make -rR` | Disable built-in rules and variables |

### Diagnostic Functions

```makefile
# Print variable value
$(info DEBUG: CFLAGS = $(CFLAGS))

# Warning (continues execution)
$(warning Something looks wrong)

# Error (stops execution)
$(error FATAL: Missing required variable)
```

### Common Symptoms

| Symptom | Likely Cause |
|---------|--------------|
| "Nothing to be done" | Target exists and is up-to-date, or missing `.PHONY` |
| Rebuilds every time | Missing dependency, or `.PHONY` on file target |
| Breaks with `-j` | Hidden dependencies between targets |
| "missing separator" | Spaces instead of tabs in recipe |
| Variable empty | Wrong expansion timing (`=` vs `:=`) or typo |

## Portability Notes

### GNU Make vs BSD Make

| Feature | GNU Make | BSD Make | POSIX 2024 (Issue 8) |
|---------|----------|----------|----------------------|
| `:=` assignment | Yes | Yes | **No** — use `::=` |
| `::=` / `:::=` assignment | 4.4+ | Yes | Yes |
| `?=` / `+=` assignment | Yes | Yes | Yes |
| `.PHONY` | Yes | Yes | Yes |
| `.WAIT` / `.NOTPARALLEL` | `.NOTPARALLEL` only | Yes | Yes |
| `$(shell ...)` | Yes | `!=` syntax | `!=` assignment only |
| `$(wildcard ...)` | Yes | No | No |
| `.DELETE_ON_ERROR` | Yes | No | No |
| Pattern rules `%` | Yes | Limited | No — reserved, not specified |
| Grouped targets `&:` | 4.3+ | No | No |

**POSIX caught up in 2024.** Issue 8 (IEEE Std 1003.1-2024) standardized
`.PHONY`, `.WAIT`, `.NOTPARALLEL`, and the `::=` / `:::=` / `?=` / `+=` / `!=`
assignment operators — all previously "common extension, not standard". The one
trap: **plain `:=` is still not standard.** Issue 8 spells immediate expansion
`::=`, and the rationale asks implementations to keep `:=` as a compatibility
extension while telling portable makefiles not to rely on it under `.POSIX:`.
Pattern rules stay unspecified — `%` is reserved for possible future use, and
metarules were considered and rejected.

### Shell Portability

- Default `SHELL` is `/bin/sh` (often dash on Debian, not bash)
- Avoid bashisms unless `SHELL := bash` is declared
- `sed -i` differs between GNU and BSD
- `echo -e` is non-portable; use `printf`

