#!/usr/bin/env python3
"""Measure what a bare model already knows about a skill's subject.

Whatever the model knows unaided does not need to be in the skill. As the
bleeding edge is absorbed into training, a skill should shrink to the delta.
This probe finds that delta, per model and per effort level.

The skill is its own answer key: it already asserts dated, sourced facts, so
each claim is extracted once, then put to a BARE model -- no skills loaded, no
tools, no web -- and the answer is bucketed against what the skill says:

  KNOWS     model states the skill's claim correctly    -> deletion candidate
  UNKNOWN   model does not know, or hedges              -> keep, real transfer
  CONFLICTS model confidently states something else     -> keep, and strengthen

CONFLICTS is the valuable bucket. Filling a blank is worth something; overriding
a confident wrong answer is worth far more, because unaided the model does not
hesitate -- it proceeds, wrong.

Two limits are built in and must stay:

  1. Recall is not application. A model can state a flag correctly and still not
     think to use it mid-task. KNOWS is a deletion CANDIDATE; confirm with an
     eval delta before cutting.
  2. A conflict never means the skill is wrong. Skills here are freshened past
     the model cutoff, so the skill is presumed correct and the model is
     presumed stale. The grader is instructed accordingly. Without that, this
     probe silently becomes a downgrade machine.

Usage:
    knowledge-floor.py --skill keda --extract          # build the claim set
    knowledge-floor.py --skill keda                    # probe, default matrix
    knowledge-floor.py --skill keda --models sonnet,opus --efforts low,high
    knowledge-floor.py --skill keda --json

Claims cache to <skill>/references/knowledge-claims.json so probes are cheap,
repeatable, and comparable across model releases. Re-extract when the skill
changes materially; the cache records the SKILL.md hash it was built from.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

DENY = [
    "Bash", "Edit", "Write", "NotebookEdit", "Agent", "Task",
    "WebFetch", "WebSearch", "Read", "Glob", "Grep", "Skill",
]  # fmt: skip

BUCKETS = ("KNOWS", "UNKNOWN", "CONFLICTS")


def search_roots() -> list[Path]:
    """Every `.claude/skills` from the cwd upward, then the profile one.

    Running from inside a skill's own `scripts/` is normal, so walking up
    matters -- a bare `Path.cwd()/".claude"/"skills"` only resolves when the
    caller happens to stand at a repo root.
    """
    roots = []
    for d in [Path.cwd(), *Path.cwd().parents]:
        c = d / ".claude" / "skills"
        if c.is_dir():
            roots.append(c)
    profile = Path.home() / ".claude" / "skills"
    if profile.is_dir() and profile not in roots:
        roots.append(profile)
    return roots


EXTRACT_PROMPT = """\
Read this SKILL.md and extract up to {n} atomic factual claims that a model \
would need to KNOW to do this work -- version floors, flag names, defaults, \
dates, API shapes, hard thresholds, named failure modes.

Rules:
- Each claim must be checkable and have one short answer.
- Ask about the SUBJECT, never about the skill document. Bad: "what does this \
skill recommend". Good: "what is the minimum KEDA version for X".
- Skip anything site-specific, opinion, or workflow instruction.
- Prefer claims that would be wrong if the model's knowledge were a year old.

Return ONLY a JSON array, no prose, no fences:
[{{"question": "<question, one sentence>", "skill_answer": "<the skill's \
answer, under 20 words>"}}]

SKILL.md follows.
---
{body}
"""

PROBE_PROMPT = """\
Answer from your own knowledge only. You have no tools and no documents.

{question}

Answer in one short sentence. If you do not know, or are not reasonably \
confident, reply with exactly: I DO NOT KNOW\
"""

GRADE_PROMPT = """\
You are grading whether a model already knows facts that a reference document \
asserts.

CRITICAL: the reference is presumed CORRECT. It is maintained and re-verified \
continuously, often past the model's training cutoff. When the model's answer \
disagrees, that is the MODEL being stale -- never evidence the reference is \
wrong. Never grade the reference.

For each item, choose one bucket:
- KNOWS: the model's answer matches the reference in substance. Wording, \
formatting, and extra detail do not matter. Close-but-vaguer still counts if \
it would lead to the same action.
- UNKNOWN: the model said it does not know, hedged, refused, or answered \
something unrelated.
- CONFLICTS: the model gave a confident, specific answer that contradicts the \
reference.

Return ONLY a JSON array, no prose, no fences, one object per item, in order:
[{{"id": <id>, "bucket": "KNOWS|UNKNOWN|CONFLICTS", "why": "<under 15 words>"}}]

