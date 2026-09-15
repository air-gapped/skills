# Improvement backlog — jinja-expert

Work-not-done log from skill-improver APPLY passes. `## Open` is for issues
attempted as a hypothesis but not landable in a single atomic iteration (or
deliberately deferred with rationale). `## Resolved this pass` records changes
the metric actually registered.

## Resolved — 2026-09-15 (two conditional decisions closed; neither was blocked)

- **`scripts/render-parity.py` — CLOSED, decided against for now.** Its own text
  records that recon rated Dim 7 at **8** and "explicitly noted illustrative
  resources are appropriate for a knowledge skill", so a script "risks lowering
  Simplicity (Dim 6) without a guaranteed Dim 7 lift". The condition it names —
  "revisit if Dim 7 becomes the binding constraint" — is not met: Dim 7 is not
  the binding dimension. Nothing absent is preventing this; a reasoned judgement
  already settled it.
- **Surfacing the `/v1/chat/completions/render` probe in the at-a-glance section
  — CLOSED, same shape.** The entry ends "apply only if a future pass shows the
  body has slack", expected impact "+0/+1", and warns the at-a-glance block is
  already tight. A conditional whose condition is unmet is not an open item.
- Both stay reachable: the parity harness is in
  `references/chat-template/debugging-and-testing.md` §5 and the render probe in
  §6. Neither was lost, only not promoted.

## Open

_None._ Nothing here is waiting on an absent ruling, credential, release, or
measurement nobody can run.

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
