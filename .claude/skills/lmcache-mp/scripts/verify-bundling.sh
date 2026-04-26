#!/usr/bin/env bash
#
# Verify that LMCache + NIXL + Mooncake are not just *installed* but actually
# *importable* at runtime inside a vllm-openai container, and that all three
# KV-offload connector classes load cleanly.
#
# This is the runtime check that the build-flag inspection (inspect-vllm-image.sh
# in the vllm-caching skill) cannot make. Build flag = "we tried to install it",
# this script = "the package actually imports". Different things — the torch-
# conflict era of 2025 had cases where the build flag said yes but runtime
# failed.
#
# Usage:
#   verify-bundling.sh <image-tag>          # default repo: vllm/vllm-openai
#   verify-bundling.sh <full-image-ref>     # if it contains a /, used verbatim
#
# Examples:
#   verify-bundling.sh v0.19.1
#   verify-bundling.sh v0.20.0-cu130
#   verify-bundling.sh lmcache/vllm-openai:latest-nightly
#
# Prints a tabular report. Exits 0 if all critical imports pass, 1 otherwise.

set -euo pipefail

REF="${1:?usage: verify-bundling.sh <tag|full-image-ref>}"
if [[ "$REF" == */* ]]; then
  IMAGE="$REF"
else
  IMAGE="vllm/vllm-openai:$REF"
fi

CONTAINER="lmcache-verify-$$"

echo ">>> verifying $IMAGE"
echo ">>> pulling (skipped if already cached) ..."
docker pull "$IMAGE" >/dev/null

echo ">>> starting sleep-overridden container ..."
docker run -d --rm --name "$CONTAINER" --entrypoint sleep "$IMAGE" 600 >/dev/null

cleanup() { docker stop "$CONTAINER" >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo ">>> running runtime import test ..."
# Use heredoc to avoid quote-nesting issues with python's single quotes
docker exec -i "$CONTAINER" python3 <<'PYEOF'
import sys, importlib.metadata as md, shutil
exit_code = 0

print("python:", sys.version.split()[0])
print()
print("--- pip metadata ---")
for pkg in ["vllm", "lmcache", "nixl", "mooncake-transfer-engine"]:
    try:
        print(f"{pkg:30s} {md.version(pkg)}")
    except md.PackageNotFoundError:
        print(f"{pkg:30s} NOT INSTALLED")
        if pkg in ("vllm", "lmcache", "nixl"):
            exit_code = 1

print()
print("--- runtime import (real proof) ---")
# NB: mooncake imports as "mooncake", not "mooncake_transfer_engine"
for label, mod in [("lmcache", "lmcache"), ("nixl", "nixl"), ("mooncake", "mooncake")]:
    try:
        m = __import__(mod)
        loc = getattr(m, "__file__", "(no file)")
        print(f"import {label:15s} OK  {loc}")
    except Exception as e:
        print(f"import {label:15s} FAIL  {type(e).__name__}: {e}")
        if label in ("lmcache", "nixl"):
            exit_code = 1

print()
print("--- LMCache MP adapter classes (used by LMCacheMPConnector) ---")
try:
    from lmcache.integration.vllm.vllm_multi_process_adapter import (
        LMCacheMPSchedulerAdapter, LMCacheMPWorkerAdapter, LoadStoreOp,
    )
    print("LMCacheMPSchedulerAdapter, LMCacheMPWorkerAdapter, LoadStoreOp: OK")
except Exception as e:
    print(f"MP adapter classes FAIL  {type(e).__name__}: {e}")
    exit_code = 1
try:
    from lmcache.integration.vllm.vllm_multi_process_adapter import ParallelStrategy  # noqa: F401
    print("ParallelStrategy (vLLM main needs this): OK")
except Exception as e:
    print(f"ParallelStrategy NOT PRESENT  ({type(e).__name__}: {e})")
    print("  -> fine for vLLM v0.19.x / v0.20.x; FAIL if you intend to run vLLM main")

print()
print("--- LMCache server CLI ---")
print(f"lmcache  {shutil.which('lmcache') or 'NOT IN PATH'}")

print()
print("--- vLLM connector factory registrations ---")
from vllm.distributed.kv_transfer.kv_connector.factory import KVConnectorFactory
reg = sorted(KVConnectorFactory._registry.keys())
print("registered:", reg)
for must in ("OffloadingConnector", "LMCacheConnectorV1", "LMCacheMPConnector", "NixlConnector"):
    if must not in reg:
        print(f"  X MISSING {must}")
        exit_code = 1
    else:
        print(f"  OK {must}")

print()
print("--- connector class instantiation (catches bad imports) ---")
# NixlConnector path varies across vLLM versions (file vs package). Use the
# factory to look up classes — that's the path vLLM itself uses at runtime.
import importlib
for name in ("LMCacheMPConnector", "LMCacheConnectorV1", "OffloadingConnector", "NixlConnector"):
    if name not in KVConnectorFactory._registry:
        continue
    try:
        loader = KVConnectorFactory._registry[name]
        cls = loader()  # the loader is a thunk that imports + returns the class
        print(f"{name:25s} class load: OK ({cls.__module__}.{cls.__name__})")
    except Exception as e:
        print(f"{name:25s} class load FAIL  {type(e).__name__}: {e}")
        if name in ("LMCacheMPConnector", "LMCacheConnectorV1", "OffloadingConnector"):
            exit_code = 1

print()
print("=" * 60)
if exit_code == 0:
    print("RESULT: all critical KV-offload paths are bundled and loadable.")
else:
    print("RESULT: at least one critical path failed -- check output above.")
sys.exit(exit_code)
PYEOF
