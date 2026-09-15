#!/usr/bin/env python3
"""Flag Argo CD exposure to the two ServerSideDiff Secret-leak advisories.

Two independent checks, because the annotation alone does not decide it:

  CVE-2026-42880 (critical) needs `IncludeMutationWebhook=true` in a
  `argocd.argoproj.io/compare-options` annotation. Removing it closes this one.

  CVE-2026-45737 needs NO annotation — it fires on `argocd app diff
  --server-side-diff` for any Secret previously written by client-side apply,
  whose `kubectl.kubernetes.io/last-applied-configuration` still carries the
  plaintext. Only the version closes this one.

So a manifest scan that comes back clean proves nothing about the second, and a
version at or below 3.4.1 / 3.3.9 / 3.2.11 is exposed regardless of manifests.
Pass --version to check both.

Manifests are scanned as TEXT, not parsed as YAML, deliberately: the annotation
must be caught inside Helm templates, kustomize patches and ApplicationSet
`template:` blocks, none of which parse as standalone YAML.

Exit status: 0 clean, 1 exposure found, 2 usage error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Per-minor floors. CVE-2026-42880 was fixed at 3.3.9 / 3.2.11, but
# CVE-2026-45737 lists 3.2.0-3.2.11, 3.3.9 and 3.4.1 as affected, so the real
# floors are one patch higher. Verified 2026-09-15 against the advisories and
# the "apply HideSecretData to server-side diff results" commit in each release.
# minor -> (floor for CVE-2026-45737, floor for CVE-2026-42880 or None if the
# line shipped already carrying that fix).
FLOORS = {
    (3, 2): ((3, 2, 12), (3, 2, 11)),
    (3, 3): ((3, 3, 10), (3, 3, 9)),
    (3, 4): ((3, 4, 2), None),  # 3.4 was patched for -42880 before v3.4.1 shipped
}
# 3.5 shipped after both fixes; nothing on that line or later is affected.
FIRST_CLEAN_MINOR = (3, 5)

ANNOTATION = re.compile(r"IncludeMutationWebhook\s*=\s*true", re.I)
VERSION = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")
SUFFIXES = {".yaml", ".yml"}


def parse_version(raw: str) -> tuple[int, int, int]:
    m = VERSION.match(raw.strip())
    if not m:
        raise ValueError(f"not a version: {raw!r}")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def version_exposed(v: tuple[int, int, int]) -> str | None:
    """Return a message if this version is exposed, else None."""
    minor = (v[0], v[1])
    if minor >= FIRST_CLEAN_MINOR:
        return None
    entry = FLOORS.get(minor)
    if entry is None:
        # Older than the tracked lines (<= 3.1) — those are EOL and never got
        # the fix. Saying "unknown" here would read as "probably fine".
        if minor < (3, 2):
            return (
                f"v{v[0]}.{v[1]}.{v[2]} predates the patched lines and is EOL upstream "
                f"— exposed, and no patch exists for it. Move to a supported minor."
            )
        return f"v{v[0]}.{v[1]}.{v[2]}: no floor recorded for the {minor[0]}.{minor[1]} line — re-derive before trusting."
    floor, crit_floor = entry
    if v >= floor:
        return None
    msg = (
        f"v{v[0]}.{v[1]}.{v[2]} is below the {minor[0]}.{minor[1]} floor "
        f"v{floor[0]}.{floor[1]}.{floor[2]} — exposed to CVE-2026-45737"
    )
    if crit_floor is not None and v < crit_floor:
        msg += (
            f", and below v{crit_floor[0]}.{crit_floor[1]}.{crit_floor[2]} "
            f"it is also inside CVE-2026-42880 (CRITICAL)"
        )
    return msg + "."


def scan(paths: list[Path]) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    for root in paths:
        files = (
            [root]
            if root.is_file()
            else [p for p in root.rglob("*") if p.suffix.lower() in SUFFIXES]
        )
        for f in sorted(files):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                print(f"warning: cannot read {f}: {e}", file=sys.stderr)
                continue
            for n, line in enumerate(text.splitlines(), 1):
                if ANNOTATION.search(line):
                    hits.append((f, n, line.strip()))
    return hits


def selfcheck() -> int:
    assert version_exposed((3, 4, 1)) is not None, "3.4.1 is affected"
    assert version_exposed((3, 4, 2)) is None, "3.4.2 is the 3.4 floor"
    assert version_exposed((3, 3, 9)) is not None, "3.3.9 is affected by the follow-up"
    assert version_exposed((3, 3, 10)) is None, "3.3.10 is the 3.3 floor"
    assert version_exposed((3, 2, 11)) is not None, "3.2.11 is affected"
    assert version_exposed((3, 2, 12)) is None, "3.2.12 is the 3.2 floor"
    assert version_exposed((3, 5, 0)) is None, "3.5 postdates both fixes"
    assert version_exposed((3, 1, 16)) is not None, "3.1 is EOL and unpatched"
    # 3.4.1 is inside the follow-up only: the 3.4 line shipped with -42880 fixed.
    assert "42880" not in (version_exposed((3, 4, 1)) or ""), "no -42880 claim on 3.4"
    assert "42880" in (version_exposed((3, 3, 8)) or ""), "3.3.8 is inside -42880"
    assert "42880" not in (version_exposed((3, 3, 9)) or ""), "3.3.9 cleared -42880"
    assert parse_version("v3.4.2") == (3, 4, 2)
    assert parse_version("3.4.2+abc") == (3, 4, 2)
    assert ANNOTATION.search(
        "argocd.argoproj.io/compare-options: IncludeMutationWebhook=true"
    )
    assert ANNOTATION.search("IncludeMutationWebhook = True")
    assert not ANNOTATION.search("IncludeMutationWebhook=false")
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("paths", nargs="*", type=Path, help="files or dirs to scan")
    ap.add_argument("--version", help="running Argo CD version, e.g. 3.4.1")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        return selfcheck()
    if not a.paths and not a.version:
        ap.error("give paths to scan, --version, or both")

    bad = False

    if a.version:
        try:
            msg = version_exposed(parse_version(a.version))
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        if msg:
            print(f"VERSION EXPOSED: {msg}")
            bad = True
        else:
            print(f"version ok: {a.version} is at or above its line's floor")

    if a.paths:
        hits = scan(a.paths)
        for f, n, line in hits:
            print(f"ANNOTATION: {f}:{n}: {line}")
        if hits:
            print(
                f"\n{len(hits)} occurrence(s) of IncludeMutationWebhook=true — "
                "remove them; on an exposed version they are the critical CVE's vector."
            )
            bad = True
        else:
            print(
                f"manifests ok: no IncludeMutationWebhook=true under {', '.join(map(str, a.paths))}"
            )
            if not a.version:
                print(
                    "note: this says NOTHING about CVE-2026-45737, which needs no "
                    "annotation. Re-run with --version."
                )

    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
