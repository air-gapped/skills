#!/usr/bin/env python3
"""What each skill costs in the always-loaded skill listing, and how it is invoked.

Every automatic skill's name + `description` + `when_to_use` sits in context on
every turn, inside one shared budget. A slash-only skill
(`disable-model-invocation: true`) costs nothing there; a `paths`-scoped skill
costs only where a matching file is in play. This prints one row per skill:

  mode   auto | slash | paths
  chars  listing characters (description + when_to_use); 0 counted for slash
  ~tok   chars / 4, an estimate
  share  this skill's part of all automatic listing characters
  uses   usageCount and last use from `skillUsage` in ~/.claude.json, bare and
         plugin-prefixed names summed (a hint: zero uses can mean the
         description was being dropped from the listing)
  flags  CAP   over the 1,536-character listing cap
         VER   a version number in the listing text (it goes stale first)
         NAME  the name collides with, or is a hyphen-part of, another skill's
         ORIGIN not inside a git repository and no `metadata.origin`
         CC    fields that only Claude Code accepts (claude.ai upload and the
               Skills API reject them)

Usage:
  listing-cost.py [ROOT ...] [--json] [--usage ~/.claude.json]
                  ROOT: a directory of skill dirs (default: ./.claude/skills
                  and ~/.claude/skills)
  listing-cost.py --selfcheck
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_frontmatter import listing_description, read_frontmatter  # noqa: E402

CAP = 1536
VERSION = re.compile(r"(?<![\w.])v?\d+\.\d+(?:\.\d+)*(?![\w.])")
# Agent Skills spec fields; anything else is a Claude Code extension.
SPEC_FIELDS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}


def in_git(path: Path) -> bool:
    return (
        subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def load_usage(path: Path) -> dict:
    try:
        return json.loads(path.read_text()).get("skillUsage", {}) or {}
    except (OSError, ValueError):
        return {}


def usage_for(name: str, usage: dict) -> tuple[int, int | None]:
    count, last = 0, None
    for key, rec in usage.items():
        if key == name or key.endswith(":" + name):
            count += int(rec.get("usageCount", 0))
            ts = rec.get("lastUsedAt")
            if ts and (last is None or ts > last):
                last = ts
    return count, last


def scan(roots: list[Path], usage: dict) -> list[dict]:
    seen, rows = set(), []
    for root in roots:
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            real = skill_md.resolve()
            if real in seen:
                continue
            seen.add(real)
            try:
                fm = read_frontmatter(skill_md.read_text())
            except (OSError, ValueError):
                fm = {}
            name = str(fm.get("name") or skill_md.parent.name)
            text = listing_description(fm)
            if str(fm.get("disable-model-invocation", "")).lower() == "true":
                mode = "slash"
            elif fm.get("paths"):
                mode = "paths"
            else:
                mode = "auto"
            meta = fm.get("metadata")
            has_origin = isinstance(meta, dict) and bool(meta.get("origin"))
            count, last = usage_for(name, usage)
            flags = []
            if len(text) > CAP:
                flags.append("CAP")
            if mode != "slash" and VERSION.search(text):
                flags.append("VER")
            if not has_origin and not in_git(real.parent):
                flags.append("ORIGIN")
            extra = sorted(k for k in fm if k not in SPEC_FIELDS)
            if extra:
                flags.append("CC:" + ",".join(extra))
            rows.append(
                {
                    "name": name,
                    "path": str(skill_md.parent),
                    "mode": mode,
                    "chars": len(text),
                    "uses": count,
                    "last_used": (
                        datetime.fromtimestamp(last / 1000, timezone.utc).strftime(
                            "%Y-%m-%d"
                        )
                        if last
                        else None
                    ),
                    "flags": flags,
                }
            )
    names = [r["name"] for r in rows]
    for r in rows:
        parts = set(r["name"].split("-"))
        clash = sorted(
            {
                n
                for n in names
                if n != r["name"] and (n in parts or r["name"] in set(n.split("-")))
            }
            | ({r["name"]} if names.count(r["name"]) > 1 else set())
        )
        if clash:
            r["flags"].append("NAME~" + "/".join(clash))
    total = sum(r["chars"] for r in rows if r["mode"] == "auto") or 1
    for r in rows:
        listed = r["chars"] if r["mode"] != "slash" else 0
        r["tokens"] = round(listed / 4)
        r["share"] = round(100 * listed / total, 1) if r["mode"] == "auto" else 0.0
    return sorted(rows, key=lambda r: (r["mode"] == "slash", -r["chars"]))


def report(rows: list[dict]) -> None:
    w = max([len(r["name"]) for r in rows] + [4])
    print(f"{'skill':<{w}}  mode   chars  ~tok  share  uses  last        flags")
    for r in rows:
        chars = r["chars"] if r["mode"] != "slash" else 0
        print(
            f"{r['name']:<{w}}  {r['mode']:<5}  {chars:>5}  {r['tokens']:>4}  "
            f"{r['share']:>4}%  {r['uses']:>4}  {r['last_used'] or '-':<10}  "
            f"{' '.join(r['flags'])}"
        )
    for mode in ("auto", "paths", "slash"):
        sel = [r for r in rows if r["mode"] == mode]
        chars = sum(r["chars"] for r in sel) if mode != "slash" else 0
        print(f"{mode}: {len(sel)} skills, {chars} chars, ~{round(chars / 4)} tokens")


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        def plant(name, fm):
            d = root / name
            d.mkdir()
            (d / "SKILL.md").write_text(f"---\nname: {name}\n{fm}---\n\nBody.\n")

        plant("scout", "description: Scout things.\n")
        plant("daily-scout", "description: Runs the v0.7.4 scout daily.\n")
        plant(
            "slashy",
            "description: Does a migration.\ndisable-model-invocation: true\n",
        )
        plant("rusty", "description: Rust work.\npaths: '**/*.rs'\n")
        plant(
            "origin-ok",
            "description: Has origin.\nmetadata:\n  origin: https://example.com/x\n",
        )
        usage = {
            "scout": {"usageCount": 2, "lastUsedAt": 1},
            "p:scout": {"usageCount": 3},
        }
        rows = {r["name"]: r for r in scan([root], usage)}
        assert rows["slashy"]["mode"] == "slash" and rows["slashy"]["tokens"] == 0
        assert rows["rusty"]["mode"] == "paths" and rows["rusty"]["share"] == 0.0
        assert "VER" in rows["daily-scout"]["flags"]
        assert "VER" not in rows["scout"]["flags"]
        assert any(f.startswith("NAME~") for f in rows["scout"]["flags"])
        assert any(f.startswith("NAME~") for f in rows["daily-scout"]["flags"])
        assert "ORIGIN" in rows["scout"]["flags"]
        assert "ORIGIN" not in rows["origin-ok"]["flags"]
        assert "CC:disable-model-invocation" in rows["slashy"]["flags"]
        assert rows["scout"]["uses"] == 5
        auto = [r for r in rows.values() if r["mode"] == "auto"]
        assert abs(sum(r["share"] for r in auto) - 100) < 0.5
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("roots", nargs="*", type=Path)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--usage", type=Path, default=Path.home() / ".claude.json")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    roots = a.roots or [Path(".claude/skills"), Path.home() / ".claude/skills"]
    rows = scan([r.expanduser() for r in roots], load_usage(a.usage))
    if a.json:
        print(json.dumps(rows, indent=2))
    else:
        report(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
