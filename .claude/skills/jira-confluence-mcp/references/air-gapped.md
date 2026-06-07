# Air-gapped install of mcp-atlassian

The full recipe for installing the server with no internet, plus the in-container CA handling that bites almost everyone.

## First principle: three artifact types, three mirrors

"Installing" mcp-atlassian materialises a runtime + a dependency closure that does **not** all live in one place. A mirror only helps if it serves the *right artifact type*:

| Need | Lives in | Served by |
|---|---|---|
| Source + git tags | git | a git mirror (cgit, Gitea, …) |
| Python dependency **wheels** (the `uv.lock` closure) | PyPI | an internal PyPI index (Artifactory / Nexus / devpi) |
| The **prebuilt image** + its base layers | OCI registry | an internal registry (Harbor, …) |

A **full git mirror is NOT sufficient by itself** — Python packages don't commit their dependency wheels, so the ~26 direct deps (+ transitive closure: `atlassian-python-api`, `httpx`, `fastmcp`, `pydantic`, `markdownify`, `keyring`, `truststore`, …) are simply not in the repo. Git serves git, not wheels and not images.

What the git mirror *does* give you (when it carries **tags**): correct source + a real version. The build backend is `uv-dynamic-versioning`, which derives the version from git tags — a tag-less clone or tarball builds as a bogus `0.0.0`. With a full tag-carrying mirror, that gotcha is gone.

## Path A — mirror the prebuilt image (recommended; needs only a registry)

The published image is **self-contained**: its Dockerfile bakes the full `.venv` (Python 3.13 + every wheel) into a `python:3.13-alpine` final stage. So once the image is in your registry, **nothing touches PyPI, ghcr, or git at install or run time.** This is the only path that needs neither a PyPI mirror nor the git mirror.

```bash
# 1. Resolve a real digest for the release you want (don't pin :latest)
skopeo inspect docker://ghcr.io/sooperset/mcp-atlassian:v0.21.1 | jq -r '.Digest'

# 2. Copy into your registry. --all preserves the multi-arch manifest;
#    drop it / use --override-arch to copy a single platform if the gap is one arch.
skopeo copy --all \
  docker://ghcr.io/sooperset/mcp-atlassian@sha256:<digest> \
  docker://harbor.internal/mirror/mcp-atlassian@sha256:<digest>
# (also tag it for humans: skopeo copy ...:v0.21.1 ...:v0.21.1)

# 3. Connect to Claude Code. stdio MCP server → `docker run -i` is mandatory.
claude mcp add mcp-atlassian \
  -e JIRA_URL=https://jira.internal.company.com \
  -e JIRA_PERSONAL_TOKEN=<pat> \
  -- docker run -i --rm -e JIRA_URL -e JIRA_PERSONAL_TOKEN \
       -v /etc/pki/internal-ca.crt:/usr/local/share/ca-certificates/internal-ca.crt:ro \
       harbor.internal/mirror/mcp-atlassian@sha256:<digest>
```

Pin **by digest** (`@sha256:…`), not a tag — the digest is what your supply-chain controls and what survives a re-pushed tag. Verify the source image's signature/provenance (cosign) if your policy requires it before mirroring. Keep the git mirror only for audit/SBOM — it is not needed to run the image.

## Path B — build the image from your git mirror (needs registry **and** PyPI)

Only choose this if policy requires building from source you control. The repo `Dockerfile` proves what the build still reaches for:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.13-alpine AS uv   # ← base image #1 (registry)
RUN uv lock
RUN uv sync --frozen --no-install-project --no-dev    # ← pulls dep wheels (PyPI)
COPY . /app
RUN uv sync --frozen --no-dev --no-editable           # ← installs project (PyPI)
FROM python:3.13-alpine                               # ← base image #2 (registry)
COPY --from=uv /app/.venv /app/.venv
ENTRYPOINT ["mcp-atlassian"]
```

So Path B needs, all inside the gap:
1. The git mirror (source + tags).
2. **Both base images mirrored** to your registry: `ghcr.io/astral-sh/uv:python3.13-alpine` and `python:3.13-alpine`.
3. **A PyPI index** the build can reach for the two `uv sync` steps — point uv at it with `UV_INDEX_URL` / `UV_DEFAULT_INDEX` (or a pre-populated `--mount=type=cache,target=/root/.cache/uv`).

Build with the base images rewritten to your registry and `UV_INDEX_URL` set, then push the result. More moving parts than Path A for the same outcome — prefer A unless build-from-source is mandated.

## Path C — pip / uv install, no Docker (needs PyPI mirror + toolchain)

For a host install without containers: git mirror (or just the wheel) **+** an internal PyPI index **+** Python ≥3.10 **+** uv/pip inside the gap.

- Generate the exact wheel set to seed the index from the lockfile: `uv export --frozen --no-dev --format requirements-txt > requirements.lock`, then mirror those wheels.
- Install offline against the internal index: `UV_INDEX_URL=https://pypi.internal/simple uvx mcp-atlassian` (or `pip install --index-url …`).
- Or pre-seed the uv cache on a connected box and transfer it, then run with `UV_OFFLINE=1`. Avoid bare `uvx` at *launch* if it would re-check PyPI each start — a cached/offline cache or the image avoids that.

## The in-container CA (most common air-gap surprise)

A self-contained image still does **not** trust *your* internal CA — it ships only the stock Alpine bundle. So an internal Jira behind a private-CA cert fails TLS until you fix trust. Two options:

- **Mount the CA (preferred — keeps verification on).** The image is `python:3.13-alpine`; mount your CA into the cert dir:
  ```bash
  docker run -i --rm \
    -v /etc/pki/internal-ca.crt:/usr/local/share/ca-certificates/internal-ca.crt:ro \
    ... harbor.internal/mirror/mcp-atlassian@sha256:<digest>
  ```
  `truststore` reads the OS store, so a cert in the container's CA dir is honoured. (If a step requires it, `update-ca-certificates` rebuilds the bundle; the mount alone is usually enough for `truststore`.) Alternatively point at a bundle file: `-e REQUESTS_CA_BUNDLE=/path/ca.pem` or `-e SSL_CERT_FILE=/path/ca.pem`.
- **Disable verification (escape hatch).** `-e JIRA_SSL_VERIFY=false` (`CONFLUENCE_SSL_VERIFY=false`). Acceptable on a trusted internal network; record it as a deliberate downgrade. `MCP_ATLASSIAN_USE_SYSTEM_TRUSTSTORE=false` falls back to the bundled certifi CA instead of the OS store.

## Runtime is genuinely offline-friendly — on Data Center

Once installed, with **PAT auth** the server only talks to your internal Jira/Confluence over HTTPS — **no mandatory internet phone-home**, no telemetry required for operation. (Cloud OAuth flows *would* hit Atlassian, but DC uses internal PAT, so that's moot.) The only run-time dependency is reachability of your Jira/Confluence host and TLS trust (above).

## Sources
See `references/sources.md`. Anchors: the repo `Dockerfile` + `pyproject.toml` (`requires-python>=3.10`, `uv-dynamic-versioning`, dep list), the Installation + Authentication + Configuration + Troubleshooting docs.
