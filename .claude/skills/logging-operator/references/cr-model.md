# CR model — the 16 CRDs and how routing actually works

Verified against operator 6.7.0 (CRD set unchanged since 6.1.0; only additive field
changes 6.1→6.7).

## Inventory

Group `logging.banzaicloud.io`, served version `v1beta1` (Logging, Flow, ClusterFlow,
Output, ClusterOutput also retain a legacy non-storage `v1alpha1`):

| Kind | Scope | Role |
|---|---|---|
| Logging | **Cluster** | Pipeline domain: controlNamespace, aggregator choice, watch scope |
| Flow | Namespaced | Route logs OF ITS OWN NAMESPACE through filters to outputs |
| ClusterFlow | **Namespaced** (control ns only) | Cross-namespace routing |
| Output | Namespaced | Destination, referenced by same-ns Flows (`localOutputRefs`) |
| ClusterOutput | **Namespaced** (control ns only) | Cluster-wide destination (`globalOutputRefs`) |
| FluentbitAgent | **Cluster** | Node collector DaemonSet config (4.2+) |
| FluentdConfig | Namespaced (control ns) | Detached aggregator config (4.5+) |
| SyslogNGConfig | Namespaced (control ns) | Detached syslog-ng aggregator config |
| SyslogNGFlow / SyslogNGClusterFlow | Namespaced | syslog-ng routing (match tree, not list) |
| SyslogNGOutput / SyslogNGClusterOutput | Namespaced | syslog-ng destinations |
| LoggingRoute | **Cluster** | Multi-tenant collector→aggregator fan-out (4.4+) |
| AxoSyslog | Namespaced | Thin raw-config wrapper (logPaths/filterx + destinations); frozen, not a full aggregator |

Group `logging-extensions.banzaicloud.io`, `v1alpha1`:

| Kind | Scope | Role |
|---|---|---|
| EventTailer | **Cluster** | eventrouter pod dumping k8s Events to stdout for collection |
| HostTailer | Namespaced | Tail node files / systemd journal units |

Removed: **NodeAgent** (CRD + `Logging.spec.nodeagents`) gone in 6.0.0. There is no
6.x path for its Windows use case (Telemetry Controller nominally, immature).

