---
name: makefile-best-practices
description: Makefile best practices, patterns, and templates for GNU Make 4.x — dependency graphs, task-runner workflows, parallel-safe recipes, self-documenting help targets, and language-specific patterns (Go, Python, Node, Docker, Helm, POSIX).
when_to_use: Triggers on "write a Makefile", "review Makefile", "make target", "Makefile for Go/Python/Node/Docker/Helm", "fix Makefile", "parallel make", "make -j", "GNU Make", "self-documenting help target", "recursive make", a "missing separator" or "tab vs space" error, or improving any Makefile.
---

# Makefile Best Practices

**Target:** GNU Make 4.x. Covers Make as both a build system (dependency-driven
compilation) and a task runner (developer workflow automation).

**On the `dev` plugin.** Its members are grouped by "general development
tooling", not by a shared workflow — this skill has no dependency on
**`baml-expert`**, **`jinja-expert`**, or
**`transformers-config-tokenizers-expert`**, and none of them on it. Don't hunt
for a pipeline that isn't there. The one overlap worth knowing: a Makefile that
shells out to render templates is still a Makefile question here, but the
template body itself is `jinja-expert`.

## Golden Rules

### 0. Simplicity First

- Start with the minimum viable solution; each target does ONE thing well.
- Default to <=10 focused targets; expand only on explicit request.

### 1. Make is a Dependency Graph, Not a Script

Targets represent outputs; prerequisites represent inputs; recipes transform inputs → outputs. Think graph-first.

```makefile
# WRONG: Script thinking - order-dependent, breaks with -j
build:
	compile src/a.c
	compile src/b.c
	link

# RIGHT: Graph thinking - declares real dependencies
program: a.o b.o
	$(CC) -o $@ $^

%.o: %.c
	$(CC) -c $< -o $@
```

### 2. Correctness Under `make -j` is the Real Bar

If it breaks with parallel builds, it's broken. Always declare real dependencies.

```makefile
# WRONG: Hidden dependency, races under -j
generated.h:
	./generate-header.sh > $@

main.o: main.c  # Missing: generated.h
	$(CC) -c $< -o $@

# RIGHT: Explicit dependency
main.o: main.c generated.h
	$(CC) -c $< -o $@
```

Validate dependency correctness with `make --shuffle=random -j` (GNU Make 4.4+).
Randomizing prerequisite order exposes missing edges that a fixed order hides.

### 3. Phony vs File Targets Drive Behavior

Use `.PHONY` for commands, not for artifacts. Understanding timestamps is 80% of Make proficiency.

```makefile
.PHONY: clean test lint help  # Commands - always run
# Don't mark file-producing targets as phony
```

### 4. Variable Expansion Rules Matter

```makefile
# := immediate (evaluated when defined) - use for $(shell), most cases
FILES := $(shell find src -name '*.c')

# = deferred (evaluated when used) - use when referencing later-defined vars
CFLAGS = $(BASE_FLAGS) $(EXTRA_FLAGS)

# ?= conditional (set only if undefined) - use for user-overridable defaults
PREFIX ?= /usr/local
CC ?= gcc
```

`$(shell ...)` with `=` re-runs the command every time the variable is expanded
— always use `:=` for shell captures unless repeated execution is intentional.

### 5. Pattern Rules + Automatic Variables Enable Elegance

| Variable | Meaning |
|----------|---------|
| `$@` | Target name |
| `$<` | First prerequisite |
| `$^` | All prerequisites (deduped) |
| `$?` | Prerequisites newer than target |
| `$*` | Stem matched by `%` |
| `$(@D)` | Directory part of target |

```makefile
$(BUILD_DIR)/%.o: src/%.c | $(BUILD_DIR)
	@mkdir -p $(@D)
	$(CC) $(CFLAGS) -c $< -o $@
```

## Minimal Skeleton

The essential hygiene directives plus a self-documenting `help` target. For a
production-ready template with verbosity toggle, color output, and a GNU Make
4.0+ compatibility check, see **`references/Makefile.gnumake-template`**.

Each line of the preamble matters:

| Directive | Effect |
|---|---|
| `SHELL := bash` | Use bash (not `/bin/sh`/dash) for richer recipe syntax |
| `.SHELLFLAGS := -eu -o pipefail -c` | Unset vars, errors, and pipe failures all abort the recipe |
| `.DELETE_ON_ERROR:` | Remove the target file on recipe failure — prevents stale half-built artifacts |
| `--warn-undefined-variables` | Catch typos in variable names at parse time |
| `--no-builtin-rules` | Strip implicit rules for faster parsing and explicit semantics |
| `.DEFAULT_GOAL := help` | Bare `make` prints help instead of building the first target |

```makefile
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables --no-builtin-rules
.DEFAULT_GOAL := help

.PHONY: build test clean help

build: ## Build the project
	go build ./...

test: ## Run tests
	go test ./...

clean: ## Remove build artifacts
	rm -rf build/

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
```

### `##@ Section` Headers — Group the Targets

The version above prints a flat alphabetical list. At the 10-20 targets typical
of a real Makefile that is already hard to scan, and it throws away **ordering** —
which is the most important information in any Makefile that encodes a
*procedure* (release pipelines, upgrades, migrations) rather than independent
tasks. `##@` is the convention kubebuilder, operator-sdk and most of the
Kubernetes tooling ecosystem use:

