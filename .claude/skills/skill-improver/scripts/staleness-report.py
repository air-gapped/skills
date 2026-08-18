#!/usr/bin/env python3
"""Usage: ./staleness-report.py [search_root...] [name-glob...] [--json]

Fast fleet-wide staleness readout — no probes, no network, filesystem only.
For every skill found (same default roots as scan-skills.sh), reports the
sources.md verification-date spread and the Dim 9 staleness cap it implies
(quality-rubric.md §Dim 9), plus the last improvement-pass date from
references/improvement-backlog.md.

Output is one row per skill, stalest first — the ranking `freshen --all`
batch mode uses. `--json` emits the same rows as a JSON array.

Date extraction per sources.md, in order:
  1. table with a `Last verified` header column → that column's cell per row
  2. table without that header → rightmost cell that is exactly a date
     (prose dates in notes cells never count)
  3. no usable table rows → inline `Last verified: YYYY-MM-DD` occurrences

Args that are existing directories are search roots; anything else is a
name glob (`'vllm-*'`) filtering the skills reported.

Two date tracks per skill — they answer different questions:
  oldest/age  when the skill's EXTERNAL claims were last verified online
              (freshen track — sources.md `Last verified:` dates)
  changed     when the skill's CONTENT last changed on disk (newest file
              mtime in the skill dir — edits, improve passes, by-hand fixes)

Columns:
  age    days since the OLDEST counted `Last verified` date (- if none)
  oldest that date itself
  changed newest file-mtime date in the skill directory
  rows   dated-rows/counted-rows in sources.md (ignore-freshen rows excluded)
  cap    Dim 9 staleness cap: -=no cap, 7 (91-180d), 5 (>180d),
         6 (no sources.md, or <80% of rows dated)
  pass   newest non-future date in references/improvement-backlog.md
  evals  t if references/trigger-evals.json exists, o if evals/evals.json
         exists (outcome evals), to for both, - for neither
"""

import json
import re
import sys
from datetime import date
from fnmatch import fnmatch
from pathlib import Path

DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
INLINE_LV_RE = re.compile(r"Last verified:?\s*\**(\d{4}-\d{2}-\d{2})", re.I)


def default_roots():
    roots = []
    home = Path.home() / ".claude" / "skills"
    if home.is_dir():
        roots.append(home)
    proj = Path(".claude/skills")
    if proj.is_dir():
        roots.append(proj)
    for nested in Path(".").glob("*/**/.claude/skills"):
        if (
            nested.is_dir()
            and ".git" not in nested.parts
            and "node_modules" not in nested.parts
        ):
            roots.append(nested)
    return roots


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_sources(path):
    """Return (oldest, dated_rows, counted_rows) for a sources.md file."""
    lines = path.read_text(errors="replace").splitlines()
    lv_col = None  # `Last verified` column of the current table, if any
    skip_table = False  # current table has a header without that column
    saw_header = False  # file has at least one explicit table header
    dates, counted = [], 0
    for i, line in enumerate(lines):
        s = line.strip()
        if not s.startswith("|") or "ignore-freshen" in s:
            continue
        row = cells(s)
        if all(re.fullmatch(r":?-+:?", c) or c == "" for c in row):  # separator
            continue
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        is_header = nxt.startswith("|") and all(
            re.fullmatch(r":?-+:?", c) or c == "" for c in cells(nxt)
        )
        if is_header:
            saw_header = True
            hits = [
                j
                for j, c in enumerate(row)
                if re.fullmatch(r"last verified:?", c, re.I)
            ]
            lv_col, skip_table = (hits[0], False) if hits else (None, True)
            continue
        if skip_table:
            continue
        counted += 1
        found = None
        if lv_col is not None and lv_col < len(row):
            m = DATE_RE.search(row[lv_col])
            if m:
                found = m.group(0)
        elif not saw_header:
            for cell in reversed(row):  # headerless table: cell must BE a date
                if DATE_RE.fullmatch(cell):
                    found = cell
                    break
        if found:
            dates.append(found)
    if counted == 0:  # not a table — fall back to inline markers
        inline = INLINE_LV_RE.findall("\n".join(lines))
        if inline:
            return min(inline), len(inline), len(inline)
        # bullet-list format: `- [title](url) ... [LV: YYYY-MM-DD]` per row
        bullets = [
            ln
            for ln in lines
            if ln.lstrip().startswith("- [") and "ignore-freshen" not in ln
        ]
        if bullets:
            lv = [
                m.group(1)
                for ln in bullets
                if (m := re.search(r"\[LV: (\d{4}-\d{2}-\d{2})", ln))
            ]
            return (min(lv) if lv else None), len(lv), len(bullets)
    if not dates:
        return None, 0, counted
    return min(dates), len(dates), counted


