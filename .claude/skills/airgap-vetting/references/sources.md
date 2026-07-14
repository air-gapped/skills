# Sources — dated per-URL index

Primary sources grounding the fingerprints, mechanisms, and pitfall classes
in the pattern files. Verified 2026-07-14 unless restamped; freshen mode
probes and re-stamps rows here, fastest-drifting rows marked `volatile`.
Product-row evidence lives inline in `known-products.md` and is re-verified
at re-vet time, not tracked here.

| Source | Grounds | Last verified |
|---|---|---|
| https://docs.sentry.io + DSN format (SDK docs) | Sentry DSN regex, ingest hostnames (telemetry.md) | 2026-07-14 |
| https://docs.scarf.sh (gateway, package-analytics, pixel) | Scarf's three mechanisms (telemetry.md) | 2026-07-14 |
| https://github.com/beatcracker/toptout (repo + schema) | opt-out schema model; FROZEN 2023-02-19 (telemetry.md) | 2026-07-14 |
| https://donottrack.sh (consoledonottrack.com lapsed) | DO_NOT_TRACK spec location; advisory-only status (telemetry.md) | 2026-07-14 |
| checkpoint-api.hashicorp.com/v1/check docs | Checkpoint update-ping mechanism + rehosting pattern (telemetry.md) | 2026-07-14 |
| github.com/qdrant/fastembed #615; tiktoken #369 | offline-flag fallback-download class; ML first-run fetch env vars (downloads-and-proxy.md) | 2026-07-14 |
| kube-prometheus-stack values (admission-webhook Job image) | Helm secondary-image trap (downloads-and-proxy.md) | 2026-07-14 |
| aiohttp #3180; electron #41590; undici #2200; rustls/webpki-roots; distroless #582 | CA-injection failure modes per ecosystem (ca-trust.md) — Node/undici row volatile | 2026-07-14 |
| pip 24.2 changelog (system trust via truststore) | Python OS-trust note (ca-trust.md) | 2026-07-14 |
| secure.gravatar.com URL format; gravatar toggle-ignored issue reports | gravatar email-hash class + verify-with-trace caveat (content-egress.md) | 2026-07-14 |
| elastic.co maps/geoip docs + kibana kill-switch-breakage issues | maps/GeoIP class; kill-switch ≠ degradation lesson (content-egress.md) | 2026-07-14 |
| synapse url_preview config docs | link-preview off-by-default + SSRF-blacklist good pattern (content-egress.md) | 2026-07-14 |
| docs.slack.dev socket-mode | inbound-expectations sub-check (content-egress.md) | 2026-07-14 |
| bitwarden.com configure-push-relay | vendor-held push keys pattern (content-egress.md) | 2026-07-14 |
| docs.dependencytrack.org NVD (feeds retired 2023-12-15) | mirror-and-re-serve + upstream-feed-death lesson (sustainment.md) | 2026-07-14 |
| docs.rke2.io airgap; openshift/oc-mirror README; docs.zarf.dev differential; hauler.dev; docs.replicated.com airgap | offline upgrade patterns + sync tooling (sustainment.md) | 2026-07-14 |
| cosign issues #3423/#3437/#3368/#1293; cosign repo doc/cosign_verify.md (v2.6.3 vs main v3.1.1, direct grep); sigstore/root-signing README; blog.sigstore.dev cosign-3-0 | stdout lie, v2→v3 flag break, TUF 7-day expiry — volatile (verification-time.md) | 2026-07-14 |
| kyverno#10115/#16435; docs.sigstore.dev policy-controller; Red Hat disconnected-sigstore articles (OCP 4.19/4.20) | policy-engine air-gap paths (verification-time.md) | 2026-07-14 |
| notaryproject.dev v1.3 blog + notation#959 + trust-policy spec | default revocation enforcement + skip override (verification-time.md) | 2026-07-14 |
| docker.com DCT retirement + migration blogs | notary.docker.io shutdown 2026-12-08 (verification-time.md, known-products.md) | 2026-07-14 |
| gnupg.org config docs + 2017 devel-list default change | auto-key-retrieve trap (verification-time.md) | 2026-07-14 |
| Oracle PKIXRevocationChecker; MS X509RevocationMode + dotnet/runtime#64689; pkg.go.dev crypto/x509; dev.chromium.org CRLSets | per-runtime revocation defaults (verification-time.md) | 2026-07-14 |
| access.redhat.com NTP KBs 4510631/5071541; RFC 7519 §4.1.4; RFC 5280 §4.1.2.5 | clock prerequisites + skew semantics (verification-time.md) | 2026-07-14 |
| coder.com/docs/install/airgap; docs.jfrog.com manage-licenses + JFConnect offline | license-expiry pattern spectrum (verification-time.md §Licenses) | 2026-07-14 |
| github.com/wolfcw/libfaketime; docs.mitmproxy.org modes/certificates; net7.be Docker iptables (DOCKER-USER); docs.docker.com none-driver; tetragon.io; github.com/elesiuta/picosnitch; github.com/devops-works/egress-auditor | dynamic-harness mechanics (dynamic-harness.md) | 2026-07-14 |
| redhat.com "Is your Operator Air-Gap Friendly?" (NIRDD); OpenShift infrastructure-features annotations | verdict rubric grounding: disconnected vs proxy-aware split (SKILL.md rubric) | 2026-07-14 |
