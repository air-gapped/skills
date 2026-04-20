# Sources

Per-URL index of external references cited in the skill. `Last verified:`
is stamped by `freshen` mode; rows that fail to verify stay undated and
are re-probed on the next pass. Add `<!-- ignore-freshen -->` to any row
that should be pinned to an archival version.

| Source | Purpose | Last verified | Notes |
|---|---|---|---|
| https://jinja.palletsprojects.com/ | Pallets Jinja2 upstream — authoritative language reference | 2026-04-20 | |
| https://jinja.palletsprojects.com/en/stable/templates/ | Core Jinja template syntax reference | 2026-04-20 | |
| https://jinja.palletsprojects.com/en/stable/sandbox/ | `SandboxedEnvironment` / `ImmutableSandboxedEnvironment` behavior | 2026-04-20 | |
| https://github.com/huggingface/transformers/blob/main/src/transformers/utils/chat_template_utils.py | HF `apply_chat_template` compilation code — function is `_cached_compile_jinja_template` (verified 2026-04-20) | 2026-04-20 | Pinned path on `main`; file has been renamed historically, verify on drift |
| https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_templating.html | Ansible templating overview | 2026-04-20 | Via earlier WebSearch — page CDN-blocks generic bot fetches |
| https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_filters.html | Ansible built-in + collection filters | 2026-04-20 | |
| https://docs.ansible.com/projects/ansible/latest/plugins/lookup.html | Ansible lookups | 2026-04-20 | |
| https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/k8s_module.html | `kubernetes.core.k8s` module reference | 2026-04-20 | |
| https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/helm_module.html | `kubernetes.core.helm` module reference | 2026-04-20 | |
| https://docs.ansible.com/projects/lint/ | ansible-lint documentation | 2026-04-20 | |
| https://pypi.org/project/j2lint/ | j2lint PyPI page | 2026-04-20 | Version 1.2.0 released 2025-04-04 (per upstream research) |
| https://github.com/ansible-actions/j2lint-action | j2lint GitHub Action for CI | 2026-04-20 | |
| https://gist.github.com/mkrizek/dbcf415b485fc3f2d4b3676ce0013397 | Ansible + Jinja2 native-types discussion | 2026-04-20 | Informational gist, not official docs |
| https://helm.sh/docs/chart_template_guide/ | Helm Go `text/template` + Sprig chart guide | 2026-04-20 | |
| https://github.com/helm/helm/issues/6184 | Helm RFC "Pluggable templating engines" | 2026-04-20 | CLOSED 2020-09-05 — never accepted; Helm stays Go-only through 2026 |
| https://kluctl.io | kluctl — Jinja-native Kubernetes deployment tool | 2026-04-20 | Confirmed Jinja2 integration on homepage |
| https://www.home-assistant.io/docs/configuration/templating/ | Home Assistant Jinja templating (mentioned as "out of scope" pointer) | 2026-04-20 | |
| https://github.com/unslothai/unsloth | Unsloth — community chat-template patches | 2026-04-20 | Mentioned in exemplars |
| https://github.com/chujiezheng/chat_templates | chujiezheng/chat_templates community collection | 2026-04-20 | Mentioned in exemplars |
| https://github.com/axolotl-ai-cloud/axolotl | Axolotl training framework — ships chat templates | 2026-04-20 | Mentioned in exemplars |

## Freshness rules

- Any row not verified in the last 90 days is fair game for re-probing.
- If a URL 403s / 404s but the content is still canonical (CDN bot blocks
  are common on docs.ansible.com), annotate the source of verification in
  `Notes` (earlier WebSearch, archive.org snapshot, official RSS) and
  still stamp `Last verified:`.
- Version numbers cited inline in the skill (e.g. "j2lint 1.2.0") should
  be dropped in favor of "latest stable" unless the pin is load-bearing.
