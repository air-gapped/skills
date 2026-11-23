"""One hash for the part of a skill an agent reads, shared by the eval scripts.

Covers the SKILL.md body and references/. Leaves out the SKILL.md frontmatter
(name, description, invocation and path settings decide whether the skill is
loaded, not what an answer says, and the outcome evals force invocation),
scripts/ (their own self-checks test them) and what records the checking
itself: evals/, sources.md, improvement-backlog.md, knowledge-claims.json and
trigger-evals.json. Two calls agree when that content is byte-identical,
whether it is read from the working tree or from a git ref.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

SKIP_NAMES = {
    "sources.md",
    "improvement-backlog.md",
    "knowledge-claims.json",
    "trigger-evals.json",
}
SKIP_PARTS = {"evals", "scripts", "__pycache__"}
FRONTMATTER = re.compile(rb"\A---\r?\n.*?^---[ \t]*(?:\r?\n|\Z)", re.S | re.M)


def _counts(rel: str) -> bool:
    parts = rel.split("/")
    return parts[-1] not in SKIP_NAMES and not SKIP_PARTS.intersection(parts[:-1])


def body_id(raw: bytes) -> str:
    """Stand-in blob id for SKILL.md: its text with the frontmatter removed."""
    return "body:" + hashlib.sha256(FRONTMATTER.sub(b"", raw, count=1)).hexdigest()


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
    rows = [
        (r, body_id((skill_dir / r).read_bytes()) if r == "SKILL.md" else blob)
        for r, blob in zip(rels, out)
    ]
    return _digest(rows)


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
        if not _counts(rel):
            continue
        blob = meta.split()[2]
        if rel == "SKILL.md":
            raw = subprocess.run(
                ["git", "-C", str(repo), "cat-file", "blob", blob],
                capture_output=True,
                check=True,
            ).stdout
            blob = body_id(raw)
        rows.append((rel, blob))
    return _digest(rows) if rows else ""
