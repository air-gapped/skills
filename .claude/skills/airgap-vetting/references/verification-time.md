# Sub-checks — Time, Revocation & Offline Signature Verification

**Contents:** cosign/sigstore (stdout lie, v2→v3 flags, TUF expiry) · other
signers (Notation, DCT, GPG) · OCSP/CRL per runtime · clock dependencies ·
licenses vs wall clock · greps.

Run these when the candidate (or its install path) verifies signatures
(cosign, Notation, GPG), embeds a browser, does its own TLS revocation
checking, or carries an expiring license. Provenance verification is itself
a common hidden egress, and air-gapped environments add drifting clocks
with no external responders.

## Sigstore / cosign — verifying provenance can itself phone home

A naive `cosign verify` calls `tuf-repo-cdn.sigstore.dev` (trust-root
refresh) and `rekor.sigstore.dev` (log lookup); signing additionally hits
`fulcio.sigstore.dev` + `oauth2.sigstore.dev`.

Two traps:

1. **stdout lies** — "Existence of the claims in the transparency log was
   verified offline" prints statically regardless of actual behavior
   (maintainer-confirmed, cosign#3423). Never accept cosign output as
   no-egress evidence; observe the network.
2. **v2→v3 flag break** — v2.6.3 `verify` has `--offline`,
   `--private-infrastructure`, `--new-bundle-format`, `--rekor-url`; cosign
   v3.1.1 removed all four (verified by repo-doc grep 2026-07-14), replaced
   by bundle-by-default + `--trusted-root <json>` + `--local-image`.
   Version-gate any guidance emitted in the report.

Zero-egress keyless verification IS possible — the protobuf bundle embeds
the Rekor SET/inclusion proof. Recipe: online side `cosign initialize`
(`--mirror` accepts `file:///` for air-gap) + `cosign save`; gapped side
verify with `--trusted-root` + `--local-image`.

**TUF metadata is a ~7-day time bomb**: sigstore's public root re-signs
every ≤3 days and consumers must refresh within ~7; expired mirrors
historically panicked (`failed to decode timestamp.json: expired at …`,
cosign#1293). `--trusted-root` bypasses the TUF client (and its expiry
checks) entirely. Env escape hatches: `SIGSTORE_ROOT_FILE`,
`SIGSTORE_REKOR_PUBLIC_KEY`, `SIGSTORE_CT_LOG_PUBLIC_KEY_FILE` (v2-era;
whether v3 still honors them is a freshen target).

Policy engines: Kyverno `rekor.ignoreTlog: true` / inline pubkeys (but
kyverno#10115 documents the flag being ignored — test, don't trust);
sigstore policy-controller `TrustRoot` CR accepts a serialized TUF repo for
air-gap; OpenShift `ClusterImagePolicy` embeds Fulcio CA + Rekor key with
no callout, and oc-mirror v2 mirrors sigstore signatures alongside images
(OCP 4.19+).

## Other signers

- **Notation** verifies offline in principle, but its **default trust
  policy enforces OCSP/CRL revocation checking** — in a gap: "revocation
  status is unknown" failures (notation#959). Opt out per-policy:
  `"override": { "revocation": "skip" }` (or `"log"`) in
  `trustpolicy.json`. CRL caching landed v1.3.0.
- **Docker Content Trust is retired** (announced July 2025;
  `notary.docker.io` shuts down 2026-12-08). Flag any runbook still setting
  `DOCKER_CONTENT_TRUST=1` as verifying against a corpse.
- **GPG** verifies offline by default (`--no-auto-key-retrieve` since
  2017), but `auto-key-retrieve` in gpg.conf turns unknown-key-signature
  verification into a keyserver/WKD lookup — grep for it.

## OCSP/CRL as hidden egress, per runtime

| Runtime | Default | Knobs / notes |
|---|---|---|
| Java | revocation checking **off** | phones home only if `ocsp.enable` / `com.sun.security.enableCRLDP` / `PKIXRevocationChecker` enabled; `Option.SOFT_FAIL` exists |
| .NET / Windows | `X509RevocationMode.Online` fetches CDP **and AIA** URLs — chain *building* can egress, not just revocation | gap behavior: long `UrlRetrievalTimeout` then `RevocationStatusUnknown`/`OfflineRevocation` flags the caller decides on; `Offline` uses cached CRLs; `NoCheck` disables |
| Go | `crypto/x509` does **no** revocation checking (re-verified 2026) | the Go cloud-native ecosystem is air-gap-quiet and revocation-blind by default |
| Chromium / Electron | no online checks; CRLSets via component updater | embedded browsers in a gap run silently stale (soft-fail, no breakage) |

## Clock dependencies

- Minutes of drift → `x509: certificate has expired or is not yet valid`
  (documented Kubernetes bootstrap failures).
- **Internal NTP is a documented prerequisite** for disconnected installs
  across major platforms. Check the candidate's docs for an equivalent
  statement; absence is a gap in their air-gap story.
- JWT `exp` (RFC 7519 §4.1.4: leeway "no more than a few minutes") and SAML
  `NotOnOrAfter` (recommended 30–120 s skew) break under drift.
- Sigstore's verify-time model is drift-tolerant (compares embedded Rekor
  SET / RFC 3161 timestamps against the ~10-minute Fulcio cert window, not
  local clock) — but TUF refresh is not.

## Licenses vs wall clock

- **Model behavior (green flag):** license validated locally by
  cryptographic signature, zero callbacks ever, and the vendor publishes
  the full hostname list to mirror or disable.
- **Common non-fatal pattern:** banner ahead of expiry plus a grace period
  of weeks; a missed manual usage sync does not downgrade features.
- **Danger patterns:** platform drops to read-only (or shuts down) at
  expiry; entitlement loading or renewal requires connectivity.

Vet: what happens at expiry (grace vs read-only vs shutdown), and whether
renewal requires connectivity.

## Greps for this file's checks

Hostnames:
`rekor\.sigstore\.dev|fulcio\.sigstore\.dev|tuf-repo-cdn\.sigstore\.dev|oauth2\.sigstore\.dev|notary\.docker\.io`.
Keys/flags: `--rekor-url`, `ignoreTlog`, `"revocation"` overrides in
trustpolicy.json, `auto-key-retrieve`, `ocsp.enable`,
`com.sun.security.enableCRLDP`, `X509RevocationMode`,
`DOCKER_CONTENT_TRUST`. TUF artifacts: `root.json` / `timestamp.json` /
`trusted_root.json` and the `"expires"` fields inside them. License code:
`exp` / `notAfter` / `NotOnOrAfter` checks near license validation.

Dynamic confirmation: the `faketime` skew runs
(`references/dynamic-harness.md` step 8).
