# Helm Testing & CI/CD Reference

## Table of Contents
- [Testing Pyramid](#testing-pyramid)
- [helm-unittest](#helm-unittest)
- [chart-testing (ct)](#chart-testing-ct)
- [kubeconform](#kubeconform)
- [Security Scanning](#security-scanning)
- [Pluto (Deprecated APIs)](#pluto-deprecated-apis)
- [helm diff](#helm-diff)
- [CI/CD Workflows](#cicd-workflows)
- [Release-Please Integration](#release-please-integration-for-helm-charts)
- [Helmfile](#helmfile)
- [Renovate for Helm](#renovate-for-helm)
- [Pre-Commit Hooks](#pre-commit-hooks)

---

## Testing Pyramid

Five layers from fastest (no cluster) to slowest (real cluster):

| Layer | Tool | Cluster? | Time |
|-------|------|----------|------|
| 1. Syntax/lint | `helm lint`, `yamllint` | No | Seconds |
| 2. Schema validation | `kubeconform` | No | Seconds |
| 3. Unit tests | `helm-unittest` | No | Seconds |
| 4. Security/policy | Trivy, Polaris, kube-linter, conftest | No | Seconds |
| 5. Integration tests | `ct install`, `helm test` | Yes (kind/k3d) | Minutes |

**Minimum CI pipeline**: lint -> kubeconform -> security scan -> ct install.

**Anti-pattern**: Relying solely on `--dry-run` (skips admission logic and RBAC).

---

## helm-unittest

BDD-style unit testing. No cluster needed. v1.0.3 (October 2025).

### Installation

```bash
helm plugin install https://github.com/helm-unittest/helm-unittest
```

### Test File Structure

Test files go in `tests/` with `_test.yaml` suffix:

```yaml
suite: deployment tests
templates:
  - templates/deployment.yaml
tests:
  - it: should create a deployment
    asserts:
      - isKind:
          of: Deployment
      - equal:
          path: metadata.name
          value: RELEASE-NAME-mychart

  - it: should use custom image
    set:
      image.repository: custom/image
      image.tag: "2.0"
    asserts:
      - equal:
          path: spec.template.spec.containers[0].image
          value: docker.io/custom/image:2.0

  - it: should not create when disabled
    set:
      enabled: false
    asserts:
      - hasDocuments:
          count: 0

  - it: should set resource limits
    values:
      - ../ci/production-values.yaml
    asserts:
      - isNotNullOrEmpty:
          path: spec.template.spec.containers[0].resources.limits

  - it: should fail without required value
    set:
      image.repository: null
    asserts:
      - failedTemplate: {}
```

### Key Assertions

| Assertion | Description |
|-----------|------------|
| `equal` | Exact match at path |
| `notEqual` | Not equal at path |
| `matchRegex` | Regex match at path |
| `contains` | Array/map contains item |
| `isKind` | Resource kind matches |
| `isAPIVersion` | API version matches |
| `hasDocuments` | Document count |
| `isSubset` | Path contains subset of content |
| `exists` / `notExists` | Path exists or not |
| `isNullOrEmpty` / `isNotNullOrEmpty` | Null/empty check |
| `failedTemplate` / `notFailedTemplate` | Template error testing |
| `matchSnapshot` | Snapshot comparison |
| `containsDocument` | Multi-doc: specific kind+apiVersion+name exists |

All assertions support `not` (invert), `template` (target specific file),
`documentIndex` (nth document), `documentSelector` (path/value matching).

### Snapshot Testing

```yaml
  - it: should match snapshot
    asserts:
      - matchSnapshot: {}
```

Snapshots stored in `__snapshot__/`. Update with `helm unittest -u`. Add
`*/__snapshot__/*` to `.helmignore`.

### Overrides

Test-level overrides for cluster capabilities:

```yaml
  - it: should create Route on OpenShift
    capabilities:
      apiVersions:
        - route.openshift.io/v1
    asserts:
      - isKind:
          of: Route
```

### Run

```bash
helm unittest ./mychart
helm unittest -f 'tests/*_test.yaml' ./mychart
helm unittest -t JUnit -o results.xml ./mychart   # CI output
```

---

## chart-testing (ct)

Integration testing tool from the Helm project. Uses git to detect changed charts.

### Configuration (ct.yaml)

```yaml
chart-dirs:
  - charts
remote: origin
target-branch: main
validate-maintainers: false
validate-chart-schema: true
validate-yaml: true
check-version-increment: true
helm-extra-args: --timeout 600s
```

### Commands

```bash
# List charts changed vs target branch
ct list-changed --config ct.yaml

# Lint changed charts
ct lint --config ct.yaml

# Install changed charts into cluster + run helm test
ct install --config ct.yaml

# Install + test upgrades (important for schema migrations)
ct install --upgrade --config ct.yaml
```

### CI Values

Charts can include `ci/*-values.yaml` files tested separately during `ct install`.
Each file gets its own install/test/delete cycle:

```
mychart/
  ci/
    default-values.yaml
    production-values.yaml
    openshift-values.yaml
```

### Requirements

ct requires Python (for Yamale schema validation and yamllint).

---

## kubeconform

Successor to deprecated kubeval. Validates rendered manifests against Kubernetes
OpenAPI schemas.

```bash
# Basic validation
helm template ./mychart | kubeconform -strict -kubernetes-version 1.28.0

# Ignore CRDs (no schema available)
helm template ./mychart | kubeconform -strict -ignore-missing-schemas

# Custom schema locations (for CRDs)
helm template ./mychart | kubeconform -strict \
  -schema-location default \
  -schema-location 'https://raw.githubusercontent.com/datreeio/CRDs-catalog/main/{{.Group}}/{{.ResourceKind}}_{{.ResourceAPIVersion}}.json'

# JUnit output for CI
helm template ./mychart | kubeconform -strict -output junit > results.xml
```

### Helm Plugin

```bash
helm plugin install https://github.com/melmorabity/helm-kubeconform
helm kubeconform ./mychart
```

---

## Security Scanning

### Polaris

30+ built-in policies for Kubernetes best practices:

```bash
polaris audit --helm-chart ./mychart --helm-values values.yaml
polaris audit --helm-chart ./mychart --format json
```

### kube-linter

Static analysis for Kubernetes YAML:

```bash
kube-linter lint ./charts/mychart
```

Configuration (`.kube-linter.yaml`):
```yaml
checks:
  addAllBuiltIn: true
  exclude:
    - "unset-cpu-requirements"
```

Per-object exemption via annotation:
`ignore-check.kube-linter.io/<check-name>: "reason"`

### Conftest (OPA/Rego)

Custom policies in Rego:

```bash
helm template ./mychart | conftest test - --policy ./policy
```

Example policy (`policy/main.rego`):
```rego
package main

deny[msg] {
  input.kind == "Deployment"
  not input.spec.template.spec.securityContext.runAsNonRoot
  msg := sprintf("Deployment %s must set runAsNonRoot", [input.metadata.name])
}
```

### Trivy

Scan chart for vulnerabilities and misconfigurations:

```bash
# Render then scan
helm template ./mychart > rendered.yaml
trivy config rendered.yaml

# Scan container images referenced in chart
trivy image myorg/myapp:1.0.0
```

**Note**: Pin Trivy action to SHA in CI — trivy-action was compromised in March 2026.

---

## Pluto (Deprecated APIs)

Detects deprecated and removed Kubernetes API versions:

```bash
# Scan rendered templates
helm template ./mychart | pluto detect -

# Scan chart files directly
pluto detect-files -d ./charts/

# Target specific future K8s version
helm template ./mychart | pluto detect - --target-versions k8s=v1.29.0
```

Differentiates `DEPRECATED` (still works) from `REMOVED` (will fail).

---

## helm diff

Preview what `helm upgrade` would change:

```bash
helm diff upgrade myrelease ./mychart -f values.yaml -n mynamespace
helm diff upgrade myrelease ./mychart --suppress-secrets
helm diff upgrade myrelease ./mychart --three-way-merge
```

**Helm 4 note**: Requires `--verify=false` during plugin install (no GPG
provenance yet).

---

## CI/CD Workflows

### Lint + Test (PR Workflow)

```yaml
name: Lint and Test
on: pull_request

permissions:
  contents: read

jobs:
  lint-test:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
        with:
          fetch-depth: 0

      - uses: azure/setup-helm@b9e51907a09c216f16ebe8536097933489208112 # v4.3.0

      - uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
        with:
          python-version: '3.x'

      - uses: helm/chart-testing-action@e6669bcd63d7cb57cb4380c33043eebe5d111992 # v2.7.0

      - name: List changed charts
        id: list-changed
        run: |
          changed=$(ct list-changed --config ct.yaml)
          if [[ -n "$changed" ]]; then
            echo "changed=true" >> "$GITHUB_OUTPUT"
          fi

      - name: Lint
        run: ct lint --config ct.yaml

      - name: Validate schemas
        if: steps.list-changed.outputs.changed == 'true'
        run: |
          for chart in $(ct list-changed --config ct.yaml); do
            helm template "$chart" | kubeconform -strict -kubernetes-version 1.28.0 -ignore-missing-schemas
          done

      - name: Create kind cluster
        if: steps.list-changed.outputs.changed == 'true'
        uses: helm/kind-action@a1b0e391336a6ee6713a0583f8c6240d70863de3 # v1.12.0

      - name: Install and test
        if: steps.list-changed.outputs.changed == 'true'
        run: ct install --config ct.yaml --upgrade
```

### Release to GitHub Pages

```yaml
name: Release Charts
on:
  push:
    branches: [main]
    paths: ['charts/**']

permissions:
  contents: write
  pages: write

jobs:
  release:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
        with:
          fetch-depth: 0

      - uses: azure/setup-helm@b9e51907a09c216f16ebe8536097933489208112 # v4.3.0

      - uses: helm/chart-releaser-action@cae68fefc6b5f367a13b05b6d575c93921f3b899 # v1.7.0
        env:
          CR_TOKEN: "${{ secrets.GITHUB_TOKEN }}"
```

### OCI Push to GHCR

```yaml
name: Push to OCI
on:
  push:
    tags: ['charts/*-v*']

permissions:
  contents: read
  packages: write
  id-token: write     # For cosign keyless signing

jobs:
  push:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

      - uses: azure/setup-helm@b9e51907a09c216f16ebe8536097933489208112 # v4.3.0

      - uses: docker/login-action@74a5d142397b4f367a81961eba4e8cd7edddf772 # v3.4.0
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - uses: sigstore/cosign-installer@3454372be43e8dfc343da0005bc1f32d2e0e54af # v3.8.2

      - name: Authenticate cosign to GHCR
        run: cosign login ghcr.io -u ${{ github.actor }} -p ${{ secrets.GITHUB_TOKEN }}

      - name: Package and push
        id: push-chart
        run: |
          CHART_DIR=$(echo "${{ github.ref_name }}" | sed 's/-v[0-9].*//')
          helm package "charts/${CHART_DIR#charts/}"
          PACKAGE=$(ls *.tgz)
          OUTPUT=$(helm push "$PACKAGE" oci://ghcr.io/${{ github.repository_owner }}/charts 2>&1)
          echo "$OUTPUT"
          DIGEST=$(echo "$OUTPUT" | grep -oP 'sha256:[a-f0-9]+')
          echo "digest=${DIGEST}" >> "$GITHUB_OUTPUT"

      - name: Sign chart
        env:
          DIGEST: ${{ steps.push-chart.outputs.digest }}
        run: |
          CHART_DIR=$(echo "${{ github.ref_name }}" | sed 's/-v[0-9].*//')
          CHART_NAME=$(basename "$CHART_DIR")
          cosign sign -y "ghcr.io/${{ github.repository_owner }}/charts/${CHART_NAME}@${DIGEST}"
```

### Release-Please Integration for Helm Charts

release-please can manage chart version bumps in `Chart.yaml` automatically, but
there are several critical gotchas.

#### NEVER set `release-type` as an action input

If `release-type` is set in the workflow YAML, the action builds config entirely
from inputs and **completely ignores** `release-please-config.json`. This silently
disables `extra-files`, `changelog-sections`, `draft`, and all other config-file
features. Always put `release-type` in the config file, not the action input:

```yaml
# WRONG — config file is ignored
- uses: googleapis/release-please-action@...
  with:
    release-type: go       # ← causes config file to be skipped
    token: ${{ steps.token.outputs.token }}

# CORRECT — config file is read
- uses: googleapis/release-please-action@...
  with:
    token: ${{ steps.token.outputs.token }}
```

#### Use `changelog-sections` and `draft: true`

Hide non-user-facing commit types from release notes. Without this config,
`ci:` and `chore:` commits appear in a misleading "Breaking Changes" section.
Use `draft: true` so maintainers can add highlights before publishing:

```jsonc
{
  "packages": {
    ".": {
      "release-type": "go",
      "changelog-sections": [
        { "type": "feat", "section": "Features" },
        { "type": "fix", "section": "Bug Fixes" },
        { "type": "perf", "section": "Performance" },
        { "type": "revert", "section": "Reverts" },
        { "type": "docs", "section": "Documentation", "hidden": true },
        { "type": "chore", "section": "Miscellaneous", "hidden": true },
        { "type": "refactor", "section": "Code Refactoring", "hidden": true },
        { "type": "test", "section": "Tests", "hidden": true },
        { "type": "ci", "section": "CI", "hidden": true },
        { "type": "build", "section": "Build System", "hidden": true }
      ],
      "draft": true
    }
  }
}
```

Section ordering is array-position-based. `hidden: true` suppresses from
notes but still triggers version bumps (a hidden `fix:` still bumps patch).

#### Chart.yaml with release-please annotations

Use `x-release-please-version` comments to mark the version field:

```yaml
apiVersion: v2
name: mychart
version: 0.3.0 # x-release-please-version
appVersion: "1.2.0"
```

#### extra-files: MUST use object form with `"type": "generic"`

**WARNING**: The string shorthand `extra-files: ["charts/mychart/Chart.yaml"]`
causes release-please to run the GenericYaml updater first, which parses and
re-serializes the YAML — **stripping all comments** including the
`x-release-please-version` annotation. The Generic updater then finds nothing
to replace, and the version is never bumped.

```jsonc
// WRONG — strips YAML comments, breaks annotation-based versioning
"extra-files": [
  "charts/mychart/Chart.yaml"
]

// CORRECT — uses Generic updater directly, preserves comments
"extra-files": [
  {"type": "generic", "path": "charts/mychart/Chart.yaml"}
]
```

#### Synced vs independent chart versioning

**Synced** — chart version tracks the application version. Use when the chart
and app live in the same repo and release together:

```jsonc
// release-please-config.json
{
  "packages": {
    ".": {
      "extra-files": [
        {"type": "generic", "path": "charts/mychart/Chart.yaml"}
      ]
    }
  }
}
```

**Independent** — chart has its own release lifecycle. Use a separate
release-please component for the chart directory:

```jsonc
{
  "packages": {
    "charts/mychart": {
      "release-type": "helm",
      "component": "mychart-chart"
    }
  }
}
```

The `helm` release-type natively understands `Chart.yaml` and bumps `version`
based on conventional commits scoped to the chart path.

---

## Helmfile

Declarative multi-release management. v1.3.1 (February 2026). Supports Helm 3+4.

### helmfile.yaml

```yaml
repositories:
  - name: bitnami
    url: https://charts.bitnami.com/bitnami

environments:
  staging:
    values:
      - environments/staging.yaml
  production:
    values:
      - environments/production.yaml

releases:
  - name: postgresql
    namespace: db
    chart: bitnami/postgresql
    version: 12.x
    values:
      - values/postgresql.yaml
      - values/postgresql-{{ .Environment.Name }}.yaml

  - name: myapp
    namespace: app
    chart: ./charts/myapp
    needs:
      - db/postgresql
    values:
      - values/myapp.yaml
    secrets:
      - secrets/myapp.yaml     # SOPS-encrypted
```

### Commands

```bash
helmfile -e production diff     # Preview changes
helmfile -e production apply    # Diff + sync atomically
helmfile -e production sync     # Force sync without diff
helmfile -e production destroy  # Uninstall all releases
```

---

## Renovate for Helm

Renovate is significantly more capable than Dependabot for Helm chart management.

### renovate.json

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["config:recommended"],
  "helmv3": {
    "enabled": true
  },
  "helm-values": {
    "enabled": true
  },
  "postUpdateOptions": ["helmUpdateSubChartArchives"],
  "packageRules": [
    {
      "matchManagers": ["helmv3"],
      "bumpVersion": "patch"
    }
  ]
}
```

### Capabilities

| Feature | Renovate | Dependabot |
|---------|----------|-----------|
| Chart.yaml dependency versions | Yes | Yes (April 2025) |
| Image tags in values.yaml | Yes (`helm-values` manager) | No |
| Auto-bump chart version | Yes (`bumpVersion`) | No |
| Regex for arbitrary files | Yes | No |
| Self-hostable (air-gapped) | Yes | No |
| Subchart archive updates | Yes (`helmUpdateSubChartArchives`) | No |

---

## Pre-Commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
        exclude: templates/

  - repo: https://github.com/adrienverge/yamllint
    rev: v1.38.0
    hooks:
      - id: yamllint
        args: [-c=.yamllint.yaml]
        exclude: templates/

  - repo: https://github.com/norwoodj/helm-docs
    rev: v1.14.2
    hooks:
      - id: helm-docs
        args: [--chart-search-root=charts]

  - repo: https://github.com/dadav/helm-schema
    rev: v0.23.0
    hooks:
      - id: helm-schema
```

Note: Exclude `templates/` from yamllint — Go templates are not valid YAML until
rendered.
