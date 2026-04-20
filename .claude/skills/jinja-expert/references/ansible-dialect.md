# Ansible Jinja dialect

Ansible is the largest Jinja-in-production deployment outside web frameworks.
Jinja renders on the **control node** before tasks ship to managed hosts, so
every variable resolution, template, and expression in a playbook passes
through a Jinja pipeline that is *Ansible-flavored*, not stock Pallets Jinja.

This file is the reference for that dialect — what it adds, what it breaks,
and the failure modes that recur across real Ansible codebases in 2026.

For core statement/expression/filter syntax, see `language-surface.md`. For
the chat-template dialect (`ImmutableSandboxedEnvironment`, `tojson
ensure_ascii=False`, etc.), see `chat-template/transformers-dialect.md`.

---

## Table of contents

1. What Ansible adds on top of Jinja2
2. Where templating fires — the evaluation surface
3. Variable precedence and `hostvars`
4. Native types (`jinja2_native`)
5. The `!unsafe` tag and double-templating
6. `{% raw %}` and `{{ '{{' }}` escaping
7. The `when:` and conditional trap
8. Built-in filters (Ansible-specific)
9. Lookups and the `template` lookup
10. Custom filter/test/lookup plugins
11. `ansible_managed` and header templates
12. Rendering Kubernetes manifests from Jinja
13. Debugging Jinja in Ansible (`ansible-playbook --check --diff`, `debug`,
    `j2lint`)
14. Ten gotchas that bite every Ansible engineer at some point

---

## 1. What Ansible adds on top of Jinja2

Ansible wraps Jinja2 with:

- **Undefined handling** — references to undefined vars raise
  `AnsibleUndefinedVariable`, not the silent-empty behavior of stock Jinja's
  default `Undefined`. `| default(x)` suppresses it. `| default(omit)`
  *removes* the parameter from the task call entirely.
- **Recursive templating** — if a variable's value is itself a template,
  Ansible renders it again (and again) until the result is stable or a
  recursion cap trips. This is the single largest source of surprise.
- **Lazy templating** — variables aren't rendered at definition time; they're
  rendered when a task actually reads them. Change one `set_fact` earlier in
  the play and a downstream template sees the new value.
- **`hostvars`** — a dict-of-dicts giving access to every other host's
  variables. Load-bearing for multi-host orchestration; easy to accidentally
  template the wrong host's value.
- **Conditional eval** — `when:`, `failed_when:`, `changed_when:`, `until:`
  evaluate as Jinja expressions *without* the usual `{{ ... }}` wrappers.
  Writing `when: "{{ foo }}"` is almost always wrong (see §7).
- **Native-types mode** — opt-in flag (since Ansible 2.7, off by default as
  of 2.10) that makes renders return Python objects rather than strings
  (§4).
- **Custom filters/tests/lookups** — dropped into `filter_plugins/`,
  `test_plugins/`, `lookup_plugins/` adjacent to the playbook, in a role, or
  inside a collection (§10).
- **`ansible_managed`** — a configurable string that a best-practice template
  renders into its own header so that humans and tooling know the file is
  managed (§11).

None of these live in Pallets Jinja. Assuming stock behavior in an Ansible
codebase is a reliable way to generate confusing bugs.

---

## 2. Where templating fires — the evaluation surface

Ansible runs Jinja in more places than most people realize:

| Surface | Delimiter | Example |
|---|---|---|
| Template files (`.j2`) | `{{ }} {% %}` | `templates/nginx.conf.j2` |
| Task args | `{{ }}` in YAML strings | `name: "{{ pkg_name }}"` |
| `when:` / `failed_when:` / `changed_when:` / `until:` | Bare expression (no delimiters) | `when: ansible_os_family == "RedHat"` |
| `loop:` / `with_items:` / `with_*` | Bare expression | `loop: "{{ groups['web'] }}"` |
| `vars:` values | `{{ }}` in the value | `app_port: "{{ base_port + 1 }}"` |
| `debug: msg:` | `{{ }}` | `msg: "host: {{ inventory_hostname }}"` |
| `assert: that:` | Bare expression | `that: user_count > 0` |
| `set_fact` RHS | `{{ }}` | `set_fact: total="{{ a | int + b | int }}"` |
| Inventory (`group_vars/`, `host_vars/`) | `{{ }}` | `api_url: "https://{{ env }}.api.example.com"` |

