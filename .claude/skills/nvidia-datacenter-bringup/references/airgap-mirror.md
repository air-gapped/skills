# Air-gap mirror setup

How to stand up the two apt mirrors a B300 host needs (NVIDIA CUDA repo + DOCA repo), the GPG-key three-tier story, and the `apt file://` sneakernet path that works as a stopgap before a proper internal mirror exists.

## Mirror inventory

| Repo | URL | Approx size | Mirror filter |
|---|---|---|---|
| NVIDIA CUDA | `https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/` (`ubuntu2404` no dot) | Full ≈ several GB; driver+FM+NVLSM+toolkit filtered subset ≈ 1.5–2 GB | Allowlist `nvidia-open*`, `nvidia-driver-pinning-*`, `nvidia-driver-*-open`, `nvlink5-*`, `nvlsm*`, `libnvsdm*`, `nvidia-fabricmanager-*`, `cuda-drivers-fabricmanager-*`, `libnvidia-nscq-*`, `libnvidia-compute-*`, `libnvidia-cfg1-*`, `nvidia-dkms*`, `nvidia-kernel-*`, `nvidia-utils-*`, `nvidia-modprobe`, `nvidia-persistenced`, `cuda-keyring`, `nvidia-container-toolkit*`, `libnvidia-container*`, `datacenter-gpu-manager-4-*` |
| DOCA | `https://linux.mellanox.com/public/repo/doca/latest-3.2-LTS/ubuntu24.04/x86_64/` (`ubuntu24.04` WITH dot) | Flat repo, ~600–700 MB, 227 .debs | Full mirror is fine — small enough |
| Ubuntu archive | Usually already mirrored fleet-wide via Landscape or local mirror | — | Subset needed: kernel-headers, libibumad3 (also in DOCA repo), infiniband-diags, build-essential, dkms |

**`nvidia-container-toolkit` lives in the NVIDIA CUDA repo** — verified 2026-05-21 (`apt-cache policy nvidia-container-toolkit` shows `developer.download.nvidia.com` as the source). No need for the separate `nvidia.github.io/libnvidia-container/stable/deb/` repo. One less mirror to maintain.

## Path-string trap

This catches everyone:

- DOCA: `linux.mellanox.com/public/repo/doca/latest-3.2-LTS/ubuntu24.04/x86_64/` — **with the dot**
- CUDA: `developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/` — **no dot**

Verified live: `ubuntu2404` returns 404 on the DOCA host; `ubuntu24.04` returns 404 on the CUDA host.

## GPG key three-tier layout (DOCA)

```
public/repo/doca/
├── GPG-KEY-Mellanox.pub                    ← Tier 1: umbrella key (4.4 KB, 2024-04-16)
├── public_keys/                            ← Tier 2: current split keys (2026-02-24)
│   ├── nvidia-doca-debian-gpg-public-key.gpg   (1.2 KB, for apt)
│   └── nvidia-doca-rpm-gpg-public-key.asc      (1.6 KB, for dnf/yum)
└── latest-3.2-LTS/ubuntu24.04/x86_64/
    ├── GPG-KEY-Mellanox.pub                ← Tier 3: per-repo copy (~1.7 KB, subset of Tier 1)
    ├── Release, Release.gpg, Packages.gz
    └── *.deb
```

NVIDIA is mid-rotation. Belt-and-braces keyring concatenates Tier 1 and Tier 2 into one file so apt accepts packages signed by either:

```bash
sudo install -d -m 0755 /etc/apt/keyrings
{
  curl -fsSL https://linux.mellanox.com/public/repo/doca/public_keys/nvidia-doca-debian-gpg-public-key.gpg
  curl -fsSL https://linux.mellanox.com/public/repo/doca/GPG-KEY-Mellanox.pub | gpg --dearmor
} | sudo tee /etc/apt/keyrings/nvidia-doca.gpg >/dev/null
sudo chmod 0644 /etc/apt/keyrings/nvidia-doca.gpg

# Verify
gpg --no-default-keyring --keyring /etc/apt/keyrings/nvidia-doca.gpg --list-keys
```

## GPG key (CUDA repo)

Single key. The `cuda-keyring_1.1-1_all.deb` package installs both the key file and the apt source-list entry in one step. Use this rather than fetching the raw `.pub` and editing source-lists by hand.

```bash
curl -fsSL -O https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
```

After install:
- `/usr/share/keyrings/cuda-archive-keyring.gpg` — key
- `/etc/apt/sources.list.d/cuda-ubuntu2404-x86_64.list` — source-list entry

Last key rotation was April 2022. No rotation since.

## Mirror with `wget -r`

For the DOCA repo (flat repo — easiest):

```bash
mkdir -p /srv/nvidia-mirror && cd /srv/nvidia-mirror
wget -e robots=off -r -np -nH --cut-dirs=3 -R "index.html*" \
  https://linux.mellanox.com/public/repo/doca/latest-3.2-LTS/ubuntu24.04/x86_64/

# Result: /srv/nvidia-mirror/latest-3.2-LTS/ubuntu24.04/x86_64/{*.deb,Packages,Packages.gz,Release,Release.gpg}
```

The `--cut-dirs=3` strips `public/repo/doca/` so the local layout matches the URL.

For the CUDA repo, full mirror is several GB. Use Pulp's `deb_remote` with an `includes` filter, or `apt-mirror` with a custom mirror.list that limits to the allowlist (see the table above). For a quick-and-dirty sneakernet bring-up, full-mirror with `wget -r` is fine — disk is cheap.

