# tooling.md — supporting tools

What to trust, what to use, what's dead.

## apiserver `apiserver_requested_deprecated_apis` — primary

Truth source for what deprecated APIs the cluster **has actually served**.
Reported as a Prometheus counter per `(group, version, resource, subresource,
removed_release)` label set. Canonical signal — nothing else proves that a
deprecated API is in active use.

How to read it: see `references/cluster-survey.md` § Phase 3a.

**The two gotchas to remember:**

1. **Counter reset on apiserver restart.** Each kube-apiserver process keeps
   its own counters. A pod restart wipes the slate. Combined with HA
   apiservers (3+ replicas typical), a "clean" reading across the fleet
   requires polling each pod *and* trusting that each has run long enough to
   accumulate signal. Cross-check pod ages.
2. **RBAC.** The cluster-root `/metrics` scrape (`kubectl get --raw /metrics`)
   is usually restricted to component-level Go runtime metrics; the
   apiserver's full metrics surface lives at the pod-proxy path. The
   operator's bound role must allow `get pods/proxy` in `kube-system` to
   reach it. Restricted operators should configure Prometheus to scrape the
   apiserver directly and read the metric from there.

## pluto (FairwindsOps) — primary fallback / pre-apply scan

Two distinct uses:

- `pluto detect-api-resources --target-versions k8s=v<minor>` — live cluster
  scan of currently-served resource types. Catches "this kind exists in the
  cluster but is deprecated at target minor."
- `pluto detect-helm --target-versions k8s=v<minor>` — static scan of all
  Helm release manifests. Catches deprecated `apiVersion:` declarations in
  manifests **before** they're applied — useful pre-upgrade when reviewing
  what's about to roll.

**The pluto gotcha to remember.** Default `--target-versions` baselines are
years stale (k8s=v1.25.0, cert-manager=v1.5.3, istio=v1.11.0 in pluto 5.24).
Always pass current/target k8s minor explicitly. Verify the bundled rule
set's freshness with `pluto list-versions`.

Pluto's rule set lives in the binary — works air-gapped. No network call.

Install: GitHub releases at https://github.com/FairwindsOps/pluto/releases.
Verify version periodically; pluto's deprecation database lags upstream
Kubernetes by several months — fine for catching legacy APIs but not for
brand-new deprecations announced in the latest minor.

## endoflife.date — supplementary

EOL data + JSON API. Useful for cross-referencing whether a component minor
is past upstream maintenance.

```
https://endoflife.date/api/v1/products/<name>/
```

Products relevant to this skill's registry: `kubernetes`, `rancher`, `rke2`,
`cilium`, `cert-manager`, `keda`, `argo-cd`, `harbor`, `traefik`, `harvester`,
`gitlab`.

**The endoflife.date gotchas to remember:**

- API is labelled beta; schema may change without notice. Pin parsing logic
  to a known shape and re-verify on schema drift.
- Some products track Prime/EE editions and community editions in the same
  feed. For Rancher specifically, ignore Prime-flavored end-of-line dates;
  the community minor's support window is what the verdict cares about.
- Network call — use only at maintenance time (`skill-improver freshen`),
  not at survey time.

## DEAD — do not use: kube-no-trouble (kubent)

`doitintl/kube-no-trouble`. Last stable 0.7.3; last commit early 2025;
deprecation rulesets stop at k8s 1.32. Will under-report on any cluster
running a current k8s minor. The combination of pluto's static scan +
apiserver metric covers everything kubent did, with current rule sets.

If a legacy runbook mentions kubent, replace with the apiserver-metric +
pluto pair documented in `cluster-survey.md`. No exceptions.

## Pinning logic

Where each tool has version sensitivity:

| Tool | Pin needed? | Why |
|---|---|---|
| `kubectl` | Soft pin to within ±1 of cluster server minor | Outside skew, some operations fail or warn (visible during survey but doesn't affect compat verdict) |
| `helm` | Helm 3.x; v3.14+ recommended | OCI + chart parsing improvements |
| `pluto` | Latest stable | Rule set ages — older pluto under-reports |
| `endoflife.date` parser | Pinned to a known JSON shape | Beta API; schema drift will silently misparse |

## Why no other tools?

The skill keeps the surface small on purpose. The above five (kubectl, helm,
pluto, apiserver metric, endoflife.date) cover every signal needed to verdict
an upgrade. Tools occasionally suggested but deliberately excluded:

- **kubent** — dead (see above).
- **deprek8ion / kubectl-deprecations** — duplicates pluto with smaller rule
  set.
- **kubescape** — security-focused; deprecated-API check is a side feature
  that's noisier than pluto for this use case.
- **k8s-version-checker / similar** — version-checker variants exist for
  image tags; out of scope for compat tracking.

If a new tool appears that improves on this set (e.g. an apiserver-side
exporter that exposes the counter via a stable, RBAC-friendly path),
re-evaluate and update this file.