The two delimiter families matter: conditionals want bare expressions;
strings want `{{ ... }}`. Mixing them (§7) is the #1 ansible-lint warning.

---

## 3. Variable precedence and `hostvars`

Ansible's variable precedence is 22 levels deep. The three levels that matter
for Jinja debugging, from lowest to highest:

1. **`group_vars/all`** — applies to every host.
2. **`host_vars/<host>` / `group_vars/<group>`** — narrower scope wins.
3. **`set_fact`** — overrides everything below it for the current play.

When a template renders `{{ my_var }}`, the value comes from the highest
layer that defined `my_var` *for the current host at render time*. That last
qualifier is the trap: `hostvars['other_host'].my_var` reads `other_host`'s
view of `my_var`, not the current host's.

```yaml
- name: wrong — pulls inventory of the controller, not of the db host
  template:
    src: app.conf.j2
    dest: /etc/app.conf
  vars:
    db_ip: "{{ hostvars['db01'].ansible_default_ipv4.address }}"
```

If `db01` hasn't been fact-gathered yet in this run, `ansible_default_ipv4`
is undefined on that host. The template crashes at render time, on the host
that doesn't even need `db_ip`. Solution: depend on `gather_facts: true` for
`db01` earlier, or use `delegate_to: db01` + `delegate_facts: true` to
populate facts on it explicitly.

---

## 4. Native types (`jinja2_native`)

Stock Jinja always returns a string. Ansible can opt into native Python types
by setting `ANSIBLE_JINJA2_NATIVE=1` (env), `jinja2_native = True` in
`ansible.cfg`, or `DEFAULT_JINJA2_NATIVE`. Off by default as of 2.10;
stabilized since 2.7.

```yaml
# Without jinja2_native
- debug: var=foo
  vars:
    foo: "{{ [1, 2, 3] }}"
# => foo: "[1, 2, 3]"     (a STRING)

# With jinja2_native
# => foo: [1, 2, 3]        (a LIST)
```

**When to enable:** expressions must yield real Python dicts/lists
without `| from_yaml` / `| from_json` wrappers. Common in 2026 codebases
that pass structured data between tasks.

**When to avoid:** legacy playbooks that depend on the string coercion. A
template that writes `"{{ some_list }}"` into a config file and expects the
Python `repr` output will break silently — native mode returns the list
*object*, not a rendered string. YAML serialization then turns it back into
a different shape.

**Test before flipping the flag in a mature codebase.** Even simple
expressions can change type:

- `"{{ 3 }}"` — string `"3"` without, int `3` with.
- `"{{ true }}"` — string `"True"` without, bool `True` with.
- `"{{ '42' | int }}"` — always int (explicit filter).

Since the rollout is all-or-nothing per Ansible config, staging this through
one playbook first and checking `ansible-playbook --check --diff` output is
the safe path.

---

## 5. The `!unsafe` tag and double-templating

Ansible re-templates variables lazily. If a variable's value contains
Jinja-looking syntax, Ansible will try to render that too. Usually benign;
occasionally catastrophic.

```yaml
user_motd: "Welcome {{ user }}! Today is {{ ansible_date_time.date }}."
```

Fine — `{{ user }}` and `{{ ansible_date_time.date }}` both resolve. But:

```yaml
user_password: "S3cr3t{{notReallyAVariable}}P@ss"
```

Ansible tries to resolve `notReallyAVariable`, raises
`AnsibleUndefinedVariable`, and the play dies. The fix is to mark the value
as un-templateable:

```yaml
user_password: !unsafe "S3cr3t{{notReallyAVariable}}P@ss"
```

`!unsafe` is all-or-nothing — **no Jinja in the whole value**. Lookups
inside an `!unsafe`-tagged value don't resolve. The string is opaque.

For mixed content (some parts template, some are literal), use `{% raw %}`
or the inline escape trick:

