# Q3 + Q4 — Runtime Downloads & Proxy-in-Disguise

## Runtime downloads that break air-gap (Q4)

**Organizing principle: build-time vs runtime.** Downloads in a Dockerfile
`RUN` layer are fine (they happen on the connected build host); downloads in
`ENTRYPOINT`/`CMD`/`entrypoint.sh`/initContainers/first-run code break
air-gap. Grep entrypoints for `curl|wget|pip install|npm install`.

### Highest-frequency breaker classes

- **ML asset first-run fetches** — common libraries fetch models,
  encodings, or data at first use; each has a pre-seed/offline path:
  tiktoken (`TIKTOKEN_CACHE_DIR`), HuggingFace Hub
  `from_pretrained(`/`snapshot_download` (`HF_HUB_OFFLINE=1`,
  `TRANSFORMERS_OFFLINE=1`), NLTK `nltk.download` (`NLTK_DATA`), Playwright
  browsers (`PLAYWRIGHT_BROWSERS_PATH` pre-seed +
  `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`). Grep for the library, then verify
  the pre-seed path is wired up.
- **Offline flags are not proof** — offline modes have shipped with code
  paths that *fall back to downloading* when the offline path errors.
  Always grep for fallback download hosts
  (`storage.googleapis.com|s3.amazonaws.com|[a-z0-9-]+\.blob\.core\.windows\.net`)
  even when an offline flag is present; prefer a *tested* offline path
  (docs example or closed issue) over flag existence.
- **Feed/ruleset/DB updaters at start** — scanners and security tools
  commonly fetch databases or rulesets at startup. Find BOTH the skip flag
  AND the repository-override flag (skip-only means stale-forever), and
  check whether registry-hosted rulesets also send project metadata
  upstream when fetched. Full sustainment detail:
  `references/sustainment.md`.
- **Plugin installs at container start** — env-var-driven plugin lists
  downloaded from a vendor registry at startup. Grep entrypoint/startup
  code for plugin-install hooks; the in-gap failure signature is a startup
  crash referencing the registry host or a temp-file write.
- **Helm secondary images** — breakers hide in hook/Job/initContainer
  images *outside* the main `image:` block. Enumerate with
  `helm template <chart> | grep -oE 'image: *"?[^"]+' | sort -u`, never by
  grepping values.yaml alone. Caveat: this misses refs computed in
  `_helpers.tpl` or by operators at runtime — **runtime-computed image
  names are an automatic `no-go`** (defeats webhook-rewriting mirrors and
  all mirroring). Charts honoring a single `global.imageRegistry`-style
  override (the Bitnami convention) are a green flag.
- **License phone-home** — its own failure class; mature vendors ship
  signed license files/JWTs validated locally (offline activation). See
  `references/verification-time.md` §Licenses for expiry behavior.

## Proxy-in-disguise detection (Q3)

The sharpest published test: **can you read, run, and self-host the
component that stores credentials and executes the work?** An open
SDK/CLI/MCP wrapper does not make the platform open source.

1. **Repo topology** — if the org's public repos are all
   `*-sdk`/`*-cli`/`docs`/`examples` with no server or `docker-compose.yml`
   that runs the engine, it's a thin client around a hosted backend.
2. **Hardcoded base URLs** —
   `grep -rE 'https?://api\.[a-z0-9.-]+\.(com|dev|ai)'`; then check whether
   the constant is overridable via env/config.
3. **BYOK-but-still-proxied** — bring-your-own-key does not imply
   direct-to-provider traffic. Read the BYOK docs page for "routed through
   our servers/backend".
4. **SDK demands a cloud key even against a self-hosted URL** — try the
   client against a self-hosted endpoint; a mandatory vendor API key is the
   tell.
5. **Pricing page, not the repo** — "self-hosted" appearing only under an
   Enterprise tier is the tell.
   `gh search issues --repo <o>/<r> "offline OR air-gap OR login required"`
   surfaces mandatory-login-on-a-local-tool complaints. Skip when vetting
   from inside a gap; note as not-run.
6. **License-as-contract** — a product can be 100% technically mirrorable
   yet require air-gap as a negotiated license tier, enforced by a license
   ping that nags, degrades, or shuts the instance down. Score as a
   `proxy-in-disguise` trigger, not an artifact-only check.
7. **Identity/auth against vendor cloud** — the engine can be self-hosted
   while login still needs the internet; sub-check list at the tail of
   `references/content-egress.md`.

**The Q3 boundary is settled dynamically, not statically:** the mandated
tie-breaker is the post-activation egress-deny test
(`references/dynamic-harness.md` step 5). Works behind an HTTP proxy but
dies behind a true gap = proxy-in-disguise.

## Positive air-gap signals (green flags to reward in Q8)

A dedicated docs page titled "Air-Gapped"/"Offline"/"Disconnected"; a
published image-list file or SBOM; distribution as a Zarf package /
Replicated air-gap bundle / Hauler archive; `global.imageRegistry`-style
single registry override; documented offline env vars by name;
cryptographic-signature local license validation; vendor tests the air-gap
path in CI.
