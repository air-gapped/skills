#!/usr/bin/env python3
"""Regenerate the skill index table in README.md between
<!-- skills-start --> and <!-- skills-end --> markers.

Uses a lenient line-by-line frontmatter parser because skill descriptions
often contain colons inside backticks (e.g. `initialDelaySeconds: 600`)
that trip strict YAML parsers.
"""

import pathlib
import re
import sys

README = pathlib.Path("README.md")
SKILLS = pathlib.Path(".claude/skills")
MARK_A = "<!-- skills-start -->"
MARK_B = "<!-- skills-end -->"
MAX_LEN = 250


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


def summarise(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    if len(s) <= MAX_LEN:
        return s
    return s[:MAX_LEN].rsplit(" ", 1)[0] + "…"


def build_table() -> str:
    rows = ["| Skill | Description |", "|---|---|"]
    for skill_md in sorted(SKILLS.glob("*/SKILL.md")):
        fm = parse_frontmatter(skill_md.read_text())
        name = fm.get("name", skill_md.parent.name)
        desc = summarise(fm.get("description", ""))
        rows.append(f"| [`{name}`]({skill_md}) | {desc} |")
    return "\n".join(rows)


def main() -> int:
    text = README.read_text()
    if MARK_A not in text or MARK_B not in text:
        print(f"error: README.md missing {MARK_A} or {MARK_B}", file=sys.stderr)
        return 2
    table = build_table()
    new = re.sub(
        re.escape(MARK_A) + r".*?" + re.escape(MARK_B),
        f"{MARK_A}\n{table}\n{MARK_B}",
        text,
        flags=re.DOTALL,
    )
    if new != text:
        README.write_text(new)
    return 0


if __name__ == "__main__":
    sys.exit(main())
