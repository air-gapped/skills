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

## gh / GitHub releases — version grounding (use-time AND freshen)

`gh` is the truth source for **whether a specific release exists** and **what the
real latest patch of a minor is**. The registry's compat files carry *sifted*
version numbers that can be fabricated (a verdict once cited Argo CD `v3.2.10` /
`v3.2.12` — the line ended at `v3.2.6`, unpatched); `gh` grounds them. Use it at
**survey time when the workstation is online** (House Rule #8 / cluster-survey
Phase 4b) and at **freshen time** when writing the files. Full protocol +
component→repo map: `references/version-verification.md`.

**The gotcha that matters — queries get rubber-stamped.** Existence, list, and
even per-tag lookups will confirm plausible-but-fake versions (observed:
`releases/tags/v3.2.10` returned 200; harbor `v2.15.0` "confirmed" while
`releases/latest` was `v2.14.4`; the releases *list* echoes back any version
named in the same command). Only absurd fakes (`v9.9.9`, `v2.99.0`) reliably
404. So **never ask "does vX exist?"** — instead:

- Anchor on the authoritative scalar, with no candidate version in the command:
  ```bash
  gh api repos/<org>/<repo>/releases/latest --jq '.tag_name'   # the real ceiling
  ```
  Reject anything cited that is newer than this.
- Enumerate, then take the max yourself:
  ```bash
  gh api 'repos/<org>/<repo>/releases?per_page=100' \
    --jq '[.[]|select(.prerelease|not)|.tag_name]|.[]' | grep -E '^v?<minor>\.' | sort -V | tail -1
  ```

`gh` is authenticated and returns structured JSON — prefer it over WebFetch of
release pages. **GitLab is the exception** — its chart is not on GitHub; use the
GitLab API / `glab` / `helm search`, else mark the version `UNVERIFIED`.

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
- Network call. Use at **freshen** time, and at **survey** time too when the
  workstation is online (EOL confirmation as part of version grounding, House
  Rule #8). A genuinely air-gapped survey skips it and marks EOL claims
  `UNVERIFIED`.

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
