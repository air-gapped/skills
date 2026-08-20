#!/usr/bin/env python3
"""Run intra-skill dedup across a fleet, resumably, and rank what it finds.

`skillevaluator context-optimization-check` answers one skill at a time and
keeps nothing: every run re-embeds and re-classifies from scratch. Over ~100
skills that is an hour of API calls to re-learn what did not change. This drives
it across a fleet, writes each result the moment it lands, and skips skills whose
content has not changed since their last verdict.

What the verdicts mean (quality-rubric / improvement-patterns Pattern 6.1):

    DUPLICATE             repeats with nothing added        -> consolidate
    INTENTIONAL_DETAIL    overview here, development there  -> KEEP
    RELATED_BUT_DISTINCT  same topic, different purpose     -> KEEP

Only the first is actionable. Two of three verdicts existing is the whole point:
a similarity score alone would flag all of them, and deleting on that basis
destroys progressive disclosure.

Results cache in ${XDG_CACHE_HOME:-~/.cache}/skillevaluator/dedup/ — never in
the repo. The cache key is the skill's content hash PLUS the model and endpoint
that produced the verdicts, because a verdict is only valid for the model that
made it. Switching gateways re-runs everything rather than serving stale calls:
the same `bge-m3` scored an unrelated pair 0.4014 through one gateway and 0.4375
through another.

Skills the tool refuses are reported as SKIPPED with the reason rather than
failing the run. The bound is `n*(n-1)/2 * vector_dimension <= 25_000_000`, so
at bge-m3's 1024 dims it refuses above ~221 chunks — `skill-improver` needs 100M
against that 25M budget at 444 chunks. It is a resource guard on untrusted
input, not a quality judgement: the cosine is deliberately pure stdlib, so 25M
float operations is seconds and 200M would be minutes.

Config comes from an env file (see --env-file); both the chat and embedding
roles are required. Skill content leaves the machine for both.

Usage:
    dedup-fleet.py --env-file ~/.config/skillevaluator/env
    dedup-fleet.py --env-file ... --root .claude/skills --workers 4
    dedup-fleet.py --report            # re-print from cache, no API calls
    dedup-fleet.py --redo              # ignore cache, re-run everything
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

VERDICT_RE = re.compile(r"Verdict:\s*([A-Z_]+)")
CHUNKS_RE = re.compile(r"Extracted\s+(\d+)\s+chunk")
TOO_BIG_RE = re.compile(r"scalar comparison work exceeds", re.I)
VERDICTS = ("DUPLICATE", "INTENTIONAL_DETAIL", "RELATED_BUT_DISTINCT")
# A duplicate share computed over 1-2 clusters is arithmetic, not evidence.
MIN_CLUSTERS_FOR_SHARE = 5
# Three members of a name family repeating means shared material, not coincidence.
FAMILY_MIN = 3


def cache_root() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "skillevaluator" / "dedup"


def load_env(path: Path) -> None:
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if value:  # a blank value must not mask a real environment variable
            os.environ.setdefault(key.strip(), value)


def config_fingerprint() -> str:
    """Identity of the pipeline that produces a verdict.

    A cached verdict is only meaningful for the model and endpoint that made it,
    so both belong in the key alongside the content hash.
    """
    parts = [
        os.environ.get("SKILL_EVAL_LLM_MODEL", ""),
        os.environ.get("SKILL_EVAL_EMBEDDING_MODEL", ""),
        os.environ.get("SKILL_EVAL_EMBEDDING_BASE_URL")
        or os.environ.get("SKILL_EVAL_LLM_BASE_URL", ""),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]


def content_hash(skill: Path) -> str:
    """Hash of everything the checker reads, so unchanged skills are skipped."""
    h = hashlib.sha256()
    for f in sorted(skill.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in (".md", ".py", ".sh"):
            continue
        if any(p in {"evals", "results", "__pycache__", ".git"} for p in f.parts):
            continue
        h.update(str(f.relative_to(skill)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def run_one(skill: Path) -> dict:
    proc = subprocess.run(
        ["skillevaluator", "context-optimization-check", str(skill), "-r", "cli"],
        capture_output=True,
        text=True,
        check=False,
    )
    blob = (proc.stdout or "") + (proc.stderr or "")
    chunks = CHUNKS_RE.search(blob)
    row = {
        "skill": skill.name,
        "chunks": int(chunks.group(1)) if chunks else None,
        "verdicts": {v: 0 for v in VERDICTS},
        "status": "ok",
    }
    if TOO_BIG_RE.search(blob):
        # Not a failure of the skill: the tool refuses when
        # n*(n-1)/2 * dim exceeds 25M (~221 chunks at 1024 dims).
        row["status"] = "skipped-too-large"
        return row
    found = VERDICT_RE.findall(blob)
    for v in found:
        if v in row["verdicts"]:
            row["verdicts"][v] += 1
    if not found and proc.returncode != 0:
        row["status"] = "error"
        row["error"] = (
            blob.strip().splitlines()[-1][:200] if blob.strip() else "no output"
        )
    row["clusters"] = sum(row["verdicts"].values())
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description="Fleet-wide intra-skill dedup.")
    ap.add_argument("--root", type=Path, default=Path(".claude/skills"))
    ap.add_argument("--env-file", type=Path)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument(
        "--report", action="store_true", help="print from cache, no API calls"
    )
    ap.add_argument("--redo", action="store_true", help="ignore cache")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    if args.env_file:
        load_env(args.env_file)

    skills = [p.parent for p in sorted(args.root.rglob("SKILL.md"))]
    if not skills:
        print(f"no skills under {args.root}", file=sys.stderr)
        return 2

    fp = config_fingerprint()
    cdir = cache_root() / fp
    cdir.mkdir(parents=True, exist_ok=True)

    todo, rows = [], []
    for skill in skills:
        chash = content_hash(skill)
        cached = cdir / f"{skill.name}.{chash}.json"
        if cached.is_file() and not args.redo:
            rows.append(json.loads(cached.read_text()))
        elif args.report:
            rows.append(
                {
                    "skill": skill.name,
                    "status": "not-cached",
                    "verdicts": {v: 0 for v in VERDICTS},
                    "clusters": 0,
                    "chunks": None,
                }
            )
        else:
            todo.append((skill, cached))

    if todo and not args.report:
        if not shutil.which("skillevaluator"):
            print("skillevaluator not on PATH (needs the tier2 extra)", file=sys.stderr)
            return 2
        if not os.environ.get("SKILL_EVAL_EMBEDDING_MODEL"):
            print("SKILL_EVAL_EMBEDDING_MODEL unset — pass --env-file", file=sys.stderr)
            return 2
        print(
            f"  {len(rows)} cached, {len(todo)} to run "
            f"(chat {os.environ.get('SKILL_EVAL_LLM_MODEL')}, "
            f"embed {os.environ.get('SKILL_EVAL_EMBEDDING_MODEL')})",
            file=sys.stderr,
        )
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(run_one, s): (s, c) for s, c in todo}
            for fut in as_completed(futs):
                skill, cached = futs[fut]
                try:
                    row = fut.result()
                except Exception as exc:  # keep the fleet moving
                    row = {
                        "skill": skill.name,
                        "status": "error",
                        "error": str(exc)[:200],
                        "verdicts": {v: 0 for v in VERDICTS},
                        "clusters": 0,
                        "chunks": None,
                    }
                # Write on arrival so a killed run keeps everything finished.
                cached.write_text(json.dumps(row, indent=1))
                rows.append(row)
                done += 1
                print(
                    f"\r  {done}/{len(todo)} {skill.name[:38]:38}",
                    end="",
                    file=sys.stderr,
                )
        print(file=sys.stderr)

    if args.as_json:
        print(json.dumps({"config": fp, "rows": rows}, indent=2))
        return 0

    # An unmatched cache reads as a clean fleet unless this is said out loud.
    # --report with different (or missing) provider config looks in a different
    # key and finds nothing; reporting that as "no duplicates" is the same
    # fail-open as coercing a missing measurement to zero.
    uncached = [r for r in rows if r.get("status") == "not-cached"]
    if uncached and len(uncached) == len(rows):
        print(
            f"\nNOTHING CACHED for this provider config ({fp}) — {len(rows)} skill(s)"
            " unmeasured.\nThis is not a clean fleet. --report needs the same"
            " --env-file the run used;\nverdicts are keyed by chat model, embedding"
            " model and endpoint.",
            file=sys.stderr,
        )
        return 2

    # Rank by SHARE, not count. A skill with 1 duplicate among 22 clusters is
    # noise; one with 4 among 7 is structurally repetitive. Sorting by raw count
    # buries the second behind large skills that are mostly fine.
    for r in rows:
        v = r["verdicts"]
        r["keep"] = v["INTENTIONAL_DETAIL"] + v["RELATED_BUT_DISTINCT"]
        total = v["DUPLICATE"] + r["keep"]
        r["dup_share"] = (v["DUPLICATE"] / total) if total else None

    dupes = [r for r in rows if r["verdicts"]["DUPLICATE"]]
    # A share needs a denominator to mean anything: 1-of-2 is not "50% duplicated",
    # it is two clusters. Those rank by count and are marked, never by share.
    solid = [
        r
        for r in dupes
        if (r["verdicts"]["DUPLICATE"] + r["keep"]) >= MIN_CLUSTERS_FOR_SHARE
    ]
    thin = [r for r in dupes if r not in solid]
    solid.sort(key=lambda r: -r["dup_share"])
    thin.sort(key=lambda r: -r["verdicts"]["DUPLICATE"])

    print(f"\n{len(rows)} skills · cache {cdir}")
    print(f"\n{'dup':>4} {'keep':>5} {'share':>6} {'chunks':>7}  skill")
    for r in solid:
        print(
            f"{r['verdicts']['DUPLICATE']:>4} {r['keep']:>5} {r['dup_share']:>5.0%} "
            f"{r['chunks'] or '-':>7}  {r['skill']}"
        )
    for r in thin:
        print(
            f"{r['verdicts']['DUPLICATE']:>4} {r['keep']:>5} {'  n/a':>6} "
            f"{r['chunks'] or '-':>7}  {r['skill']}  (under {MIN_CLUSTERS_FOR_SHARE} clusters, share not meaningful)"
        )
    if not dupes:
        print("   none — no DUPLICATE verdict anywhere")

    # Name the families. Repetition concentrated in one prefix is a different
    # problem from repetition scattered across unrelated skills: it means the
    # same material restated per skill, and it is fixed once, not N times.
    fams: dict[str, list] = {}
    for r in dupes:
        prefix = r["skill"].split("-")[0]
        fams.setdefault(prefix, []).append(r)
    hot = {k: v for k, v in fams.items() if len(v) >= FAMILY_MIN}
    if hot:
        print(
            "\nfamilies with repetition in 3+ members (fix the shared material once):"
        )
        for k, v in sorted(hot.items(), key=lambda kv: -len(kv[1])):
            n = sum(x["verdicts"]["DUPLICATE"] for x in v)
            print(f"   {k}-*  {len(v)} skills, {n} duplicate clusters")

    clean = [r for r in rows if r["status"] == "ok" and not r["verdicts"]["DUPLICATE"]]
    kept = sum(
        r["verdicts"]["INTENTIONAL_DETAIL"] + r["verdicts"]["RELATED_BUT_DISTINCT"]
        for r in rows
    )
    skipped = [r for r in rows if r["status"] == "skipped-too-large"]
    errored = [r for r in rows if r["status"] == "error"]
    print(
        f"\n{len(clean)} skill(s) clean · {kept} cluster(s) correctly kept "
        f"(deleting those would destroy progressive disclosure)"
    )
    if skipped:
        print(
            f"{len(skipped)} skipped, over the tool's pairwise-work budget "
            f"(~221 chunks at 1024 dims): "
            f"{', '.join(r['skill'] for r in skipped[:6])}"
        )
    if uncached:
        # Partially-stale reports must say so: these skills changed since their
        # last verdict, so the table below is silent about them rather than
        # clean. Same failure family as an unmatched cache reading as clean.
        print(
            f"{len(uncached)} not measured for current content (changed since "
            f"last run): {', '.join(r['skill'] for r in uncached[:6])}"
        )
    if errored:
        print(f"{len(errored)} errored: {', '.join(r['skill'] for r in errored[:6])}")
    print(
        "\nOnly DUPLICATE is actionable, and it is one model's judgement — read "
        "both sides\nbefore cutting (improvement-patterns.md Pattern 6.1)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
