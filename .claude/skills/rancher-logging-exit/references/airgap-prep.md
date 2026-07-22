# Air-gap prep — step zero for air-gapped clusters

Do ALL of this before touching the cluster. The cutover happens with no internet;
a missing image mid-migration means a stalled pipeline.

## 1. Mirror the images (6.7.0 set)

Required:

```
ghcr.io/kube-logging/logging-operator:6.7.0
ghcr.io/kube-logging/logging-operator/fluentd:6.7.0-full
ghcr.io/kube-logging/logging-operator/config-reloader:6.7.0
ghcr.io/kube-logging/logging-operator/fluentd-drain-watch:6.7.0
ghcr.io/kube-logging/logging-operator/node-exporter:6.7.0     # buffer metrics sidecar
ghcr.io/fluent/fluent-bit:5.0.5
registry.k8s.io/pause:3.9                                     # drain placeholder pod
docker.io/library/busybox:latest                              # volume-mode init
```

Optional by feature:

```
ghcr.io/kube-logging/logging-operator/syslog-ng-reloader:6.7.0   # syslog-ng mode
ghcr.io/axoflow/axosyslog:4.24.0                                 # syslog-ng mode
ghcr.io/axoflow/axosyslog-metrics-exporter:0.0.15                # syslog-ng mode
ghcr.io/kube-logging/eventrouter:1.0.0                           # EventTailer
```

Pin digests at mirror time. (The old rancher/mirrored-kube-logging-* images can be
retired from the mirror after rollback confidence is reached.)

## 2. Mirror the chart (OCI-only since 4.3)

```bash
helm pull oci://ghcr.io/kube-logging/helm-charts/logging-operator --version 6.7.0
helm push logging-operator-6.7.0.tgz oci://<internal-registry>/kube-logging/helm-charts
# or install straight from the .tgz carried across the gap
```

Also pre-extract the CRDs for the server-side apply step (works offline from the
tarball): `helm show crds ./logging-operator-6.7.0.tgz > crds-6.7.0.yaml`.

## 3. Draft the values overrides

Upstream has **no `systemDefaultRegistry`-style global rewrite** — every image is
overridden explicitly. Skeleton `upstream-values.yaml`:

```yaml
image:
  repository: <registry>/kube-logging/logging-operator
  tag: 6.7.0
# operator-created workload images are set on the CRs, not chart values:
```

And on the Logging / FluentbitAgent CRs (patch after adoption, or bake into
restored YAML):

```yaml
# Logging.spec.fluentd:
  image: {repository: <registry>/kube-logging/logging-operator/fluentd, tag: 6.7.0-full}
  configReloaderImage: {repository: <registry>/.../config-reloader, tag: 6.7.0}
  scaling: {drain: {image: {repository: <registry>/.../fluentd-drain-watch, tag: 6.7.0},
                    pauseImage: {repository: <registry>/pause, tag: "3.9"}}}
  bufferVolumeImage: {repository: <registry>/.../node-exporter, tag: 6.7.0}
# FluentbitAgent.spec:
  image: {repository: <registry>/fluent/fluent-bit, tag: 5.0.5}
```

Verify exact field paths against the 6.7.0 CRD/docs when authoring — image
override spellings differ per component (`image`, `configReloaderImage`,
`bufferVolumeImage`).

## 4. Pre-flight connectivity sanity

On a cluster node (or a debug pod):

```bash
crictl pull <registry>/kube-logging/logging-operator:6.7.0
```

Never rely on `kubectl run test-pull --image=ghcr.io/...` on an air-gapped
cluster — it tests the wrong path.

## 5. Registry-auth edge

ghcr.io anonymously rate-limits and has caused `helm ... 403` on OCI pulls
(upstream #1522) — relevant only for the mirroring host, not the cluster. Use a
token on the mirroring side if pulls flake.
