SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables --no-builtin-rules
.DEFAULT_GOAL := help

.PHONY: scan gitleaks trufflehog lint ruff shellcheck hooks help

scan: gitleaks trufflehog ## Run all secret scanners

gitleaks: ## Scan working tree + history for secrets (gitleaks)
	@command -v gitleaks >/dev/null || { echo "gitleaks not installed"; exit 1; }
	gitleaks git -v --log-opts="--all" .

trufflehog: ## Scan filesystem for verified secrets (trufflehog)
	@command -v trufflehog >/dev/null || { echo "trufflehog not installed"; exit 1; }
	trufflehog filesystem --no-update --results=verified,unknown .

lint: ruff shellcheck ## Run all linters

ruff: ## Lint + format-check Python with ruff
	@command -v ruff >/dev/null || { echo "ruff not installed (uv tool install ruff)"; exit 1; }
	ruff check .
	ruff format --check .

shellcheck: ## Lint all shell scripts
	@command -v shellcheck >/dev/null || { echo "shellcheck not installed (sudo dnf install ShellCheck)"; exit 1; }
	@files=$$(find . -name '*.sh' -not -path './.git/*' -not -path './.research/*'); \
	if [ -n "$$files" ]; then echo $$files | xargs shellcheck --severity=warning; else echo "no .sh files"; fi

hooks: ## Install pre-commit hooks
	pre-commit install
	pre-commit run --all-files

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
