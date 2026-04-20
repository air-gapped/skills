# Helm and Jinja — what really runs where

**TL;DR — Helm charts do not use Jinja.** They use Go's `text/template`
package with the Sprig function library. Any `{{ ... }}` in a
`.tpl`, `_helpers.tpl`, `templates/*.yaml`, or `values.yaml.gotmpl` file is
Go template syntax, not Jinja. The two look alike for the first ten
seconds and diverge hard after that.

This file exists because "Jinja for Kubernetes" is a real and common
workflow — it just almost never lives *inside* a Helm chart. It lives
*around* Helm, or instead of it. Knowing which is which prevents hours of
wasted time.

For chart authoring itself (`_helpers.tpl`, `values.schema.json`, library
charts, helm-unittest, OCI push), use the **`helm` skill** — that's its
exact domain. This file covers only the Jinja-adjacent patterns.

---

## Table of contents

1. Helm ≠ Jinja — the quick disambiguation
2. The 2026 landscape — where Jinja and Helm actually meet
3. Pattern A: Ansible wraps Helm
4. Pattern B: Jinja renders `values.yaml` before `helm install`
5. Pattern C: Jinja renders raw manifests, Helm skipped entirely
6. Pattern D: Helm post-renderer + Jinja preprocessor
7. Pattern E: kluctl, helmfile, and Jinja-adjacent tools
8. Pattern F: The dead-end — `helm-jinja` plugins
9. Decision matrix — pick the right pattern
10. Gotchas when mixing Go and Jinja templates

---

## 1. Helm ≠ Jinja — the quick disambiguation

If a file is rendered by Helm, these syntactic markers are Go, not Jinja:

| Marker | Meaning | Jinja equivalent |
|---|---|---|
| `{{ .Values.image.repository }}` | Value lookup from `values.yaml` | `{{ values.image.repository }}` |
| `{{- if ... }}` / `{{- end }}` | `{{- -}}` strips whitespace on *its own side only* | `{%- -%}` strips whitespace |
| `{{ include "mychart.fullname" . }}` | Call a named template | `{% macro %}` + `{{ foo() }}` |
| `{{ .Release.Name }}` | Built-in context | Jinja has no equivalent; pass via `globals` |
| `{{ .Values.replicas | default 3 }}` | Sprig's `default` (two-arg pipe) | `{{ values.replicas \| default(3) }}` |
| `{{ toYaml .Values.labels | indent 4 }}` | Sprig `toYaml`, Go's `indent` | `{{ values.labels \| tojson }}` (no exact equivalent) |
| `{{- range .Values.ports }}` | Go range; the `.` inside is the *item* | `{%- for port in values.ports %}` |
| `{{ .Chart.Name }}` | Chart metadata | No equivalent |

Key differences that trip Jinja-first engineers:

- **`$` and `.` semantics.** In Go templates, `.` means "current scope"; `$`
  is the root. `range` changes `.`. `with` changes `.`. Jinja has no such
  thing — a loop variable is named explicitly (`for x in ...`).
- **Pipes take positional args.** Go's `{{ x | default 3 }}` is "default 3
  for x"; Jinja's `{{ x | default(3) }}` is the same idea but with
  parentheses. Sprig pipes never use parentheses.
- **No `namespace()`**, no `{% set %}` that escapes scope, no loopcontrols.
  Go's `range` is scoped and `break` / `continue` didn't exist before Go
  1.22 (they do now; Helm still uses a vendored Go).
- **Sprig is load-bearing.** Helm relies on hundreds of Sprig functions
  (`toYaml`, `trimPrefix`, `required`, `lookup`, `randAlphaNum`,
  `genCA`, `genSignedCert`, ...). None of these exist in Jinja.
- **Functions aren't filters.** Sprig `include` is a function; Jinja
  `include` is a statement. Calling shape is different.

Writing `{% for %}` inside a Helm chart is a dialect mismatch — stop and
reach for the `helm` skill. Writing `{{ range .Values
}}` inside a `.j2` file, stop and reach for `ansible-dialect.md`.

---

## 2. The 2026 landscape — where Jinja and Helm actually meet

Helm's own proposal for pluggable templating engines (`helm/helm#6184`) was
never accepted; as of 2026 the core engine is still Go `text/template` +
Sprig only. Everything else is *around* Helm. The patterns that show up in
real codebases:

