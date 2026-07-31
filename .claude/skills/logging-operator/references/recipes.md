# Worked recipes — pod stdout → destination, complete chains

Everything here is grounded in official quickstarts, the operator's own
`config/samples/`, and issue-tracker verified gotchas. The base chain (Logging +
FluentbitAgent + Flow + Output) is in SKILL.md; this file covers the variations.

## Contents
- [JSON pod logs (the CRI trap)](#json-pod-logs)
- [Record shape at each stage](#record-shape)
- [Multiline / stack traces](#multiline)
- [Selecting sources](#selecting-sources)
- [Kubernetes events + host/systemd logs](#events-and-host-logs)
- [External syslog ingestion (receiver pod)](#external-syslog-ingestion)
- [Testing and per-destination pointers](#destinations)

## JSON pod logs

Two parse points exist. **Pick exactly one per field** — using both double-parses
(duplicated fields with `Keep_Log On`, or `pattern not matched` floods with
`Keep_Log Off`).

### Parse point A: fluent-bit side (Merge_Log) — zero-config for clean JSON apps

The operator defaults `filterKubernetes.Merge_Log: On`. **On containerd/CRI
(RKE2, k3s, anything modern) this silently does NOTHING** — the CRI tail parser
puts the line into `message`, Merge_Log only reads `log`. This is the
single-most-reported confusion upstream (#1784, #1007, #1353).

Fix, operator ≥4.9 — one flag on the Logging:

```yaml
kind: Logging
spec:
  enableDockerParserCompatibilityForCRI: true
```

Re-parses CRI lines into `log` (docker-compatible), Merge_Log then auto-merges
JSON, and downstream `concat`/`parser` filters see `log` again. Renders an error if
you ALSO override `inputTail.Parser` ("enableDockerParserCompatibilityForCRI is
set, but fluentbit config overrides it").

Pre-4.9 manual equivalent (from `config/samples/containerd-merge-log.yaml`):

```yaml
kind: FluentbitAgent
spec:
  inputTail: {Parser: cri-log-key}
  customParsers: |
                  [PARSER]
                      Name cri-log-key
                      Format regex
                      Regex ^(?<time>[^ ]+) (?<stream>stdout|stderr) (?<logtag>[^ ]*) (?<log>.*)$
                      Time_Key    time
                      Time_Format %Y-%m-%dT%H:%M:%S.%L%z
```

Indentation of `customParsers` matters — wrong indent makes fluent-bit swallow the
whole message.

Tuning: `Merge_Log_Key: parsed` nests merged fields under one key (prevents app
JSON with its own `time`/`kubernetes` keys colliding with metadata).
`Keep_Log: "Off"` drops the raw string after a successful merge (default On keeps
it → doubled data at the destination).

### Parse point B: Flow-side parser filter — per-app control

The pattern every official example uses; **both flags, always**:

```yaml
filters:
  - tag_normaliser: {}
  - parser:
      remove_key_name_field: true   # drop raw string after successful parse
      reserve_data: true            # WITHOUT THIS the parsed JSON replaces the
                                    # whole record → kubernetes.* metadata lost
      parse: {type: json}           # or regexp | nginx | logfmt | grok | multi_format
```

- `key_name` empty = "container-runtime default" (`log` docker-compat, `message`
  raw CRI) — the same Flow behaves differently across runtimes unless
  `enableDockerParserCompatibilityForCRI` pins it.
- Type casting: `parse: {type: regexp, expression: ..., types: "port:integer,duration:float"}`.
- `replace_invalid_sequence: true` retries after swapping invalid UTF-8.
- `emit_invalid_record_to_error: true` routes parse failures to @ERROR →
  capturable via `Logging.spec.errorOutputRef`.

When to use which: A for uniform well-behaved JSON across the cluster (per-node
parsing, top-level fields); B for per-app formats, regexp/nginx/grok, casting.

syslog-ng mode parses JSON natively; set `Logging.spec.syslogNG.jsonKeyDelim: '#'`
and match on `json#kubernetes#labels#...` (see outputs-syslogng.md).

## Record shape

With defaults, what the aggregator sees per record:

```
{"log" => "<raw line>", "stream" => "stdout", "time" => "...",
 "kubernetes" => {"pod_name", "namespace_name", "pod_id", "labels" => {...},
                  "host", "container_name", "docker_id", "container_image", "container_hash"}}
```

The app line stays an unparsed string in `log` (or `message` on raw CRI) until
something parses it. After a correct B-parse with reserve_data: parsed fields at
top level, `kubernetes.*` intact, raw field removed.

## Multiline

Three mechanisms — pick by where the reassembly should happen:

1. **fluent-bit built-in multiline parsers** (collector-side, cheapest):
   ```yaml
   kind: FluentbitAgent
   spec:
     inputTail: {multiline.parser: [cri, java]}
   ```
   Note: "when this option is enabled the Parser option is not used". Also
   REQUIRED (`[cri]` at minimum) when enabling `filterKubernetes.K8S-Logging.Parser`
   (pod-annotation-driven parsing via `fluentbit.io/parser`), else annotation
   parsing breaks.
2. **`concat` filter** (Flow-side, regex-driven): `multiline_start_regexp`,
   `flush_interval`, `use_first_timestamp`; leave `key` empty for runtime default.
   CRI splits long lines at 16KB — reassemble with `use_partial_cri_logtag: true` +
   `partial_cri_logtag_key: logtag`.
3. **`detectExceptions` filter** (language-aware stack traces:
   `languages: [java, python]`) — but it is mutually exclusive with
   `tag_normaliser` (tag handling) and broken with multi-worker fluentd (#1490
   open). Flow `parser type: multiline` has sharp edges (#1608: needs exact
   `format_firstline` regex syntax; #2071: `multiline_end_regexp` render bug).

## Selecting sources

- Only some pods: Flow in the workload namespace, `match: [{select: {labels: ...}}]`.
- Only some namespaces: ClusterFlow with `namespaces:` or `namespaces_regex: ".*-prod$"`.
- Exclude noisy namespaces: `match: [{exclude: {namespaces: [...]}}, {select: {}}]`.
- Per-container: `container_names: [sidecar]` (container names, not pod names).
- Pod self-exclusion: annotation-driven via `filterKubernetes.K8S-Logging.Exclude`
  (default On) — pods set `fluentbit.io/exclude: "true"`.

## Events and host logs

**Kubernetes events** — EventTailer (cluster-scoped) runs an eventrouter pod that
prints Events to stdout; collect them like any pod:

```yaml
apiVersion: logging-extensions.banzaicloud.io/v1alpha1
kind: EventTailer
metadata: {name: main}
spec: {controlNamespace: logging, positionVolume: {pvc: {...}}}   # pvc optional
---
kind: Flow   # in the control namespace
spec:
  match: [{select: {labels: {app.kubernetes.io/name: main-event-tailer}}}]
  localOutputRefs: [dest]
```

eventrouter 1.0.0 ships with operator 6.7.0 (earlier eventrouter had a memory-leak
history, #1993 — another reason for the 6.7.0 floor).

**Host files / systemd** — HostTailer (namespaced):

```yaml
kind: HostTailer
spec:
  fileTailers: [{name: audit, path: /var/log/audit/audit.log}]
  systemdTailers: [{name: kubelet, systemdFilter: kubelet.service, maxEntries: 100}]
```

Collect via Flow selecting `labels: {app.kubernetes.io/name: <name>-host-tailer}`,
split multiple tailers with `container_names: [<tailer-name>]`.

## External syslog ingestion

The operator has no CRD for **receiving** network syslog (the `syslog` output
ships OUT only). Same idiom as EventTailer: run a receiver pod that prints each
message to stdout, collect it like any pod — real `kubernetes.*` metadata, normal
Flow routing, no custom wiring. Verified live 2026-07-31 (RKE2 1.34/containerd,
axosyslog 4.26.0, non-root):

```
@version: current
options { keep_hostname(yes); };   # default (no) rewrites $HOST to the peer IP —
                                   # behind an SNAT'd Service every sender looks identical
source s_net {
  network(transport("udp") port(5514));                          # RFC3164
  network(transport("tcp") port(5601) flags(syslog-protocol));   # RFC5424
};
destination d_stdout {
  file("/dev/stdout" template("$(format-json --scope rfc5424 --key ISODATE --key SOURCEIP)\n"));
};
log { source(s_net); destination(d_stdout); };
```

Deployment: `ghcr.io/axoflow/axosyslog:<ver>`, command
`/usr/sbin/syslog-ng -F --no-caps -f <conf>`, runs cleanly as non-root with all
caps dropped provided:

- container listens ≥1024; the Service maps 514/UDP + 601/TCP → 5514/5601
  (no NET_BIND_SERVICE needed);
- **emptyDir mounted at `/var/lib/syslog-ng`** — the image dir is root-owned;
  without it syslog-ng CrashLoops with
  `Error creating persistent state file ... Permission denied (13)`.

Each message becomes one stdout JSON line:

```json
{"SOURCEIP":"172.26.1.180","PROGRAM":"charon","PRIORITY":"info","HOST":"fw-edge-01",
 "MESSAGE":"...","ISODATE":"2026-07-31T20:15:00+00:00","FACILITY":"local0",...}
```

- **Fan-in, not one-receiver-per-sender**: senders are disambiguated per message —
  `HOST`/`PROGRAM` from the syslog header, `SOURCEIP` the actual peer. Replicas >1
  behind one Service is fine (stateless; identity travels in the message).
- Route with a normal Flow selecting the receiver pod + parse-point-B `parser`
  (`type: json`, both flags) — `HOST`/`PROGRAM` land as top-level fields for
  per-sender `grep`-filter Flows (fluentd mode) or native content matching
  (syslog-ng mode), or as destination labels.
- For external senders use LoadBalancer/NodePort; `externalTrafficPolicy: Local`
  if `SOURCEIP` must be the true device IP (SNAT otherwise masks it).
- Internal-only exposure (isolated mgmt/backside network) works with Cilium
  LB-IPAM: a `CiliumLoadBalancerIPPool` carved from the internal CIDR with a
  label `serviceSelector`, plus a matching `CiliumL2AnnouncementPolicy` (pool
  alone assigns the IP but never answers ARP — the classic half-config). Pin the
  VIP with `lbipam.cilium.io/ips` since LB-IPAM doesn't check for in-use
  addresses on the subnet. Source-IP behavior (verified live, external
  non-cluster sender through the L2 leader): L2 announcements are
  documented-incompatible with `externalTrafficPolicy: Local`, so what survives
  depends on the LB mode — with `bpf-lb-mode: hybrid`, **TCP keeps the real
  sender IP (DSR); UDP arrives SNAT'd to the leader node's IP**. Prefer TCP
  senders for source fidelity; UDP-only devices are identified by the header
  hostname, which `keep_hostname(yes)` preserves.
- Kubelet-hop limits apply (16KB line split, rotation loss at extreme volume).
  High-EPS alternative: receiver speaks fluentd forward straight to
  `<logging>-fluentd.<controlNamespace>.svc:24240` — but those records have no
  `kubernetes.*` metadata so namespaced Flows never match (ClusterFlow + tag
  handling required), and collector↔aggregator TLS client certs are on you.

## Destinations

Full per-plugin specs: `outputs-fluentd.md` (31 types) / `outputs-syslogng.md` (18).
For testing a chain end-to-end without a real destination:

```yaml
# Option 1: null sink + stdout tap (records appear in fluentd pod logs)
spec:
  nullout: {}
# …with a debug filter in the Flow:  - stdout: {}
# Option 2: file inside the fluentd pod
spec:
  file: {path: /tmp/logs/${tag}, append: true, buffer: {timekey: 1m, timekey_wait: 10s}}
# read back: kubectl exec <logging>-fluentd-0 -- sh -c 'ls /tmp/logs && tail /tmp/logs/*'
```

Remember: delivery latency ≈ `timekey + timekey_wait` — with the quickstart's
1m/30s, logs "missing" for 90 seconds is normal behavior, not a broken chain.
