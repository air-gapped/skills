#!/usr/bin/env bash
#
# Inspect a vllm/vllm-openai Docker Hub image to verify CUDA version and whether
# LMCache / NIXL / Mooncake were baked in at build time via INSTALL_KV_CONNECTORS.
#
# Pulls only the manifest + config blob (a few kilobytes). Does NOT pull layers,
# so this is safe to run against multi-GB images.
#
# Usage: inspect-vllm-image.sh <tag> [<arch>]
#   tag:  any tag on docker.io/vllm/vllm-openai, e.g. v0.19.0-cu130, glm51-cu130
#   arch: amd64 (default) or arm64
#
# Exits 0 on success, prints a human-readable report.

set -euo pipefail

TAG="${1:?tag is required, e.g. v0.19.0-cu130}"
ARCH="${2:-amd64}"
REPO="vllm/vllm-openai"

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
for m in d.get('manifests',[]):
    if m['platform']['architecture']==arch:
        print(m['digest']); break")

if [[ -z "$DIGEST" ]]; then
  echo "error: no ${ARCH} manifest found for ${REPO}:${TAG}" >&2
  exit 1
fi

MANIFEST=$(curl -sf -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
  "https://registry-1.docker.io/v2/${REPO}/manifests/${DIGEST}")

CFG_DIGEST=$(echo "$MANIFEST" \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['config']['digest'])")

curl -sfL -H "Authorization: Bearer $TOKEN" \
  "https://registry-1.docker.io/v2/${REPO}/blobs/${CFG_DIGEST}" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
envs = {e.split('=',1)[0]: e.split('=',1)[1] for e in d['config'].get('Env',[]) if '=' in e}
print(f\"image:      ${REPO}:${TAG} (${ARCH})\")
print(f\"CUDA:       {envs.get('CUDA_VERSION', 'unknown')}\")
print(f\"entrypoint: {d['config'].get('Entrypoint')}\")
kv_seen = False
kv_true = False
for h in d.get('history', []):
    cb = h.get('created_by', '')
    if 'kv_connectors.txt' in cb and 'INSTALL_KV_CONNECTORS' in cb:
        kv_seen = True
        if 'INSTALL_KV_CONNECTORS=true' in cb:
            kv_true = True
if kv_true:
    print('LMCache/NIXL/Mooncake: YES (built with INSTALL_KV_CONNECTORS=true)')
elif kv_seen:
    print('LMCache/NIXL/Mooncake: NO (INSTALL_KV_CONNECTORS=false at build)')
else:
    print('LMCache/NIXL/Mooncake: UNKNOWN (pre-bundling era or custom build)')
"
