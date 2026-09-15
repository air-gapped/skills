#!/usr/bin/env python3
"""Find markdown table rows whose cell count disagrees with their header.

Markdown renderers do not warn about a ragged table. They **drop every cell past
the header's column count**, so the row still renders, still looks deliberate,
and silently loses its tail. Nothing else in this repo looks at table shape:
skillevaluator checks frontmatter and links, and the fence checkers parse code
blocks, which a table is not.

The damage lands on the last column, which is where tables put the payload.
Measured 2026-09-15: **34 ragged rows across 7 files**. The worst was a
troubleshooting table whose header read `| Symptom | Issue | Fix |` while most of
its rows had been written in a four-column shape with a model/scenario column --
so on exactly the rows carrying a model-specific workaround, the **Fix** column
was the one thrown away.

**A too-short row is the quieter half and still wrong.** A hardware comparison
table had rows stating one value for both variants; each rendered with an empty
second column, which reads as *absent on that variant* rather than *same on
both*.

Ragged rows cluster, because they come from a table whose shape changed once and
whose header did not follow. Fix the header, not the rows, when the rows agree
with each other.

Pipes inside backticks are not column separators; a row need not end in a pipe.
Both are handled -- get either wrong and the tool reports every table as ragged.

Usage:
    python3 check-tables.py [root]
    python3 check-tables.py --selfcheck

Exit: 0 clean, 1 ragged rows found, 2 usage error.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SEPARATOR = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")


def cells(line: str) -> list[str]:
    """Split one markdown row into cells.

    Two kinds of `|` are content rather than a border: one inside backticks, and
    one escaped as `\\|`. Documentation tables list alternatives constantly
    (`` `a` \\| `b` ``), so missing either turns a correct table into a page of
    findings.
    """
    s = line.strip()
    out, buf, tick = [], "", False
    i = 0
    while i < len(s):
        c = s[i]
        if c == "`":
            tick = not tick
        if c == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            buf += s[i : i + 2]  # escaped pipe: content
            i += 2
            continue
        if c == "|" and not tick:
            out.append(buf)
            buf = ""
        else:
            buf += c
        i += 1
    out.append(buf)
    if out and not out[-1].strip():  # trailing pipe is optional
        out = out[:-1]
    return out[1:]


def ragged(path: Path) -> list[tuple[int, int, int, str]]:
    """(line number, row width, header width, row text) for each ragged row."""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    found, fence, i = [], False, 0
    while i < len(lines):
        if lines[i].lstrip().startswith("```"):
            fence = not fence
            i += 1
            continue
        head = lines[i].strip()
        sep = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not fence and head.startswith("|") and "-" in sep and SEPARATOR.match(sep):
            width = len(cells(head))
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                got = len(cells(lines[j]))
                if got != width:
                    found.append((j + 1, got, width, lines[j].strip()))
                j += 1
            i = j
            continue
        i += 1
    return found


def selfcheck() -> int:
    assert cells("| a | b | c |") == [" a ", " b ", " c "]
    assert cells("| a | b | c") == [" a ", " b ", " c"]  # no trailing pipe
    # A pipe inside code is content. Getting this wrong flags every such row.
    assert len(cells("| a | `x | y` | c |")) == 3
    # So is an escaped pipe -- how every docs table writes "this OR that".
    assert len(cells(r"| `--mode` | `a` \| `b` \| `c` | notes |")) == 3
    assert SEPARATOR.match("|---|---|")
    assert SEPARATOR.match("|:--|--:|")
    assert not SEPARATOR.match("| a | b |")

    import tempfile

    doc = (
        "| Symptom | Issue | Fix |\n"
        "|---|---|---|\n"
        "| a | b | c |\n"
        "| a | model | b | c |\n"  # the real defect: Fix gets dropped
        "| a | b |\n"  # the quiet half: an empty cell reads as absent
        "\n"
        "```\n"
        "| not | a | table |\n"  # inside a fence, must be ignored
        "|---|---|---|\n"
        "| x |\n"
        "```\n"
    )
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "t.md"
        f.write_text(doc, encoding="utf-8")
        hits = ragged(f)
    assert [(n, got, want) for n, got, want, _ in hits] == [(4, 4, 3), (5, 2, 3)], hits
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("root", nargs="?", default=Path(".claude/skills"), type=Path)
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        return selfcheck()
    if not a.root.is_dir():
        print(f"not a directory: {a.root}", file=sys.stderr)
        return 2

    total = 0
    for md in sorted(a.root.rglob("*.md")):
        if md.relative_to(a.root).parts[0].endswith("-workspace"):
            continue
        for n, got, want, text in ragged(md):
            total += 1
            print(f"{md}:{n}: {got} cells, header has {want}\n    {text[:150]}")

    print(f"\n=== {total} ragged rows ===")
    if not total:
        print("none.")
    else:
        print(
            "Rows that agree with each other and disagree with the header mean\nthe header is what changed. Fix the header."
        )
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
