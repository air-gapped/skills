# Sources

Freshened: 2026-08-18

Authoritative references this skill is derived from. A freshen pass verifies
every row and updates the stamp above; rows that cannot be machine-verified
carry an inline note. Latest BAML SDK release: **0.225.0** (PyPI + npm,
published 2026-08-01; no breaking-change notes in the release body).

**Two version lines — do not confuse them.** `baml-py` / `@boundaryml/baml` are the user-facing SDK, currently **0.225.0**. Since 2026-06 the repo ALSO cuts `baml-language-0.NN.N` releases (0.17.0, 2026-08-16) for the `baml_language` Rust workspace — the new compiler (`compiler2` / `sys_llm` renderer) and its VM. `gh release list` shows the language tags plus nightlies at the top because they are more *recent*, not because they supersede the SDK. Never "downgrade" a 0.22x SDK pin to a 0.1x language-toolchain number.

| Ref | Scope | Pinned |
|---|---|---|
| https://docs.boundaryml.com/home | BAML public docs landing + /guide /ref tree | — |
| https://docs.boundaryml.com/guide/introduction/what-is-baml | BAML overview | — |
| https://docs.boundaryml.com/ref/baml/function | function syntax + semantics | — |
| https://docs.boundaryml.com/ref/baml/class | class syntax (no colons, no inheritance) | — |
| https://docs.boundaryml.com/ref/attributes/what-are-attributes | @/@@ attribute catalogue (docs reorg 2026-08: was /ref/baml/attributes, now split per-attribute under /ref/attributes/) | — |
| https://docs.boundaryml.com/ref/baml/test | test block + @@assert / @@check | — |
| https://docs.boundaryml.com/ref/llm-client-providers | provider catalogue (openai, anthropic, vertex, bedrock, openai-generic, fallback, round-robin) | — |
| https://docs.boundaryml.com/guide/baml-basics/streaming | @stream.done / @stream.not_null / @stream.with_state semantics | — |
| https://docs.boundaryml.com/guide/baml-advanced/prompt-caching-message-role-metadata | Anthropic cache_control role metadata (page renamed 2026-08; old /prompt-caching 404s) | — |
| https://docs.boundaryml.com/ref/baml-cli | baml-cli commands (init/generate/test/serve/dev/fmt) | — |
| https://www.boundaryml.com/blog/schema-aligned-parsing | SAP motivation and behavior | — |
| https://www.boundaryml.com/blog/type-definition-prompting-baml | why ctx.output_format uses type-def syntax over JSON Schema | — |
| https://github.com/boundaryml/baml | source of truth — compiler, clients, changelog | SDK 0.225.0 (2026-08-01); toolchain baml-language-0.17.0 (2026-08-16) |
| https://github.com/boundaryml/baml/pull/1251 | optional lists + maps (`string[]?`, `map<..>?`) — contradicts public types.mdx | merged |
| https://github.com/boundaryml/baml/blob/canary/fern/pages/changelog.mdx | canonical changelog for release-gated features | tops out at 0.226.0 (canary pre-release entry, 2026-08-17; 0.225.0 is the latest *released* SDK) |
| https://github.com/boundaryml/baml/pull/3822 | `ctx.output_format(render_null_as=...)` — shipped in 0.223.0 | merged 2026-06-23 |
| https://pypi.org/project/baml-py/ | Python SDK package (pip install baml-py) | latest 0.225.0 |
| https://www.npmjs.com/package/@boundaryml/baml | npm package + `baml-cli`/`baml` binaries (TS/JS) | latest 0.225.0 |
| https://studio.boundaryml.com | Boundary Studio v2 (v1 at app.boundaryml.com deprecated end-of-March 2026) | deprecation: 2026-03-31 |
| https://marketplace.visualstudio.com/items?itemName=Boundary.baml-extension | VSCode/Cursor playground extension | — |
| https://promptfiddle.com | web playground, embeddable | — |
| https://github.com/BoundaryML/baml-examples | starter repos (Python FastAPI, Next.js, Rails) | — |

## Version-sensitive claims tracked here

- `baml_options={"client": "..."}` shorthand — **0.216.0+** (0.216.0 released 2025-12-31; verified against repo changelog).
- `baml-cli test` auto-loads `.env` — **0.214.0+** (SKILL.md gotchas).
- `Collector` API — **0.79.0+**.
- Canary/recent-release features (lambdas, `?.`/`??`, `ns_*`, `baml run`) — shipped in **0.221.0** (2026-04-14); see `references/canary-features.md`.
- Literal types `"a" | "b"` — **0.61.0+**.
- `ctx.output_format(render_null_as="omit")` — **0.223.0+** (PR #3822, merged 2026-06-23).
- Type aliases `type X = ...` — **0.71.0+**.