Items:
{items}
"""


# --------------------------------------------------------------------------
# claude -p plumbing
# --------------------------------------------------------------------------


_PROBE_HOME: Path | None = None


def _probe_home() -> str:
    """One temp project reused by every probe in this process.

    A fresh TemporaryDirectory per call looked tidy and was not: Claude Code
    derives a project directory under ~/.claude/projects from the cwd, so a
    per-call temp dir leaves one junk project dir per probe -- hundreds in a
    fleet pass. One dir per process keeps the isolation (still empty, still no
    discoverable skills) and leaves one.
    """
    global _PROBE_HOME
    if _PROBE_HOME is None:
        _PROBE_HOME = Path(tempfile.mkdtemp(prefix="kfloor-"))
    return str(_PROBE_HOME)


def run_claude(
    prompt: str, *, model: str | None = None, effort: str | None = None, timeout: int
) -> tuple[str, float, bool]:
    """Run one hermetic `claude -p`. Returns (text, cost_usd, ok).

    Hermetic means: an empty temp project so no skills are discoverable, and
    every tool denied so the answer is parametric knowledge rather than
    lookup. Deny rules beat any allow-list in the user's settings, so this
    holds regardless of host configuration.
    """
    work = _probe_home()
    if True:
        cmd = ["claude", "-p", prompt, "--output-format", "json",
               "--setting-sources", "project"]  # fmt: skip
        if model:
            cmd += ["--model", model]
        if effort:
            cmd += ["--effort", effort]
        cmd += ["--disallowedTools", *DENY]  # variadic: keep last

        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        try:
            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=work,
                env=env,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return ("", 0.0, False)
        if p.returncode != 0:
            return ("", 0.0, False)
        try:
            d = json.loads(p.stdout)
        except json.JSONDecodeError:
            return ("", 0.0, False)
        if d.get("is_error"):
            return ("", float(d.get("total_cost_usd") or 0), False)
        return (
            str(d.get("result") or ""),
            float(d.get("total_cost_usd") or 0),
            True,
        )


def parse_json_array(text: str):
    """Models fence JSON despite instructions. Recover the array."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.MULTILINE).strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j == -1:
        return None
    try:
        return json.loads(t[i : j + 1])
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------
# skill + claims
# --------------------------------------------------------------------------


def find_skill(name: str) -> Path:
    p = Path(name)
    if p.is_dir() and (p / "SKILL.md").is_file():
        return p.resolve()
    if p.is_file() and p.name == "SKILL.md":
        return p.parent.resolve()
    roots = search_roots()
    for root in roots:
        cand = root / name
        if (cand / "SKILL.md").is_file():
            return cand.resolve()
    sys.exit(f"knowledge-floor: no skill '{name}' in {[str(r) for r in roots]}")


def claims_path(skill: Path) -> Path:
    return skill / "references" / "knowledge-claims.json"


def skill_hash(skill: Path) -> str:
    return hashlib.sha256((skill / "SKILL.md").read_bytes()).hexdigest()[:12]


def extract_claims(skill: Path, n: int, model: str | None, timeout: int) -> dict:
    body = (skill / "SKILL.md").read_text()
    text, cost, ok = run_claude(
        EXTRACT_PROMPT.format(n=n, body=body), model=model, timeout=timeout
    )
    if not ok:
        sys.exit("knowledge-floor: extraction call failed")
    arr = parse_json_array(text)
    if not arr:
        sys.exit(f"knowledge-floor: extractor returned no JSON array:\n{text[:400]}")
    claims = [
        {
            "id": i,
            "question": str(c.get("question", "")).strip(),
            "skill_answer": str(c.get("skill_answer", "")).strip(),
        }
        for i, c in enumerate(arr)
        if c.get("question") and c.get("skill_answer")
    ]
    doc = {
        "skill": skill.name,
        "extracted": date.today().isoformat(),
        "extractor_model": model or "session-default",
        "skill_md_sha": skill_hash(skill),
        "extraction_cost_usd": round(cost, 4),
        "claims": claims,
    }
    path = claims_path(skill)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n")
    return doc


def load_claims(skill: Path) -> dict | None:
    p = claims_path(skill)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


# --------------------------------------------------------------------------
# probe + grade
# --------------------------------------------------------------------------


def probe_cell(claims, model, effort, timeout, workers):
    """Probe every claim once for one (model, effort) cell."""
    answers: dict[int, str] = {}
    cost = 0.0
    failures = 0

    def one(c):
        return c["id"], run_claude(
            PROBE_PROMPT.format(question=c["question"]),
            model=model,
            effort=effort,
            timeout=timeout,
        )

    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for cid, (text, c, ok) in ex.map(one, claims):
            cost += c
            if ok:
                answers[cid] = text.strip()
            else:
                failures += 1
    return answers, cost, failures