| Pattern | Who uses it | What Jinja does |
|---|---|---|
| **A. Ansible wraps Helm** | Shops with an Ansible-first infra team. IDPs. | Templates `values.yaml.j2`; `community.kubernetes.helm` task does the install. |
| **B. Standalone `jinja2-cli` preprocessor** | Build pipelines, GitOps workflows that don't want Ansible. | Pipes `values.yaml.j2` → `values.yaml` in a Makefile / CI step. |
| **C. Raw Jinja manifests, no Helm** | Smaller teams, one-app clusters, air-gapped sites without Helm tooling. | Renders `Deployment.yaml.j2` etc. directly from CI or Ansible. |
| **D. Helm post-renderer chained with Jinja** | Large charts with last-mile env-specific tweaks. | Pre-renders vars into a patch, then `helm install --post-renderer`. |
| **E. Jinja-like DSLs (kluctl, helmfile)** | Kubernetes-native GitOps shops. | Not Jinja but often confused for it — see §7. |
| **F. `helm-jinja` plugin** | Niche, low adoption, not recommended. | A Helm plugin that swaps Go for Jinja — §8. |

Patterns A and C together cover 80%+ of Jinja-for-k8s in production. B and
D are specializations of A. E is a different tool entirely. F is worth
knowing about only to avoid it.

---

## 3. Pattern A: Ansible wraps Helm

The most common "Jinja + Helm" shape. Ansible's `community.kubernetes.helm`
module runs `helm install` / `helm upgrade`; the values file it consumes
is a Jinja-templated `values.yaml.j2`:

```yaml
# playbooks/deploy-app.yml

- name: render env-specific values
  ansible.builtin.template:
    src: values.yaml.j2
    dest: /tmp/values-{{ env }}.yaml
    mode: "0644"

- name: install or upgrade release
  kubernetes.core.helm:
    name: my-app
    chart_ref: charts/my-app          # local path, repo ref, or OCI URL
    release_namespace: "{{ env }}"
    create_namespace: true
    values_files:
      - /tmp/values-{{ env }}.yaml
    state: present
    atomic: true
    wait: true
```

`values.yaml.j2`:

```jinja
{# {{ ansible_managed }} #}
image:
  repository: registry.internal/my-app
  tag: {{ image_tag }}
  pullPolicy: {{ "Always" if env == "dev" else "IfNotPresent" }}

replicaCount: {{ replica_count | default(1) }}

resources:
  requests:
    cpu: {{ cpu_request | default("100m") }}
    memory: {{ mem_request | default("128Mi") }}
  limits:
    cpu: {{ cpu_limit | default("500m") }}
    memory: {{ mem_limit | default("512Mi") }}

{%- if enable_autoscaling %}
autoscaling:
  enabled: true
  minReplicas: {{ hpa_min | default(2) }}
  maxReplicas: {{ hpa_max | default(10) }}
  targetCPUUtilizationPercentage: {{ hpa_cpu | default(70) }}
{%- else %}
autoscaling:
  enabled: false
{%- endif %}

podAnnotations:
  {%- for k, v in pod_annotations.items() %}
  {{ k }}: {{ v | quote }}
{%- endfor %}

{%- if chart_template_contains_go_block %}
{# The chart itself renders Go template syntax that looks like Jinja. #}
{# Use {% raw %} so Ansible's Jinja pass leaves it alone. #}
extraContent: |
{% raw %}
  {{ .Release.Name }}-leaderelection
{% endraw %}
{%- endif %}
```

Things to know:

- **Double templating risk.** If `values.yaml.j2` includes content that the
  *chart's* Go templates will later process (Helm charts that insert raw
  YAML via `toYaml`), Go syntax in that content must be wrapped in
  `{% raw %}...{% endraw %}` so Ansible's Jinja pass doesn't try to render
  it first.
- **`values_files:` wins over `values:`.** When both are set, Helm merges
  `values_files` *then* `values`. Build one fully-rendered file rather
  than mixing the two — easier to debug.
- **Use `atomic: true`.** On failure, `helm rollback` runs automatically.
  Saves a minute of triage on every flaky deploy.
