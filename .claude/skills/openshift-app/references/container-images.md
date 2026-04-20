# Container Images Reference

## Table of Contents
- [UBI Variant Details](#ubi-variant-details)
- [Multi-Stage Build Patterns](#multi-stage-build-patterns)
- [Arbitrary UID Handling](#arbitrary-uid-handling)
- [Red Hat Container Certification](#red-hat-container-certification)
- [Podman and Build Tooling](#podman-and-build-tooling)
- [ImageStreams and Internal Registry](#imagestreams-and-internal-registry)
- [Image Size Optimization](#image-size-optimization)
- [FIPS-Compliant Images](#fips-compliant-images)

---

## UBI Variant Details

### ubi9 (Standard)
- Full RHEL 9 userspace with `dnf` and `yum`
- Includes tar, gzip, and common utilities
- Use as: builder stage, development, or when you need `dnf install`

### ubi9-minimal
- Stripped-down, uses `microdnf` (not dnf/yum)
- ~36 MB compressed / ~92 MB on disk
- Use as: light runtime when you need to install a few packages

### ubi9-micro
- **No package manager at all** -- packages must be installed via multi-stage build
- Smallest UBI variant (~12 MB compressed)
- Smallest attack surface
- Use as: production runtime image
- **Gotcha**: if a post-submission Clair scan finds CVEs, you cannot mitigate them
  in-image since there's no package manager. You must rebuild from an updated base.

### ubi9-init
- Includes systemd support
- Uses `SIGRTMIN+3` as StopSignal
- Use for: multi-service containers that need systemd process management

### Licensing
UBI is freely redistributable without a Red Hat subscription. Technical support
requires an active RHEL or OpenShift subscription when running UBI on the Red Hat
supported stack.

---

## Multi-Stage Build Patterns

### Standard Three-Stage Pattern

For compiled languages (Go, Rust, C++, Java):

```dockerfile
# Stage 1: Dependencies
FROM registry.access.redhat.com/ubi9/ubi-minimal:latest AS deps
RUN microdnf install -y --setopt=tsflags=nodocs --setopt=install_weak_deps=0 \
    golang-1.22.* && microdnf clean all

# Stage 2: Build
FROM deps AS builder
COPY . /src
WORKDIR /src
RUN CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /app/server ./cmd/server

# Stage 3: Runtime
FROM registry.access.redhat.com/ubi9/ubi-micro:latest
LABEL name="mycompany/myapp" \
      vendor="My Company" \
      version="1.0.0" \
      release="1" \
      summary="My Application" \
      description="My Application on OpenShift"
COPY licenses/ /licenses/
COPY --from=builder --chown=1001:0 /app/server /app/server
RUN chmod g=u /app/server
USER 1001
EXPOSE 8080
ENTRYPOINT ["/app/server"]
```

### Python / Node.js Pattern (Runtime Needed)

```dockerfile
FROM registry.access.redhat.com/ubi9/python-312:latest AS builder
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM registry.access.redhat.com/ubi9/python-312:latest
COPY --from=builder /opt/app-root/lib /opt/app-root/lib
COPY --chown=1001:0 . /opt/app-root/src
USER 1001
EXPOSE 8080
CMD ["python", "app.py"]
```

### installroot Technique (Maximum Size Reduction)

Install packages into a clean directory tree, then copy only that tree:

```dockerfile
FROM registry.access.redhat.com/ubi9/ubi:latest AS installer
RUN dnf install -y --installroot /output --releasever 9 \
    --setopt=tsflags=nodocs --setopt=install_weak_deps=0 \
    python3 && \
    dnf clean all --installroot /output && \
    rm -rf /output/var/cache/dnf /output/var/log/*

FROM scratch
COPY --from=installer /output /
```

**Note**: `FROM scratch` causes issues with compliance scanners. Prefer UBI Micro
as final stage unless image size is the absolute priority.

### Key dnf/microdnf Flags for Size

- `--setopt=tsflags=nodocs` -- skip documentation
- `--setopt=install_weak_deps=0` -- skip weak/suggested dependencies
- `--nodocs` -- alternative nodocs flag
- `--releasever 9` -- pin RHEL version for installroot
- Always run `microdnf clean all` or `dnf clean all` in the same RUN layer

---

## Arbitrary UID Handling

### How It Works

OpenShift assigns each namespace a UID range via the annotation:
```
openshift.io/sa.scc.uid-range: 1000680000/10000
```

Pods run as a random UID from this range (e.g., 1000680042) with GID 0.

### Dockerfile Pattern

```dockerfile
# Create app directory owned by root group
RUN mkdir -p /app && \
    chgrp -R 0 /app && \
    chmod -R g=u /app

# Set conventional non-root user
USER 1001
```

The `chmod -R g=u` mirrors owner permissions to the root group, so the arbitrary
UID (which is in GID 0) can read/write/execute as needed.

### /etc/passwd Workaround

Some applications (SSH, certain JVMs, NSS lookups) require a valid passwd entry.
Make `/etc/passwd` group-writable and use an entrypoint script:

```bash
#!/bin/bash
if ! whoami &>/dev/null 2>&1; then
  if [ -w /etc/passwd ]; then
    echo "${USER_NAME:-default}:x:$(id -u):0:${USER_NAME:-default}:${HOME}:/sbin/nologin" >> /etc/passwd
  fi
fi
exec "$@"
```

In the Dockerfile:
```dockerfile
RUN chmod g=u /etc/passwd
ENTRYPOINT ["/app/uid-entrypoint.sh"]
CMD ["/app/server"]
```

**Security note**: making `/etc/passwd` world-writable is a risk (allows in-container
escalation to root). Only use when the application truly needs it.

### Init Containers Cannot Fix Permissions

A common Kubernetes pattern is using a privileged init container to `chown` volumes.
**This does not work under restricted SCC** -- init containers run as the same
arbitrary UID. Fix permissions in the Dockerfile or use `fsGroup` in the pod
securityContext (if SCC allows it).

### Volume Permissions

Volume mounts are owned by `root:root`. Options:
- Set `fsGroup` in pod securityContext (SCC must allow it) -- sets group ownership
  on volume contents
- Design the application to create its own subdirectories within the mount point
- Use emptyDir for temporary writable storage

---

## Red Hat Container Certification

### Preflight Checks (9 Total)

1. **RunAsNonRoot** -- image must not run as root (USER directive or numeric UID)
2. **BasedOnUBI** -- base image must be UBI or RHEL
3. **HasModifiedFiles** -- cannot modify files in base Red Hat layers (except security updates)
4. **HasLicense** -- `/licenses` directory must contain software terms
5. **HasUniqueTag** -- image must have a unique tag (not just `latest`)
6. **LayerCountAcceptable** -- max 40 layers total (recommended 5-20)
7. **HasNoProhibitedPackages** -- no banned packages
8. **HasRequiredLabel** -- all required labels present
9. **Post-submission vulnerability scan** -- Clair grade C or above

### Required Labels

```dockerfile
LABEL name="vendor/product" \
      vendor="Company Name" \
      version="1.0.0" \
      release="1" \
      summary="One-line summary" \
      description="Detailed description"
```

Optional but recommended: `io.k8s.display-name`, `io.k8s.description`,
`io.openshift.tags`, `io.openshift.expose-services`.

### Security Updates

Include in your Dockerfile:
```dockerfile
RUN dnf -y update-minimal --security \
    --sec-severity=Important --sec-severity=Critical && \
    dnf clean all
```

### Recertification Triggers

- Critical CVE older than 3 months
- Important CVE older than 12 months
- Certification older than 12 months
- Corresponding RHOCP 4.x release exits EUS Term 2

---

## Podman and Build Tooling

**Podman** is Red Hat's recommended build tool -- daemonless, rootless, no central
daemon, no single point of failure. The full toolchain:

- **podman**: build, run, push images (Docker CLI compatible)
- **buildah**: low-level image building (used by podman internally)
- **skopeo**: copy/inspect images between registries without pulling

### Build Commands

```bash
# Standard build
podman build -t myapp:1.0.0 -f Containerfile .

# Multi-arch build
podman build --platform linux/amd64,linux/arm64 --manifest myapp:1.0.0 .
podman manifest push myapp:1.0.0 docker://registry.example.com/myapp:1.0.0

# Push to OCI registry
podman push myapp:1.0.0 docker://registry.example.com/myapp:1.0.0
```

### Local Testing with Kube YAML

```bash
podman play kube deployment.yaml
```

---

## ImageStreams and Internal Registry

### Creating an ImageStream for External Images

```bash
oc import-image myapp:latest --from=registry.example.com/myapp:latest --confirm
```

### Periodic Re-Import

```bash
oc tag --scheduled registry.example.com/myapp:latest myapp:latest
```
Re-imports every 15 minutes cluster-wide.

### Local Lookup Policy

Required when using ImageStreams with Deployments (not DeploymentConfigs):
```bash
oc set image-lookup myapp
```
Sets `spec.lookupPolicy.local: true` on the ImageStream.

### Digest-Based References

For immutable production references:
```bash
oc import-image myapp@sha256:abc123... --confirm
```

### oc-mirror v2

GA in OCP 4.18. Mirrors release images, operator catalogs, and Helm charts for
disconnected environments. See `references/disconnected.md` for full details.

---

## Image Size Optimization

| Technique | Savings |
|-----------|---------|
| UBI Micro instead of UBI Standard | ~68 MB compressed |
| Multi-stage build (don't ship compilers) | 2-10x reduction |
| `--setopt=tsflags=nodocs` | 10-30% per package |
| `--setopt=install_weak_deps=0` | Variable |
| Combine RUN layers | Reduces layer overhead |
| `.dockerignore` for build context | Faster builds |
| Static binaries (Go/Rust) | Only binary + UBI Micro |

Red Hat's OpenJDK team achieved 361 MB -> 146 MB by switching to UBI Micro.

---

## FIPS-Compliant Images

FIPS must be enabled at OS install time on all cluster nodes -- cannot be enabled
post-install. Supported on OCP 4.7+.

### Container Image Requirements for FIPS

1. Build with RHEL's Go compiler (not upstream Go)
2. Set `CGO_ENABLED=1`
3. Do NOT use static linking flags
4. Do NOT use `-tags no_openssl`
5. Include RHEL OpenSSL in the container image

Go relies on OpenSSL to detect FIPS mode. Without it, Go uses its own crypto
which is not FIPS-validated.

### FIPS Validation Status

- FIPS 140-2 validations remain active through September 21, 2026
- RHEL 9.0/9.2 modules submitted for FIPS 140-3 validation (pending CMVP review)
- Validated modules: OpenSSL, kernel crypto API, NSS, GnuTLS, libgcrypt

### Gotchas

- HAProxy does NOT respect cluster FIPS settings (includes OpenSSL directly)
- Not all layered operators claim FIPS validation
- The `oc` CLI is not FIPS-validated in non-FIPS environments
- "Products are not FIPS validated, cryptographic components are"
