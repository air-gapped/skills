#!/usr/bin/env python3
"""Measure overlap between skills in a fleet, on two axes that disagree.

Dimension 10 (Differentiation) asks "if this skill were deleted, would Claude
produce noticeably worse results?" — and scorers answer it from intuition,
which SkillLens clocked at 46.4%, worse than chance. This supplies the missing
measurement: embed every skill, compare every pair, and rank.

It runs SkillEvaluator's `similarity-check` TWICE, because the two modes answer
different questions and one alone answers the wrong one:

  description mode  embeds `name: description` — the frontmatter only.
                    High score = the two skills compete for the same QUERIES.
                    That is a trigger problem, not duplicated content.
  --full-body       embeds the whole SKILL.md in 512-token chunks, averaged.
                    High score = the two skills may duplicate MATERIAL.

The cross-tab is the deliverable:

  body high, desc low   duplicated material the descriptions do not advertise
  desc high, body low   competing triggers over different content -> trigger mode
  both high             genuine siblings: merge candidates, or a deliberate suite

READ THE RANKING, NOT THE BANDS. SkillEvaluator's 0.95/0.90/0.75 classification
was calibrated on another model and another corpus. Measured here on 68 skills
with bge-m3, the MEDIAN full-body pair scored 0.789 — already above the
`SIMILAR` threshold — so a `--full-body --threshold 0.75` run aborts with
"Similarity match limit exceeded". This script therefore saves the vectors once
and does its own scoring locally, reporting z-scores against the fleet's own
distribution instead of absolute bands.

It also prints a lexical-overlap column as a reality check. Average-pooling a
long document washes out specifics, so full-body similarity partly measures
document *register* rather than subject: two unrelated 400-line operator guides
score high simply for both being long operator guides. Measured correlation
between full-body cosine and lexical Jaccard was 0.515 — the top of the ranking
is real, the mid-range is contaminated. A pair with a high body score and a low
lexical score is a register artifact, not a finding.

Configuration comes from the environment ONLY — there are no defaults naming a
host, and none should ever be added:

    SKILL_EVAL_LLM_PROVIDER=openai-compatible
    SKILL_EVAL_LLM_BASE_URL=<your OpenAI-compatible /v1 endpoint>
    SKILL_EVAL_LLM_API_KEY=<key>
    SKILL_EVAL_EMBEDDING_MODEL=<model id>       # required; key and URL fall back
    SKILL_EVAL_EMBEDDING_PROVIDER=openai-compatible

Requires the tier2 extra:
    uv tool install --python 3.13 --force \\
        "skillevaluator[tier2] @ git+https://github.com/NVIDIA/SkillEvaluator.git"

Skill content leaves the process: description mode sends each `name:
description`, --full-body sends every SKILL.md in chunks. Point it at an
endpoint you control. Catalogs hold vectors, paths, and an endpoint
fingerprint — they are written to a scratch dir and deleted unless --keep.

Usage:
    overlap-scan.py --root .claude/skills
    overlap-scan.py --root .claude/skills --top 25
    overlap-scan.py --keep-catalogs DIR    # reuse vectors, skip re-embedding
    overlap-scan.py --from-catalogs DIR    # score offline, no API calls
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import re
import shutil
import statistics as st
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED_ENV = ("SKILL_EVAL_EMBEDDING_MODEL",)
# High enough that find_duplicates returns almost nothing: we only want the
# catalog side effect. The reporting threshold does not affect the vectors, and
# a low one trips the 1000-match cap on any real fleet.
CATALOG_THRESHOLD = "0.99"
# Below this, no pair can reach +2 sigma and every quadrant renders empty.
MIN_PAIRS_FOR_Z = 30
WORD = re.compile(r"[a-z][a-z0-9_.-]{3,}")


def run_catalog(root: Path, out: Path, full_body: bool) -> None:
    """Embed every skill once and persist the vectors."""
    cmd = [
        "skillevaluator", "similarity-check", str(root),
        "--type", "skill",
        "--threshold", CATALOG_THRESHOLD,
        "--save-catalog", str(out),
        "-r", "cli",
    ]  # fmt: skip
    if full_body:
        cmd.append("--full-body")
    mode = "full-body" if full_body else "description"
    print(f"  embedding ({mode}) ...", file=sys.stderr, flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if not out.is_file():
        # Fail closed: no catalog means no measurement, not an empty result.
        tail = (proc.stderr or proc.stdout or "")[-500:]
        raise SystemExit(f"error: no catalog written for {mode} mode.\n{tail}")


def load_catalog(path: Path) -> dict[str, list[float]]:
    data = json.loads(path.read_text())
    return {e["name"]: e["embedding"] for e in data["entries"]}


def cosine(a: list[float], b: list[float]) -> float:
    na = math.sqrt(math.fsum(x * x for x in a))
    nb = math.sqrt(math.fsum(x * x for x in b))
    if not na or not nb:
        return 0.0
    return math.fsum((x / na) * (y / nb) for x, y in zip(a, b, strict=True))


def lexical(root: Path, name: str, cache: dict[str, set[str]]) -> set[str]:
    """Rare-ish word set for a skill's SKILL.md, for the reality-check column."""
    if name not in cache:
        path = root / name / "SKILL.md"
        text = path.read_text(errors="ignore").lower() if path.is_file() else ""
        cache[name] = set(WORD.findall(text))
    return cache[name]


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def zscores(values: list[float]) -> tuple[float, float]:
    return st.mean(values), (st.pstdev(values) or 1e-9)