- **`chart_ref` accepts OCI URLs** (`oci://registry.internal/charts/foo`)
  since `community.kubernetes` 3.x — the 2026 default for private
  registries.

---

## 4. Pattern B: Jinja renders `values.yaml` before `helm install`

Same idea as A, without Ansible. Common in CI pipelines and GitOps shops
that don't want a second orchestrator.

```bash
# Makefile target
render-values:
	jinja2 \
	  --strict \
	  -D env=$(ENV) \
	  -D image_tag=$(IMAGE_TAG) \
	  -D replica_count=$(REPLICA_COUNT) \
	  charts/my-app/values.yaml.j2 \
	  > charts/my-app/values-$(ENV).yaml

deploy: render-values
	helm upgrade --install \
	  my-app charts/my-app \
	  --namespace $(ENV) --create-namespace \
	  --values charts/my-app/values-$(ENV).yaml \
	  --atomic --wait
```

`jinja2-cli` (`pip install jinja2-cli[yaml]`) is the minimal tool. `--strict`
fails on undefined variables — the default is lenient, which silently
produces broken YAML. **Always use `--strict` in CI.**

For more complex rendering (env vars, loops over dicts, pulling secrets
from Vault), write a small Python script:

```python
# render_values.py
import os, sys, yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

env = Environment(
    loader=FileSystemLoader("charts/my-app"),
    undefined=StrictUndefined,    # fail fast on undefined
    trim_blocks=True,
    lstrip_blocks=True,
)
ctx = {
    "env": os.environ["TARGET_ENV"],
    "image_tag": os.environ["IMAGE_TAG"],
    "replica_count": int(os.environ.get("REPLICAS", "1")),
    # ... pull from Vault, Consul, AWS Secrets Manager, whatever
}
tmpl = env.get_template("values.yaml.j2")
out = tmpl.render(**ctx)
# parse-validate before writing so broken YAML fails at render time
yaml.safe_load(out)
sys.stdout.write(out)
```

Always round-trip the rendered output through `yaml.safe_load` before
writing. A single stray indentation in the template produces a file that
Helm will happily try to use, and Helm's resulting error won't point
back at the Jinja template.

---

## 5. Pattern C: Jinja renders raw manifests, Helm skipped entirely

For small apps or environments where Helm is overkill — or where it's
not available at all (some air-gapped sites forbid Helm's internal
templating engine from pulling anything dynamic).

```yaml
# templates/deployment.yaml.j2
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ app_name }}
  namespace: {{ namespace }}
spec:
  replicas: {{ replicas }}
  selector:
    matchLabels:
      app: {{ app_name }}
  template:
    metadata:
      labels:
        app: {{ app_name }}
    spec:
      containers:
        - name: {{ app_name }}
          image: {{ image }}:{{ image_tag }}
          ports:
            - containerPort: {{ port }}
          env:
            {%- for k, v in env_vars.items() %}
            - name: {{ k }}
              value: {{ v | to_yaml }}
            {%- endfor %}
```

Apply via Ansible:

```yaml
- name: apply deployment manifest
  kubernetes.core.k8s:
    state: present
    template: templates/deployment.yaml.j2
```

Or a CI-only pipeline:

```bash
jinja2 --strict -D app_name=api -D namespace=prod ... templates/deployment.yaml.j2 \
  | kubectl apply -f -
```

Trade-offs vs. Helm:

| | Raw Jinja manifests | Helm chart |
|---|---|---|
| Learning curve | Low (one templating language) | Higher (Go + Sprig + chart conventions) |
| Release tracking | Manual (git commit, CI history) | `helm history`, `helm rollback` |
| Rollback | `kubectl apply` previous YAML | `helm rollback N` |
| CRD management | Manual `kubectl apply` order | `crds/` dir, Helm handles it |
| Hooks | None | `helm.sh/hook` annotations |
| Dependency charts | Not a thing | `Chart.yaml` `dependencies:` |
| Lint / test | `kubeconform`, `yamllint`, `j2lint` | `helm lint`, `helm template`, `helm-unittest`, `chart-testing` |
| Distribution | Git clone / copy | OCI / Helm repo |

Raw Jinja wins for ≤ 5 manifests per app, homogeneous environments, and
teams that already know Jinja inside-out. Helm wins for anything that
benefits from release tracking, rollback, or redistribution.

