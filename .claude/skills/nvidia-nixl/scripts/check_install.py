#!/usr/bin/env python3
"""
NIXL install + environment sanity check.

Run this inside a NIXL-using container or host before debugging deeper issues.
It validates the most common failure modes from `references/gotchas.md` top-10:

  1. nixl wheel imports + NIXL_PLUGIN_DIR resolves
  2. CUDA wheel matches host CUDA (cu12 vs cu13 mismatch)
  3. agent.getAvailPlugins() lists expected backends
  4. UCX_TLS includes cuda_copy when CUDA tensors will flow
  5. NIXL_ETCD_ENDPOINTS reachable (if set)
  6. cufile.json present + allow_compat_mode (if GDS plugin loaded)

Exit codes: 0 = all checks passed, 1 = at least one failure.

Usage:
  python check_install.py
  python check_install.py --json           # machine-readable output
  python check_install.py --backends UCX,LIBFABRIC,GDS
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str, fix: str = "") -> None:
    CHECKS.append({"name": name, "ok": ok, "detail": detail, "fix": fix})


def check_nixl_import() -> tuple[bool, object]:
    try:
        import nixl
        import nixl._bindings as b

        check(
            "nixl import",
            True,
            f"nixl version: {getattr(nixl, '__version__', 'unknown')}",
        )
        return True, b
    except ImportError as e:
        check(
            "nixl import",
            False,
            f"ImportError: {e}",
            "pip install nixl  (auto-selects nixl-cu12 / nixl-cu13). "
            "If LD error mentions libcudart.so.12 vs .so.13, host CUDA "
            "and wheel CUDA disagree.",
        )
        return False, None


def check_cuda_wheel_match() -> None:
    try:
        import torch
    except ImportError:
        check("CUDA wheel match", True, "torch not installed; skipping match check")
        return
    torch_cuda = (torch.version.cuda or "").split(".")[0]
    cu12 = (
        shutil.which("python")
        and subprocess.run(
            [sys.executable, "-c", "import nixl_cu12"], capture_output=True
        ).returncode
        == 0
    )
    cu13 = (
        subprocess.run(
            [sys.executable, "-c", "import nixl_cu13"], capture_output=True
        ).returncode
        == 0
    )
    if torch_cuda == "12":
        ok = cu12
    elif torch_cuda == "13":
        ok = cu13
    else:
        ok = cu12 or cu13
    detail = f"torch CUDA {torch_cuda}; nixl-cu12={cu12} nixl-cu13={cu13}"
    fix = (
        "pip install nixl  (the meta-wheel auto-selects). "
        "If on CUDA 13 host with only nixl-cu12 installed, "
        "uninstall nixl-cu12 and pip install nixl-cu13 explicitly."
    )
    check("CUDA wheel match", ok, detail, fix if not ok else "")


def check_plugin_dir() -> None:
    pdir = os.environ.get("NIXL_PLUGIN_DIR")
    if not pdir:
        check("NIXL_PLUGIN_DIR", True, "unset (wheel-managed default)")
        return
    p = Path(pdir)
    plugins = sorted(p.glob("libplugin_*.so")) if p.exists() else []
    check(
        "NIXL_PLUGIN_DIR",
        bool(plugins),
        f"{pdir}: {len(plugins)} plugin(s) ({', '.join(x.name for x in plugins[:5])}{'...' if len(plugins) > 5 else ''})",
        "ls $NIXL_PLUGIN_DIR/libplugin_*.so. If empty, the dir is wrong.",
    )


def check_avail_plugins(b, expected: list[str]) -> None:
    try:
        agent = b.nixlAgent("install-check", b.nixlAgentConfig())
        avail = agent.getAvailPlugins()
        missing = [e for e in expected if e not in avail]
        check(
            "available plugins",
            not missing,
            f"loaded: {avail}; expected: {expected}; missing: {missing}",
            f"Plugin {missing} not built or not in NIXL_PLUGIN_DIR. See references/plugins.md for build deps."
            if missing
            else "",
        )
    except Exception as e:
        check("available plugins", False, f"agent creation raised: {e}", "")


def check_ucx_tls() -> None:
    tls = os.environ.get("UCX_TLS", "")
    if not tls:
        check("UCX_TLS", True, "unset (UCX picks defaults)")
        return
    has_cuda = "cuda_copy" in tls or "cuda_ipc" in tls or "all" in tls
    if tls.strip() == "tcp":
        check(
            "UCX_TLS",
            False,
            f"UCX_TLS={tls!r} — tcp alone segfaults nixlUcxSharedThread::run() on CUDA buffers",
            "Set UCX_TLS=cuda_copy,sm,tcp (single-node) or cuda_copy,cuda_ipc,sm,tcp,rc (cross-node IB).",
        )
    elif not has_cuda:
        check(
            "UCX_TLS",
            False,
            f"UCX_TLS={tls!r} — missing CUDA memtype",
            "Add cuda_copy (and cuda_ipc on H100/H200+NVLink). e.g. UCX_TLS=cuda_copy,sm,tcp",
        )
    else:
        check("UCX_TLS", True, f"{tls} (CUDA memtype enabled)")


def check_etcd() -> None:
    eps = os.environ.get("NIXL_ETCD_ENDPOINTS")
    if not eps:
        check("NIXL_ETCD_ENDPOINTS", True, "unset (side-channel mode)")
        return
    first = eps.split(",")[0].strip()
    try:
        import urllib.request

        urllib.request.urlopen(f"{first.rstrip('/')}/v2/keys/", timeout=3).read(64)
        check("NIXL_ETCD_ENDPOINTS", True, f"{first} reachable")
    except Exception as e:
        check(
            "NIXL_ETCD_ENDPOINTS",
            False,
            f"{first} unreachable: {type(e).__name__}: {e}",
            "Verify ETCD service is up + NetworkPolicy allows pod→ETCD on 2379.",
        )


def check_cufile() -> None:
    path = os.environ.get("CUFILE_ENV_PATH_JSON")
    if not path:
        check("cufile.json", True, "unset (only relevant if GDS plugin loaded)")
        return
    p = Path(path)
    if not p.exists():
        check(
            "cufile.json",
            False,
            f"{path} does not exist",
            "export CUFILE_ENV_PATH_JSON to a real path with allow_compat_mode=true.",
        )
        return
    try:
        cfg = json.loads(p.read_text())
        compat = cfg.get("properties", {}).get("allow_compat_mode")
        check(
            "cufile.json",
            compat is True,
            f"{path}: properties.allow_compat_mode={compat}",
            "Set properties.allow_compat_mode: true unless you have full GDS support."
            if compat is not True
            else "",
        )
    except Exception as e:
        check("cufile.json", False, f"{path}: parse error: {e}", "")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    ap.add_argument(
        "--backends",
        default="UCX",
        help="comma-separated backends to require (default: UCX)",
    )
    args = ap.parse_args()

    expected = [b.strip() for b in args.backends.split(",") if b.strip()]

    ok, bindings = check_nixl_import()
    check_cuda_wheel_match()
    check_plugin_dir()
    if ok and bindings is not None:
        check_avail_plugins(bindings, expected)
    check_ucx_tls()
    check_etcd()
    check_cufile()

    if args.json:
        print(json.dumps({"checks": CHECKS}, indent=2))
    else:
        for c in CHECKS:
            mark = "OK  " if c["ok"] else "FAIL"
            print(f"[{mark}] {c['name']}: {c['detail']}")
            if not c["ok"] and c["fix"]:
                print(f"       fix: {c['fix']}")

    return 0 if all(c["ok"] for c in CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