def main() -> int:
    ap = argparse.ArgumentParser(description="Cross-mode skill overlap scan.")
    ap.add_argument("--root", type=Path, default=Path(".claude/skills"))
    ap.add_argument("--top", type=int, default=15, help="rows per section")
    ap.add_argument(
        "--keep-catalogs", type=Path, help="write catalogs here and keep them"
    )
    ap.add_argument(
        "--from-catalogs", type=Path, help="score existing catalogs, no API calls"
    )
    ap.add_argument(
        "--env-file",
        type=Path,
        help="KEY=VALUE file with the endpoint config; keeps the key out of shell history",
    )
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    if args.env_file:
        # Existing environment wins, so an explicit export can still override.
        for line in args.env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))

    root = args.root.resolve()
    if not root.is_dir():
        print(f"no such directory: {root}", file=sys.stderr)
        return 2

    tmp: str | None = None
    if args.from_catalogs:
        cat_dir = args.from_catalogs
    elif args.keep_catalogs:
        cat_dir = args.keep_catalogs
        cat_dir.mkdir(parents=True, exist_ok=True)
    else:
        tmp = tempfile.mkdtemp(prefix="overlap-scan-")
        cat_dir = Path(tmp)

    desc_path, full_path = cat_dir / "cat-desc.json", cat_dir / "cat-full.json"
    try:
        if not args.from_catalogs:
            if not shutil.which("skillevaluator"):
                print(
                    "skillevaluator not on PATH — install the tier2 extra.",
                    file=sys.stderr,
                )
                return 2
            missing = [v for v in REQUIRED_ENV if not os.environ.get(v)]
            if missing:
                print(
                    f"unset: {', '.join(missing)} (see the module docstring)",
                    file=sys.stderr,
                )
                return 2
            run_catalog(root, desc_path, full_body=False)
            run_catalog(root, full_path, full_body=True)
        for p in (desc_path, full_path):
            if not p.is_file():
                print(f"missing catalog: {p}", file=sys.stderr)
                return 2

        desc, full = load_catalog(desc_path), load_catalog(full_path)
        names = sorted(set(desc) & set(full))
        if len(names) < 2:
            print("need at least two skills to compare", file=sys.stderr)
            return 2

        cache: dict[str, set[str]] = {}
        pairs = []
        for a, b in itertools.combinations(names, 2):
            pairs.append(
                {
                    "a": a,
                    "b": b,
                    "desc": cosine(desc[a], desc[b]),
                    "body": cosine(full[a], full[b]),
                    "lex": jaccard(lexical(root, a, cache), lexical(root, b, cache)),
                }
            )
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    dm, dsd = zscores([p["desc"] for p in pairs])
    fm, fsd = zscores([p["body"] for p in pairs])
    for p in pairs:
        p["desc_z"] = (p["desc"] - dm) / dsd
        p["body_z"] = (p["body"] - fm) / fsd

    if args.as_json:
        print(
            json.dumps(
                {
                    "skills": len(names),
                    "pairs": pairs,
                    "calibration": {
                        "desc_mean": dm,
                        "desc_sd": dsd,
                        "body_mean": fm,
                        "body_sd": fsd,
                    },
                },
                indent=2,
            )
        )
        return 0

    print(f"\n{len(names)} skills · {len(pairs)} pairs")
    # A z-score cannot exceed sqrt(n-1)/... for tiny n: with 6 pairs nothing can
    # reach +2 and every section renders empty, which reads as "no overlap
    # found" when the truth is "this fleet is too small to rank". Say so, and
    # show the raw ranking instead of three empty tables.
    if len(pairs) < MIN_PAIRS_FOR_Z:
        print(
            f"\nToo few pairs ({len(pairs)}) for z-scoring — no pair can reach +2σ,\n"
            f"so the quadrant tables below would be empty by construction, not by\n"
            f"evidence. Showing the raw ranking; re-run over {MIN_PAIRS_FOR_Z}+ pairs "
            "(~10+ skills) to rank.\n"
        )
        print(f"    {'body':>6} {'desc':>6} {'lex':>6}   pair")
        for p in sorted(pairs, key=lambda p: -p["body"])[: args.top]:
            print(
                f"    {p['body']:.3f}  {p['desc']:.3f}  {p['lex']:.3f}   {p['a']} ~ {p['b']}"
            )
        return 0
    print(
        f"calibration: description mean {dm:.3f} (sd {dsd:.3f}) · "
        f"full-body mean {fm:.3f} (sd {fsd:.3f})"
    )
    if fm >= 0.75:
        print(
            "note: the MEDIAN full-body pair already exceeds SkillEvaluator's "
            "SIMILAR band.\n      Read the ranking and the z-scores; the absolute "
            "bands do not apply here."
        )

    siblings = [p for p in pairs if p["desc_z"] >= 2 and p["body_z"] >= 2]
    dm_lex = st.mean([p["lex"] for p in pairs])
    # Pairs that agree on BOTH axes are the closest thing to a known-good set,
    # so their lexical overlap is the reference for "actually shares material".
    # Anchoring to the all-pairs mean instead would set the bar at the noise
    # floor and the flag would never fire on the artifacts it exists to catch.
    lex_ref = st.mean([p["lex"] for p in siblings]) if siblings else dm_lex

    def table(title: str, note: str, rows: list[dict]) -> None:
        print(f"\n=== {title} ===\n    {note}\n")
        print(f"    {'body':>6} {'desc':>6} {'lex':>6}   pair")
        for p in rows[: args.top]:
            flag = "  <- register, not content" if p["lex"] < lex_ref / 2 else ""
            print(
                f"    {p['body']:.3f}  {p['desc']:.3f}  {p['lex']:.3f}   "
                f"{p['a']} ~ {p['b']}{flag}"
            )
        if not rows:
            print("    (none)")

    table(
        "BOTH HIGH — genuine siblings",
        "merge candidates, or a deliberate suite. Confirm before acting.",
        sorted(
            [p for p in pairs if p["desc_z"] >= 2 and p["body_z"] >= 2],
            key=lambda p: -(p["desc_z"] + p["body_z"]),
        ),
    )
    table(
        "CONTENT overlap without trigger overlap",
        "duplicated material the descriptions do not advertise -> Dim 10 / dedup.",
        sorted(
            [p for p in pairs if p["body_z"] >= 2 and p["desc_z"] < 1],
            key=lambda p: -(p["body_z"] - p["desc_z"]),
        ),
    )
    table(
        "TRIGGER overlap without content overlap",
        "competing for the same queries while teaching different things -> trigger mode.",
        sorted(
            [p for p in pairs if p["desc_z"] >= 1.5 and p["body_z"] < 1],
            key=lambda p: -(p["desc_z"] - p["body_z"]),
        ),
    )
    print(
        f"\nlexical Jaccard mean {dm_lex:.3f} — a high body score with a low "
        "lexical score is\nshared document register, not shared content. "
        "Verify a pair by reading it."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
