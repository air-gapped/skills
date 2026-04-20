# Canary / bleeding-edge features

Only load this if the user is working inside the BAML repo itself, or on a project that pins `baml-py` to a canary build (0.221.0+). These features may not be reflected in the public docs yet. Source of truth: `fern/pages/changelog.mdx` + `beps/docs/` (BAML Enhancement Proposals) in the BAML repo.

## 0.221.0 (2026-04-14) and in-flight canary

- **Lambda expressions** in BAML compiler (#3302). First-class function values — syntax under evolution; check `beps/docs/` for the current spec.
- **Optional chaining `?.` and null coalescing `??`** (BEP-020, #3267). Finally — e.g. `resume.profile?.email ?? "unknown"` inside expressions/Jinja-adjacent contexts.
- **Folder-based namespace system `ns_*`** (#3292). Subfolders under `baml_src/` named `ns_<x>/` create namespaces, allowing identifier reuse across modules.
- **Void return type** for functions (#3346) — `function DoSomething(...) -> void`. For side-effect-only calls.
- **Dynamic test/testset expression syntax** (#3317) — parameterize test runs.
- **Stack traces with source line numbers in thrown errors** (#3339).
- **AWS Bedrock token caching support** (#3334). Cached tokens now reported where the Bedrock API provides them.
- **MIR skip on errors + void test bodies** (0.221.0).

## Agent-oriented CLI

Commit `ec33bde53` + 0.221.0 additions:

- **`baml grep`** — semantic search across `.baml` sources. Designed for LLMs and humans that want to answer "which functions accept `image`?"-style queries fast.
- **`baml describe`** — describe a function/class/enum in natural language for agent consumption.
- **Filesystem API** with write ops, seek, Bun-style naming — for scripting against BAML from within the playground / VM.
- **`baml.io.input(prompt?) -> string`** namespace — interactive input inside BAML scripts.
- **Bound & unbound method closure types** (commit `4f68636e1`).

## Standalone execution — `baml run`

The `baml_language` crate (commit `c109a4d73`) adds a VM so `.baml` files execute end-to-end without a host language. `baml run` is the entry point.

Use cases:
- One-off scripts / agentic flows where Python codegen feels like overkill.
- Prototyping a function with real inputs before wiring into the host app.

Status: early. Pin an exact version; expect breaking changes.

## BEPs — BAML Enhancement Proposals

Design-doc collection at `beps/docs/` in the repo. When a canary feature has semantics you don't understand, read the corresponding BEP — it's usually more accurate than the public docs for the first few releases of a feature.

Notable recent BEPs:
- BEP-020: optional chaining + null coalescing.
- BEP-022 (approx.): lambda expressions.
- BEP on `ns_*` namespace system.
- BEP on `baml.io` namespace.
- BEP export-all tooling (commit `8442c48ec`) — generate a consolidated markdown of all BEPs for AI consumption.

## Version signals for feature gating

When documenting/writing BAML for a shared codebase, gate feature use:

```baml
// requires BAML >= 0.221
result SomeField?.value ?? "fallback"
```

Update the generator's `version "0.221.0"` to match and document the minimum in a `BAML_VERSION` or README section.

## When canary matters

- User is **working on the BAML project itself** (a local checkout of [boundryml/baml](https://github.com/boundryml/baml)) → read BEPs before making syntax assumptions.
- User **pinned a canary SDK** intentionally → new syntax is fair game.
- User **pinned stable** → stick to the main SKILL.md reference; avoid canary-only features.

Fallback rule: if unsure, check `baml_client`'s embedded version (printed at top of generated files) or `pip show baml-py`.
