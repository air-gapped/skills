---
name: jinja-expert
description: >-
  Author, read, and debug Jinja2 templates across the three places Jinja
  lives in 2026 — HuggingFace `chat_template.jinja` (rendered by
  `apply_chat_template` for vLLM / sglang), Ansible playbooks + `.j2`
  files, and Jinja-adjacent Kubernetes workflows (`values.yaml.j2`,
  `kubernetes.core.k8s + template`, Helm post-renderers). Companion to
  the `helm` skill — Helm charts are Go `text/template` + Sprig, not
  Jinja, and this skill makes that disambiguation explicit.
when_to_use: >-
  Triggers on the phrases "chat template", "chat_template.jinja",
  "j2 file", ".j2", "jinja filter", "jinja2 filter", "ansible template",
  "ansible jinja", "ansible playbook", "values.yaml jinja", "jinja helm",
  "jinja2-cli", "helm-jinja", "kubernetes jinja", or any request to
  write / read / fix a Jinja template. Also triggers on symptoms —
  `TemplateError`, `SecurityError`, `AnsibleUndefinedVariable`,
  `add_generation_prompt` misbehavior, `tool_call.arguments` rendering
  wrong, `{% set %}` not persisting outside a `{% for %}` loop (the
  namespace/loop-scope trap), double-templating via `!unsafe` /
  `{% raw %}`, whitespace drift shifting tokenization, content-format
  bifurcation (`message.content` list vs string), `when:` conditional
  delimiters, `hostvars`, `lookup('template', ...)`, `jinja2_native`
  types, `ansible_managed`, custom filter plugins, `kubernetes.core.k8s`,
  `community.kubernetes.helm`, "render a jinja template", "fix chat
  template", and Helm questions that turn out to be Go/Jinja mix-ups.
---

# Jinja Expert

Jinja2 shows up in three mostly-disjoint ecosystems in 2026. Each has its
own dialect — different sandbox, different extensions, different filters,
different failure modes. Using chat-template idioms in an Ansible playbook
will silently misbehave. Using Ansible `!unsafe` in a chat template is a
syntax error. This skill is the map.

---

## Which dialect am I in?

Pick the row that matches the file under review. The rightmost column
points to the next file to read.

| Signal | Dialect | Go to |
|---|---|---|
| File named `chat_template.jinja`; `apply_chat_template`, `tokenizer_config.json`, vLLM/sglang in play; messages/tools/`add_generation_prompt` in scope | **HF chat template** (sandboxed, `loopcontrols`, `tojson ensure_ascii=False`) | `references/chat-template/` |
| File ends in `.j2`; inside an Ansible playbook/role/collection; `{{ ansible_managed }}`, `hostvars`, `lookup(...)`, `| default(omit)`; `when:` bare expressions | **Ansible Jinja** (recursive templating, native-types flag, `!unsafe`) | `references/ansible-dialect.md` |
| `values.yaml.j2` / `deployment.yaml.j2` feeding Helm or `kubectl`; `jinja2-cli`; `community.kubernetes.helm` / `kubernetes.core.k8s`; ArgoCD config management plugin | **Helm-adjacent Jinja** (Jinja *around* Helm, not inside) | `references/helm-and-jinja.md` |
| File inside a Helm chart (`templates/*.yaml`, `_helpers.tpl`, `Chart.yaml`); `{{ .Values.x }}`, `{{ toYaml ... }}`, `{{ include "mychart.name" . }}`, Sprig functions | **Go `text/template` + Sprig** — *not Jinja* | Reach for the **`helm` skill** instead |
| Syntax looks like `{{ }}` but something else — `.gotmpl`, `helmfile.yaml`, Flask, Saltstack state, dbt model, Home Assistant config | Not covered here; use the core-language cheatsheet | `references/language-surface.md` + upstream docs |

When the dialect is uncertain, start at `references/language-surface.md` —
dialect-neutral, covers the statements, expressions, filters, tests,
globals, and whitespace rules shared by every Jinja deployment.

