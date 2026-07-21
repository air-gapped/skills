# Sources

Per-URL index of external references cited in the skill. `Last verified:`
is stamped by `freshen` mode; rows that fail to verify stay undated and
are re-probed on the next pass. Add `<!-- ignore-freshen -->` to any row
that should be pinned to an archival version.

| Source | Purpose | Last verified | Notes |
|---|---|---|---|
| https://jinja.palletsprojects.com/ | Pallets Jinja2 upstream — authoritative language reference | 2026-07-21 | Jinja2 still 3.1.6 — released 2025-03-05, no release in 16 months. The pin is stable upstream, not a stale probe. chat-template env requires >=3.1.0 |
| https://jinja.palletsprojects.com/en/stable/templates/ | Core Jinja template syntax reference | 2026-04-20 | |
| https://jinja.palletsprojects.com/en/stable/sandbox/ | `SandboxedEnvironment` / `ImmutableSandboxedEnvironment` behavior | 2026-04-20 | |
| https://github.com/huggingface/transformers/blob/main/src/transformers/utils/chat_template_utils.py | HF `apply_chat_template` compilation code | 2026-07-21 | transformers 5.9.0 → **5.14.1** (2026-07-16). Env contract re-read line-by-line against `main` and **unchanged**: `ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, extensions=[AssistantTracker, jinja2.ext.loopcontrols])`, `tojson` overridden with `ensure_ascii=False`, `raise_exception` + `strftime_now` globals. **But the two compile functions have swapped roles — see the note below.** |
| https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_templating.html | Ansible templating overview | 2026-07-21 | Via WebSearch — page CDN-blocks generic bot fetches. ansible-core 2.21.0 → 2.21.2 (PyPI, 2026-07-13, patch only); native-types history (2.7 stabilized, 2.10 off-by-default) and bare-expression `when:` semantics unchanged |
| https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_filters.html | Ansible built-in + collection filters | 2026-04-20 | |
| https://docs.ansible.com/projects/ansible/latest/plugins/lookup.html | Ansible lookups | 2026-04-20 | |
| https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/k8s_module.html | `kubernetes.core.k8s` module reference | 2026-04-20 | |
| https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/helm_module.html | `kubernetes.core.helm` module reference | 2026-04-20 | |
| https://docs.ansible.com/projects/lint/ | ansible-lint documentation | 2026-04-20 | |
| https://pypi.org/project/j2lint/ | j2lint PyPI page | 2026-07-21 | Probed; no new release since the last pass. Use latest stable; do not pin inline (see freshness rules) |
| https://github.com/ansible-actions/j2lint-action | j2lint GitHub Action for CI | 2026-04-20 | |
| https://pypi.org/project/jinja2-cli/ | jinja2-cli preprocessor (`pip install jinja2-cli[yaml]`, `--strict`) | 2026-07-21 | Latest stable 1.0.1 (2026-04-05); `[yaml]` extra + `--strict` flag valid |
| https://gist.github.com/mkrizek/dbcf415b485fc3f2d4b3676ce0013397 | Ansible + Jinja2 native-types discussion | 2026-04-20 | Informational gist, not official docs |
| https://helm.sh/docs/chart_template_guide/ | Helm Go `text/template` + Sprig chart guide | 2026-04-20 | |
| https://github.com/helm/helm/issues/6184 | Helm RFC "Pluggable templating engines" | 2026-07-21 | CLOSED 2020-09-05 — never accepted; Helm stays Go-only through 2026 (re-confirmed closed 2026-07-21, incl. across the Helm 4 line) |
| https://kluctl.io | kluctl — Jinja-native Kubernetes deployment tool | 2026-04-20 | Confirmed Jinja2 integration on homepage |
| https://www.home-assistant.io/docs/configuration/templating/ | Home Assistant Jinja templating (mentioned as "out of scope" pointer) | 2026-04-20 | |
| https://github.com/unslothai/unsloth | Unsloth — community chat-template patches | 2026-04-20 | Mentioned in exemplars |
| https://github.com/chujiezheng/chat_templates | chujiezheng/chat_templates community collection | 2026-04-20 | Mentioned in exemplars |
| https://github.com/axolotl-ai-cloud/axolotl | Axolotl training framework — ships chat templates | 2026-04-20 | Mentioned in exemplars |

## The transformers compile-function name trap — 2026-07-21

`chat_template_utils.py` defines **two** functions whose names now say the
opposite of what they do:

```python
@lru_cache
def _compile_jinja_template(chat_template):        # <- THIS is the cached one
    return _cached_compile_jinja_template(chat_template)

@no_type_check
def _cached_compile_jinja_template(chat_template): # <- despite the name, NOT cached
    ...                                            #    builds the env, returns from_string()
```

`render_jinja_template()` calls `_compile_jinja_template`. So when patching
the environment for debugging, or reasoning about why an edited template still
renders the old output, the cache to defeat is on `_compile_jinja_template` —
the one *without* `cached` in its name. This row previously named
`_cached_compile_jinja_template` as "the" compilation function, which is now
the uncached builder.

## Freshness rules

- Any row not verified in the last 90 days is fair game for re-probing.
- If a URL 403s / 404s but the content is still canonical (CDN bot blocks
  are common on docs.ansible.com), annotate the source of verification in
  `Notes` (earlier WebSearch, archive.org snapshot, official RSS) and
  still stamp `Last verified:`.
- Version numbers cited inline in the skill (e.g. "j2lint 1.2.0") should
  be dropped in favor of "latest stable" unless the pin is load-bearing.