## `apt` with `file://` (sneakernet)

Works because both DOCA and CUDA repos already ship `Packages`/`Packages.gz`/`Release`/`Release.gpg`. No metadata regeneration needed.

```bash
# Copy the mirror tree to the air-gapped box (USB / sneakernet)
rsync -a /srv/nvidia-mirror/ root@b300-host:/srv/nvidia-mirror/

# On the B300, set up the apt sources
sudo tee /etc/apt/sources.list.d/nvidia-doca-local.sources <<'EOF'
Types: deb
URIs: file:///srv/nvidia-mirror/latest-3.2-LTS/ubuntu24.04/x86_64
Suites: ./
Signed-By: /etc/apt/keyrings/nvidia-doca.gpg
EOF

sudo tee /etc/apt/sources.list.d/nvidia-cuda-local.sources <<'EOF'
Types: deb
URIs: file:///srv/nvidia-mirror/cuda/ubuntu2404/x86_64
Suites: ./
Signed-By: /usr/share/keyrings/cuda-archive-keyring.gpg
EOF

sudo apt update
# Output should list both file:// repos hitting their local Release files
```

Notes:
- `Suites: ./` + trailing-slash `URIs:` is the deb822 syntax for a **flat repository** (no `dists/<suite>/` hierarchy). Both DOCA and CUDA repos are flat.
- The legacy one-liner equivalent works too: `deb [signed-by=/etc/apt/keyrings/X.gpg] file:///srv/.../  ./`
- Permissions: world-readable (`chmod -R a+rX /srv/nvidia-mirror`). apt runs as `_apt` user and won't traverse symlinks across overlay mounts.
- Don't symlink across the network/USB mount — copy to local disk first.

## Long-term: internal HTTP mirror

After sneakernet works for the first bring-up, set up a proper internal mirror. Options:

### nginx static (simplest)

```dockerfile
FROM nginx:alpine
COPY nvidia-mirror /usr/share/nginx/html/nvidia-mirror
```

Then on the B300:
```
URIs: http://internal-mirror.lan/nvidia-mirror/cuda/ubuntu2404/x86_64
```

Works because both repos already have signed metadata. No metadata regen, no Pulp, no Artifactory. Just static file serving.

### Pulp `deb_remote`

Better for allowlist filtering (trim CUDA toolkit out of the mirror). Pulp's `deb_remote` supports `includes` and `excludes` package-name globs. Mirror sync becomes:

```
pulp deb remote create --name nvidia-cuda \
  --url https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/ \
  --distributions / \
  --includes "nvidia-open*,nvidia-driver-pinning-*,nvidia-driver-*-open,nvlink5-*,nvlsm*,libnvsdm*,nvidia-fabricmanager-*,cuda-drivers-fabricmanager-*,libnvidia-nscq-*,nvidia-dkms*,nvidia-kernel-*,nvidia-utils-*,nvidia-modprobe,nvidia-persistenced,cuda-keyring,nvidia-container-toolkit*,libnvidia-container*,datacenter-gpu-manager-4-*"
pulp deb repository sync --name nvidia-cuda --remote nvidia-cuda
```

### Artifactory / Nexus

Both support apt remote-mirror with allowlist filtering and immutable snapshots. Choose based on existing enterprise infra.

## Snapshot pinning

The DOCA repo URL `latest-3.2-LTS/` is a symlink that follows the LTS line. For reproducible installs, mirror to a version-specific path:

```
/srv/nvidia-mirror/doca/3.2.2/ubuntu24.04/x86_64/   ← snapshot taken 2026-04-15
/srv/nvidia-mirror/doca/3.2.3/ubuntu24.04/x86_64/   ← snapshot taken 2026-06-01
```

Bring-up scripts pin to `3.2.2` (or whatever). The LTS line still gets refreshed on a cadence, but installed hosts don't change underfoot.

For CUDA repo, the directory is monolithic (no per-version subdir), but snapshot by date — `cuda-2026-05-21/` — and pin source-lists to that.

## Update cadence and monitoring

| Repo | Cadence | Source |
|---|---|---|
| DOCA LTS minor | 1–3 months (3.2.0 Oct 2025 → 3.2.1 Nov 2025 → 3.2.2 Feb 2026) | https://developer.nvidia.com/doca-archive |
| NVIDIA driver branch | ~6 months production branch, ~3 months new branch | https://docs.nvidia.com/datacenter/tesla/drivers/index.html |
| nvidia-container-toolkit | ~monthly | https://github.com/NVIDIA/nvidia-container-toolkit/releases |
| gpu-operator | ~quarterly minor, monthly patch | https://github.com/NVIDIA/gpu-operator/releases |
| CUDA repo key | Last rotation April 2022, stable | https://developer.nvidia.com/blog/updating-the-cuda-linux-gpg-repository-key/ |
| DOCA umbrella key | 2024-04-16, stable | inside `public/repo/doca/` |
| DOCA split keys | 2026-02-24, recent rotation | `public/repo/doca/public_keys/` |

Set up Renovate (or equivalent) against an internal manifest listing pinned versions; trigger fresh mirror syncs on upstream releases.

## MLNX_OFED is dead — don't mirror it

Last standalone MLNX_OFED October 2024; security-only until October 2027. CX-8 support is **only** in DOCA-OFED. Do not mirror MLNX_OFED for new B300 builds.

Reference: https://docs.nvidia.com/doca/sdk/MLNX_OFED-to-DOCA-OFED-Transition-Guide/index.html
