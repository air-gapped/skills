#!/usr/bin/env python3
"""Parse every ```yaml fence in a skill tree. Sibling of check-shell-fences.py.

Same reasoning: a manifest in skill markdown is copy-paste material, and nothing
in the gate chain parses it, so a broken one fails on the reader's cluster.

Measured on the fleet, 2026-09-15: 576 yaml fences (count cross-checked against
a raw grep of the fence openers), **one real bug** — a
LeaderWorkerSet manifest where a `fieldPath` containing `[` and `]` sat unquoted
inside a YAML **flow** mapping (`{...}`). Flow style forbids those characters in
a plain scalar, so the whole mapping failed to parse. In block style the same
value is legal, which is why this survived review: it looks like every other
`fieldRef` in Kubernetes documentation.

YAML is in much better shape than shell here, so expect this to be quiet. Its
value is the next edit, not this run.

Two classes fail by design and are reported separately: Go/Jinja templating
(`{{ ... }}` — Helm charts are not YAML until rendered) and placeholders.

Usage:
    python3 check-yaml-fences.py [root]        # default: .claude/skills
    python3 check-yaml-fences.py --selfcheck

Exit: 0 clean, 1 real failures, 2 usage error or PyYAML missing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print(
        "PyYAML not installed — `pip install pyyaml` to run this check.",
        file=sys.stderr,
    )
    sys.exit(2)

FENCE = re.compile(r"^```(?:yaml|yml)\s*$(.*?)^```\s*$", re.M | re.S)
TEMPLATE = re.compile(r"\{\{|\{%|\$\{")
PLACEHOLDER = re.compile(r"<[^<>\n]{1,60}>|\.\.\.|YOUR_|\bTODO\b|\bELIDED\b")


def scan(root: Path):
    real, tmpl, ph, total = [], [], [], 0
    for md in sorted(root.rglob("*.md")):
        text = md.read_text(encoding="utf-8", errors="replace")
        for m in FENCE.finditer(text):
            total += 1
            body = m.group(1)
            line = text[: m.start()].count("\n") + 1
            try:
                list(yaml.safe_load_all(body))
            except Exception as e:  # noqa: BLE001 - any parse failure is the signal
                msg = " ".join(str(e).split())[:150]
                rec = (str(md), line, msg)
                if TEMPLATE.search(body):
                    tmpl.append(rec)
                elif PLACEHOLDER.search(body):
                    ph.append(rec)
                else:
                    real.append(rec)
    return real, tmpl, ph, total


def selfcheck() -> int:
    import tempfile
    import textwrap

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "a.md").write_text(
            textwrap.dedent("""\
            ```yaml
            - {name: X, valueFrom: {fieldRef: {fieldPath: metadata.annotations['a.b/c']}}}
            ```
            ```yaml
            - {name: X, valueFrom: {fieldRef: {fieldPath: "metadata.annotations['a.b/c']"}}}
            ```
            ```yaml
            metadata:
              labels: {{ include "chart.labels" . }}
            ```
            """),
            encoding="utf-8",
        )
        real, tmpl, ph, total = scan(root)

    assert total == 3, f"expected 3 fences, got {total}"
    assert len(real) == 1, f"the unquoted flow scalar must fail, got {real}"
    assert len(tmpl) == 1, f"the Helm block must be template-classed, got {tmpl}"
    assert len(ph) == 0, f"nothing should be placeholder-classed here, got {ph}"
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

    real, tmpl, ph, total = scan(root)
    print(f"scanned {total} yaml fences under {root}\n")

    print(f"=== {len(real)} do not parse, with no template or placeholder ===")
    for f, line, e in real:
        print(f"{f}:{line}: {e}")
    if not real:
        print("none.")

    print(
        f"\n=== {len(tmpl)} contain Go/Jinja templating (not YAML until rendered) ==="
    )
    for f, line, e in tmpl[:15]:
        print(f"{f}:{line}: {e}")

    print(f"\n=== {len(ph)} contain placeholders ===")
    for f, line, e in ph[:15]:
        print(f"{f}:{line}: {e}")

    return 1 if real else 0


if __name__ == "__main__":
    sys.exit(main())