The cluster-scoped kinds surprise people twice: `kubectl get clusterflows -n x`
works (they're namespaced) but only control-namespace ones are honored;
`kubectl get loggings` needs no namespace.

## Match semantics (fluentd family)

`Flow.spec.match` is an **ordered list** of `select` / `exclude` statements:

- Fields: `labels`, `hosts`, `container_names` (**container**, not pod, names).
- ClusterFlow adds `namespaces`, `namespaces_regex` (ruby regex, 5.3+),
  `namespace_labels` (4.8+; requires `filterKubernetes.namespace_labels: "On"`,
  default on since 4.9).
- Multiple criteria **inside one statement = AND**; **separate statements = OR**;
  evaluated in order.
- **No `select` statement ⇒ nothing matches.** Select-all: `- select: {}`.
- Canonical exclude-noisy-namespaces ClusterFlow:
  ```yaml
  match:
    - exclude: {namespaces: [dev, sandbox]}
    - select: {}
  ```

Output binding: Flow → `localOutputRefs` (same-ns Output) + `globalOutputRefs`
(ClusterOutput). **ClusterFlow → `globalOutputRefs` only.**
`ClusterOutput.spec.protected: true` (4.7+) blocks namespaced Flows from referencing
it; no Flow-level equivalent exists yet (open #2191).

## Logging spec — the keys that matter

```yaml
spec:
  controlNamespace: logging          # REQUIRED; admin ns: aggregator runs here,
                                     # cluster resources evaluated here
  fluentd: {}                        # or syslogNG: {} — the mode switch
  watchNamespaces: [a, b]            # limit compiled-in Flows/Outputs (union with…)
  watchNamespaceSelector: {...}      # …this label selector
  loggingRef: tenant-a               # partition logging domains; Flows/Outputs with
                                     # empty loggingRef are processed by ALL Loggings
  allowClusterResourcesFromAllNamespaces: false
  errorOutputRef: err-clusteroutput  # fluentd @ERROR records (no filters allowed)
  defaultFlow: {...}                 # catch-all for unmatched logs
  globalFilters: [...]               # filters applied to every Flow
  skipInvalidResources: true         # skip broken Flows instead of failing all
  configCheck: {strategy: DryRun|StartWithTimeout, timeoutSeconds: 10}
  enableDockerParserCompatibilityForCRI: true   # 4.9+; THE containerd JSON fix
  fluentBitAgentNamespace: collectors           # 6.1+
  clusterDomain: cluster.local.
  enableRecreateWorkloadOnImmutableFieldChange: true
  routeConfig: {enableTelemetryControllerRoute: false, ...}   # experimental
```

Status to check when debugging: `problems`/`problemsCount`,
`configCheckResults` (map confighash→bool), `fluentdConfigName`, `watchNamespaces`.
Flows/Outputs carry `status.active` + `status.problems`
(`kubectl get logging-all -n <ns>` shows ACTIVE/PROBLEMS columns).

## Decoupled pattern (current best practice)

Three-way split instead of a monolithic Logging:

- `Logging` — domain + control namespace only
- `FluentbitAgent` — collector; **metadata.name must equal the Logging's name**
- `FluentdConfig` / `SyslogNGConfig` — aggregator; same name rule, must live in the
  control namespace. Only ONE may attach per Logging (`status.active: true` on the
  winner; a second gets `active: false` + problems).

`Logging.spec.fluentbit` (inline) is **deprecated**; `spec.fluentd`/`spec.syslogNG`
inline still work but the split wins on RBAC separation, avoiding the
last-applied-annotation size limit on giant Logging objects, and multi-tenancy.
Multiple FluentbitAgents per Logging are allowed (node-group configs, rolling
collector upgrades).

Migration gotcha (inline fluentbit → FluentbitAgent): explicitly set
`positiondb.hostPath.path: ""` and `bufferStorageVolume.hostPath.path: ""` — the
empty string regenerates the operator-managed default path
(`/opt/logging-operator/<logging>/<volume>`) so existing position DB/buffers are
retained; omitting them can lose buffered data.

## LoggingRoute — hard multi-tenancy

The isolation ladder (weakest→strongest):

1. Single Logging: Flow/Output are namespace-bound and the aggregator enforces it —
   tenant A's Flow cannot select tenant B's logs. BUT everyone shares one
   aggregator's fate (see the SPOF trap).
2. Multiple Loggings with `watchNamespaces`/`watchNamespaceSelector` — costs one
   full DaemonSet per tenant reading ALL node logs.
3. Add `loggingRef` everywhere to keep domains explicit.
4. **LoggingRoute (4.4+)**: one ops-owned Logging holds the ONLY FluentbitAgent;
   tenant Loggings are aggregator-only. `spec.source` names the collector's
   Logging; `spec.targets` is a label selector over tenant Loggings; per-tenant
   namespace filtering comes from each **target's** watchNamespaces. Tenants "work
   in isolation on their own logs and nothing more".
   Documented con: one collector now manages many output queues — fluent-bit
   "does not handle well by default"; tune flow control (see production-hardening).
   Status carries `tenants[]` (name + expanded namespaces) + problems.
   Note: a tenant's ClusterFlow only sees namespaces routed to that tenant.

## How CRs become running config

Operator renders everything into `Secret <logging>-fluentd-app` key `fluentd.conf`
(syslog-ng: `<logging>-syslogng-app`, `syslog-ng.conf`):

```
<source> @type forward            ← from fluent-bit
<match **> @type label_router     ← one <route> per Flow (namespace + label criteria)
@label @<hash>                    ← per-Flow block: filters in order, then
  <filter> ...                       <match> per referenced output
  <match> @type <output-plugin>
```

Every change first runs a `<logging>-fluentd-configcheck-<hash>` pod:
- `DryRun` (default): parse/validate only.
- `StartWithTimeout`: actually boots with the config (`timeoutSeconds`, default 10)
  — catches connection-level errors, but only at apply time.
Result lands in `Logging.status.configCheckResults`. A failed check silently blocks
ALL subsequent config rollouts until the offending resource is fixed/removed.
