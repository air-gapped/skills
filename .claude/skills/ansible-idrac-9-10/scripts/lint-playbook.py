#!/usr/bin/env python3
"""Lint Ansible playbooks/roles for dellemc.openmanage iDRAC 9/10 breakage.

Checks every task in the given files or directories (*.yml, *.yaml):

  ERROR    module removed in collection 11.0.0
  ERROR    x_auth_token passed to a module whose arg-spec rejects it
  ERROR    x_auth_token together with idrac_user/idrac_password (mutually exclusive)
  ERROR    ansible.builtin.uri to Redfish with credentials but neither
           force_basic_auth nor an X-Auth-Token header (401s on Unadvertised)
  ERROR    idrac_os_deployment iso_image containing '/' (rejected on >= 10.0.1)
  IDRAC10  idrac_user password set without privilege/custom_privilege
  IDRAC10  attribute key renamed or deprecated on iDRAC 10 — read from the
           tables in references/idrac-10-deltas.md, so the data has one home

Exit status: 0 clean, 1 ERROR found (or any IDRAC10 finding with --idrac10),
2 usage error. Needs PyYAML (present wherever Ansible is installed).
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("lint-playbook: PyYAML missing — run with the Python that runs Ansible")

DELTAS = Path(__file__).resolve().parent.parent / "references" / "idrac-10-deltas.md"
NS = "dellemc.openmanage."

REMOVED_11 = {
    "idrac_network": "idrac_network_attributes",
    "idrac_syslog": "idrac_attributes",
    "idrac_timezone_ntp": "idrac_attributes",
    "dellemc_configure_idrac_eventing": "idrac_attributes",
    "dellemc_configure_idrac_services": "idrac_attributes",
    "dellemc_idrac_lc_attributes": "idrac_attributes",
    "dellemc_idrac_storage_volume": "idrac_storage_volume",
    "dellemc_system_lockdown_mode": "idrac_attributes",
}
# AnsibleModule(idrac_auth_params): no x_auth_token in the arg-spec.
REJECTS_TOKEN = {
    "idrac_bios",
    "idrac_firmware",
    "idrac_firmware_info",
    "idrac_system_info",
    "idrac_lifecycle_controller_jobs",
    "idrac_lifecycle_controller_job_status_info",
    "idrac_lifecycle_controller_logs",
    "idrac_lifecycle_controller_status_info",
    "idrac_bios_registry_info",
    "idrac_network_info",
    "idrac_network_attributes_info",
    "idrac_session_info",
}
URI = {"ansible.builtin.uri", "ansible.legacy.uri", "uri"}
ATTR_ARGS = {
    "idrac_attributes": "iDRAC",
    "system_attributes": "System",
    "lifecycle_controller_attributes": "LifecycleController",
}


class _AnyTagLoader(yaml.SafeLoader):
    """SafeLoader that turns !vault, !unsafe and other tags into plain values."""


def _any_tag(loader, _suffix, node):
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_scalar(node)


_AnyTagLoader.add_multi_constructor("!", _any_tag)


def load_deltas(path: Path) -> tuple[dict[str, str], set[str], set[str]]:
    """Return (renames old->new, deprecated attrs, deprecated groups) from the deltas file."""
    renames: dict[str, str] = {}
    attrs: set[str] = set()
    groups: set[str] = set()
    section = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line
            continue
        ticks = re.findall(r"`([^`]+)`", line)
        if "Reorganized" in section and line.startswith("| `") and len(ticks) >= 2:
            cells = [c for c in line.strip().strip("|").split("|")]
            if len(cells) < 2:
                continue
            old = re.findall(r"`([^`]+)`", cells[0])
            new = re.findall(r"`([^`]+)`", cells[1])
            for o, n in zip(_expand(old), _expand(new)):
                renames[o] = n
        elif "Deprecated groups" in section and line.startswith("- `") and ticks:
            tok = ticks[0].rstrip(".*")
            if tok.count(".") == 1:
                groups.add(tok)
            elif tok.count(".") == 2:
                attrs.add(tok)
    return renames, attrs, groups


def _expand(tokens: list[str]) -> list[str]:
    """`iDRAC.IPv4Static.DNS1` / `.DNS2` -> full names for each token."""
    out: list[str] = []
    for t in tokens:
        if t.startswith(".") and out:
            out.append(out[0].rsplit(".", 1)[0] + t)
        else:
            out.append(t)
    return out


def _fqdd(prefix: str, key: str) -> str | None:
    parts = str(key).split(".")
    if len(parts) == 3:
        return f"{prefix}.{parts[0]}.{parts[2]}"
    if len(parts) == 2:
        return f"{prefix}.{parts[0]}.{parts[1]}"
    return None


def check_task(task: dict, where: str, deltas, out: list[tuple[str, str]]) -> None:
    renames, dep_attrs, dep_groups = deltas
    name = task.get("name", "<unnamed>")
    tag = f"{where}: task '{name}'"
    for key, args in task.items():
        mod = key[len(NS) :] if str(key).startswith(NS) else str(key)
        if mod in REMOVED_11:
            out.append(
                (
                    "ERROR",
                    f"{tag}: {mod} was removed in collection 11.0.0 — use {REMOVED_11[mod]}",
                )
            )
        if not isinstance(args, dict):
            continue
        has_token = "x_auth_token" in args or "auth_token" in args
        has_creds = "idrac_user" in args or "idrac_password" in args
        if mod in REJECTS_TOKEN and has_token:
            out.append(
                (
                    "ERROR",
                    f"{tag}: {mod} rejects x_auth_token (Unsupported parameters) — pass idrac_user/idrac_password",
                )
            )
        elif (
            mod.startswith(("idrac_", "redfish_"))
            and mod != "idrac_session"
            and has_token
            and has_creds
        ):
            out.append(
                (
                    "ERROR",
                    f"{tag}: {mod} given x_auth_token AND idrac_user/idrac_password — mutually exclusive",
                )
            )
        if key in URI and "redfish" in str(args.get("url", "")):
            headers = args.get("headers") or {}
            token_hdr = isinstance(headers, dict) and any(
                str(h).lower() == "x-auth-token" for h in headers
            )
            creds = "url_username" in args or "url_password" in args
            fba = str(args.get("force_basic_auth", "")).lower() in ("true", "yes", "1")
            if creds and not fba and not token_hdr:
                out.append(
                    (
                        "ERROR",
                        f"{tag}: uri to Redfish with credentials but no force_basic_auth: true — 401 on BasicAuthState Unadvertised",
                    )
                )
        if mod == "idrac_os_deployment" and "/" in str(args.get("iso_image", "")):
            out.append(
                (
                    "ERROR",
                    f"{tag}: iso_image contains '/' — directory goes in share_name, bare filename in iso_image",
                )
            )
        if (
            mod == "idrac_user"
            and "user_password" in args
            and not ({"privilege", "custom_privilege"} & args.keys())
        ):
            out.append(
                (
                    "IDRAC10",
                    f"{tag}: idrac_user sets a password without privilege — iDRAC 10 demotes the user to ReadOnly",
                )
            )
        for arg, prefix in ATTR_ARGS.items():
            if mod == "idrac_attributes" and isinstance(args.get(arg), dict):
                for k in args[arg]:
                    _check_attr(
                        _fqdd(prefix, k), k, tag, renames, dep_attrs, dep_groups, out
                    )
        if mod == "idrac_bios" and isinstance(args.get("attributes"), dict):
            for k in args["attributes"]:
                moved = renames.get(f"BIOS.SysSecurity.{k}")
                if moved:
                    out.append(
                        (
                            "IDRAC10",
                            f"{tag}: BIOS attribute {k} moved to {moved} on iDRAC 10 — set it via idrac_attributes system_attributes",
                        )
                    )


def _check_attr(fq, key, tag, renames, dep_attrs, dep_groups, out) -> None:
    if not fq:
        return
    if fq in renames:
        out.append(
            (
                "IDRAC10",
                f"{tag}: {key} ({fq}) is {renames[fq]} on iDRAC 10 — silently ignored under the old name",
            )
        )
    elif fq in dep_attrs or fq.rsplit(".", 1)[0] in dep_groups:
        out.append(
            (
                "IDRAC10",
                f"{tag}: {key} ({fq}) does not exist on iDRAC 10 — silently ignored",
            )
        )


def walk(node, where: str, deltas, out) -> None:
    if isinstance(node, dict):
        check_task(node, where, deltas, out)
        for v in node.values():
            walk(v, where, deltas, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, where, deltas, out)


def lint(paths: list[Path], deltas) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    files: list[Path] = []
    for p in paths:
        files += sorted(p.rglob("*.y*ml")) if p.is_dir() else [p]
    for f in files:
        try:
            docs = list(
                yaml.load_all(f.read_text(encoding="utf-8"), Loader=_AnyTagLoader)
            )
        except yaml.YAMLError as e:
            out.append(
                ("ERROR", f"{f}: does not parse as YAML ({e.__class__.__name__})")
            )
            continue
        for d in docs:
            walk(d, str(f), deltas, out)
    return out


SELFCHECK = """
- hosts: idracs
  tasks:
    - name: bios over token
      dellemc.openmanage.idrac_bios:
        idrac_ip: x
        x_auth_token: t
        attributes: {AcPwrRcvry: "On"}
    - name: old net
      dellemc.openmanage.idrac_network:
        idrac_ip: x
    - name: attrs
      dellemc.openmanage.idrac_attributes:
        idrac_ip: x
        x_auth_token: t
        idrac_attributes: {"IPv4Static.1.Address": 1.2.3.4, "SNMP.1.AgentEnable": Enabled, "ACME.1.CA-URL": u}
    - name: raw
      ansible.builtin.uri: {url: "https://x/redfish/v1", url_username: u, url_password: p}
    - name: ok raw
      ansible.builtin.uri: {url: "https://x/redfish/v1", url_username: u, url_password: p, force_basic_auth: true}
    - name: secret
      dellemc.openmanage.idrac_user: {idrac_ip: x, idrac_user: u, idrac_password: !vault p, user_name: root, user_password: n}
