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

## Resolved this pass (2026-05-28)

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
