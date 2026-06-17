# netbox-chart (helm) deployment gotchas

Verified against netbox-chart 8.3.x source (`charts/netbox/templates/`) and a
production install of chart 8.3.14 / NetBox v4.6.2. Chart repo:
`netbox-community/netbox-chart`; chart museum: `charts.netbox.oss.netboxlabs.com`.

Ordered as a pre-flight checklist for a fresh install.

Contents: §1 External PostgreSQL (naming collision, operator secrets,
one-way migrations) · §2 External Redis/Valkey sentinel wiring ·
§3 Chart-generated secrets + offline-render trap · §4 API token bootstrap ·
§5 Enabling plugins (UI catalog ≠ installer, two-part install, image lineage,
derived-image workflow, version-pin + migrations, no init-container) ·
§6 Operational defaults (housekeeping,
metrics, first boot, distroless preflight) · §7 Upgrade workflow ·
§8 Media storage: RWO-PVC-with-a-worker trap → migrate to S3 (zero-loss recipe).

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

## 5. Enabling plugins (custom image)

### 5.0 The UI catalog is discovery, not an installer

NetBox's **Plugins** page (`/plugins/`) lists hundreds of community plugins
pulled from the public netboxlabs registry. It is a *catalog* — there is **no
enable toggle**, and seeing a plugin there does NOT mean it is installed or
installable from the UI. A stock install shows the full catalog with zero
installed; that is the expected state, not a misconfiguration. Plugins are never
enabled from the web UI. [docs: netbox plugins catalog]

### 5.1 Every plugin needs TWO things — missing either is the usual failure

1. **The Python package present in the running venv** — pip-installed into the
   image NetBox actually runs.
2. **The plugin's name listed in `PLUGINS`** (helm `plugins:`). Per-plugin
   settings go in `PLUGINS_CONFIG` (helm `pluginsConfig:`).

Failure modes:
- In `PLUGINS` but package NOT installed → pod **crashloops** at startup
  (`ModuleNotFoundError`). This is the most common "I enabled it and NetBox
  died" report.
- Package installed but NOT in `PLUGINS` → silently **inert**, no error.

The chart values only ever render *configuration*, never code
[source: templates/configmap.yaml → `PLUGINS: {{ toJson .Values.plugins }}`,
`PLUGINS_CONFIG: {{ toJson .Values.pluginsConfig }}`]. The stock image carries
zero plugin code, so `plugins:` alone can never turn anything on.

### 5.2 Image lineage — why the netbox-docker wiki only half-applies

