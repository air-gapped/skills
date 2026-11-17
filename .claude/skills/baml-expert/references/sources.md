# Sources

Freshened: 2026-11-17 — every row probed. v0 SDK is 0.226.3 (security and build fixes only); the v1 toolchain reached baml-language-0.25.2 (2026-11-06) and gained `baml codequality`. Not re-checked this pass: the VS Code marketplace version string and the npmjs.com listing title.

Authoritative references this skill is derived from. A freshen pass verifies
every row and updates the stamp above; rows that cannot be machine-verified
carry an inline note. Latest BAML v0 SDK release: **0.226.3** (PyPI + npm,
uploaded 2026-10-28; changelog date 2026-10-27; TLS trust-store and Node/Go/Rust build updates plus a license-bundling fix, no breaking/removed/renamed lines; same for 0.226.1 and 0.226.2). v0 changes since 0.223.0 are fixes (0.224.0), connection-pooling config and `openai-transcriptions` (0.226.0), and a token-detail fix (0.226.1); 0.225.0's "Intersection bounds" entry is a v1 (`baml_language/`) feature.

**Two version lines — do not confuse them.** `baml-py` / `@boundaryml/baml` are **BAML v0**, currently **0.226.3**. The repo ALSO cuts `baml-language-0.NN.N` releases (0.25.2, 2026-11-06) for **BAML v1** — the `baml_language` Rust workspace, a separate language and toolchain installed by `brew install baml`. `gh release list` shows the language tags plus nightlies at the top because they are more *recent*, not because they are a newer v0. Never "downgrade" a 0.22x SDK pin to a 0.NN language-toolchain number, and never read a v1 tag as a v0 release.

