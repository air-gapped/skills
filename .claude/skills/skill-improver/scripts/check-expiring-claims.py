#!/usr/bin/env python3
"""List skill claims dated in the future — statements that expire on a known day.

A skill saying "X happens on <future date>" is correct today and wrong afterwards,
usually with nothing to signal the change. `freshen` catches sources that drifted;
this catches content scheduled to become false.

**Flag the relative phrases, not only the dates.** Measured on the fleet
2026-09-15: 37 future-dated claims, 2 worth acting on, and the more instructive
one had a *correct* date beside a rotted description of it — "2.11 goes EOL
2026-10-24 — roughly three months out" when the date was 5½ weeks away. The
absolute fact stayed true while the sentence around it decayed, in a warning whose
whole purpose was conveying how short the runway was. So `--relative` reports
future dates sitting next to a phrase like "months out" or "weeks away"; those
rot without the date ever becoming wrong.

The other find was a FIPS 140-2 validation window six days from closing, stated
with no expiry marker in a block read for compliance answers.

Not every hit is a defect — a table of EOL dates is *supposed* to hold future
dates. Read the near ones and the `[rel]`-tagged ones; ignore a well-formed
lifecycle table.

Usage:
    python3 check-expiring-claims.py [root] [--days N] [--relative]
    python3 check-expiring-claims.py --selfcheck

Exit: 0 always (advisory), 2 on usage error.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ISO = re.compile(r"\b(20\d\d)-(\d{2})-(\d{2})\b")
MONTH_NAMES = (
    "January February March April May June July August September October November December"
).split()
LONG = re.compile(r"\b(" + "|".join(MONTH_NAMES) + r")\s+(\d{1,2}),\s+(20\d\d)\b")
MONTHS = {m: i + 1 for i, m in enumerate(MONTH_NAMES)}

# Phrases that describe a distance in time and therefore decay independently.
RELATIVE = re.compile(
    r"\b(?:roughly|about|approximately|~|just|only|barely|under|over)?\s*"
    r"(?:a|an|one|two|three|four|five|six|several|\d+)?\s*"
    r"(?:day|week|month|year)s?\s*(?:out|away|from now|left|remaining|to go)\b",
    re.I,
)

SKIP_FILES = {"improvement-backlog.md"}


def scan(root: Path, today: dt.date, horizon_days: int):
    horizon = today + dt.timedelta(days=horizon_days)
    rows = []
    for skill in sorted(p for p in root.iterdir() if p.is_dir()):
        for md in sorted(skill.rglob("*.md")):
            if md.name in SKIP_FILES or "/results/" in str(md):
                continue
            text = md.read_text(encoding="utf-8", errors="replace")

            def add(d: dt.date, start: int, end: int):
                if not (today < d <= horizon):
                    return
                ls = text.rfind("\n", 0, start) + 1
                le = text.find("\n", end)
                ctx = text[ls : le if le != -1 else len(text)].strip()
                rows.append(
                    (
                        d,
                        skill.name,
                        str(md),
                        text[:start].count("\n") + 1,
                        ctx,
                        bool(RELATIVE.search(ctx)),
                    )
                )

            for m in ISO.finditer(text):
                try:
                    add(
                        dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))),
                        m.start(),
                        m.end(),
                    )
                except ValueError:
                    continue
            for m in LONG.finditer(text):
                try:
                    add(
                        dt.date(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))),
                        m.start(),
                        m.end(),
                    )
                except (ValueError, KeyError):
                    continue
    rows.sort(key=lambda r: r[0])
    return rows


def selfcheck() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "s").mkdir()
        (root / "s" / "SKILL.md").write_text(
            "EOL is 2099-01-01 — roughly three months out.\n"
            "Shipped on 2020-01-01, long past.\n"
            "Support ends January 2, 2099.\n",
            encoding="utf-8",
        )
        (root / "s" / "references").mkdir()
        (root / "s" / "references" / "improvement-backlog.md").write_text(
            "planned for 2099-06-06\n", encoding="utf-8"
        )
        rows = scan(root, dt.date(2098, 12, 1), 400)

    dates = sorted({r[0] for r in rows})
    assert dates == [dt.date(2099, 1, 1), dt.date(2099, 1, 2)], f"got {dates}"
    assert any(r[5] for r in rows), (
        "the 'three months out' line must be flagged relative"
    )
    assert not any("improvement-backlog" in r[2] for r in rows), (
        "backlogs must be skipped"
    )
    assert not any(r[0].year == 2020 for r in rows), "past dates must not appear"
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("root", nargs="?", default=".claude/skills", type=Path)
    ap.add_argument(
        "--days", type=int, default=400, help="horizon in days (default 400)"
    )
    ap.add_argument(
        "--relative", action="store_true", help="only claims beside a relative phrase"
    )
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        return selfcheck()
    if not a.root.is_dir():
        print(f"not a directory: {a.root}", file=sys.stderr)
        return 2

    today = dt.date.today()
    rows = scan(a.root, today, a.days)
    if a.relative:
        rows = [r for r in rows if r[5]]

    print(
        f"{len(rows)} future-dated claims under {a.root} "
        f"(today {today}, horizon +{a.days}d)\n"
    )
    for d, skill, f, line, ctx, rel in rows:
        tag = " [rel]" if rel else ""
        print(f"{d} (+{(d - today).days:4d}d){tag} {skill}")
        print(f"    {f}:{line}: {ctx[:110]}")

    if rows:
        print(
            "\nRead the nearest ones and every [rel] line. A lifecycle table of EOL "
            "dates is\nsupposed to look like this — a [rel] phrase beside a date is not."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
