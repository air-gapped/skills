# Air-gapped GitLab — the image set the chart does not reveal

**Tag convention.** Untagged claims were verified against a primary source or a
live install on 2026-08-29. **[A]** = reported but not independently
re-verified — re-check before acting.

## Start from the right expectation

**GitLab has no official air-gapped Helm guidance.** The offline quick-start
guide scopes itself explicitly to the Linux package — *"This guide assumes the
server is Ubuntu 20.04 using the Linux package installation method"* — and
contains no image-mirroring or Helm content. **[A]**

**There is no GitLab-maintained image manifest per chart release.** The
documented community method is: clone the chart at the exact version,
`grep -nir "image:"` across all subcharts, and accept that it is incomplete.
Charts issue #4918 ("mirror chart images to an external registry") is open —
upstream has not solved its own single point of failure either. **[A]**

Treat air-gap as an engineering problem the operator owns, with the chart as an
**unreliable narrator about its own image set**.

## Six sources of images a rendered manifest cannot show

A `grep image:` over a render of *site* values finds none of these.

1. **The runner helper image.** Declared in the runner's `config.toml` as TOML
   (`helper_image = "..."`), tagged `${CI_RUNNER_VERSION}`, expanded by the
   runner at job time. Runner issue #4509 documents the underlying asymmetry
   (runner tagged `CI_RUNNER_VERSION`, helper historically `CI_RUNNER_REVISION`)
   and is **closed** — the tagging was reconciled, but the image still never
   appears in a rendered manifest, so it stays on the list. **[A]**
   **Derive it, do not hardcode it:** take the runner's chart image tag
   (`gitlab-runner:alpine-v18.6.3`), strip `alpine-v`, substitute →
   `gitlab-runner-helper:x86_64-v18.6.3`. Confirmed against a live runner
   reporting exactly `18.6.3`. Deriving from the values file means editing
   `helper_image` moves the list.
2. **The default CI job image** (`image = "ubuntu:22.04"` in the same TOML) —
   whatever runs when a `.gitlab-ci.yml` names no image. If a separate
   base-image pipeline mirrors it, **write that down**: its absence from the
   list looks exactly like an oversight and invites a well-meaning "fix" that
   adds noise.
3. **Helm hook Jobs** — migrations, shared-secrets, upgrade-check — which exist
   only during `helm upgrade`.
4. **`helm test` pods.**
5. **Images only rendered when an optional subchart is enabled** that the site's
   values disable. A render of *site* values misses them; a render of *stock*
   values includes them. At chart 10.x this includes `ai-gateway`
   (`ai-gateway.install: false` by default), `gitlab-zoekt`, `openbao`,
   `envoy-gateway` and the bundled ingress/cert-manager charts — several of
   which are new since chart 9.x, so a mirror list carried forward from an
   older version has gaps that no diff of *site* values reveals.
6. **Security scanner images**, fetched at pipeline runtime by
   `Secure-Binaries.gitlab-ci.yml`. Without mirroring these *and* rewriting the
   template, scanners cannot run offline at all. **[A]**

**Derive the list from more than one render pass** — site values *and* stock
defaults — plus an explicit extraction from the runner config, plus the derived
helper tag.

**From chart 10.0 the stock-defaults render fails outright** unless scaffolded
with placeholder external-dependency values. The all-features image sweep dies
with it. Scaffold: `references/upgrade-campaign.md` § the chart-10 wall.

**Sort the list under `LC_ALL=C`.** Without it the list reorders between
machines purely by locale collation (`-` vs `:` around `redis` /
`redis-exporter`), producing phantom diffs between versions that waste review
attention.

## Things that silently need internet

Each fails quietly or noisily depending on the component; none of them
announces itself as an air-gap problem. **[A]**

| Feature | Behaviour offline | Disable separately? |
|---|---|---|
| Version Check / Service Ping | attempts and fails to reach out | yes |
| Runner version management | separate phone-home about runner staleness | **yes — not covered by disabling Service Ping** |
| Scanner advisory / vulnerability DBs | need manual sync; auto-update checks cannot run; auto-remediation MRs may not work at all | n/a |
| GitLab Duo | standard self-managed Duo needs egress to GitLab's AI Gateway | see `references/duo-ai.md` |

## Pinning

**GitLab's docs are silent on digest-vs-tag pinning** for both Omnibus and
Helm. **[A]** Defensible practice, independent of the docs:

- Pin the chart **tarball** in git, not a repo reference. A chart clone only
  ~4 weeks stale has failed to deploy because the images no longer matched what
  the chart expected. **[A]**
- Keep **both** the digest form and the de-digested tag form in the mirror list.
  Some references arrive with a digest attached while the same image is pulled
  by tag elsewhere.
- Vendor the rendered template, the stock values and the image list alongside
  the tarball. They are the common ancestors the next upgrade's diff layers
  need → `references/upgrade-campaign.md`.

Artifact vetting before it crosses the gap: **`airgap-vetting`**.