def dim9_cap(oldest, dated, counted, today):
    """quality-rubric.md §Dim 9 staleness-cap table."""
    if counted == 0 or dated == 0 or dated / counted < 0.8:
        return "6", None
    age = (today - date.fromisoformat(oldest)).days
    if age > 180:
        return "5", age
    if age > 90:
        return "7", age
    return "-", age


def scan_skill(skill_md, today):
    d = skill_md.parent
    row = {"skill": d.name, "path": str(skill_md)}
    src = d / "references" / "sources.md"
    if src.is_file():
        oldest, dated, counted = parse_sources(src)
        row["oldest"] = oldest
        row["rows"] = f"{dated}/{counted}"
        row["cap"], row["age"] = dim9_cap(oldest, dated, counted, today)
    else:
        row.update(oldest=None, rows="-", cap="6", age=None)
    backlog = d / "references" / "improvement-backlog.md"
    dates = (
        DATE_RE.findall(backlog.read_text(errors="replace"))
        if backlog.is_file()
        else []
    )
    past = [x for x in dates if x <= today.isoformat()]
    row["pass"] = max(past) if past else None
    row["evals"] = (
        ("t" if (d / "references" / "trigger-evals.json").is_file() else "")
        + ("o" if (d / "evals" / "evals.json").is_file() else "")
    ) or "-"
    mtimes = [f.stat().st_mtime for f in d.rglob("*") if f.is_file()]
    row["changed"] = date.fromtimestamp(max(mtimes)).isoformat() if mtimes else None
    return row


def main():
    args = sys.argv[1:]
    as_json = "--json" in args
    positional = [a for a in args if a != "--json"]
    roots = [Path(a) for a in positional if Path(a).is_dir()]
    globs = [a for a in positional if not Path(a).is_dir()]
    roots = roots or default_roots()
    if not roots:
        sys.exit("No skill directories found.")

    today = date.today()
    rows = []
    for root in roots:
        for skill_md in sorted(root.rglob("SKILL.md")):
            row = scan_skill(skill_md, today)
            if not globs or any(fnmatch(row["skill"], g) for g in globs):
                rows.append(row)

    # Stalest first: hard caps (5, then 6) ahead of soft (7) ahead of fresh,
    # oldest date first within each bucket.
    cap_rank = {"5": 0, "6": 1, "7": 2, "-": 3}
    rows.sort(key=lambda r: (cap_rank[r["cap"]], r["oldest"] or "9999", r["skill"]))

    if as_json:
        json.dump(rows, sys.stdout, indent=1)
        print()
        return
    print(
        f"{'age':>4}  {'oldest':<10}  {'changed':<10}  {'rows':>7}  {'cap':>3}  "
        f"{'pass':<10}  {'evals':<5}  skill"
    )
    for r in rows:
        print(
            f"{r['age'] if r['age'] is not None else '-':>4}  {r['oldest'] or '-':<10}  "
            f"{r['changed'] or '-':<10}  {r['rows']:>7}  {r['cap']:>3}  "
            f"{r['pass'] or '-':<10}  {r['evals']:<5}  {r['skill']}"
        )


if __name__ == "__main__":
    main()
