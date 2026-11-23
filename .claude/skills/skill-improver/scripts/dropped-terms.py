#!/usr/bin/env python3
"""Terms a description trim removed that the skill's body does not hold.

Compares the listing text (description + when_to_use) at a git ref, or in a
file, with the current one, takes the distinctive terms of the old text
(backticked, quoted, and anything containing a digit), and prints each term
that is in neither the new listing text, SKILL.md's body nor references/
(sources.md and improvement-backlog.md excluded).

Read every printed term: a fact (a version, flag, error string, limit,
behaviour) goes into the body before the trim is kept; a phrase users type
("litellm budget") or a name from a "not for" clause needs nothing.

Usage:
  dropped-terms.py <skill-dir> --against <git-ref>     old text from git
  dropped-terms.py <skill-dir> --old-file <file>       old text from a file
  dropped-terms.py --selfcheck
Exit: 0 nothing missing, 1 terms printed, 2 usage error.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_frontmatter import listing_description, read_frontmatter  # noqa: E402

SKIP = ("sources.md", "improvement-backlog.md")


def terms(text: str) -> set[str]:
    found = {a or b for a, b in re.findall(r"`([^`]+)`|\"([^\"]+)\"", text)}
    found |= set(re.findall(r"[\w./*:-]*\d[\w./*:-]*", text))
    return {t.strip() for t in found if len(t.strip()) >= 3}


def body_text(skill: Path) -> str:
    md = (skill / "SKILL.md").read_text()
    end = md.find("\n---", 3)
    parts = [md[end + 4 :] if end > 0 else md]
    for f in sorted((skill / "references").glob("*.md")):
        if f.name not in SKIP:
            parts.append(f.read_text())
    return "\n".join(parts).lower()


def missing(old: str, new: str, body: str) -> list[str]:
    seen = (new + "\n" + body).lower()
    return sorted(t for t in terms(old) if t.lower() not in seen)


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "references").mkdir()
        (d / "SKILL.md").write_text(
            "---\nname: x\ndescription: Short.\n---\n\nUse `--flag-a` on v1.2.\n"
        )
        (d / "references" / "a.md").write_text("Error `E_BAD` means retry.\n")
        (d / "references" / "sources.md").write_text("`--only-in-sources`\n")
        old = 'Covers `--flag-a`, `E_BAD`, `--gone`, `--only-in-sources`, v1.2, "a phrase".'
        got = missing(old, "Short.", body_text(d))
        assert got == ["--gone", "--only-in-sources", "a phrase"], got
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("skill", nargs="?", type=Path)
    ap.add_argument("--against")
    ap.add_argument("--old-file", type=Path)
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not a.skill or not (a.against or a.old_file):
        ap.print_usage()
        return 2
    skill = a.skill.resolve()
    if a.old_file:
        old = a.old_file.read_text()
    else:
        rel = os.path.relpath(skill / "SKILL.md", os.getcwd())
        shown = subprocess.run(
            ["git", "show", f"{a.against}:./{rel}"], capture_output=True, text=True
        )
        if shown.returncode:
            print(shown.stderr.strip(), file=sys.stderr)
            return 2
        old = listing_description(read_frontmatter(shown.stdout))
    new = listing_description(read_frontmatter((skill / "SKILL.md").read_text()))
    gone = missing(old, new, body_text(skill))
    for t in gone:
        print(t)
    print(
        f"{len(gone)} of {len(terms(old))} terms are in neither the new text nor the body"
    )
    return 1 if gone else 0


if __name__ == "__main__":
    sys.exit(main())