"""


def selfcheck(deltas) -> int:
    renames, attrs, groups = deltas
    assert renames.get("iDRAC.IPv4Static.Address") == "iDRAC.IPv4.StaticAddress", (
        "rename table not parsed"
    )
    assert renames.get("iDRAC.IPv4Static.DNS2") == "iDRAC.IPv4.StaticDNS2", (
        "compound rename row not expanded"
    )
    assert "iDRAC.ACME" in groups and "iDRAC.Redfish.Enable" in attrs, (
        "deprecation list not parsed"
    )
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "play.yml"
        f.write_text(SELFCHECK, encoding="utf-8")
        got = lint([f], deltas)
    msgs = " ".join(m for _, m in got)
    expect = [
        "idrac_bios rejects x_auth_token",
        "AcPwrRcvry moved to System.ServerPwr.AcPwrRcvry",
        "idrac_network was removed",
        "is iDRAC.IPv4.StaticAddress",
        "ACME.1.CA-URL (iDRAC.ACME.CA-URL) is iDRAC.ACE.CA-URL",
        "task 'raw': uri to Redfish",
        "without privilege",
    ]
    missing = [e for e in expect if e not in msgs]
    extra = [m for _, m in got if "ok raw" in m or "SNMP" in m]
    if missing or extra or len(got) != len(expect):
        print(
            f"selfcheck FAILED\nmissing: {missing}\nunexpected: {extra}\ngot {len(got)}:",
            *got,
            sep="\n",
        )
        return 1
    print(
        f"selfcheck ok: {len(renames)} renames, {len(attrs)} deprecated attrs, {len(groups)} deprecated groups parsed; {len(got)} findings as expected"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "paths", nargs="*", type=Path, help="playbook/role files or directories"
    )
    ap.add_argument(
        "--idrac10",
        action="store_true",
        help="treat IDRAC10 findings as failures (play targets iDRAC 10)",
    )
    ap.add_argument(
        "--selfcheck",
        action="store_true",
        help="verify table parsing and every check on a fixture",
    )
    a = ap.parse_args()
    deltas = load_deltas(DELTAS)
    if a.selfcheck:
        return selfcheck(deltas)
    if not a.paths:
        ap.error("give at least one path, or --selfcheck")
    out = lint(a.paths, deltas)
    for level, msg in out:
        print(f"{level:8} {msg}")
    print(
        f"{sum(1 for lv, _ in out if lv == 'ERROR')} ERROR, {sum(1 for lv, _ in out if lv == 'IDRAC10')} IDRAC10"
    )
    fail = any(lv == "ERROR" or (a.idrac10 and lv == "IDRAC10") for lv, _ in out)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
