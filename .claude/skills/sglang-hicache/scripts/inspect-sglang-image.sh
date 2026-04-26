#!/usr/bin/env bash
#
# Inspect an lmsysorg/sglang Docker Hub image to verify CUDA version and which
# HiCache L3 backends (mooncake-transfer-engine / nixl-cu* / aibrix-kvcache /
# lmcache) were baked in at build time.
#
# Pulls only the manifest + config blob (a few kilobytes). Does NOT pull layers,
# so this is safe to run against multi-GB images.
#
# Usage: inspect-sglang-image.sh <tag> [<arch>]
#   tag:  any tag on docker.io/lmsysorg/sglang, e.g. v0.5.10, v0.5.10.post1
#   arch: amd64 (default) or arm64
#
# Exits 0 on success, prints a human-readable report.

set -euo pipefail

TAG="${1:?tag is required, e.g. v0.5.10.post1}"
ARCH="${2:-amd64}"
REPO="lmsysorg/sglang"

TOKEN=$(curl -sf "https://auth.docker.io/token?service=registry.docker.io&scope=repository:${REPO}:pull" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")

MANIFEST_LIST=$(curl -sf -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
  -H "Accept: application/vnd.oci.image.index.v1+json" \
  "https://registry-1.docker.io/v2/${REPO}/manifests/${TAG}")

DIGEST=$(echo "$MANIFEST_LIST" \
  | ARCH="$ARCH" python3 -c "import json,sys,os
d=json.load(sys.stdin)
arch=os.environ['ARCH']
# Image may be a raw manifest (single-arch) or manifest list (multi-arch).
if 'manifests' in d:
    for m in d['manifests']:
        if m['platform']['architecture']==arch:
            print(m['digest']); break
else:
    # raw manifest, no platform list — assume the requested arch matches
    print('')
")

if [[ -z "$DIGEST" ]]; then
  # Single-arch image — fetch the manifest by tag directly
  MANIFEST="$MANIFEST_LIST"
else
  MANIFEST=$(curl -sf -H "Authorization: Bearer $TOKEN" \
    -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
    "https://registry-1.docker.io/v2/${REPO}/manifests/${DIGEST}")
fi

CFG_DIGEST=$(echo "$MANIFEST" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['config']['digest'])")

curl -sfL -H "Authorization: Bearer $TOKEN" \
  "https://registry-1.docker.io/v2/${REPO}/blobs/${CFG_DIGEST}" \
  | python3 -c "
import json, sys, re
d = json.load(sys.stdin)
envs = {e.split('=',1)[0]: e.split('=',1)[1] for e in d['config'].get('Env',[]) if '=' in e}
print(f\"image:      ${REPO}:${TAG} (${ARCH})\")
print(f\"CUDA:       {envs.get('CUDA_VERSION', envs.get('NV_CUDA_LIB_VERSION', 'unknown'))}\")
print(f\"PYTHON:     {envs.get('PYTHON_VERSION', 'unknown')}\")
print(f\"entrypoint: {d['config'].get('Entrypoint')}\")
print()
print('HiCache L3-backend libs (from build history):')
backends = {
    'mooncake-transfer-engine': None,
    'nixl-cu12':                None,
    'nixl-cu13':                None,
    'aibrix-kvcache':           None,
    'lmcache':                  None,
}
for h in d.get('history', []):
    cb = h.get('created_by', '')
    for pkg in list(backends):
        # match e.g.   pip install ... mooncake-transfer-engine==0.3.10.post1
        m = re.search(rf'{re.escape(pkg)}([=<>!~]+[A-Za-z0-9._-]+)?', cb)
        if m and backends[pkg] is None:
            backends[pkg] = m.group(0)
for pkg, val in backends.items():
    status = val or 'NOT BUNDLED'
    print(f'  {pkg:30s} {status}')
print()
print('Other notable HiCache deps (best effort):')
for keyword in ('sgl-kernel', 'flashinfer', 'torch'):
    for h in d.get('history', []):
        cb = h.get('created_by', '')
        m = re.search(rf'{re.escape(keyword)}([=<>!~]+[A-Za-z0-9._-]+)?', cb)
        if m:
            print(f'  {keyword:30s} {m.group(0)}')
            break
"
