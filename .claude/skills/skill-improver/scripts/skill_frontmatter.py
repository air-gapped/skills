#!/usr/bin/env python3
"""Read a SKILL.md frontmatter block the way a YAML loader does.

The one reader for every script here that needs `name`, `description` or
`when_to_use`. PyYAML does the parsing when it is installed. Without it a
fallback handles the scalar forms skill frontmatter uses: plain, quoted, and
block scalars `|` and `>` with a chomping indicator (`-`, `+`) and an
indentation digit. The fallback returns every scalar as text and skips nested
values; it is checked against PyYAML by `--selfcheck` and by a file run.

    from skill_frontmatter import read_frontmatter, listing_description

    skill_frontmatter.py --selfcheck
    skill_frontmatter.py <SKILL.md>...   # exit 1 where the fallback and PyYAML differ
"""

import json
import re
import sys
from pathlib import Path

KEY = re.compile(r"^([A-Za-z_][\w-]*):(?:[ \t]+(.*))?$")
BLOCK = re.compile(r"^([|>])([+-]?\d?|\d?[+-]?)[ \t]*(?:#.*)?$")
FIELDS = ("name", "description", "when_to_use")


def split_frontmatter(text: str) -> str | None:
    """The text between the opening and closing `---` lines, or None."""
    text = text.removeprefix(chr(0xFEFF))  # a byte-order mark is not content
    m = re.match(r"---[ \t]*\r?\n(.*?\r?\n)---[ \t]*(?:\r?\n|$)", text, re.S)
    return m.group(1).replace("\r\n", "\n") if m else None


def _fold(lines: list[str]) -> str:
    """YAML line folding: a break between two text lines is a space, n blank
    lines are n newlines, and a more-indented line keeps its breaks."""
    out, blanks, prev_more, started = "", 0, False, False
    for line in lines:
        if not line.strip():
            blanks += 1
            continue
        more = line[0] in " \t"
        if not started:
            out = "\n" * blanks + line
        elif blanks:
            out += "\n" * (blanks + (1 if more or prev_more else 0)) + line
        else:
            out += ("\n" if more or prev_more else " ") + line
        blanks, prev_more, started = 0, more, True
    return out


def _block(style: str, flags: str, body: list[str]) -> str:
    chomp = "-" if "-" in flags else "+" if "+" in flags else ""
    digit = re.search(r"\d", flags)
    filled = [line for line in body if line.strip()]
    if not filled:
        return "\n" * len(body) if chomp == "+" else ""
    indent = (
        int(digit.group(0))
        if digit
        else min(len(line) - len(line.lstrip(" ")) for line in filled[:1])
    )
    lines = [line[indent:] if line.strip() else "" for line in body]
    trailing = 0
    while lines and not lines[-1]:
        lines.pop()
        trailing += 1
    text = "\n".join(lines) if style == "|" else _fold(lines)
    if chomp == "-":
        return text
    return text + "\n" * (1 + trailing if chomp == "+" else 1)


def _flow(first: str, more: list[str]) -> str:
    """A plain or quoted scalar; continuation lines fold like a `>` block."""
    lines = [first.strip()] + [line.strip() for line in more]
    while lines and not lines[-1]:
        lines.pop()
    text = _fold(lines)
    if len(text) >= 2 and text[0] == text[-1] == "'":
        return text[1:-1].replace("''", "'")
    if len(text) >= 2 and text[0] == text[-1] == '"':
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text[1:-1]
    return re.sub(r"[ \t]+#.*$", "", text).strip()


def _fallback(block: str) -> dict:
    out: dict = {}
    lines = block.removesuffix("\n").split("\n")
    i = 0
    while i < len(lines):
        m = KEY.match(lines[i])
        i += 1
        if not m:
            continue
        body = []
        while i < len(lines) and (not lines[i].strip() or lines[i][0] in " \t"):
            body.append(lines[i])
            i += 1
        key, value = m.group(1), (m.group(2) or "").strip()
        b = BLOCK.match(value)
        if b:
            out[key] = _block(b.group(1), b.group(2), body)
        elif value and value[0] not in "[{&*!":
            out[key] = _flow(value, body)
        elif not value and not any(line.strip() for line in body):
            out[key] = None
        # anything else is a nested or flow collection: not a scalar, skipped
    return out


