# Q5 — Custom CA / Private TLS Trust

The recurring trap across every ecosystem: **additive vs replacement
semantics**. `NODE_EXTRA_CA_CERTS` *appends* to defaults (the safe kind);
`REQUESTS_CA_BUNDLE`, `SSL_CERT_FILE`, and `javax.net.ssl.trustStore`
*replace* them — pointing any of the latter at a file containing only the
corporate root breaks TLS to every public-CA site. Flag docs that say "add
your CA" for a replacement-semantics variable.

| Ecosystem | Inject via | Failure mode to grep for |
|-----------|-----------|--------------------------|
| Python | `REQUESTS_CA_BUNDLE`/`SSL_CERT_FILE`; `truststore` pkg for OS trust; pip ≥24.2 uses OS store | `certifi.where()` w/o env override; **aiohttp ignores all CA env vars** (aiohttp#3180); `verify=False` |
| Node | `NODE_EXTRA_CA_CERTS` (appends); npm `cafile`; Yarn Berry `httpsCaFilePath` | **Electron ignores `NODE_EXTRA_CA_CERTS`** (electron#41590); **undici/fetch() ignored it on Node 18** (undici#2200); `rejectUnauthorized:false` |
| Go | native system store; `SSL_CERT_FILE`/`SSL_CERT_DIR` | **`FROM scratch`/distroless with no ca-certificates** → `x509: unknown authority`; `InsecureSkipVerify: true` |
| Java | JKS/PKCS12 truststore; `-Djavax.net.ssl.trustStore`; `keytool -import` | replaces cacerts entirely; per-app `SSLContext` bypass; empty `X509TrustManager` |
| Rust | `rustls-native-certs` / native-tls (runtime OS trust) | **`webpki-roots` compiles Mozilla roots INTO the binary — cannot trust a corporate CA without a rebuild**; `danger_accept_invalid_certs` |
| Containers/OS | Debian `/usr/local/share/ca-certificates/*.crt` + `update-ca-certificates`; RHEL/UBI `/etc/pki/ca-trust/source/anchors/` + `update-ca-trust` | wrong distro's path silently no-ops; distroless has no updater |
| Kubernetes | OpenShift `config.openshift.io/inject-trusted-cabundle=true`; cert-manager trust-manager `Bundle` | registries need SEPARATE trust: `/etc/docker/certs.d/`, containerd `hosts.toml` `ca=` |

## Hard blockers (cannot be fixed by injecting a CA at runtime)

1. **rustls `webpki-roots`-only** — roots compiled into the binary; needs a
   rebuild.
2. **Certificate pinning** — forces a proxy-bypass rule, which strict
   environments reject.

Both force either a rebuild or a bypass → weigh heavily toward `no-go` when
the pinned/compiled endpoint is one that must be mirrored.

## Anti-pattern taxonomy (negative signals)

1. Verification-off switches offered *instead of* a CA option: `--insecure`,
   `verify=False`, `NODE_TLS_REJECT_UNAUTHORIZED=0`,
   `InsecureSkipVerify:true`, `strict-ssl=false` — these disable
   authentication entirely; security teams reject them.
2. Compiled-in roots (above).
3. Certificate pinning (above).

## Positive greps

`NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `truststore`,
`rustls-native-certs`, `SystemCertPool`, `--cacert|--ca-bundle|cafile` in
the arg parser.

## Dynamic confirmation

The mitmproxy CA-injection test (`references/dynamic-harness.md` step 4)
settles this question empirically: decrypts cleanly → passes; still fails
after correct CA injection ("certificate verify failed" on the handshake)
→ pinning → blocker. When version-specific TLS behavior matters (e.g.
which Node versions' `fetch()` honor `NODE_EXTRA_CA_CERTS`), test
dynamically rather than trusting a table.
