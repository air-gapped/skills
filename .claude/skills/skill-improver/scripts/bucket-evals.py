#!/usr/bin/env python3
"""Label trigger-eval queries by bucket, and report the fleet's balance.

A trigger corpus of true/false says whether a query should fire the skill, but
not what KIND of query it is — and the kinds fail differently:

    explicit     the user names the skill or its distinctive tokens
    implicit     the user describes the task, never naming the skill
    contextual   the request arrives inside a realistic project scenario,
                 often mid-task, with the real intent implied rather than stated
    negative     should NOT fire

A description tuned on explicit queries passes by keyword match and can still
miss every implicit one — which is what a real user types. Aggregate pass rate
hides that completely: 80% overall reads as healthy whether the misses are
spread evenly or concentrated entirely in one bucket.

Measured on this fleet before any labelling: 121 positives across 14 corpora,
61% of which name the skill or a distinctive token of it. That skew is the
reason for the split.

`should_trigger: false` is `negative` by definition and needs no model. The
three positive buckets are a judgement about phrasing, so they are classified by
the configured chat model, one batched call per skill.

Writes `bucket` back into each entry, in place, preserving everything else.
Existing labels are kept unless --relabel. Files are only rewritten when
something changed.

Usage:
    bucket-evals.py --env-file ~/.config/skillevaluator/env        # label + report
    bucket-evals.py --report                                       # balance only, no calls
    bucket-evals.py --env-file ... --relabel                       # redo positives
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

BUCKETS = ("explicit", "implicit", "contextual", "negative")
POSITIVE_BUCKETS = ("explicit", "implicit", "contextual")

# What a healthy corpus looks like. Not a hard gate: contextual is the one that
# matters most and is the hardest to write, so it is called out when thin rather
# than enforced.
TARGET = {"explicit": 0.20, "implicit": 0.30, "contextual": 0.20, "negative": 0.30}
MIN_CONTEXTUAL_SHARE = 0.10
# Reasoning models spend tokens before the array; 2000 truncated 8 of 14 corpora.
MAX_TOKENS = 8000

PROMPT = """Classify each user query by how it refers to the skill "{skill}".

Skill purpose: {purpose}

Buckets:
- explicit: names the skill, its command, or a distinctive token of its name
- implicit: describes the task in the user's own words, never naming the skill
- contextual: arrives inside a realistic working scenario — mentions a concrete
  file, error, tool output, or mid-task situation — with the need implied

Return ONLY a JSON array, one object per query, in the same order:
[{{"i": 0, "bucket": "explicit"}}, ...]

