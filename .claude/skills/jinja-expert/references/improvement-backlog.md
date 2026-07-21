# Improvement backlog — jinja-expert

Work-not-done log from skill-improver APPLY passes. `## Open` is for issues
attempted as a hypothesis but not landable in a single atomic iteration (or
deliberately deferred with rationale). `## Resolved this pass` records changes
the metric actually registered.

## Open

- **Ship a runnable `scripts/render-parity.py`** (Dim 7, Resource Quality) —
  file-set: new `scripts/` dir wrapping the parity harness in
  `references/chat-template/debugging-and-testing.md` §5. Not applied this pass:
  adding a new executable file + dir is a medium-complexity addition that needs
  its own iteration and re-score; recon rated Dim 7 at 8 and explicitly noted
  illustrative resources are appropriate for a knowledge skill, so a script
  risks lowering Simplicity (Dim 6) without a guaranteed Dim 7 lift. Revisit if
  Dim 7 becomes the binding constraint.

- **Surface the vLLM `/v1/chat/completions/render` probe in the chat-template
  at-a-glance section** (Dim 5, Completeness) — file:line:
  `SKILL.md:78-93` ("The chat-template dialect at a glance"). The render
  endpoint + `/tokenize`+`/detokenize` fallback currently live only in
  `references/chat-template/debugging-and-testing.md` §6. Deferred, not applied:
  the expected impact is +0/+1 and the hypothesis itself warned "only apply if
  it doesn't bloat the body"; the at-a-glance section is already a tight
  goal+pointer block and adding a probe one-liner trades Simplicity for a
  marginal Completeness gain. Apply only if a future pass shows the body has
  slack.

## Resolved — 2026-07-21 (freshen)

Probed 7 refs. Every version claim held except transformers, and the one real
finding is a naming trap rather than a version.

- **transformers 5.9.0 → 5.14.1** (2026-07-16, five minors). The load-bearing
  claim — the chat-template environment contract — was re-read line-by-line
  against `main` and is **byte-for-byte what the skill says**:
  `ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True,
  extensions=[AssistantTracker, jinja2.ext.loopcontrols])`, `tojson` overridden
  with `ensure_ascii=False`, `raise_exception` + `strftime_now` globals. Five
  minors of churn moved none of it.
- **The two compile functions have swapped roles, and their names now lie.**
  `_cached_compile_jinja_template` is the *uncached* builder;
  `@lru_cache` sits on the wrapper `_compile_jinja_template`, which is what
  `render_jinja_template` calls. The sources row had named the former as "the"
  compilation function, which is no longer the useful pointer. Documented in
  `sources.md` and, in its actionable form, in `transformers-dialect.md` §1:
  an edited template that keeps rendering stale output is cached on the
  function *without* `cached` in its name.
- **ansible-core 2.21.0 → 2.21.2** (patch, 2026-07-13). Native-types history and
  bare-expression `when:` semantics unchanged.
- **Jinja2 is still 3.1.6** — released 2025-03-05, no release in 16 months. Row
  now says so explicitly, so a future pass reads it as upstream stability
  rather than a probe that failed to find anything.
- **j2lint unchanged; pin deliberately NOT restored.** The 2026-05-28 pass
  removed the inline `1.2.0 (2025-04-04)` from the Notes column on purpose, per
  the file's own "do not pin inline" rule. The probe confirmed no new release,
  and that evidence is recorded here rather than being written back into the row
  the previous pass cleaned up.
- **helm#6184 still CLOSED** (2020-09-05, never accepted) — re-confirmed across
  the Helm 4 line. jinja2-cli still 1.0.1.

## Resolved — 2026-05-28

- Narrowed the over-broad `"ansible playbook"` frontmatter trigger to
  `"ansible playbook template"` + `"ansible .j2"` (Dim 1) — removes the lone
  likely false positive on pure-YAML Ansible work containing no Jinja.
- Dropped the drift-prone inline `j2lint 1.2.0 (2025-04-04)` version pin from
  `references/sources.md` Notes in favor of "latest stable" (Dim 9), aligning
  the file with its own stated freshness rule.
- Re-stamped `references/sources.md` Last-verified to 2026-05-28 on the five
  rows re-confirmed against live sources this pass (Pallets Jinja2 3.1.6,
  transformers 5.9.0 env contract, helm#6184 still CLOSED, ansible-core 2.21.0,
  jinja2-cli) and added a dedicated `jinja2-cli` PyPI row (1.0.1) the trigger
  referenced but the index lacked (Dim 9).