---

## Quick decision guide (chat-template default)

Chat templates are the dialect most likely to bring someone here, so the
body below stays biased toward them. When the task is Ansible or
Helm-adjacent, branch to the matching reference and ignore the rest.

| Task | Go to |
|---|---|
| Look up a statement, filter, test, or global | `references/language-surface.md` |
| Understand the exact env `apply_chat_template` builds | `references/chat-template/transformers-dialect.md` |
| Diagnose a specific category of chat-template bug | `references/chat-template/seven-failure-categories.md` |
| Write a new chat template (or patch an existing one) | `references/chat-template/authoring-patterns.md` |
| Find a "clean" chat template to study, or a broken one to learn from | `references/chat-template/exemplars-and-antiexemplars.md` |
| Debug a chat template or set up coverage/parity testing | `references/chat-template/debugging-and-testing.md` |
| Write Ansible playbooks or `.j2` files — filters, lookups, `!unsafe`, native types, k8s manifests | `references/ansible-dialect.md` |
| Jinja around Helm — `values.yaml.j2`, raw manifests, post-renderers, the Helm-is-Go disambiguation | `references/helm-and-jinja.md` |
| Author a Helm chart (Go templates, `_helpers.tpl`, Sprig) | cross to the `helm` skill |

---

## The chat-template dialect at a glance

Every chat template in the HuggingFace ecosystem is rendered through an
`ImmutableSandboxedEnvironment` (`trim_blocks=True, lstrip_blocks=True`,
`loopcontrols` extension loaded, `tojson` filter forced to
`ensure_ascii=False`, `raise_exception` + `strftime_now` globals). vLLM
and sglang both delegate to `tokenizer.apply_chat_template`, so the
sandbox is the whole surface. `.append` / `.pop` / `.update` raise
`SecurityError`; `ext.do` / `ext.i18n` / `ext.debug` are NOT loaded.
Variables in scope: `messages`, `tools`, `documents`,
`add_generation_prompt`, all `special_tokens_map` entries, `date_string`,
plus caller `chat_template_kwargs`.

Full env config, sandbox rules, and canonical skeleton →
`references/chat-template/transformers-dialect.md` (env) and
`references/chat-template/authoring-patterns.md` (skeleton).

---

## The seven chat-template failure categories

Roughly 90% of real chat-template bugs. Templates written against these
defensive idioms survive the next model release.

| # | Category | Symptom | Defensive idiom |
|---|---|---|---|
| 1 | **Content-format bifurcation** | Template assumes `content` is a string; caller passes a list of parts. Python repr of the list lands in the prompt. | Branch `is string` → else `is sequence and is not string` → else `is mapping` → catch-all. Never `isinstance`. |
| 2 | **Loop-scope escape** | `{% set flag = true %}` inside `{% for %}` doesn't persist after the loop. | `{% set ns = namespace(flag=false) %}` then `{% set ns.flag = true %}`. |
| 3 | **`add_generation_prompt` bimodal** | Template hardcodes the assistant primer, breaking training; or reads the flag via `**kwargs`, so vLLM's AST detection can't see it. | Explicit `{% if add_generation_prompt %}` at the tail; render both modes in tests and diff. |
| 4 | **Tool-call shape variance** | `tool_call.function.arguments` is sometimes a JSON string, sometimes a dict. `tool_call.id` is optional. Unguarded access crashes. | `{{ args if args is string else args | tojson }}`; `tool_call.get('id', '')`. |
| 5 | **Whitespace control** | Stray `\n` before `<|im_start|>` shifts tokenization. Silent drift from coherent to broken. | `trim_blocks=True, lstrip_blocks=True` + aggressive `{%- -%}`. |
| 6 | **Special-token doubling** | BOS emitted by tokenizer (`add_bos_token=True`) AND by template (`{{ bos_token }}`) → double BOS. | Emit BOS in exactly one place. Check `tokenizer_config.json` before adding `{{ bos_token }}`. |
| 7 | **Sandbox mutation attempts** | `.append`, `.pop`, `.update` raise `SecurityError`. `{% do x.append(...) %}` doesn't parse (ext.do not loaded). | `namespace()` for accumulators; filter chains (`selectattr`, `map`, `join`) for transformations. |

