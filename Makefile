SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables --no-builtin-rules
.DEFAULT_GOAL := help

.PHONY: scan gitleaks trufflehog hooks help

scan: gitleaks trufflehog ## Run all secret scanners

gitleaks: ## Scan working tree + history for secrets (gitleaks)
	@command -v gitleaks >/dev/null || { echo "gitleaks not installed"; exit 1; }
	gitleaks git -v --log-opts="--all" .

trufflehog: ## Scan filesystem for verified secrets (trufflehog)
	@command -v trufflehog >/dev/null || { echo "trufflehog not installed"; exit 1; }
	trufflehog filesystem --no-update --results=verified,unknown .

hooks: ## Install pre-commit hooks
	pre-commit install
	pre-commit run --all-files

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
