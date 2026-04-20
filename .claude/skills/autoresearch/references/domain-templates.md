# Domain Templates

Pre-built experiment configurations for common optimization targets. Use these as
starting points — adapt to the specific project.

## Table of Contents
- [Web Performance (Bundle Size)](#web-performance-bundle-size)
- [Web Performance (Lighthouse / Core Web Vitals)](#web-performance-lighthouse--core-web-vitals)
- [API Latency](#api-latency)
- [Database Query Optimization](#database-query-optimization)
- [ML Training (Karpathy Original)](#ml-training-karpathy-original)
- [Prompt Optimization](#prompt-optimization)
- [Test Coverage](#test-coverage)
- [Rust / C++ Compilation Speed](#rust--c-compilation-speed)
- [Docker Image Size](#docker-image-size)
- [Creating Your Own Template](#creating-your-own-template)

---

## Web Performance (Bundle Size)

```yaml
truth_layer: [tests/, package.json, tsconfig.json]
mutable_surface: [src/, webpack.config.js or vite.config.ts]
verifier: "npm run build && du -sb dist/"
metric: "bytes (lower is better)"
typical_experiments:
  - Tree-shaking unused exports
  - Code splitting by route
  - Replacing heavy dependencies with lighter alternatives
  - Dynamic imports for below-the-fold features
  - Compression configuration (brotli/gzip levels)
```

## Web Performance (Lighthouse / Core Web Vitals)

```yaml
truth_layer: [tests/, e2e/]
mutable_surface: [src/components/, src/pages/]
verifier: "npx lighthouse <url> --output=json --quiet | jq '.categories.performance.score'"
metric: "score 0-1 (higher is better)"
typical_experiments:
  - Image optimization (format, sizing, lazy loading)
  - CSS critical path extraction
  - Font loading strategy (swap, preload)
  - Render-blocking resource elimination
  - Component-level code splitting
```

## API Latency

```yaml
truth_layer: [tests/, migrations/, schema.sql]
mutable_surface: [src/routes/, src/services/, src/queries/]
verifier: "wrk -t4 -c100 -d10s http://localhost:3000/api/endpoint"
metric: "p99 latency in ms (lower is better)"
typical_experiments:
  - Query optimization (indexes, joins, N+1 elimination)
  - Response caching (Redis, in-memory, HTTP cache headers)
  - Connection pooling tuning
  - Serialization format (JSON vs MessagePack vs Protobuf)
  - Middleware ordering and short-circuiting
```

## Database Query Optimization

```yaml
truth_layer: [migrations/, seeds/, tests/]
mutable_surface: [queries/ or src/repositories/]
verifier: "psql -c 'EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) <query>' | jq '.[0].\"Execution Time\"'"
metric: "execution time in ms (lower is better)"
typical_experiments:
  - Index creation and type selection
  - Query rewriting (subquery → JOIN, OR → UNION)
  - Partial indexes for filtered queries
  - Materialized views for expensive aggregations
  - Partitioning for large tables
```

## ML Training (Karpathy Original)

```yaml
truth_layer: [prepare.py, data/]
mutable_surface: [train.py]
verifier: "python train.py 2>&1 | grep 'val_bpb:'"
metric: "val_bpb (lower is better)"
typical_experiments:
  - Architecture changes (depth, width, attention patterns)
  - Optimizer hyperparameters (learning rate, weight decay, betas)
  - Activation functions
  - Normalization strategies
  - Positional encoding modifications
  - Training schedule (warmup, warmdown ratios)
```

## Prompt Optimization

```yaml
truth_layer: [evals/, test_cases.json]
mutable_surface: [prompt.md or system_message.txt]
verifier: "python run_eval.py --prompt prompt.md --cases test_cases.json"
metric: "pass_rate (higher is better)"
typical_experiments:
  - Structural reorganization (ordering, headers, emphasis)
  - Adding/removing constraints
  - Example selection and formatting
  - Tone and specificity adjustments
  - Chain-of-thought scaffolding
  - Negative examples ("do NOT do X")
notes: |
  Prompt optimization is especially susceptible to overfitting to a small eval set.
  Keep a held-out test set that you check only at the end, not after every iteration.
  Run each eval 3 times to account for LLM sampling variance.
```

## Test Coverage

```yaml
truth_layer: [src/]
mutable_surface: [tests/]
verifier: "npm test -- --coverage --coverageReporters=json-summary && cat coverage/coverage-summary.json | jq '.total.lines.pct'"
metric: "line coverage % (higher is better)"
typical_experiments:
  - Adding tests for uncovered branches
  - Edge case coverage (null, empty, boundary values)
  - Error path testing
  - Integration tests for untested flows
notes: |
  Coverage percentage is a crude metric. Prioritize meaningful tests over coverage
  gaming. A test that asserts on real behavior is worth more than one that just
  executes a code path without checking results.
```

## Rust / C++ Compilation Speed

```yaml
truth_layer: [tests/, Cargo.toml or CMakeLists.txt]
mutable_surface: [src/]
verifier: "cargo clean && time cargo build --release 2>&1 | grep real"
metric: "seconds (lower is better)"
typical_experiments:
  - Reducing monomorphization (trait objects vs generics)
  - Splitting large modules to improve parallelism
  - Reducing procedural macro usage
  - Feature flag cleanup
  - Moving heavy dependencies behind feature gates
```

## Docker Image Size

```yaml
truth_layer: [tests/, docker-compose.test.yml]
mutable_surface: [Dockerfile, .dockerignore]
verifier: "docker build -t bench . && docker image inspect bench --format='{{.Size}}'"
metric: "bytes (lower is better)"
typical_experiments:
  - Multi-stage builds
  - Base image selection (alpine, distroless, scratch)
  - Layer ordering for cache efficiency
  - Removing unnecessary files and build artifacts
  - Using .dockerignore effectively
```

---

## Creating Your Own Template

If your domain isn't listed above, define the four components:

```yaml
truth_layer: [files that define correctness — never modified]
mutable_surface: [files to optimize — modified each iteration]
verifier: "command that outputs a number"
metric: "what the number means and which direction is better"
typical_experiments:
  - List 5-10 categories of changes to try
notes: |
  Any domain-specific gotchas or considerations
```

The key requirement is a **verifier that produces a comparable numeric metric**.
If you can't measure it, you can't optimize it with the experiment loop — use
Mode 3 (Improve) instead, which can handle qualitative improvement through
research-informed changes.