```yaml
# mixed: welcome comes from a variable; the {{literal}} stays literal
banner: "Welcome {{ user }} to {% raw %}{{literal_braces}}{% endraw %} zone"

# single literal `{{` inline:
quirky: "Use {{ '{{' }} and {{ '}}' }} to escape braces."
```

`{% raw %}` wins on readability when embedding example Jinja (docs, error
messages, a config file with its own Jinja or Go template syntax inside —
a k8s ConfigMap containing a Helm template, say).

---

## 6. `{% raw %}` and `{{ '{{' }}` escaping

Three idioms:

| Idiom | Scope | Use when |
|---|---|---|
| `!unsafe ...` | Whole value | No Ansible vars anywhere in the value |
| `{% raw %}...{% endraw %}` | Region | Mix literal Jinja-looking text with Ansible vars |
| `{{ '{{' }}` | Single token | One-off literal `{{` next to real variables |

Common failure: generating a Jinja template from Jinja. The outer Jinja runs
first, then the rendered file ships to a machine and is run by another Jinja
(e.g. Ansible generating a chat template, or a dbt model, or a SaltStack
state). Without `{% raw %}`, the outer renderer eats the inner's
placeholders.

```jinja
{# outer ansible template writing a chat template #}
{% raw %}
{% for msg in messages %}
  <|im_start|>{{ msg.role }}
  {{ msg.content }}<|im_end|>
{% endfor %}
{% endraw %}
```

Outer leaves everything inside `{% raw %}` alone. File on disk contains
literal `{{ msg.role }}` for the inner Jinja to see.

---

## 7. The `when:` and conditional trap

`when:` takes a Jinja *expression*, not a Jinja *template*. Writing `{{ ...
}}` inside `when:` causes ansible-lint to warn and produces wrong behavior
in edge cases (the wrapped value coerces to a truthy string).

```yaml
# WRONG — ansible-lint: no-jinja-when
- command: /usr/bin/reboot
  when: "{{ reboot_required }}"

# RIGHT
- command: /usr/bin/reboot
  when: reboot_required
```

The rule applies to every conditional surface:

- `when:`
- `failed_when:`
- `changed_when:`
- `until:`

It does **not** apply to `loop:` / `with_*` — those take a rendered value,
so `{{ }}` is correct there.

The reason is that Ansible already treats the value as a Jinja expression.
Wrapping it in `{{ }}` renders the expression to a string (e.g. `"True"`)
and then evaluates that string as a new expression — which happens to work
for simple booleans but fails subtly for `None`, empty strings, numbers,
and anything with quoting.

---

## 8. Built-in filters (Ansible-specific)

These filters aren't in Pallets Jinja. They ship with Ansible and are
frequently needed:

| Filter | Purpose |
|---|---|
| `to_json`, `to_nice_json`, `from_json` | JSON serialization (nice variants pretty-print) |
| `to_yaml`, `to_nice_yaml`, `from_yaml`, `from_yaml_all` | YAML |
| `bool` | Coerce to boolean (`"yes"` / `"true"` / `"1"` → `True`) |
| `int`, `float` | Numeric coercion |
| `default(x)` / `default(x, true)` | Stock Jinja `default`; the second arg makes it fire on *falsy* values, not just undefined |
| `default(omit)` | Remove the parameter entirely if the variable is undefined |
| `mandatory` | Raise with a clear message if the var is missing (instead of generic `AnsibleUndefinedVariable`) |
| `ternary(true_val, false_val)` | Inline conditional |
| `combine(dict2, recursive=true)` | Deep-merge dicts (the #1 reason to use `to_nice_yaml` on complex configs) |
| `difference`, `intersect`, `union`, `symmetric_difference` | Set operations on lists |
| `unique`, `flatten` | List cleanup |
| `zip`, `zip_longest`, `subelements` | Pair iteration |
| `dict2items`, `items2dict` | Dict ↔ list-of-`{key, value}` (iterable shape for `loop:`) |
| `regex_search`, `regex_findall`, `regex_replace` | Regex |
| `hash('sha256')`, `password_hash('sha512')` | Cryptographic hashes (password_hash is salt-aware) |
| `b64encode`, `b64decode` | Base64 |
| `ansible.utils.ipaddr(...)` | IP math (requires `ansible.utils` collection) |
| `community.general.json_query('...')` | JMESPath over structured data |
| `vault`, `vaulted` | Ansible Vault interop |

`combine` with `recursive=true` and `list_merge='append'` is the modern
idiom for layered config:

```yaml
- template:
    src: app.yml.j2
    dest: /etc/app.yml
  vars:
    merged: "{{ defaults | combine(env_override, role_override, recursive=true, list_merge='append') }}"
```

---

## 9. Lookups and the `template` lookup

Lookups run on the **control node**. They read local files, hit HTTP, query
vaults, enumerate groups. Inside a Jinja expression:

```jinja
{{ lookup('env', 'HOME') }}
{{ lookup('file', '/etc/hostname') | trim }}
{{ lookup('ansible.builtin.template', 'snippet.j2') }}
{{ lookup('url', 'https://ifconfig.co/json') | from_json }}
{{ lookup('community.hashi_vault.hashi_vault', 'secret=kv/data/app token=xyz') }}
```

`lookup('template', 'foo.j2')` renders a Jinja template with the *current*
variable context and returns the rendered string. The canonical way to
produce structured data from a template for consumption by the `k8s` /
`kubernetes.core.k8s` module:

```yaml
- name: apply a rendered manifest
  kubernetes.core.k8s:
    state: present
    definition: "{{ lookup('template', 'deployment.yml.j2') | from_yaml }}"
```

Or, using the `template:` parameter directly (preferred for single-document
manifests):

```yaml
- name: apply a templated manifest
  kubernetes.core.k8s:
    state: present
    template: templates/deployment.yml.j2
```

The `kubernetes.core.k8s` module supports `variable_start_string` /
`variable_end_string` when the target template has its own `{{ }}` syntax
that must be protected — useful when emitting a chart or another Jinja
template.

**`query('...')` vs `lookup('...')`:** `query` returns a list; `lookup`
returns a joined string. Use `query` almost always for structured data to
avoid accidental string-joining.

---

## 10. Custom filter/test/lookup plugins

Ansible searches these paths, first match wins:

1. Playbook-adjacent `filter_plugins/`, `test_plugins/`, `lookup_plugins/`
2. Role's `<role>/filter_plugins/` etc.
3. Collection's `plugins/filter/` etc.
4. `ansible.cfg`'s `filter_plugins` / `test_plugins` / `lookup_plugins` paths
5. System install directory

Minimal custom filter (`filter_plugins/my_filters.py`):

```python
def kebab(value):
    return "-".join(str(value).lower().split())

def strip_prefix(value, prefix):
    return value[len(prefix):] if value.startswith(prefix) else value

class FilterModule:
    def filters(self):
        return {
            "kebab": kebab,
            "strip_prefix": strip_prefix,
        }
```

Used as `{{ "Hello World" | kebab }}` → `hello-world`.

**Write a filter, not a Jinja extension.** Jinja extensions require a lot
more ceremony (`ext.Extension` subclass, parser overrides) and aren't
loaded by default in Ansible's sandboxed path anyway. Filters cover 99% of
"I want a custom transformation" cases.

**Tests** (`test_plugins/my_tests.py`) are the `is X` variant — predicates
that return `True`/`False`. They pair with `| selectattr('attr', 'is',
'my_test')` patterns.

**Lookups** (`lookup_plugins/my_lookup.py`) run on the control node and
return arbitrary data (list). Heavier to write but necessary when I/O
(HTTP, secrets backend) is required from within an expression.

Ship plugins inside a collection if they outgrow a single playbook —
collection-packaged plugins play nicer with Ansible Galaxy, CI, and
Ansible-lint's schema.

---

## 11. `ansible_managed` and header templates

Every generated config file should identify itself as Ansible-managed so a
human editing the file by hand is warned that their changes will be
overwritten. The canonical idiom:

```jinja
# {{ ansible_managed }}
#
# Generated from {{ template_path | default('templates/' + template_name) }}
# on {{ ansible_date_time.iso8601 }} for host {{ inventory_hostname }}.
# Do not edit by hand.

{# ... rest of template ... #}
```

`ansible_managed` is a string configured in `ansible.cfg`:

```ini
[defaults]
ansible_managed = Ansible managed: {file} on {host}
```

Ansible fills in `{file}` and `{host}` at render time. Some shops include
the git commit so a deployed file points back to the exact commit that
generated it.

---

## 12. Rendering Kubernetes manifests from Jinja

The cleanest idiom for "I want Jinja-templated manifests, not a Helm chart":

```yaml
- name: apply namespace-scoped manifests
  kubernetes.core.k8s:
    state: present
    template:
      path: "{{ item }}"
  loop:
    - templates/namespace.yaml.j2
    - templates/deployment.yaml.j2
    - templates/service.yaml.j2
    - templates/configmap.yaml.j2

- name: apply conditionally-included manifest
  kubernetes.core.k8s:
    state: "{{ 'present' if enable_autoscaler else 'absent' }}"
    template: templates/hpa.yaml.j2
```

Multi-document YAML (`---` separators) works via `from_yaml_all`:

```yaml
- name: apply a multi-doc manifest
  kubernetes.core.k8s:
    state: present
    definition: "{{ item }}"
  loop: "{{ lookup('template', 'bundle.yaml.j2') | from_yaml_all | list }}"
```

For the tradeoff vs. Helm, see `helm-and-jinja.md`.

---

## 13. Debugging Jinja in Ansible

**`ansible-playbook --check --diff`** — dry-run with diffs. Shows the
rendered template as it would be written, without shipping it. First line
of defense.

**`debug` module** — the Jinja REPL:

```yaml
- debug:
    msg: "user={{ user }}, type={{ user | type_debug }}, empty={{ user | length == 0 }}"
```

`type_debug` is invaluable in native-types-enabled playbooks. Prints the
actual Python type at render time.

**`-vvv`** — three-verbose shows rendered task arguments. The fourth v adds
connection-plugin noise, rarely worth it.

**`ANSIBLE_DEBUG=1`** — enables the Jinja renderer's own debug logs
(template cache hits, recursion depth, undefined attempts). Very noisy.

**`j2lint`** — static linter for `.j2` files. Catches
`jinja-variable-lower-case`, `jinja-delimiter`, `filter-enclosed-by-spaces`,
`single-space-decorator`, `jinja-statements-indentation`, and ~15 others.
Integrates into CI via `ansible-actions/j2lint-action`.

**`ansible-lint`** — playbook-level linter. Catches the `when: "{{ ... }}"`
trap, missing `default`, and most schema issues. Use `ansible-lint
--profile=production` for the strictest rule set.

**Jinja's `debug` extension is NOT loaded by default.** `{% debug %}` won't
work. Use the `debug` module instead.

---

## 14. Ten gotchas that bite every Ansible engineer at some point

1. **`when: "{{ foo }}"`** — delimiters inside conditionals. Covered in §7.
2. **`!unsafe` swallowing lookups.** Marking a value `!unsafe` disables
   *all* templating, including lookups that happen to appear in the value.
   Use `{% raw %}` for mixed content instead.
3. **Recursive templating amplifies errors.** A template that reads
   `{{ foo }}`, where `foo` is `"{{ bar }}"`, renders twice. If `bar` is
   undefined on the second pass, the error message mentions neither
   `foo` nor `bar` clearly.
4. **`ignore_errors: true` doesn't skip template errors.** Template render
   failures happen before the task runs; `ignore_errors` catches task
   failures. Use `| default(...)` or `| default(omit)` to prevent the
   render from failing in the first place.
5. **Facts not gathered for referenced host.** `hostvars['other'].foo`
   raises if `other` hasn't been fact-gathered. Always `gather_facts: true`
   or use `delegate_facts`.
6. **Integer-looking strings.** `some_var: "0123"` is a string `"0123"` in
   YAML (leading zero) but renders as `"0123"`. Chain `| int` or use
   `jinja2_native` mode to get the numeric value.
7. **Boolean-looking strings.** `"yes"`, `"no"`, `"on"`, `"off"` parse as
   bools in YAML but not in rendered templates. Use `| bool` to recover
   the YAML-style coercion after a string passes through Jinja.
8. **`combine` without `recursive=true`.** Default is shallow merge.
   Nested keys in the right-hand dict overwrite whole subtrees on the
   left. Almost never the intended behavior.
9. **`loop: "{{ dict }}"`** — iterates keys, not items. Use
   `{{ dict | dict2items }}` to iterate `{key, value}` pairs.
10. **Template reference is recursive.** If a template does
    `{% include 'common.j2' %}`, and `common.j2` references a variable the
    parent template defined with `{% set %}`, the include fires with its
    own scope *unless* vars are passed explicitly via `{% include
    'common.j2' with context %}`.

---

## See also

- **Ansible docs — Templating**:
  <https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_templating.html>
- **Ansible docs — Filters**:
  <https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_filters.html>
- **Ansible docs — Lookups**:
  <https://docs.ansible.com/projects/ansible/latest/plugins/lookup.html>
- **`kubernetes.core.k8s` module**:
  <https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/k8s_module.html>
- **j2lint** (rules + GitHub action):
  <https://pypi.org/project/j2lint/>,
  <https://github.com/ansible-actions/j2lint-action>
- **ansible-lint**: <https://docs.ansible.com/projects/lint/>
- **Native types gist / discussion**:
  <https://gist.github.com/mkrizek/dbcf415b485fc3f2d4b3676ce0013397>
