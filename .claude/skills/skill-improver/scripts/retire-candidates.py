#!/usr/bin/env python3
"""List the lines in a skill that a retire pass should look at first.

A freshen pass adds what a product gained and has to remove what it moved
past. Finding the second kind by reading takes most of a pass. These shapes
are greppable, so list them up front and let the reader only judge:

    history     "added in v0.14", "landed v0.18 #1596", "since v2.1" — when a
                thing arrived is not something an agent acts on
    fixed       "fixed in v0.20", "before v0.26 ...", "on older engines" — a
                workaround for a release nobody runs any more
    gone        "removed in", "renamed", "formerly", "was `x` until" — a name
                kept alive after the product dropped it
    below-floor a version under --floor, the oldest release still supported

A listed line is a candidate, never a verdict: a known failure on a current
release stays, and a fix must be shown in the product before its workaround
goes. Lines in sources.md and improvement-backlog.md are skipped — history
belongs there.

    retire-candidates.py <skill-dir> [--floor 0.30] [--count]
    retire-candidates.py --selfcheck

Exit: 0 listed (or none), 2 not a skill directory.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

SKIP = {"sources.md", "improvement-backlog.md", "lessons.md"}
VER = r"v?\d+\.\d+(?:\.\d+)?"
KINDS = [
    (
        "history",
        re.compile(
            rf"\b(?:added|landed|introduced|shipped|new|available|since)\b"
            rf"[^.|\n]{{0,25}}\b{VER}|\({VER}[^)\n]{{0,12}}#\d+\)",
            re.I,
        ),
    ),
    (
        "fixed",
        re.compile(
            rf"\bfixed (?:in|by|on)\b[^.|\n]{{0,25}}{VER}"
            rf"|\b(?:before|below|prior to|pre-|older than|until)\s*{VER}"
            r"|\bolder (?:engines?|versions?|releases?|installs?)\b",
            re.I,
        ),
    ),
    (
        "gone",
        re.compile(
            r"\b(?:removed in|deprecated in|renamed (?:to|from|in)|formerly|"
            r"no longer|superseded|used to be|was [`'\"][^`'\"]+[`'\"] until)\b",
            re.I,
        ),
    ),
]
VERSION = re.compile(r"(?<![\w.])v?(\d+)\.(\d+)(?:\.(\d+))?(?![\w.]*\d{4})(?!\.\d)")
FENCE = re.compile(r"^\s*(```|~~~)")


def key(text: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", text)[:3])


def candidates(skill: Path, floor: str | None):
    """(file, line number, kind, text) for every candidate line."""
    fkey = key(floor) if floor else None
    for md in sorted(skill.rglob("*.md")):
        if md.name in SKIP or "evals" in md.parts:
            continue
        fence = False
        for n, line in enumerate(md.read_text(errors="replace").splitlines(), 1):
            if FENCE.match(line):
                fence = not fence
                continue
            if fence or not line.strip():
                continue
            kind = next((k for k, rx in KINDS if rx.search(line)), None)
            if kind is None and fkey:
                for m in VERSION.finditer(line):
                    v = tuple(int(g) for g in m.groups() if g is not None)
                    # Same major line only: 2.1 is not "below" a 0.30 floor.
                    if v[0] == fkey[0] and v[: len(fkey)] < fkey:
                        kind = "below-floor"
                        break
            if kind:
                yield md, n, kind, line.strip()


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as d:
        skill = Path(d) / "s"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: s\n---\n"
            "Sage Attention (v0.12 #243) is Triton-fused.\n"  # history
            "The bridge was added in v0.16.\n"  # history
            "Below v0.26.0 a zero meant unset.\n"  # fixed
            "On older engines there is no such check.\n"  # fixed
            "P2P connector: removed in the last major.\n"  # gone
            "Set `--kv-cache-dtype fp8` on v0.33.0.\n"  # current: quiet
            "Works on 0.24.1 as well.\n"  # below floor
            "```bash\necho added in v0.1\n```\n"  # fenced: quiet
        )
        (skill / "references" / "sources.md").write_text("added in v0.1\n")
        got = [(n, k) for _, n, k, _ in candidates(skill, "0.30")]
    want = [
        (4, "history"),
        (5, "history"),
        (6, "fixed"),
        (7, "fixed"),
        (8, "gone"),
        (10, "below-floor"),
    ]
    assert got == want, got
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t"
        p.mkdir()
        (p / "SKILL.md").write_text("Use 2.1.105 or newer; current is v0.33.0.\n")
        assert list(candidates(p, "0.30")) == []  # other major line is not below
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("skill", nargs="?", type=Path)
    ap.add_argument("--floor", help="oldest supported release, e.g. 0.30")
    ap.add_argument("--count", action="store_true", help="totals per kind only")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not a.skill or not (a.skill / "SKILL.md").is_file():
        print(f"not a skill directory: {a.skill}", file=sys.stderr)
        return 2
    rows = list(candidates(a.skill, a.floor))
    if not a.count:
        for md, n, kind, text in rows:
            print(f"{md.relative_to(a.skill)}:{n}: [{kind}] {text[:150]}")
    totals: dict[str, int] = {}
    for _, _, kind, _ in rows:
        totals[kind] = totals.get(kind, 0) + 1
    print(
        f"{len(rows)} candidate line(s): "
        + (", ".join(f"{k} {v}" for k, v in sorted(totals.items())) or "none")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