Queries:
{queries}"""


def load_env(path: Path) -> None:
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("'\"")
        if value:
            os.environ.setdefault(key.strip(), value)


def chat(prompt: str) -> str | None:
    try:
        from openai import OpenAI
    except ImportError:
        print("openai package missing (needs the tier2 extra)", file=sys.stderr)
        return None
    try:
        client = OpenAI(
            api_key=os.environ["SKILL_EVAL_LLM_API_KEY"],
            base_url=os.environ["SKILL_EVAL_LLM_BASE_URL"],
            max_retries=1,
        )
        r = client.chat.completions.create(
            model=os.environ["SKILL_EVAL_LLM_MODEL"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=MAX_TOKENS,
        )
        choice = r.choices[0]
        # A truncated reply parses as "no labels" and would otherwise be
        # indistinguishable from a model that declined. Say which it was.
        if choice.finish_reason == "length":
            print(
                f"  reply hit the {MAX_TOKENS}-token cap (finish_reason=length) — "
                "raise MAX_TOKENS; the JSON was cut off mid-array",
                file=sys.stderr,
            )
        return choice.message.content
    except Exception as exc:
        print(f"  chat failed: {str(exc)[:120]}", file=sys.stderr)
        return None


def parse_array(text: str):
    t = (text or "").strip()
    i, j = t.find("["), t.rfind("]")
    if i == -1 or j == -1:
        return None
    try:
        return json.loads(t[i : j + 1])
    except json.JSONDecodeError:
        return None


def purpose_of(skill_dir: Path) -> str:
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return skill_dir.name
    text = md.read_text(errors="replace")[:4000]
    for line in text.splitlines():
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip("'\"|>-").strip()[:300]
    return skill_dir.name


def label_file(path: Path, relabel: bool, dry: bool) -> tuple[int, int]:
    """Return (labelled_now, already_labelled)."""
    entries = json.loads(path.read_text())
    if not isinstance(entries, list):
        return 0, 0
    skill_dir = path.parent.parent
    todo, already = [], 0
    for idx, e in enumerate(entries):
        if not e.get("should_trigger"):
            if e.get("bucket") != "negative":
                e["bucket"] = "negative"  # definitional, never a model call
            continue
        if e.get("bucket") in POSITIVE_BUCKETS and not relabel:
            already += 1
            continue
        todo.append((idx, e.get("query", "")))

    labelled = 0
    if todo and not dry:
        listing = "\n".join(f"{i}. {q}" for i, (_, q) in enumerate(todo))
        out = parse_array(
            chat(
                PROMPT.format(
                    skill=skill_dir.name, purpose=purpose_of(skill_dir), queries=listing
                )
            )
            or ""
        )
        if out:
            for item in out:
                try:
                    k = int(item["i"])
                    bucket = str(item["bucket"]).strip().lower()
                except (KeyError, ValueError, TypeError):
                    continue
                if 0 <= k < len(todo) and bucket in POSITIVE_BUCKETS:
                    entries[todo[k][0]]["bucket"] = bucket
                    labelled += 1
    if not dry:
        path.write_text(json.dumps(entries, indent=2) + "\n")
    return labelled, already


def main() -> int:
    ap = argparse.ArgumentParser(description="Bucket trigger-eval corpora.")
    ap.add_argument("--root", type=Path, default=Path(".claude/skills"))
    ap.add_argument("--env-file", type=Path)
    ap.add_argument(
        "--report", action="store_true", help="balance only, no model calls"
    )
    ap.add_argument(
        "--relabel", action="store_true", help="redo already-labelled positives"
    )
    args = ap.parse_args()

    if args.env_file:
        load_env(args.env_file)

    files = sorted(args.root.rglob("references/trigger-evals.json"))
    if not files:
        print(f"no trigger-evals.json under {args.root}", file=sys.stderr)
        return 2

    if not args.report:
        if not os.environ.get("SKILL_EVAL_LLM_MODEL"):
            print("SKILL_EVAL_LLM_MODEL unset — pass --env-file", file=sys.stderr)
            return 2
        print(
            f"  labelling {len(files)} corpora via "
            f"{os.environ['SKILL_EVAL_LLM_MODEL']}",
            file=sys.stderr,
        )
        for path in files:
            new, old = label_file(path, args.relabel, dry=False)
            print(
                f"    {path.parent.parent.name:38} +{new} labelled, {old} kept",
                file=sys.stderr,
            )

    counts: Counter[str] = Counter()
    per_skill = []
    for path in files:
        entries = json.loads(path.read_text())
        c = Counter(e.get("bucket") or "UNLABELLED" for e in entries)
        counts.update(c)
        per_skill.append((path.parent.parent.name, c, len(entries)))

    total = sum(counts.values())
    print(f"\n{len(files)} corpora · {total} queries\n")
    print(f"{'bucket':<12} {'n':>5} {'share':>6} {'target':>7}")
    for b in BUCKETS:
        share = counts[b] / total if total else 0
        print(f"{b:<12} {counts[b]:>5} {share:>5.0%} {TARGET[b]:>6.0%}")
    if counts["UNLABELLED"]:
        print(
            f"{'UNLABELLED':<12} {counts['UNLABELLED']:>5} "
            f"{counts['UNLABELLED'] / total:>5.0%}    — run without --report"
        )

    thin = [
        (s, c, n)
        for s, c, n in per_skill
        if n and (c["contextual"] / n) < MIN_CONTEXTUAL_SHARE
    ]
    if thin:
        print(
            f"\n{len(thin)} corpus/corpora under {MIN_CONTEXTUAL_SHARE:.0%} contextual — the bucket that"
        )
        print(
            "most resembles real usage, and the one a keyword-tuned description fails:"
        )
        for s, c, n in sorted(thin, key=lambda x: x[1]["contextual"])[:12]:
            print(f"   {s:<40} {c['contextual']}/{n} contextual")
    if counts["UNLABELLED"] and not args.report:
        # A labelling run that leaves gaps must not read as a finished corpus:
        # the shares below are computed over a denominator that is missing rows.
        print(
            f"\nINCOMPLETE — {counts['UNLABELLED']} quer(ies) unlabelled after a "
            "labelling run.\nThe shares above are over a partial corpus. Re-run; if "
            "it persists, the reply\nis being truncated (raise MAX_TOKENS).",
            file=sys.stderr,
        )
        return 1
    print("\nA description tuned on explicit queries passes by keyword match and can")
    print("still miss every implicit one. Per-bucket rates come from probe-trigger.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
