"""One hash for the part of a skill an agent reads, shared by the eval scripts.

Covers SKILL.md and references/. Leaves out scripts/ (their own self-checks test
them) and what records the checking itself: evals/, sources.md,
improvement-backlog.md, knowledge-claims.json and trigger-evals.json. Two calls
agree when that content is byte-identical, whether it is read from the working
tree or from a git ref.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

SKIP_NAMES = {
    "sources.md",
    "improvement-backlog.md",
    "knowledge-claims.json",
    "trigger-evals.json",
}
SKIP_PARTS = {"evals", "scripts", "__pycache__"}


def _counts(rel: str) -> bool:
    parts = rel.split("/")
    return parts[-1] not in SKIP_NAMES and not SKIP_PARTS.intersection(parts[:-1])


def _digest(rows: list[tuple[str, str]]) -> str:
    h = hashlib.sha256()
    for rel, blob in sorted(rows):
        h.update(f"{rel}\0{blob}\n".encode())
    return h.hexdigest()[:16]


def content_hash(skill_dir: Path) -> str:
    """Hash of the skill's content as it is on disk."""
    skill_dir = skill_dir.resolve()
    # Only what git tracks or would track: an ignored cache or results folder
    # is not in any commit, so counting it would never match content_hash_at().
    listed = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        cwd=skill_dir,
        check=True,
    ).stdout.split("\0")
    rels = sorted(r for r in listed if r and (skill_dir / r).is_file() and _counts(r))
    # git names each file's content, so the result matches content_hash_at().
    out = subprocess.run(
        ["git", "hash-object", "--stdin-paths"],
        input="".join(f"{skill_dir / r}\n" for r in rels),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return _digest(list(zip(rels, out)))


def content_hash_at(repo: Path, ref: str, skill_rel: str) -> str:
    """Hash of the skill's content at a git ref ("" when the skill is absent)."""
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", ref, "--", skill_rel],
        capture_output=True,
        text=True,
    ).stdout
    rows = []
    for line in out.splitlines():
        meta, path = line.split("\t", 1)
        rel = path[len(skill_rel) :].lstrip("/")
        if _counts(rel):
            rows.append((rel, meta.split()[2]))
    return _digest(rows) if rows else ""
