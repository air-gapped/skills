# Recipe Patterns

Lookup patterns for writing individual recipes. Pick what you need; none of
these are required in every Makefile.

## Target-Specific Variables

A variable set on a target applies to that target and everything it pulls in,
so one build graph serves several flag sets:

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

## Non-Interactive Guards (CI-Safe)

Anything that blocks on stdin deadlocks in CI, where there is no terminal to
answer it. Gate on an environment variable instead of a prompt:

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

The `guard-%` pattern rule is reusable: depend on `guard-ANYVAR` to require
`ANYVAR` be set.

## Color Output (Respecting NO_COLOR)

Honour `NO_COLOR` (https://no-color.org) so output stays readable when piped to
a file or a CI log that does not interpret escapes:

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