def grade(claims, answers, grader_model, timeout, chunk=10):
    """Bucket each answer against the skill's claim. Batched to keep it cheap."""
    by_id = {c["id"]: c for c in claims}
    out: dict[int, dict] = {}
    cost = 0.0
    todo = [cid for cid in answers]

    for k in range(0, len(todo), chunk):
        batch = todo[k : k + chunk]
        items = "\n\n".join(
            f"id: {cid}\nquestion: {by_id[cid]['question']}\n"
            f"reference answer: {by_id[cid]['skill_answer']}\n"
            f"model answer: {answers[cid]}"
            for cid in batch
        )
        text, c, ok = run_claude(
            GRADE_PROMPT.format(items=items), model=grader_model, timeout=timeout
        )
        cost += c
        arr = parse_json_array(text) if ok else None
        if not arr:
            for cid in batch:
                out[cid] = {"bucket": "UNGRADED", "why": "grader failed"}
            continue
        seen = set()
        for r in arr:
            cid = r.get("id")
            if cid in by_id and r.get("bucket") in BUCKETS:
                out[cid] = {"bucket": r["bucket"], "why": str(r.get("why", ""))[:60]}
                seen.add(cid)
        for cid in batch:
            out.setdefault(cid, {"bucket": "UNGRADED", "why": "missing from grader"})
    return out, cost


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--skill", required=True, help="skill name, dir, or SKILL.md path")
    ap.add_argument("--extract", action="store_true", help="(re)build the claim set")
    ap.add_argument("--max-claims", type=int, default=20)
    ap.add_argument("--models", default="haiku,sonnet,opus")
    ap.add_argument("--efforts", default="", help="comma list, e.g. low,high")
    ap.add_argument("--grader-model", default="sonnet")
    ap.add_argument("--extractor-model", default=None)
    ap.add_argument("--timeout", type=int, default=180)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    skill = find_skill(args.skill)
    doc = load_claims(skill)

    if args.extract or doc is None:
        if doc is None and not args.extract:
            print(
                f"no claim set yet — extracting up to {args.max_claims}",
                file=sys.stderr,
            )
        doc = extract_claims(skill, args.max_claims, args.extractor_model, args.timeout)
        print(
            f"extracted {len(doc['claims'])} claims -> "
            f"{claims_path(skill).relative_to(skill.parent)} "
            f"(${doc['extraction_cost_usd']:.3f})",
            file=sys.stderr,
        )
    elif doc.get("skill_md_sha") != skill_hash(skill):
        print(
            "warning: SKILL.md changed since claims were extracted "
            f"({doc.get('extracted')}). Re-run with --extract to refresh.",
            file=sys.stderr,
        )

    claims = doc["claims"]
    if not claims:
        sys.exit("knowledge-floor: claim set is empty")

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    efforts = [e.strip() for e in args.efforts.split(",") if e.strip()] or [None]

    results, total_cost = {}, 0.0
    for model in models:
        for effort in efforts:
            label = f"{model}/{effort}" if effort else model
            print(f"probing {label} ({len(claims)} claims)…", file=sys.stderr)
            answers, pcost, fails = probe_cell(
                claims, model, effort, args.timeout, args.workers
            )
            graded, gcost = grade(claims, answers, args.grader_model, args.timeout)
            total_cost += pcost + gcost
            results[label] = {
                "buckets": {
                    b: [c for c, g in graded.items() if g["bucket"] == b]
                    for b in (*BUCKETS, "UNGRADED")
                },
                "detail": graded,
                "answers": answers,
                "probe_cost_usd": round(pcost, 4),
                "grade_cost_usd": round(gcost, 4),
                "failures": fails,
            }

    if args.json:
        print(
            json.dumps(
                {
                    "skill": skill.name,
                    "claims": claims,
                    "extracted": doc.get("extracted"),
                    "total_cost_usd": round(total_cost, 4),
                    "cells": results,
                },
                indent=2,
            )
        )
        return

    n = len(claims)
    print(
        f"\nKnowledge floor — {skill.name}   {n} claims"
        f"   (extracted {doc.get('extracted')})\n"
    )
    print(f"{'model/effort':22}{'KNOWS':>8}{'UNKNOWN':>10}{'CONFLICTS':>11}{'cost':>9}")
    print("-" * 60)
    for label, r in results.items():
        b = r["buckets"]
        cost = r["probe_cost_usd"] + r["grade_cost_usd"]
        print(
            f"{label:22}{len(b['KNOWS']):>8}{len(b['UNKNOWN']):>10}"
            f"{len(b['CONFLICTS']):>11}{'$' + format(cost, '.2f'):>9}"
        )
        if b["UNGRADED"] or r["failures"]:
            print(
                f"{'':22}  ({len(b['UNGRADED'])} ungraded, {r['failures']} probe failures)"
            )

    by_id = {c["id"]: c for c in claims}
    for label, r in results.items():
        conf = r["buckets"]["CONFLICTS"]
        if not conf:
            continue
        print(
            f"\nCONFLICTS on {label} — the skill is overriding a confident wrong prior:"
        )
        for cid in conf:
            print(f"  · {by_id[cid]['question']}")
            print(f"      skill: {by_id[cid]['skill_answer']}")
            print(f"      model: {r['answers'].get(cid, '')[:110]}")

    strongest = list(results)[-1]
    known = results[strongest]["buckets"]["KNOWS"]
    if known:
        print(f"\nDeletion CANDIDATES ({len(known)}/{n} already known by {strongest}):")
        for cid in known:
            print(f"  · {by_id[cid]['question']}")
        print("\nCandidates only. Recall is not application — a model can state a fact")
        print("and still not think to use it mid-task. Confirm with an eval delta")
        print("before cutting anything.")

    print(f"\ntotal ${total_cost:.2f}\n")


if __name__ == "__main__":
    main()
