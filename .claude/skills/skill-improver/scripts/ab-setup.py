#!/usr/bin/env python3
"""Materialise a blinded A/B pair for the skill-comparator.

Baseline goes to x/, the current HEAD to y/, both via `git archive` (no git
metadata), with evals/ and references/improvement-backlog.md left out and every
mtime set to one value. Also writes the comparator agent definition as an
`--agents` JSON file outside the pair. One script, so sandboxes that refuse
inline `$(...)` / variable lines still run it.

    ab-setup.py <baseline-ref> <skill-dir>
    ab-setup.py --selfcheck

Prints AB=<dir> and AGENTS=<file>.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

EPOCH = 946684800  # 2000-01-01T00:00:00Z
EXCLUDE = ["--exclude=*/evals", "--exclude=*/references/improvement-backlog.md"]


def setup(ref: str, skill: Path) -> tuple[Path, Path]:
    skill = skill.resolve()
    top = Path(
        subprocess.run(
            ["git", "-C", str(skill), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    rel = skill.relative_to(top)
    ab = Path(tempfile.mkdtemp(prefix="ab-"))
    for side, rev in (("x", ref), ("y", "HEAD")):
        (ab / side).mkdir()
        arc = subprocess.run(
            ["git", "-C", str(top), "archive", rev, "--", str(rel)],
            capture_output=True,
            check=True,
        ).stdout
        # Never extract what would un-blind, rather than trusting the agent not to open it.
        subprocess.run(
            [
                "tar",
                "-x",
                "-C",
                str(ab / side),
                f"--strip-components={len(rel.parts)}",
                *EXCLUDE,
            ],
            input=arc,
            check=True,
        )
    # git archive stamps each side with its own commit time; equalise or `stat` orders the pair.
    for root, dirs, files in os.walk(ab):
        for n in dirs + files:
            os.utime(Path(root) / n, (EPOCH, EPOCH), follow_symlinks=False)
    os.utime(ab, (EPOCH, EPOCH))

    text = (top / ".claude" / "agents" / "skill-comparator.md").read_text()
    m = re.match(r"---\n(.*?)\n---\n(.*)", text, re.S)
    if not m:
        sys.exit("skill-comparator.md has no frontmatter")
    fm, body = m.groups()
    meta = dict(line.split(": ", 1) for line in fm.splitlines() if ": " in line)
    agents = Path(tempfile.mkdtemp(prefix="ab-agents-")) / "agents.json"
    agents.write_text(
        json.dumps(
            {
                "skill-comparator": {
                    "description": meta["description"],
                    "prompt": body,
                    "model": meta.get("model", "sonnet"),
                }
            }
        )
    )
    return ab, agents


def selfcheck() -> int:
    ab, agents = setup("HEAD", Path(__file__).resolve().parent.parent)
    for side in ("x", "y"):
        assert (ab / side / "SKILL.md").is_file(), side
    assert not (ab / "x" / "evals").exists()
    assert not (ab / "y" / "references" / "improvement-backlog.md").exists()
    assert (
        (ab / "x" / "SKILL.md").stat().st_mtime
        == (ab / "y" / "SKILL.md").stat().st_mtime
        == EPOCH
    )
    assert "skill-comparator" in json.loads(agents.read_text())
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("ref", nargs="?")
    ap.add_argument("skill", nargs="?", type=Path)
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if not (a.ref and a.skill):
        ap.error("usage: ab-setup.py <baseline-ref> <skill-dir>")
    ab, agents = setup(a.ref, a.skill)
    print(f"AB={ab}")
    print(f"AGENTS={agents}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