Full examples, before/after code, canonical skeleton, and real-world
incidents → `references/chat-template/seven-failure-categories.md` +
`references/chat-template/authoring-patterns.md`.

---

## The Ansible dialect at a glance

Ansible is the largest Jinja-in-production deployment outside web frameworks.
It adds a long list of things to stock Jinja — recursive templating, lazy
variable resolution, the `!unsafe` tag, native-types mode, `hostvars`,
conditional expressions without delimiters (`when:`, `failed_when:`,
`changed_when:`, `until:`), custom filter/test/lookup plugins, and a 22-level
variable precedence system. None of it lives in Pallets Jinja.

Four rules carry most of the distance:

1. **`when:` takes a bare expression, not a Jinja template.** `when: "{{ foo
   }}"` is always wrong; write `when: foo`. Same for `failed_when:`,
   `changed_when:`, `until:`.
2. **`!unsafe` is all-or-nothing.** It disables templating for the whole
   value — *including lookups*. For mixed literal + templated content, use
   `{% raw %}...{% endraw %}`.
3. **Recursive templating amplifies errors.** A variable whose value is
   itself Jinja-looking renders again. An undefined reference in
   round-two produces an error message that mentions neither round.
4. **`| default(omit)` removes a task parameter entirely.** The idiomatic
   way to make a parameter conditional without duplicating task
   definitions.

Everything else (filters, lookups, `kubernetes.core.k8s + template`,
custom plugins, `ansible_managed`, debugging with `ansible-playbook
--check --diff`, `j2lint`, ten gotchas) → `references/ansible-dialect.md`.

---

## Helm and Jinja — what really runs where

**Helm charts do not use Jinja.** They use Go's `text/template` + Sprig. Any
`{{ ... }}` inside a chart is Go syntax. The two languages look identical
for the first ten seconds and diverge hard after that — `.` semantics,
pipe argument shape (`default 3` vs `default(3)`), Sprig's `toYaml` /
`required` / `lookup`, range rebinding. Chart authoring is owned by the
**`helm` skill**, not this one.

Where Jinja *does* show up in Kubernetes workflows:

1. **Ansible wraps Helm** — `values.yaml.j2` rendered by Ansible,
   installed via `community.kubernetes.helm`. Most common pattern.
2. **`jinja2-cli` preprocessor** — same shape without Ansible. Makefile
   or CI step renders `values.yaml.j2` → `values.yaml`, then
   `helm upgrade --install`.
3. **Raw Jinja manifests, no Helm** — small apps or air-gapped sites.
   Ansible `kubernetes.core.k8s` with `template: path/to.j2`.
4. **Helm post-renderer chained with Jinja** — niche; kustomize is
   usually the better fit here.
5. **kluctl** — actually Jinja-native for Kubernetes GitOps. One of the
   few 2026 tools that isn't Go underneath.
6. **`helm-jinja` plugins** — historically tried to swap Helm's engine;
   never thrived. Don't adopt in 2026. Use patterns 1/2/3 instead.

Full patterns, decision matrix, and the ten Go-vs-Jinja gotchas (`default`
arity, `.` scope, `toYaml`, `required` vs `mandatory`, `lookup`, CRD
ordering, `genCA` / `genSignedCert`, whitespace trim, double-templating)
→ `references/helm-and-jinja.md`.

---

## Out of scope

Generic Flask web templating, custom `ext.Extension` authoring, async Jinja
(`enable_async`), bytecode caching, custom loaders, and Helm chart authoring
itself (Go `text/template` + Sprig — use the **`helm` skill**). For anything
in this list, the Pallets docs at <https://jinja.palletsprojects.com/> are
authoritative for the core language.
