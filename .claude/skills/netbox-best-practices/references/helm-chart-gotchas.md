# netbox-chart (helm) deployment gotchas

Verified against netbox-chart 8.3.x source (`charts/netbox/templates/`) and a
production install of chart 8.3.14 / NetBox v4.6.2. Chart repo:
`netbox-community/netbox-chart`; chart museum: `charts.netbox.oss.netboxlabs.com`.

Ordered as a pre-flight checklist for a fresh install.

Contents: §1 External PostgreSQL (naming collision, operator secrets,
one-way migrations) · §2 External Redis/Valkey sentinel wiring ·
§3 Chart-generated secrets + offline-render trap · §4 API token bootstrap ·
§5 Plugins need a custom image · §6 Operational defaults (housekeeping,
metrics, first boot, distroless preflight) · §7 Upgrade workflow.

## 1. External PostgreSQL

- Set `postgresql.enabled: false`; configure `externalDatabase.*`.
- **Naming collision trap** [live]: the operator-managed cluster (Zalando,
  CloudNativePG) emits Services named after the cluster CR. If the CR is named
  the same as the helm release fullname (e.g. release `netbox` ↔ cluster
  `netbox`), `helm install` fails:
  `Service "netbox" ... cannot be imported into the current release: invalid
  ownership metadata`. Name the CR `<release>-postgres-cluster`.
- Operator credential secrets can be consumed directly:
  `externalDatabase.existingSecretName: <operator-secret>` with
  `existingSecretKey: password`. The chart projects the key onto the
  `db_password` path the config reads — no key renaming needed. [source]
- The Django schema migration runs at pod startup inside `helm upgrade`.
  `helm rollback` cannot downgrade the schema — snapshot the DB before every
  upgrade.

## 2. External Redis/Valkey (sentinel)

Set `valkey.enabled: false`, then wire BOTH `tasksDatabase` (RQ, db 0) and
`cachingDatabase` (cache, db 1):

```yaml
tasksDatabase:
  sentinels:
    - my-valkey-0.my-valkey-headless:26379
    - my-valkey-1.my-valkey-headless:26379
    - my-valkey-2.my-valkey-headless:26379
  sentinelService: mymaster        # MUST equal the sentinel master group name
  existingSecretName: my-valkey-auth
  existingSecretKey: tasks-password
```

- `host`/`port` are fallback only; the sentinels list drives master discovery. [live]
- Secret keys with hyphens are fine: the chart mounts them at underscore paths
  (`tasks-password` → `tasks_password`) matching what `configuration.py`
  reads — do not "fix" the key names. [source: deployment volumes]

## 3. Secrets the chart generates (and the offline-render trap)

With `superuser.password`, `superuser.apiToken`, `secretKey`, and
`apiTokenPeppers` left empty, the chart generates them and **preserves them
across upgrades via helm `lookup`** [source: templates/_helpers.tpl — comment
reads "Existing secret value (preserved across upgrades via lookup)"].

Consequences:

- `lookup` only works against a LIVE cluster. Offline `helm template`
  regenerates all of them on every render → rendered manifests contain
  secret-shaped random material and churn on every diff. **Gitignore rendered
  templates**; treat secret churn in offline template-diffs as expected noise,
  not a finding.
- `api_token_peppers` is auto-generated (one pepper, key "1") and preserved;
  rotating means ADDING a higher-numbered pepper, never removing old ones
  (existing tokens break otherwise). [docs]

## 4. API token bootstrap {#api-token-bootstrap}

The chart's `netbox-superuser` secret contains an `api_token` key
(`uuidv4`-generated [source: templates/secret.yaml]) and mounts it at
`/run/secrets/superuser_api_token` [source: templates/deployment.yaml] — but
**NetBox 4.6's entrypoint never seeds it into the database**. Boot log says so
explicitly: `No API token was created for the superuser as SUPERUSER_API_TOKEN
and SUPERUSER_API_KEY are not set`. v2 peppered tokens cannot be pre-seeded
(the server stores only an HMAC). [live]

For the generic v2 token mechanics (peppers, rotation, client libraries),
defer to the official `netbox-labs:netbox-api-integration` skill if installed;
the wire format itself is in `version-deltas.md` §4.5. The chart-specific
bootstrap, runnable end-to-end:

```bash
# provision password comes from the chart-generated secret:
PW=$(kubectl -n <ns> get secret netbox-superuser -o jsonpath='{.data.password}' | base64 -d)
RESP=$(curl -s -X POST https://netbox.example.com/api/users/tokens/provision/ \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"admin\",\"password\":\"$PW\",\"description\":\"bootstrap\"}")
CRED="nbt_$(echo "$RESP" | jq -r .key).$(echo "$RESP" | jq -r .token)"
kubectl -n <ns> create secret generic netbox-api-token --from-literal=token="$CRED"
# .token is shown exactly once — if the secret isn't captured here, re-provision
```

- Failure signature worth knowing: a bare 40-char token WITHOUT the `nbt_`
  prefix is parsed as a v1 token and rejected with `Invalid v1 token` — the
  prefix, not the auth keyword, selects the version.
  [source: netbox/api/authentication.py]
- Read-only tokens for MCP/automation: authenticated
  `POST /api/users/tokens/` with `"write_enabled": false`.

## 5. Plugins require a custom image

`plugins:` and `pluginsConfig:` only render configuration
[source: templates/configmap.yaml → `PLUGINS: {{ toJson .Values.plugins }}`].
The official image contains no plugin code; enabling a plugin without the
package present crashloops the pod. Build and pin:

```dockerfile
FROM ghcr.io/netbox-community/netbox:v4.6.2
RUN /opt/netbox/venv/bin/pip install netbox-topology-views==<ver>
```

Push to a private registry, set `image.repository`/`tag`, then list the plugin.
Init-container pip-installs exist but need internet at every pod start — wrong
for air-gapped or deterministic deployments.

## 6. Operational defaults worth flipping

- `housekeeping:` CronJob is enabled by default (nightly) — keep it.
- `metrics.enabled: true` + `metrics.serviceMonitor.enabled: true` for
  prometheus-operator stacks; note there is a SECOND ServiceMonitor block
  under `metrics.granian.*` for the app-server's own metrics. [source]
- First boot runs every Django migration before readiness — expect several
  minutes and startup-probe noise on a fresh install; it is not a crashloop. [live]
- The release's image set includes `docker.io/rancher/kubectl` (hook) — it is
  DISTROLESS (no shell/sleep). When pre-pulling images with an idle-container
  DaemonSet, gate on every container having a non-empty `.imageID` instead of
  pod Ready; the kubectl container can never idle and crashloops by design. [live]

## 7. Upgrade workflow notes

- Vet chart bumps in layers: default-values diff → site-values diff →
  rendered-template diff (offline) → `kubectl diff` (live). The template
  layer is the only one that catches chart-side default flips on keys
  never set in the values file.
- Remember §3: secret churn in offline template diffs is expected; the same
  keys are stable across REAL upgrades.
- DB snapshot before `helm upgrade` (see §1 — migrations are one-way).
