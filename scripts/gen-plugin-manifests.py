#!/usr/bin/env python3
"""Regenerate Claude Code plugin marketplace manifests.

Writes:
- .claude-plugin/marketplace.json (repo root)
- .claude/skills/<name>/.claude-plugin/plugin.json (per skill)

Version scheme per skill: 0.YYYYMMDD.N where
- YYYYMMDD = UTC date of the most recent commit touching the skill dir
  (bumped to today if the skill has currently-staged changes).
- N = total count of commits touching the skill dir across history
  (bumped by 1 if currently-staged changes touch the skill).

Rationale: versions only change when a skill actually changes; date
stays visible; patch is monotonic. Multiple edits in the same day keep
incrementing the patch via the commit count.
"""

import datetime
import json
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
MARKETPLACE_FILE = REPO_ROOT / ".claude-plugin" / "marketplace.json"

MARKETPLACE_NAME = "air-gapped-skills"
OWNER_NAME = "air-gapped"
AUTHOR_NAME = "Jörgen"
LICENSE = "MIT"
MARKETPLACE_DESC = (
    "Reference skills for vLLM, Kubernetes, release engineering, and Claude "
    "Code authoring. Each plugin ships one SKILL.md plus supporting references."
)
TAGLINE_CAP = 200


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    lines = m.group(1).splitlines()
    result: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        kv = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not kv:
            i += 1
            continue
        key, val = kv.group(1), kv.group(2).strip()
        if val in {">-", ">", "|-", "|"}:
            buf = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i] == ""):
                buf.append(lines[i].strip())
                i += 1
            result[key] = " ".join(b for b in buf if b)
        else:
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            result[key] = val
            i += 1
    return result


def tagline(desc: str) -> str:
    desc = re.sub(r"\s+", " ", desc.strip())
    m = re.search(r"(\. |\? |! | — | - Triggers )", desc)
    if m:
        desc = desc[: m.start()].rstrip(" .")
    if len(desc) <= TAGLINE_CAP:
        return desc
    return desc[:TAGLINE_CAP].rsplit(" ", 1)[0] + "…"


def run_git(*args: str) -> str:
    r = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    return r.stdout


def _pathspec_args(path: pathlib.Path) -> list[str]:
    """Pathspec that covers the skill but excludes the generated
    .claude-plugin/ metadata so version calc is stable across runs."""
    rel = str(path.relative_to(REPO_ROOT))
    return [rel, f":(exclude){rel}/.claude-plugin"]


def commit_count(path: pathlib.Path) -> int:
    out = run_git("log", "--oneline", "--", *_pathspec_args(path))
    return sum(1 for line in out.splitlines() if line.strip())


def last_commit_date(path: pathlib.Path) -> str | None:
    out = run_git(
        "log",
        "-1",
        "--format=%cd",
        "--date=format-local:%Y%m%d",
        "--",
        *_pathspec_args(path),
    )
    out = out.strip()
    return out or None


def staged_touches(path: pathlib.Path) -> bool:
    """True if staged diff touches the skill, ignoring generated
    .claude-plugin/ metadata (which this script itself produces —
    counting it would make every run bump the version)."""
    rel = str(path.relative_to(REPO_ROOT))
    prefix = rel + "/"
    skip_prefix = rel + "/.claude-plugin/"
    out = run_git("diff", "--cached", "--name-only")
    for f in out.splitlines():
        if f.startswith(skip_prefix):
            continue
        if f == rel or f.startswith(prefix):
            return True
    return False


def today_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")


def version_for(skill_dir: pathlib.Path) -> str:
    count = commit_count(skill_dir)
    date = last_commit_date(skill_dir) or today_utc()
    if staged_touches(skill_dir):
        count += 1
        date = today_utc()
    if count == 0:
        count = 1
    return f"0.{date}.{count}"


def build_entries() -> list[dict]:
    entries: list[dict] = []
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        skill_dir = skill_md.parent
        fm = parse_frontmatter(skill_md.read_text())
        name = fm.get("name", skill_dir.name)
        desc = tagline(fm.get("description", ""))
        entries.append(
            {
                "name": name,
                "source": "./" + str(skill_dir.relative_to(REPO_ROOT)),
                "description": desc,
                "version": version_for(skill_dir),
                "_skill_dir": skill_dir,
                "_full_description": re.sub(
                    r"\s+", " ", fm.get("description", "").strip()
                ),
            }
        )
    return entries


def write_json_if_changed(path: pathlib.Path, data: dict) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text() == new:
        return False
    path.write_text(new)
    return True


def write_marketplace(entries: list[dict]) -> bool:
    marketplace = {
        "name": MARKETPLACE_NAME,
        "owner": {"name": OWNER_NAME},
        "metadata": {"description": MARKETPLACE_DESC},
        "plugins": [
            {
                "name": e["name"],
                "source": e["source"],
                "description": e["description"],
                "version": e["version"],
            }
            for e in entries
        ],
    }
    return write_json_if_changed(MARKETPLACE_FILE, marketplace)


def write_plugin(entry: dict) -> bool:
    plugin_file = entry["_skill_dir"] / ".claude-plugin" / "plugin.json"
    data = {
        "name": entry["name"],
        "description": entry["_full_description"] or entry["description"],
        "author": {"name": AUTHOR_NAME},
        "license": LICENSE,
    }
    return write_json_if_changed(plugin_file, data)


def main() -> int:
    entries = build_entries()
    if not entries:
        print("error: no skills with SKILL.md found", file=sys.stderr)
        return 2
    changed = write_marketplace(entries)
    for entry in entries:
        if write_plugin(entry):
            changed = True
    if changed:
        print(f"regenerated manifests for {len(entries)} plugins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
