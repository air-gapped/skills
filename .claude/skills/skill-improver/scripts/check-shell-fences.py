#!/usr/bin/env python3
"""Check every ```bash / ```sh fence in a skill tree. Two passes, because one is not enough.

Skill markdown is copy-paste material, and a block that breaks does so on the
reader's machine, not here. Nothing else in the gate chain looks inside a fence —
`shellcheck` runs on `.sh` files, not on markdown.

**Pass 1 — `bash -n`.** Catches genuine syntax errors.

**Pass 2 — line-continuation regex.** `cmd \\   # note` does not continue a line:
the backslash escapes the space, the `#` opens a comment to end of line, and the
next line becomes a separate command. **`bash -n` does not catch this** — the
result is usually still syntactically valid, it just means something else. It was
found by grep, not by the parser, which is the whole reason pass 2 exists.

Measured on the fleet, 2026-09-15: 753 fences, 7 occurrences of the continuation
bug across 4 skills, none of them visible to `bash -n`. One silently dropped two
of three `--config.file` flags instead of failing loudly.

Placeholders (`<model>`) and prompt transcriptions (`$ cmd` / `# cmd`) also fail
to parse and are reported as their own classes, since neither is fixed by editing
the command.

Usage:
    python3 check-shell-fences.py [root]        # default: .claude/skills
    python3 check-shell-fences.py --selfcheck

Exit: 0 clean, 1 real failures found, 2 usage error.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

FENCE = re.compile(r"^```(?:bash|sh|shell)\s*$(.*?)^```\s*$", re.M | re.S)

# The continuation bug: a backslash, then whitespace, then a comment.
CONTINUATION = re.compile(r"\\[ \t]+#")

# Deliberately loose. A missed placeholder is a false alarm someone must dismiss,
# which is the expensive direction.
PLACEHOLDER = re.compile(r"<[^<>\n|&]{1,60}>|\{\{.*?\}\}|\.\.\.|YOUR_|<your|\bTODO\b")

# `$ cmd` / `# cmd` transcribed from vendor docs: prompts, not shell syntax.
PROMPT = re.compile(r"^\s*(\$|#)\s+\S", re.M)


def scan(root: Path):
    """Return (continuation, parse_real, parse_prompt, parse_placeholder, total)."""
    cont, real, prompt, placeholder, total = [], [], [], [], 0
    for md in sorted(root.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        for m in FENCE.finditer(text):
            total += 1
            body = m.group(1)
            base = text[: m.start()].count("\n") + 1

            # Pass 2 first: it is exact, and independent of whether bash parses.
            for off, ln in enumerate(body.split("\n")):
                if CONTINUATION.search(ln):
                    cont.append((str(md), base + 1 + off, ln.strip()[:90]))

            # Pass 1.
            with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as f:
                f.write(body)
                tmp = f.name
            r = subprocess.run(["bash", "-n", tmp], capture_output=True, text=True)
            Path(tmp).unlink(missing_ok=True)
            if r.returncode == 0:
                continue
            err = (r.stderr or "").strip().splitlines()
            err = re.sub(r"^\S*\.sh: ", "", err[0]) if err else "parse error"
            rec = (str(md), base, err)
            if PROMPT.search(body):
                prompt.append(rec)
            elif PLACEHOLDER.search(body):
                placeholder.append(rec)
            else:
                real.append(rec)
    return cont, real, prompt, placeholder, total


def selfcheck() -> int:
    import textwrap

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "a.md").write_text(
            textwrap.dedent("""\
            ```bash
            echo AAA \\   # this breaks the continuation
              BBB
            ```
            ```bash
            echo fine && echo also-fine
            ```
            ```bash
            deploy --to <cluster name> (
            ```
            ```bash
            # echo "deb ..." \\
                | tee /etc/apt/sources.list.d/x.list
            ```
            ```bash
            for x in 1 2; do
            ```
            """),
            encoding="utf-8",
        )
        cont, real, prompt, ph, total = scan(root)

    assert total == 5, f"expected 5 fences, got {total}"
    # The continuation bug is invisible to bash -n — that is the point of pass 2.
    assert len(cont) == 1, f"expected 1 continuation hit, got {cont}"
    assert not any("this breaks" in e for _, _, e in real), (
        "bash -n must NOT be credited with catching the continuation bug"
    )
    # A commented line ending in `\` leaves the next line's pipe orphaned —
    # the real NVIDIA-docs shape. It fails to parse and is prompt-classed.
    # An unbalanced `do` is a genuine parse error with no placeholder or prompt.
    assert len(real) == 1, f"expected 1 real parse failure, got {real}"
    assert len(ph) == 1, f"expected 1 placeholder-classed failure, got {ph}"
    assert len(prompt) == 1, f"expected 1 prompt-classed failure, got {prompt}"
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--selfcheck":
        return selfcheck()
    root = Path(args[0]) if args else Path(".claude/skills")
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    cont, real, prompt, placeholder, total = scan(root)
    print(f"scanned {total} shell fences under {root}\n")

    print(f"=== {len(cont)} broken line-continuations (`\\` then a comment) ===")
    print("Invisible to `bash -n`. The command silently means something else.")
    for f, line, txt in cont:
        print(f"{f}:{line}: {txt}")
    if not cont:
        print("none.")

    print(f"\n=== {len(real)} do not parse, with no placeholder or prompt prefix ===")
    for f, line, err in real:
        print(f"{f}:{line}: {err}")
    if not real:
        print("none.")

    print(f"\n=== {len(prompt)} use a `$ ` / `# ` prompt transcription ===")
    print("Fix is a note that the prompt is not syntax, not an edit to the command.")
    for f, line, err in prompt[:20]:
        print(f"{f}:{line}: {err}")

    print(f"\n=== {len(placeholder)} contain a placeholder (expected not to parse) ===")
    for f, line, err in placeholder[:20]:
        print(f"{f}:{line}: {err}")

    return 1 if (cont or real) else 0


if __name__ == "__main__":
    sys.exit(main())
