# Sources

Freshened: 2026-10-27 — every row probed; the `apply_chat_template` env contract is unchanged at transformers 5.21, and the Ansible rows now track the ansible-core 2.19+ templating overhaul.

Per-URL index of external references cited in the skill. `Last verified:`
is stamped by `freshen` mode; rows that fail to verify stay undated and
are re-probed on the next pass. Add `<!-- ignore-freshen -->` to any row
that should be pinned to an archival version.

The bare `jinja.palletsprojects.com/` root row redirects to `/en/stable/` — a root pointer behaving correctly, not drift.

The six docs.ansible.com rows have intermittently returned **429 to curl**; they always loaded in a browser at the cited URL with no redirect, and curl reached all six with 200 on 2026-10-27. A 429 there is a fetcher block — do not record these as dead.

| Source | Purpose | Last verified | Notes |
|---|---|---|---|
| https://jinja.palletsprojects.com/ | Pallets Jinja2 upstream — authoritative language reference | 2026-10-27 | Jinja2 still 3.1.6 — released 2025-03-05, no release in 19 months (PyPI, 2026-10-27). The pin is stable upstream, not a stale probe. chat-template env requires >=3.1.0 |
| https://jinja.palletsprojects.com/en/stable/templates/ | Core Jinja template syntax reference | 2026-10-27 | |
| https://jinja.palletsprojects.com/en/stable/sandbox/ | `SandboxedEnvironment` / `ImmutableSandboxedEnvironment` behavior | 2026-10-27 | |
| https://github.com/huggingface/transformers/blob/main/src/transformers/utils/chat_template_utils.py | HF `apply_chat_template` compilation code | 2026-10-27 | transformers **5.21** (2026-10-26). Template variables re-read on `main`: `apply_chat_template` passes `**special_tokens_map` (v5: named tokens only — `SPECIAL_TOKENS_ATTRIBUTES` bos/eos/unk/sep/pad/cls/mask, no extra tokens) plus kwargs; `date_string` is injected nowhere (absent from `tokenization_utils_base.py` / `chat_template_utils.py` at v4.43.0, v4.45.0 and main — templates set it themselves via `strftime_now`). 5.21 also adds `_alias_reasoning_fields` (huggingface/transformers#49535: `_REASONING_FIELDS = ("reasoning_content", "thinking", "reasoning")`, applied in `render_jinja_template`) ; `apply_chat_template(sanitize_control_tokens=...)` (#47386, default False) shipped earlier, in v5.20.0. Earlier: 5.9.0 → 5.14.1 (2026-07-16). Env contract re-read line-by-line against `main` and **unchanged**: `ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, extensions=[AssistantTracker, jinja2.ext.loopcontrols])`, `tojson` overridden with `ensure_ascii=False`, `raise_exception` + `strftime_now` globals. **But the two compile functions have swapped roles — see the note below.** |
| https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_templating.html | Ansible templating overview | 2026-10-27 | ansible-core 2.21.5 (PyPI, 2026-10-05); 2.22 only as 2.22.0rc1. Templating semantics come from the 2.19 overhaul — porting guide `porting_guide_core_2.19.rst` (ansible/ansible-documentation) §"Native Jinja mode required", and `lib/ansible/config/base.yml` at `v2.21.5`: `DEFAULT_JINJA2_NATIVE` default True, deprecated ("native mode is now the default and only option", removal 2.23); `ALLOW_BROKEN_CONDITIONALS` default false (non-boolean conditional = error, since 2.19); `ALLOW_EMBEDDED_TEMPLATES` default true (fully-wrapped `{{ }}` conditional = deprecation warning). Porting guide §"Broken Conditionals", §"Multi-pass templating" |
| https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_filters.html | Ansible built-in + collection filters | 2026-10-27 | |
| https://docs.ansible.com/projects/ansible/latest/plugins/lookup.html | Ansible lookups | 2026-10-27 | |
| https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/k8s_module.html | `kubernetes.core.k8s` module reference | 2026-10-27 | |
| https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/helm_module.html | `kubernetes.core.helm` module reference | 2026-10-27 | kubernetes.core 6.6.0 on Galaxy (2026-10-27); `plain_http` added in 6.1.0 (ansible-collections/kubernetes.core#934, CHANGELOG.rst), OCI chart installs fixed for Helm 4.2.1 output in 6.6.0 (#1223). ansible-collections/community.kubernetes: `archived: true` (last push 2021-11-08), Galaxy highest 2.0.1; `meta/runtime.yml` redirects `helm` → `kubernetes.core.helm`, `k8s_info` → `kubernetes.core.k8s_info` with deprecation (removal_version 3.0.0) — no 3.x exists |
| https://docs.ansible.com/projects/lint/ | ansible-lint documentation | 2026-10-27 | |
| https://pypi.org/project/j2lint/ | j2lint PyPI page | 2026-10-27 | Latest release 2026-07-30 (PyPI, 2026-10-27). Use latest stable; do not pin inline (see freshness rules) |
| https://github.com/ansible-actions/j2lint-action | j2lint GitHub Action for CI | 2026-10-27 | Not archived; only release v0.0.1 (2023-10-20), last push 2024-10-25 |
| https://pypi.org/project/jinja2-cli/ | jinja2-cli preprocessor (`pip install jinja2-cli[yaml]`, `--strict`) | 2026-10-27 | Latest stable 1.0.1 (2026-04-05), unchanged 2026-10-27; `[yaml]` extra + `--strict` flag valid |
| https://gist.github.com/mkrizek/dbcf415b485fc3f2d4b3676ce0013397 | Ansible + Jinja2 native-types discussion | 2026-10-27 | Informational gist, not official docs |
| https://helm.sh/docs/chart_template_guide/ | Helm Go `text/template` + Sprig chart guide | 2026-10-27 | |
| https://github.com/vllm-project/vllm/pull/32473 | vLLM `/v1/chat/completions/render` endpoint (added 2026-01-19); `vllm launch` GPU-less server is #34551, `vllm launch render` #36166 | 2026-10-27 | Response model is `GenerateRequest` (`token_ids`, no prompt text) since at least v0.24.0. 403 unless `--enable-scale-out` from v0.30.0 (#54579, #55176; `scale_out/factories.py`). `/detokenize` returns `prompt` (DetokenizeResponse, unchanged since v0.8.0). `developer`→`system` rewrite and template-exception → 400: `vllm/renderers/hf.py` `safe_apply_chat_template` on main @ 8977b13a1c (old `entrypoints/openai/serving_chat.py` path is gone). Python encoders (no Jinja): `vllm/tokenizers/{deepseek_v32,deepseek_v4,deepseek_v41,mistral}.py` (mistral → transformers `MistralCommonBackend` → mistral-common `encode_chat_completion`); sglang `python/sglang/srt/entrypoints/openai/chat_encoding.py` `resolve_chat_encoding_spec` (dsv32/dsv4/dsv41/kimi_k3) |
| https://github.com/ggml-org/llama.cpp/blob/master/common/jinja/README.md | llama.cpp's native Jinja engine (replaced minja) | 2026-10-27 | Introduced by ggml-org/llama.cpp#18462, first commit to `common/jinja` 2026-01-16; `vendor/` no longer carries minja. README: modelled on huggingface.js jinja; `jinja::string` `is_input` marking against special-token injection. google/minja not archived, last push 2025-09-22 |
| https://github.com/helm/helm/issues/6184 | Helm RFC "Pluggable templating engines" | 2026-10-27 | CLOSED 2020-09-05 — never accepted; Helm stays Go-only through 2026 (re-confirmed closed 2026-10-27; last comment points proposers at the HIP process) |
| https://kluctl.io | kluctl — Jinja-native Kubernetes deployment tool | 2026-10-27 | Homepage still describes Jinja templating (2026-10-27); latest stable kluctl-v2.28.2 (2026-06-25) |
| https://www.home-assistant.io/docs/templating/ | Home Assistant Jinja templating (mentioned as "out of scope" pointer) | 2026-10-27 | |
| https://github.com/unslothai/unsloth | Unsloth — community chat-template patches | 2026-10-27 | Mentioned in exemplars |
| https://github.com/chujiezheng/chat_templates | chujiezheng/chat_templates community collection | 2026-10-27 | Mentioned in exemplars. Repo `archived: true`, last push 2024-12-13 (gh api, 2026-10-27) |
| https://github.com/axolotl-ai-cloud/axolotl | Axolotl training framework — ships chat templates | 2026-10-27 | Mentioned in exemplars |

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
