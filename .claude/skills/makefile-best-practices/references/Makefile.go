# =============================================================================
# Go Project Makefile
# =============================================================================
# Best practices for Go projects with quality gates.
# =============================================================================

.DEFAULT_GOAL := help
.DELETE_ON_ERROR:

# =============================================================================
# Configuration
# =============================================================================

# Project
BINARY_NAME := myapp
MAIN_PACKAGE := ./cmd/$(BINARY_NAME)

# Directories
BUILD_DIR := bin
DIST_DIR := dist

# Go configuration
GOCMD := go
GOTEST := $(GOCMD) test
GOBUILD := $(GOCMD) build
GOMOD := $(GOCMD) mod

# Version from git
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
GIT_HASH := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BUILD_TIME := $(shell date -u '+%Y-%m-%dT%H:%M:%SZ')

# Linker flags for version injection
LDFLAGS := -ldflags "\
  -X main.Version=$(VERSION) \
  -X main.GitHash=$(GIT_HASH) \
  -X main.BuildTime=$(BUILD_TIME)"

# =============================================================================
# Phony Targets
# =============================================================================

.PHONY: help build run test test-race test-cover lint fmt vet tidy \
        audit clean install dev docker-build docker-push release

# =============================================================================
# Help
# =============================================================================

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Development
# =============================================================================

build: ## Build binary
	@mkdir -p $(BUILD_DIR)
	$(GOBUILD) $(LDFLAGS) -o $(BUILD_DIR)/$(BINARY_NAME) $(MAIN_PACKAGE)
	@echo "Built: $(BUILD_DIR)/$(BINARY_NAME)"

run: build ## Build and run
	./$(BUILD_DIR)/$(BINARY_NAME)

dev: ## Run with hot reload (requires air)
	@command -v air >/dev/null 2>&1 || (echo "Installing air..." && go install github.com/cosmtrek/air@latest)
	air --build.cmd "make build" --build.bin "$(BUILD_DIR)/$(BINARY_NAME)"

# =============================================================================
# Testing
# =============================================================================

test: ## Run tests
	$(GOTEST) -v ./...

test-race: ## Run tests with race detector
	$(GOTEST) -v -race ./...

test-cover: ## Run tests with coverage
	$(GOTEST) -v -race -coverprofile=coverage.out -covermode=atomic ./...
	$(GOCMD) tool cover -html=coverage.out -o coverage.html
	@echo "Coverage report: coverage.html"

test-bench: ## Run benchmarks
	$(GOTEST) -bench=. -benchmem ./...

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run golangci-lint
	@command -v golangci-lint >/dev/null 2>&1 || \
	  (echo "Installing golangci-lint..." && go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest)
	golangci-lint run ./...

fmt: ## Format code
	$(GOCMD) fmt ./...
	@command -v goimports >/dev/null 2>&1 && goimports -w . || true

vet: ## Run go vet
	$(GOCMD) vet ./...

tidy: ## Tidy and verify dependencies
	$(GOMOD) tidy
	$(GOMOD) verify

# Full audit: all quality checks
audit: tidy fmt vet lint test-race ## Run full quality audit
	$(GOMOD) tidy -diff
	@test -z "$$(gofmt -l .)" || (echo "Files need formatting:" && gofmt -l . && exit 1)
	@echo "Audit passed"

# =============================================================================
# Guards
# =============================================================================

# Check for uncommitted changes
.PHONY: no-dirty
no-dirty:
	@test -z "$$(git status --porcelain)" || \
	  (echo "Error: uncommitted changes" && git status --short && exit 1)

# Non-interactive confirmation via CONFIRM=1
.PHONY: confirm
confirm:
ifndef CONFIRM
	$(error Run with CONFIRM=1 to proceed)
endif

# =============================================================================
# Release
# =============================================================================

PLATFORMS := linux/amd64 linux/arm64 darwin/amd64 darwin/arm64

release: audit no-dirty ## Build release binaries for all platforms
	@mkdir -p $(DIST_DIR)
	@for platform in $(PLATFORMS); do \
	  GOOS=$$(echo $$platform | cut -d/ -f1); \
	  GOARCH=$$(echo $$platform | cut -d/ -f2); \
	  output=$(DIST_DIR)/$(BINARY_NAME)-$(VERSION)-$$GOOS-$$GOARCH; \
	  echo "Building $$output..."; \
	  GOOS=$$GOOS GOARCH=$$GOARCH $(GOBUILD) $(LDFLAGS) -o $$output $(MAIN_PACKAGE); \
	done
	cd $(DIST_DIR) && sha256sum * > checksums.txt
	@echo "Release artifacts in $(DIST_DIR)/"

# =============================================================================
# Docker
# =============================================================================

DOCKER_IMAGE := $(BINARY_NAME)
DOCKER_TAG := $(VERSION)

docker-build: ## Build Docker image
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	docker tag $(DOCKER_IMAGE):$(DOCKER_TAG) $(DOCKER_IMAGE):latest

docker-push: confirm ## Push Docker image
	docker push $(DOCKER_IMAGE):$(DOCKER_TAG)
	docker push $(DOCKER_IMAGE):latest

# =============================================================================
# Utilities
# =============================================================================

clean: ## Remove build artifacts
	rm -rf $(BUILD_DIR) $(DIST_DIR) coverage.out coverage.html

install: build ## Install binary to GOPATH/bin
	cp $(BUILD_DIR)/$(BINARY_NAME) $(GOPATH)/bin/

version: ## Show version info
	@echo "Version:    $(VERSION)"
	@echo "Git Hash:   $(GIT_HASH)"
	@echo "Build Time: $(BUILD_TIME)"
