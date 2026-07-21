# Recently-shipped features the public docs lag on

**Reframed 2026-07-21: these have SHIPPED.** Everything in the 0.221.0 list below is reachable from a stock `pip install baml-py>=0.221` — 0.221.0 released 2026-04-14, and the SDK is on 0.223.0 as of 2026-06-23. The file's earlier "canary-only, only relevant inside the BAML repo" framing was written before those releases cut and over-restricted the guidance.

What is still true is the *documentation* gap: `docs.boundaryml.com` does not describe most of this. So the load rule is **the feature, not the audience** — read this whenever a project pins `baml-py>=0.221` and the task touches lambdas, `?.`/`??`, `ns_*` namespaces, void returns, `baml grep`/`describe`, or the `baml run` VM. Source of truth remains `fern/pages/changelog.mdx` + `beps/docs/` (BAML Enhancement Proposals) in the repo, since the public docs won't confirm them.

## Shipped in 0.221.0 (2026-04-14)

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

That crate is now cut as its own release line — `baml-language-0.NN.N` tags, at 0.15.0 on 2026-07-14, on a much faster cadence than the SDK (plus per-commit nightlies). Read those tags as the compiler/VM toolchain version, never as the SDK version; see `sources.md` §"Two version lines".

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

## When this file matters

- Project pins **`baml-py>=0.221`** → everything above is fair game; the absence of a docs page is not evidence the feature is missing.
- Project pins **below 0.221** → stick to the main SKILL.md reference and gate as shown above.
- User is **working on the BAML repo itself** ([boundaryml/baml](https://github.com/boundaryml/baml)) → read the BEPs before making syntax assumptions; semantics for young features move faster than the changelog.

Fallback rule: if unsure, check `baml_client`'s embedded version (printed at top of generated files) or `pip show baml-py`.