---

## 6. Pattern D: Helm post-renderer + Jinja preprocessor

Less common but worth knowing: a vendored Helm chart applied as-is
needs one specific tweak that values.yaml can't express (an annotation
on a generated resource, a sidecar the chart doesn't support). Helm's
post-renderer feature runs a command on the already-rendered manifest
stream:

```bash
helm install my-app ./charts/my-app \
  --values values.yaml \
  --post-renderer ./post-render.sh
```

`post-render.sh` reads rendered YAML from stdin, mutates it, writes to
stdout. A common shape is a Jinja-driven patcher:

```bash
#!/usr/bin/env bash
# post-render.sh
set -euo pipefail
helm_out=$(cat)
jinja2 --strict \
  -D helm_manifest="$helm_out" \
  -D extra_annotation_value="$EXTRA_ANNOTATION" \
  post-render.yaml.j2
```

More often the post-renderer is `kustomize build`, not Jinja — this
pattern is mentioned for completeness. When the target is a small,
mechanical mutation, kustomize is the better fit.

---

## 7. Pattern E: kluctl, helmfile, and Jinja-adjacent tools

**`kluctl`** (<https://kluctl.io>) has a Jinja2 integration — it uses
native Jinja2 (via a Go port of a subset) for templating, which makes it
the one Kubernetes tool in 2026 that's genuinely Jinja-under-the-hood,
not Go templates. Its Helm integration references charts by name +
version and layers Jinja templates on top for values and manifests.
Worth knowing about for shops specifically evaluating "Jinja for
everything" workflows.

**`helmfile`** uses Go templates (with Sprig), not Jinja. The `.gotmpl`
extension is deliberate. If a file is named `helmfile.yaml.gotmpl`, it's
Go, not Jinja — same rules as a Helm chart.

**`ytt`** (Carvel) is Starlark-based, not Jinja. Don't conflate.

**`jsonnet`** / **`ksonnet`** are their own language. Not Jinja.

**`cue`** is its own language. Not Jinja.

**ArgoCD config management plugins** can invoke anything — including a
Jinja preprocessor that renders `values.yaml.j2` → `values.yaml` and
then feeds Helm. Use the `Directory` or `Plugin` source types and a
ConfigManagementPlugin CR that runs the preprocessor. This is how teams
integrate the Ansible-style Jinja values pipeline with GitOps.

---

## 8. Pattern F: The dead-end — `helm-jinja` plugins

Over the years several Helm plugins have tried to replace the Go
templating engine with Jinja:

- `helm-jinja` (various forks) — abandoned or low-maintenance as of 2026.
- `helmt` — a separate "Helm but with Jinja" tool; small user base.
- `redhat-nfvpe/helm-ansible-template-exporter` — not a Helm plugin but
  a one-shot converter that rewrites a Helm chart into an Ansible role
  (replacing Go templates with Jinja). Interesting archaeology; not a
  maintained workflow.

Why they don't thrive:

- **Chart ecosystem locks in Go.** Every third-party chart on Artifact
  Hub uses Go templates. A plugin that swaps the engine can't render
  anyone else's chart without rewriting it.
- **Sprig coverage is large.** Reimplementing `toYaml`, `genCA`,
  `required`, `fromYaml`, `lookup` (the Kubernetes-aware version), etc.
  in Jinja is a lot of surface to keep up with.
- **Chart testing assumes Go.** `helm-unittest`, `chart-testing`,
  `kubeconform`'s Helm integration — all assume Go rendering.

**The pragmatic recommendation for 2026: don't try to replace Helm's
engine.** For Jinja-first workflows, write `values.yaml.j2` (Pattern
A/B) or skip Helm entirely (Pattern C). Those are maintained,
documented, and tooled.

---

## 9. Decision matrix — pick the right pattern

```
Need to deploy to Kubernetes.
│
├─ Is there an existing Helm chart (vendored or from a repo) that covers 80%
│  of my needs?
│   ├─ YES
│   │   ├─ Does values.yaml cover the last 20%?
│   │   │   ├─ YES ──► Pattern A (Ansible + values.yaml.j2) or
│   │   │   │          Pattern B (jinja2-cli preprocessor)
│   │   │   └─ NO  ──► Pattern D (Helm post-renderer) or
│   │   │              kustomize as post-renderer
│   │   └─ (Helm with a Jinja values file is the 90% answer)
│   │
│   └─ NO, or it's a small / simple app
│       └─ Pattern C (raw Jinja-templated manifests,
│                    apply via Ansible k8s module or kubectl)
│
├─ GitOps (ArgoCD/Flux) and want Jinja in the loop?
│   └─ ArgoCD Config Management Plugin that runs jinja2-cli →
│      values.yaml → helm template (Pattern B inside GitOps)
│
└─ Specifically want Jinja-native Kubernetes tooling?
    └─ kluctl (Pattern E). Rare, but supported.
```

---

## 10. Gotchas when mixing Go and Jinja templates

1. **Go `default` is 2-arg pipe, Jinja `default` is 1-arg.** In Go:
   `{{ x | default "fallback" }}`. In Jinja: `{{ x | default('fallback') }}`.
   Copy-paste across the boundary silently breaks.
2. **Go's `.` vs Jinja's implicit context.** Go: `{{ .Values.foo }}`.
   Jinja: `{{ values.foo }}` (no dot). Go uses `.` for current scope;
   Jinja uses dotted attribute access *on an object*, which is
   different.
3. **Go `range` rebinds `.`.** `{{ range .items }}{{ . }}{{ end }}`
   iterates and `.` *is* the current item. Jinja `{% for item in items %}
   {{ item }}{% endfor %}` names the variable explicitly.
4. **Go's whitespace trim is one-sided.** `{{- ` strips whitespace to
   the *left*; ` -}}` to the right. Jinja's `{%- %}` trims the same
   side. Same idea, looks identical — the parser is different.
5. **`toYaml` has no Jinja equivalent.** Chart authors use `{{ toYaml
   .Values.extra | indent 4 }}` to splat structured YAML. Jinja's
   `| tojson` produces JSON (also valid YAML, but reads as JSON). For
   multi-line YAML output from Jinja, use `PyYAML` or write a custom
   filter that serializes + re-indents.
6. **Double-template when feeding Jinja into Go (or vice versa).** When
   Jinja-rendered YAML contains literal `{{ ... }}` that the downstream
   Helm chart is supposed to render as Go, wrap that block in
   `{% raw %}...{% endraw %}`. Going the other way (a Go template that
   emits a `.j2` file), use Go's `{{"{{"}}` escape pair.
7. **Helm's `lookup` doesn't exist in Jinja.** Sprig's `lookup` queries
   the live cluster from a chart. Jinja has no such function. For
   runtime cluster state, use Ansible (`community.kubernetes.k8s_info`)
   and pass the result in as a variable.
8. **CRDs can't be templated the same way.** Helm handles CRDs via a
   dedicated `crds/` dir. Pure Jinja (Pattern C) requires applying CRDs
   manually first and depending on them by convention. Helm's CRD
   ordering is a feature that is given up.
9. **`genCA` / `genSignedCert` are Sprig-only.** TLS-material generation
   inside a Helm chart does not port to Jinja — cert generation has to
   move elsewhere (Ansible `community.crypto`, cert-manager, external
   CA). Jinja has no crypto primitives.
10. **Sprig `required "msg"` vs Ansible `| mandatory("msg")`.** Same
    intent, different filter name, different trigger condition.
    `required` fails when the value is empty/nil; `mandatory` fails
    only when undefined.

---

## See also

- **`helm` skill** — chart authoring, `_helpers.tpl`, Sprig, library
  charts, `helm-unittest`, `chart-testing`, OCI push. That skill is the
  right surface for anything *inside* a chart.
- **`ansible-dialect.md`** — the Ansible Jinja surface, including
  `kubernetes.core.k8s` and `kubernetes.core.helm` usage.
- **Helm docs — chart template guide**:
  <https://helm.sh/docs/chart_template_guide/>
- **Helm proposal #6184 (pluggable templating engines)**:
  <https://github.com/helm/helm/issues/6184>
- **kluctl (Jinja-native k8s tool)**: <https://kluctl.io>
- **`kubernetes.core.helm` module**:
  <https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/helm_module.html>