| Ref | Scope | Pinned |
|---|---|---|
| https://docs.boundaryml.com/home | BAML public docs landing + /guide /ref tree | — |
| https://docs.boundaryml.com/guide/introduction/what-is-baml | BAML overview | — |
| https://docs.boundaryml.com/ref/baml/function | function syntax + semantics | — |
| https://docs.boundaryml.com/ref/baml/class | class syntax (no colons, no inheritance) | — |
| https://docs.boundaryml.com/ref/attributes/what-are-attributes | @/@@ attribute catalogue (docs reorg 2026-08: was /ref/baml/attributes, now split per-attribute under /ref/attributes/) | — |
| https://docs.boundaryml.com/ref/baml/test | test block + @@assert / @@check | — |
| https://docs.boundaryml.com/ref/llm-client-providers/overview | provider catalogue (bare `/ref/llm-client-providers` redirects here). Valid provider strings are the v0 engine's `ClientProvider::allowed_providers()` in `engine/baml-lib/llm-client/src/clientspec.rs` (tag 0.226.2) — Azure is `azure-openai`; its options (`resource_name`/`deployment_id` or `base_url`, required `api_version` → `api-version` query param) are in `clients/openai.rs` and docs page `/ref/llm-client-providers/azure`. The list at 0.226.2 is openai, openai-generic, azure-openai, openai-responses, openai-transcriptions (added 0.226.0, PR #4202), anthropic, ollama, openrouter, round-robin, fallback, google-ai, vertex-ai, aws-bedrock; the per-service docs pages under `fern/03-reference/baml/clients/providers/` (groq, vllm, together, …) all use `provider openai-generic` | — |
| https://docs.boundaryml.com/guide/baml-basics/streaming | @stream.done / @stream.not_null / @stream.with_state semantics | — |
| https://docs.boundaryml.com/guide/baml-advanced/prompt-caching-message-role-metadata | Anthropic cache_control role metadata (page renamed 2026-08; old /prompt-caching 404s) | — |
| https://docs.boundaryml.com/ref/baml-cli | baml-cli commands. The bare URL 302s to `/ref/baml-cli/init`, whose body shows only `init` — but all six have their own live pages (`/init`, `/generate`, `/test`, `/serve`, `/dev`, `/fmt`, each 200) and the section sidebar links them. `/optimize`, `/grep`, `/describe`, `/run` and `/version` all 404. `check` and `optimize` are real v0 `baml-cli` subcommands without a page (clap enum in `engine/cli/src/commands.rs`); `grep`/`describe`/`run` are v1 `baml` commands | — |
| https://docs.boundaryml.com/guide/baml-advanced/prompt-optimization | `baml-cli optimize` guide (v0, beta, 0.215.0+). Two errors against the source at tag 0.226.3 (`engine/baml-runtime/src/cli/optimize.rs`, `optimize/gepa_defaults/clients.baml`): it shows `--weights` (only `--weight` exists, no clap alias) and says the reflection client is `openai/gpt-4` in `gepa.baml` (it is `ReflectionModel`, provider `anthropic`, model `claude-opus-4-5-20251101`, in `clients.baml`). The page omits `--apply`, `--auto`, `--parallel`, `--no-ui`, `--view`, `--output-dir` and the defaults (`--trials` 20, `--max-evals` 50). Confirmed by running `baml-cli` 0.226.3 from PyPI on 2026-11-17: `optimize --help` lists exactly the source's flags, `--weights` fails with `unexpected argument`, no `--beta` prints the beta notice, and `--reset-gepa-prompts` writes `.baml_optimize/gepa/baml_src/{gepa,clients}.baml` and a `.gitignore`. A full optimization run was not executed | 0.226.3 |
| https://boundaryml.com/blog/teaching-agents-to-write-beautiful-baml | 2026-11-05, BAML v1 only: upstream rewrote its agent skill from a feature list into 27 guidelines with bad/good examples and added `baml codequality` (cognitive, cyclomatic, NPath, nesting, exits; `--files`, `--functions`). The "closed type for a fixed set of values" guideline is the one carried into this v0 skill | — |
| https://github.com/stanfordnlp/dspy | DSPy 3.5.0 (2026-11-10). `dspy/adapters/baml_adapter.py`: `class BAMLAdapter(JSONAdapter)`, added by PR #8614, first in 3.0.0; imports pydantic and dspy only; not exported from `dspy/__init__.py` or `dspy/adapters/__init__.py` although `docs/docs/diving-deeper/adapters.md` writes `dspy.BAMLAdapter`. `JSONAdapter.parse` uses `json_repair.loads`. `dspy/teleprompt/gepa/gepa.py`: `GEPA(metric, *, auto, max_full_evals, max_metric_calls, reflection_lm, …)`. Streaming needs a `str` field (`docs/docs/tutorials/streaming/index.md`). Optimizer list: `docs/docs/learn/optimization/optimizers.md`. `requires-python >=3.10` — no other language | 3.5.0 |
| https://boundaryml.com/blog/schema-aligned-parsing | SAP motivation and behavior | — |
| https://boundaryml.com/blog/type-definition-prompting-baml | why ctx.output_format uses type-def syntax over JSON Schema | — |
| https://github.com/boundaryml/baml | source of truth — compiler, clients, changelog | v0 SDK 0.226.3 (2026-10-28); v1 toolchain baml-language-0.25.2 (2026-11-06) |
| https://github.com/boundaryml/baml/pull/4297 | "brand legacy releases as BAML v0" — PyPI, npm, VS Code, CLI and GitHub Release surfaces of the `baml-py` line are labelled BAML v0; the root README describes the new language (old one kept as `README.v0.md`). `baml-cli` 0.226.2's own `--help` reads "A CLI tool for working with BAML v0" | merged 2026-07-31 |
| https://boundaryml.com/quickstart | BAML v1 install (`brew install baml`, install script), `baml init` (creates `baml.toml` + `baml_src/`), `baml agent install`, `baml describe`/`run`/`test` | — |
| https://github.com/boundaryml/baml/blob/canary/skills/baml-core/SKILL.md | upstream's v1 agent skill (compiled into the v1 CLI, installed by `baml agent install`): `client<llm>` blocks and `#"..."#` strings are removed in v1, fields are `name: type,`, Python bridge imports `baml_sdk` after `baml generate` from `baml.toml`. Same text at tags baml-language-0.19.0 through 0.23.0; rewritten around 27 always-follow guidelines with bad/good pairs by 0.25.x (see the blog row below) | — |
| https://github.com/boundaryml/baml/pull/1251 | optional lists + maps (`string[]?`, `map<..>?`) — contradicts public types.mdx | merged |
| https://github.com/boundaryml/baml/blob/canary/fern/pages/changelog.mdx | canonical changelog for release-gated features — shared by v0 and v1, so check a PR's paths before treating an entry as a baml-py feature | tops out at 0.226.3 (2026-10-27) |
| https://github.com/boundaryml/baml/pull/3822 | `ctx.output_format(render_null_as=...)` — shipped in 0.223.0 | merged 2026-06-23 |
| https://pypi.org/project/baml-py/ | Python SDK package (pip install baml-py) | latest 0.226.3 |
| https://www.npmjs.com/package/@boundaryml/baml | npm package + `baml-cli`/`baml` binaries (TS/JS); listing titled "BAML v0 — Node.js runtime for baml_client". www.npmjs.com 403s to curl and loads in a browser; the registry API (`registry.npmjs.org/@boundaryml/baml`) is the machine probe | latest 0.226.3 |
| https://studio.boundaryml.com | Boundary Studio v2 (redirects to the auth login). v1 at app.boundaryml.com was deprecated for 2026-03-31 and now redirects to `/dashboard`, which 404s | v1 gone |
| https://marketplace.visualstudio.com/items?itemName=Boundary.baml-extension | VSCode/Cursor playground extension, listing titled "BAML v0" | 0.226.2 |
| https://promptfiddle.com | web playground, embeddable | — |
| https://github.com/BoundaryML/baml-examples | starter repos (Python FastAPI, Next.js, Rails) | — |

## Version-sensitive claims tracked here

- `baml_options={"client": "..."}` shorthand — **0.216.0+** (0.216.0 released 2025-12-31; verified against repo changelog).
- `baml-cli test` auto-loads `.env` — **0.214.0+** (SKILL.md gotchas).
- `Collector` API — **0.79.0+**.
- **The changelog is shared by both lines.** The 0.221.0 entries for lambdas (#3302), `?.`/`??` (#3267), `ns_*` (#3292), `void` returns (#3346), test/testset expressions (#3317), stack traces (#3339) and `baml grep`/`describe` (#3347), and 0.225.0's intersection bounds (#4291), touch only `baml_language/` (BAML v1). The v0 engine at tag 0.226.2 has no `??`/`?.` in its grammar, reserves `void`, and its CLI enum has no grep/describe/run. Of that 0.221.0 list only Bedrock token caching (#3334, `engine/`) is v0.
- Literal types `"a" | "b"` — **0.61.0+**.
- `ctx.output_format(render_null_as="omit")` — **0.223.0+** (PR #3822, merged 2026-06-23).
- Type aliases `type X = ...` — **0.71.0+**.
- `baml-cli optimize` — **0.215.0+**, `--beta` required through 0.226.3.
- No upstream document describes BAML–DSPy interop (searched docs.boundaryml.com `llms.txt`, the Boundary blog feed, dspy.ai, gepa-ai/gepa docs on 2026-11-17); the two compositions in `optimization.md` follow from how each tool works.
