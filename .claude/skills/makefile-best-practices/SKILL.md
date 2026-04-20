---
name: makefile-best-practices
description: Makefile best practices, patterns, and templates for GNU Make 4.x — dependency graphs, task-runner workflows, parallel-safe recipes, self-documenting help targets, and language-specific patterns (Go, Python, Node, Docker, Helm, POSIX).
when_to_use: Triggers on "write a Makefile", "review Makefile", "make target", "Makefile for Go/Python/Node/Docker/Helm", "fix Makefile", "parallel make", "make -j", "GNU Make", "self-documenting help target", a "missing separator" error, or improving any Makefile.
---

# Makefile Best Practices

**Target:** GNU Make 4.x. Covers Make as both a build system (dependency-driven
compilation) and a task runner (developer workflow automation).

## Golden Rules

### 0. Simplicity First

When creating Makefiles:
- Start with the minimum viable solution
- Each target should do ONE thing well
- If creating more than 10 targets or 100 lines, confirm scope with user first
- BUT: if user explicitly requests more targets, add them without pushback

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

### Target-Specific Variables

```makefile
# Different flags for different targets
debug: CFLAGS += -g -O0 -DDEBUG
debug: all

release: CFLAGS += -O3 -DNDEBUG
release: all

test: CFLAGS += -DTEST --coverage
test: $(target)
	./run-tests
```

### Non-Interactive Guards (CI-Safe)

```makefile
# BAD: Breaks in CI
confirm:
	@read -p "Are you sure? [y/N] " ans && [ "$$ans" = y ]

# GOOD: Environment variable guard
deploy: guard-CONFIRM ## Deploy (requires CONFIRM=1)
	./deploy.sh

guard-%:
	@if [ -z '${${*}}' ]; then \
		echo "ERROR: Variable $* is not set"; \
		exit 1; \
	fi
```

### Color Output (Respecting NO_COLOR)

```makefile
ifdef NO_COLOR
  CYAN :=
  GREEN :=
  RESET :=
else
  CYAN := \033[36m
  GREEN := \033[32m
  RESET := \033[0m
endif

.PHONY: build
build:
	@echo "$(CYAN)Building...$(RESET)"
	$(MAKE) all
	@echo "$(GREEN)Done$(RESET)"
```

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

| Feature | GNU Make | BSD Make |
|---------|----------|----------|
| `:=` assignment | Yes | Yes |
| `?=` assignment | Yes | Yes |
| `.PHONY` | Yes | Yes |
| `$(shell ...)` | Yes | `!=` syntax |
| `$(wildcard ...)` | Yes | No |
| `.DELETE_ON_ERROR` | Yes | No |
| Pattern rules `%` | Yes | Limited |
| Grouped targets `&:` | 4.3+ | No |

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
