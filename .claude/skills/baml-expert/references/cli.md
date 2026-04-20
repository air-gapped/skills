# `baml-cli` reference

## Contents
- [`baml-cli init`](#baml-cli-init) — scaffold baml_src/
- [`baml-cli generate`](#baml-cli-generate) — emit baml_client/
- [`baml-cli test`](#baml-cli-test) — run test blocks; flags, exit codes
- [`baml-cli serve`](#baml-cli-serve) — HTTP endpoints for functions
- [`baml-cli dev`](#baml-cli-dev) — watch + regenerate
- [`baml-cli fmt`](#baml-cli-fmt) — beta formatter
- [Canary / newer features](#canary--newer-features) — `optimize`, `grep`, `describe`, `run`
- [Exit code conventions](#exit-code-conventions-summary)
- [Debug env vars](#debug-env-vars) — BAML_LOG, BOUNDARY_API_KEY, BAML_PASSWORD

Install via `pip install baml-py` (provides the CLI) or `npm add @boundaryml/baml`.

## `baml-cli init`

Scaffolds a new BAML project. Creates `baml_src/` + a `generators.baml` + a sample function.

```bash
baml-cli init [--dest DIR] [--client-type LANG] [--openapi-client-type LANG]

# LANG values for --client-type:
#   python/pydantic   (default when baml-py installed via pip)
#   typescript
#   go
#   ruby/sorbet
#   rest/openapi
```

Fails if `baml_src/` already exists — moves no files.

## `baml-cli generate`

Runs every `generator` block in `baml_src/`, emitting language-specific clients.

```bash
baml-cli generate [--from PATH]              # path to baml_src (defaults to ./baml_src)
                  [--no-version-check]       # skip generator.version vs SDK version match
                  [--no-tests]               # strip test blocks from the inlined .baml (prod bundle)
```

Run on any `.baml` change. VSCode extension auto-runs on save if `baml.generateCodeOnSave=true` (default). Wire into pre-commit / justfile.

## `baml-cli test`

Runs `test` blocks against real LLMs.

```bash
baml-cli test [-i '<Fn>::<Test>']            # include glob (repeatable)
              [-x '<pattern>']                # exclude glob
              [--list]                        # list without running
              [--parallel N]                  # default 10
              [--pass-if-no-tests]            # exit 0 on empty
              [--require-human-eval]          # exit 2 without human confirmation
              [--dotenv-path .env.test]       # load env from file
              [--no-dotenv]                   # don't auto-load .env
              [--from PATH]
```

Exit codes: 0 pass • 1 fail • 2 human-eval-required • 3 cancelled • 4 no tests found.

## `baml-cli serve`

HTTP server exposing every function as `POST /call/:fn` and `POST /stream/:fn`.

```bash
baml-cli serve [--port 2024] [--no-version-check]
```

Endpoints:
- `POST /call/:fn` — JSON body with args, returns JSON result.
- `POST /stream/:fn` — JSON body, returns NDJSON stream.
- `GET /_debug/ping` — health check.
- `GET /docs` — Swagger UI.
- `GET /openapi.json` — OpenAPI spec.

Auth: `BAML_PASSWORD` env var enables `x-baml-api-key` header check.

**Stability = Tier 2.** Does NOT yet support TypeBuilder, Collector, or ClientRegistry in the HTTP request body. If you need those, call from a host app instead.

## `baml-cli dev`

Like `serve` but watches `baml_src/` and re-runs `generate` on file changes. Useful for iterating with a UI that talks HTTP.

```bash
baml-cli dev [--port 2024]
```

## `baml-cli fmt`

Beta formatter. In-place, non-configurable. Disable per-file with `// baml-format: ignore` at the top.

```bash
baml-cli fmt [file.baml ...]                 # defaults to all .baml in baml_src/
```

May not handle every syntax yet — watch diffs the first time.

## Canary / newer features

Only relevant if on a recent release or the BAML canary branch:

- **`baml-cli optimize`** — prompt optimization visualizer (0.215.0+).
- **`baml grep`** / **`baml describe`** — agent-oriented semantic search over BAML sources (0.221.0+, PR #3347).
- **`baml run`** — standalone `.baml` execution via the new `baml_language` VM (recent canary commits).

## Exit code conventions summary

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Generic failure |
| 2 | Human-evaluation required (`baml-cli test --require-human-eval`) |
| 3 | Cancelled (Ctrl-C) |
| 4 | No tests found (without `--pass-if-no-tests`) |

## Debug env vars

| Env | Purpose |
|---|---|
| `BAML_LOG` | `off | error | warn | info | debug | trace` (default `info`) |
| `BOUNDARY_MAX_LOG_CHUNK_CHARS` | truncate each log payload (default `3000`) |
| `BOUNDARY_API_KEY` | enable trace shipping to Boundary Studio |
| `BAML_PASSWORD` | required for auth on `baml-cli serve` |