The chart pulls `ghcr.io/netbox-community/netbox`
[source: values.yaml `image.registry/repository`], and **that image is built by
the `netbox-community/netbox-docker` repo** (same artifact published to
ghcr.io and docker.io/netboxcommunity/netbox). So plugin READMEs that link the
[netbox-docker "Using NetBox Plugins" wiki](https://github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins)
*are* describing your base image — but that wiki's `plugin_requirements.txt` +
`docker-compose build` / `Dockerfile-Plugins` flow is for running netbox-docker's
**compose stack**, which a helm deployment does NOT use. The chart has no build
step; it pulls a finished image. Apply the wiki's *principle* (extend the image),
not its compose mechanics.

### 5.3 The chart-native workflow: derived image → registry → values

Build a thin image FROM the exact base tag, pinned per plugin:

```dockerfile
FROM ghcr.io/netbox-community/netbox:v4.6.2
RUN /opt/netbox/venv/bin/pip install \
      netbox-topology-views==<ver> \
      <other-plugin>==<ver>
```

Push to your **private registry** (air-gap: Harbor is ideal — pull the base
through your proxy/cache, build, push the derived tag), then point the chart at
it AND list the plugins:

```yaml
image:
  registry: harbor.example.com
  repository: netbox/netbox-plugins
  tag: v4.6.2-plugins-1          # rev the suffix on every plugin/base change
plugins:
  - netbox_topology_views        # the PYTHON module name, not the PyPI dist name
pluginsConfig:
  netbox_topology_views: {}      # plugin-specific settings
```

Then `make diff` → `make upgrade`. Note `plugins:` wants the importable **module
name** (underscores, e.g. `netbox_topology_views`), which often differs from the
PyPI distribution name you `pip install` (hyphens, e.g. `netbox-topology-views`);
each plugin's README states its `PLUGINS` entry — use that verbatim.

### 5.4 Version pinning and migrations

- **Pin every plugin to the NetBox version.** Each plugin declares a compatible
  NetBox range in its metadata; a mismatch crashloops on boot. You must rebuild
  the derived image on every NetBox minor bump — treat the plugin set as part of
  the upgrade, not a one-time step. [docs]
- **Plugins with models run Django migrations at pod startup**, exactly like a
  NetBox upgrade, inside the `helm upgrade` rollout. `helm rollback` cannot undo
  them → **`make db-backup` first** (same one-way rule as §1). Adding a plugin
  to a running instance is therefore a DB-mutating change, not just a config
  edit.

### 5.5 Don't use the init-container pip path in prod

The chart can pip-install at pod start via an init container, but that needs
internet (or a reachable PyPI mirror) on **every** pod start and makes the
running code non-deterministic — wrong for air-gapped or reproducible
deployments. Bake plugins into the image (§5.3) so the artifact is immutable and
pull-once.

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

## 8. Media storage: the RWO-PVC-with-a-worker trap → use S3

By default the chart stores uploaded media (image attachments, device-type
images) on a **single ReadWriteOnce** PVC (`persistence.enabled: true`,
`accessMode: ReadWriteOnce`) that is mounted by **both** the web Deployment AND
the worker Deployment. This works only while both pods are co-scheduled on one
node. A node reboot/drain that reschedules them onto **different** nodes
deadlocks — RWO can't multi-attach, so the pod on the node without the volume
hangs in `Init:0/1` forever (volumes mount before init containers, so even a
trivial `mkdir` init never starts). "Pods should just recover" does NOT hold
here; there is no co-scheduling rule by default. The chart's own values comment
admits it: *"ReadWriteMany PVC(s) are required if replicaCount > 1."* [live]

What's actually on that PVC: **only uploaded files** (`image-attachments/`,
`devicetype-images/`, regenerable `cache/`) — a few MB. ALL real data
(devices, IPAM, cables) is in **Postgres**, which has no such problem (each
replica owns its own RWO volume). So the whole headache is over a photo folder.

**Fix — move media to object storage; do NOT reach for CephFS/RWX.** NetBox
supports S3 natively (the official image already ships `django-storages` +
`boto3`). Point it at any S3 (Ceph RGW / MinIO / AWS); web+worker become
stateless and reschedule anywhere. Chart wiring:
```yaml
storages:                       # merged as DEFAULT_STORAGES | STORAGES, so only override default
  default:
    BACKEND: storages.backends.s3.S3Storage
    OPTIONS:
      bucket_name: netbox-media
      endpoint_url: https://s3.example.com   # PUBLIC/browser-reachable host — NetBox mints presigned image URLs the browser must load
      region_name: <rgw-zonegroup-api_name>  # Ceph RGW: `radosgw-admin zonegroup get | .api_name`
      addressing_style: path                 # REQUIRED for custom endpoints — virtual-host style becomes bucket.host, which a SAN-scoped cert won't cover
extraEnvVarsSecret: "netbox-media"  # AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY → boto3 reads from env; keep keys out of values
worker:      { extraEnvVarsSecret: "netbox-media" }
housekeeping:{ extraEnvVarsSecret: "netbox-media" }
persistence: { enabled: false }     # drops the shared RWO PVC; media volume falls back to per-pod emptyDir
```
Gotchas learned the hard way [live]:
- **Don't bother with an ObjectBucketClaim if the RGW cert is Let's Encrypt.**
  The rook operator provisions OBC buckets via the RGW admin API over the
  internal `*.svc` name; an LE cert only covers public names and can't carry an
  internal SAN, so the admin call fails TLS verification and the OBC stays
  `Pending`. Provision the bucket+user with `radosgw-admin` instead.
- **Migrate with zero loss:** tar the media dir off-cluster FIRST, `mc mirror`
  it into the bucket preserving relative paths (DB stores those paths), set the
  PV `reclaimPolicy: Retain` before disabling persistence, THEN upgrade and
  verify an image returns HTTP 200 from S3 before trusting it.
- The media `STORAGES` config rides in the **netbox-config Secret**, so `make
  diff`/`kubectl diff` masks it (`***`); verify the change in the rendered
  `template-*.yaml` (unmasked) instead — and remember the secret_key/peppers
  churn in that diff is the §3 offline-render false positive, preserved on the
  real upgrade.