def read_frontmatter(text: str, use_yaml: bool = True) -> dict:
    """The frontmatter mapping of a SKILL.md. ValueError when there is no
    block, it is not valid YAML, or it is not a mapping."""
    block = split_frontmatter(text)
    if block is None:
        raise ValueError("no YAML frontmatter")
    if use_yaml:
        try:
            import yaml
        except ImportError:
            return _fallback(block)
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError as e:
            raise ValueError(f"frontmatter is not valid YAML: {e}") from e
        if not isinstance(parsed, dict):
            raise ValueError("frontmatter is not a YAML mapping")
        return parsed
    return _fallback(block)


def listing_description(fm: dict) -> str:
    """`description` then `when_to_use`, as the skill listing shows them."""
    description = str(fm.get("description") or "")
    when = str(fm.get("when_to_use") or "")
    return f"{description.rstrip()} {when.lstrip()}".strip() if when else description


PLANTS = [
    # (frontmatter, {field: what a YAML loader yields})
    ("description: plain value\n", {"description": "plain value"}),
    ("description: 'it''s quoted'\n", {"description": "it's quoted"}),
    ('description: "a: b \\"c\\""\n', {"description": 'a: b "c"'}),
    ("description: value # comment\n", {"description": "value"}),
    (
        "description: first\n  second\n\n  third\nname: x\n",
        {"description": "first second\nthird", "name": "x"},
    ),
    (
        "name: demo\ndescription: |-\n  First line - with a dash.\n  Second line.\nwhen_to_use: |-\n  When asked.\n",
        {
            "name": "demo",
            "description": "First line - with a dash.\nSecond line.",
            "when_to_use": "When asked.",
        },
    ),
    ("description: |\n  a\n  b\n\nname: x\n", {"description": "a\nb\n", "name": "x"}),
    ("description: |+\n  a\n  b\n\nname: x\n", {"description": "a\nb\n\n"}),
    (
        "description: >-\n  folded\n  text\n\n  new paragraph\nallowed-tools: Read\n",
        {"description": "folded text\nnew paragraph"},
    ),
    ("description: >\n  folded\n  text\n", {"description": "folded text\n"}),
    ("description: >+\n  folded\n  text\n\n", {"description": "folded text\n\n"}),
    (
        "description: |2-\n   one space kept\n  flush\n",
        {"description": " one space kept\nflush"},
    ),
    (
        "description: >-\n  a\n    more indented\n  b\n",
        {"description": "a\n  more indented\nb"},
    ),
    ("description: |- # note\n  text\n", {"description": "text"}),
]


def disagreements(text: str) -> list[str]:
    """Fields where the fallback and PyYAML read a file differently."""
    import yaml  # noqa: F401 — the comparison needs it

    want, got = read_frontmatter(text), read_frontmatter(text, use_yaml=False)
    return [
        f"{k}: fallback {got.get(k)!r:.80} != yaml {want.get(k)!r:.80}"
        for k in FIELDS
        if isinstance(want.get(k), (str, type(None))) and got.get(k) != want.get(k)
    ]


def selfcheck() -> int:
    try:
        import yaml
    except ImportError:
        yaml = None
    for block, want in PLANTS:
        text = f"---\n{block}---\n\n# body\n---\nnot: frontmatter\n"
        got = read_frontmatter(text, use_yaml=False)
        for k, v in want.items():
            assert got.get(k) == v, (block, k, got.get(k), v)
        if yaml:  # the expected values above are a YAML loader's, not this file's
            loaded = yaml.safe_load(block)
            for k, v in want.items():
                assert loaded[k] == v, (block, k, loaded[k], v)
            assert read_frontmatter(text) == loaded, block
    fm = read_frontmatter(f"---\n{PLANTS[5][0]}---\n", use_yaml=False)
    assert listing_description(fm) == (
        "First line - with a dash.\nSecond line. When asked."
    ), listing_description(fm)
    assert listing_description({"description": "only"}) == "only"
    for bad in ("# no frontmatter\n", "---\nname: x\n"):
        try:
            read_frontmatter(bad)
        except ValueError:
            continue
        raise AssertionError(f"no ValueError for {bad!r}")
    print(
        "selfcheck: all assertions passed"
        + ("" if yaml else " (PyYAML absent: fallback checked against stored values)")
    )
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print((__doc__ or "").strip().splitlines()[-2], file=sys.stderr)
        return 2
    if sys.argv[1] == "--selfcheck":
        return selfcheck()
    bad = 0
    for arg in sys.argv[1:]:
        try:
            found = disagreements(Path(arg).read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            found = [f"unreadable: {e}"]
        for line in found:
            bad += 1
            print(f"{arg}: {line}")
    print(f"{len(sys.argv) - 1} file(s), {bad} disagreement(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
