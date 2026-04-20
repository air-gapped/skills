# CI/CD Integration Patterns

Keep logic in Makefile, use CI as a thin wrapper.

## GitHub Actions

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: make install
      
      - name: Lint
        run: make lint
      
      - name: Test
        run: make test
      
      - name: Build
        run: make build
      
      # Parallel builds
      - name: Build (parallel)
        run: make -j$(nproc) build

  release:
    needs: build
    if: startsWith(github.ref, 'refs/tags/')
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build release
        run: make release
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: release
          path: dist/
```

## GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

variables:
  # Enable parallel builds
  MAKEFLAGS: "-j$(nproc)"

test:
  stage: test
  script:
    - make install
    - make lint
    - make test

build:
  stage: build
  script:
    - make build
  artifacts:
    paths:
      - build/

deploy:
  stage: deploy
  script:
    - make deploy CONFIRM=1
  only:
    - main
  when: manual
```

## Makefile CI Targets

```makefile
# CI-friendly targets
.PHONY: ci ci-test ci-build ci-release

# Full CI pipeline (for local testing)
ci: install lint test build ## Run full CI pipeline

# Individual CI steps (called from CI config)
ci-test:
	$(MAKE) test VERBOSE=1

ci-build:
	$(MAKE) -j$$(nproc) build

ci-release: no-dirty
	$(MAKE) release CONFIRM=1
```

## Key Principles

1. **Same commands locally and in CI** - `make test` works everywhere
2. **Non-interactive by default** - Use `CONFIRM=1` not prompts
3. **Parallel builds in CI** - Always use `-j$(nproc)`
4. **Verbose in CI** - Set `V=1` or `VERBOSE=1` for debugging
5. **Cache dependencies** - Cache `node_modules`, `.venv`, Go modules