```makefile
help: ## Show this help
	@awk 'BEGIN{FS=":.*?## "} \
	     /^##@/{printf "\n\033[1m%s\033[0m\n", substr($$0,5); next} \
	     /^[a-zA-Z_0-9-]+:.*?## /{printf "  \033[36m%-14s\033[0m %s\n",$$1,$$2}' $(MAKEFILE_LIST)

##@ 1 · Build
build: ## Compile the binary
test:  ## Run tests

##@ 2 · Release
push:  ## Push the image
```

```
1 · Build
  build          Compile the binary
  test           Run tests

2 · Release
  push           Push the image
```

- `substr($$0,5)` strips `##@ `; `next` stops the header line also matching the
  target rule.
- **Numbering the sections makes the help output the procedure**, so a human
  reads top-to-bottom and an agent gets the same ordering with no separate
  runbook to drift out of sync.
- Put a `##@ Help` line before the `help` target itself, or it lands under
  whatever section precedes it.
- Costs one awk clause and comments; works with `.DEFAULT_GOAL := help`.

## Essential Patterns

### Order-Only Prerequisites for Directories

```makefile
# BAD: Rebuilds when ANY file added to dir (timestamp changes)
$(objs): $(BUILD_DIR)

# GOOD: Only checks existence, not timestamp
$(objs): | $(BUILD_DIR)

$(BUILD_DIR):
	mkdir -p $@
```

### Auto-Generated Dependencies (C/C++)

```makefile
CPPFLAGS += -MMD -MP
-include $(deps)
```

Flags: `-MMD` generates `.d` files, `-MP` adds phony targets for headers (prevents errors if deleted).

### Grouped Targets (GNU Make 4.3+)

For rules producing multiple outputs, use `&:` instead of sentinel files:

```makefile
# Modern: grouped target
parser.c parser.h &: parser.y
	bison -d $<

# Legacy: sentinel file pattern
.parser.sentinel: parser.y
	bison -d $<
	touch $@
parser.c parser.h: .parser.sentinel
```

### Target-Specific Variables, CI-Safe Guards, Color Output

See **`references/recipe-patterns.md`** — per-target `CFLAGS`, the reusable
`guard-%` rule for gating destructive targets on an env var instead of a
stdin prompt that deadlocks CI, and `NO_COLOR`-respecting output.

## Anti-Patterns to Avoid

### 1. Recursive Make as Architecture

```makefile
# AVOID: Incomplete dependency graph, poor -j performance
all:
	$(MAKE) -C lib
	$(MAKE) -C src  # Can't see lib's deps!

# PREFER: Non-recursive with includes
include lib/module.mk
include src/module.mk
```

If recursion is necessary, always use `$(MAKE)` not `make` (preserves jobserver).

### 2. Multi-Line Recipe `cd` Bug

```makefile
# WRONG: Each line runs in separate shell
install:
	cd /usr/local
	cp myapp bin/  # Runs in original directory!

# RIGHT: Chain commands
install:
	cd /usr/local && cp myapp bin/

# OR: Use .ONESHELL (changes all recipes)
```

**The same bug bites heredocs, and looks completely different.** A script
inlined into a recipe does not run as a script — each line still goes to its own
shell, so the heredoc body is executed *as shell commands*:

```makefile
# WRONG
gen:
	python3 - <<'PY'
	print("hello")
	PY
```
```
/bin/sh: -c: line 1: syntax error near unexpected token `"hello"'
```

Interactively it is worse than an error: `python3 -` inherits the terminal, finds
no EOF, and the build **hangs** instead of failing. `.ONESHELL:` is not a clean
fix either — recipe tabs are preserved, so the `PY` terminator no longer matches
at column 0 and leaks into the output. Move the script to a sidecar file and call
it, which is also more readable than a heredoc buried in a recipe:

```makefile
# RIGHT
gen:
	python3 scripts/gen.py
```

### 3. Silencing Everything

```makefile
# BAD: CI failures are impossible to debug
build:
	@$(CC) -o $@ $^

# GOOD: Verbosity toggle
build:
	$(Q)$(CC) -o $@ $^
# Run: make V=1 for verbose
```

### 4. Non-Portable Shell Assumptions

```makefile
# BAD: Bashisms without declaring bash
build:
	[[ -f config ]] && source config  # Fails on /bin/sh

# GOOD: Declare shell or use POSIX
SHELL := bash
# OR use POSIX: [ -f config ] && . config
```

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

## Helm & Kubernetes Patterns

For Helm chart and Kubernetes Makefile patterns, consult
**`references/Makefile.helm-k8s`** (452 lines, 47 targets). Key principles:

- **Artifact-first**: define chart identity once (`CHART_NAME`, `VERSION`),
  derive all artifact names — eliminates hardcoding
- **Cluster safety guards**: `verify-context` target that checks
  `kubectl config current-context` against an allowed list; all mutating
  targets depend on it
- **Air-gapped image extraction**: render with all features enabled, grep images
- **Resource ordering**: CRDs first, delete in reverse
- Do NOT set `KUBECTL_EXTERNAL_DIFF` in Makefiles — users have their own diff viewers

## Resources

Reference files are **catalogs of patterns to pick from**, not templates to copy
wholesale. Real-world Makefiles typically use 10-20 targets.
- `Makefile.gnumake-template` - Modern GNU Make skeleton
- `Makefile.go` - Go project patterns
- `Makefile.python` - Python development workflow
- `Makefile.node` - Node.js with npm integration
- `Makefile.docker` - Docker build/push patterns
- `Makefile.helm-k8s` - Helm charts & Kubernetes operations
- `Makefile.portable` - Cross-platform POSIX compatible
- `ci-integration.md` - CI/CD usage patterns
- `recipe-patterns.md` - Target-specific variables, CI guards, color output
