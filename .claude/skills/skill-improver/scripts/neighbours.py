#!/usr/bin/env python3
"""The automatic skills whose listing text is closest to a target's.

A shorter description must still lose to its neighbours on their queries.
This ranks every other automatic skill (slash-only and `paths`-scoped skills
are skipped) by TF-IDF cosine over name + description + when_to_use, and with
`--eval-out` writes the target's trigger eval set plus each neighbour's
should-trigger queries relabelled `should_trigger: false`, bucket `negative`,
source `sibling:<name>`. Read that file before probing: a neighbour query
that is also the target's job is not a negative; delete it.

Usage:
  neighbours.py --score <eval-set> <probe.json> [<probe.json> ...]
      one line per probe-trigger.py result: listing characters, then passed /
      measured for should-trigger, other should-not, and sibling queries
  neighbours.py <skill-dir> [--root DIR ...] [--top 5] [--per-neighbour 3]
                [--eval-out FILE]
  neighbours.py --selfcheck

Prints one line per neighbour and the `--neighbour` arguments for
probe-trigger.py. A neighbour without `references/trigger-evals.json` adds no
queries: write two for it by hand.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skill_frontmatter import listing_description, read_frontmatter  # noqa: E402

WORD = re.compile(r"[a-z][a-z0-9_]+")
STOP = set(
    "a an and are as at be by for from has in is it its of on or that the this to "
    "use used uses when with without not any all also via into your you who what "
    "how do does should skill triggers trigger on".split()
)


def tokens(text: str) -> list[str]:
    return [w for w in WORD.findall(text.lower()) if w not in STOP]


def automatic(root: Path) -> dict[str, tuple[Path, str]]:
    out = {}
    for skill_md in sorted(root.glob("*/SKILL.md")):
        try:
            fm = read_frontmatter(skill_md.read_text())
        except (OSError, ValueError):
            continue
        if str(fm.get("disable-model-invocation", "")).lower() == "true":
            continue
        if fm.get("paths"):
            continue
        name = str(fm.get("name") or skill_md.parent.name)
        out.setdefault(name, (skill_md.parent, f"{name} {listing_description(fm)}"))
    return out


def rank(target: str, docs: dict[str, str]) -> list[tuple[str, float]]:
    tf = {n: Counter(tokens(t)) for n, t in docs.items()}
    df = Counter(w for c in tf.values() for w in c)
    n = len(docs)

    def vec(c):
        v = {w: k * math.log((1 + n) / (1 + df[w])) for w, k in c.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}

    vecs = {name: vec(c) for name, c in tf.items()}
    t = vecs[target]
    scores = [
        (name, sum(x * v.get(w, 0.0) for w, x in t.items()))
        for name, v in vecs.items()
        if name != target
    ]
    return sorted(scores, key=lambda s: -s[1])


def load_evals(skill: Path) -> list[dict]:
    p = skill / "references" / "trigger-evals.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return []


def build(target_dir: Path, roots: list[Path], top: int, per: int):
    skills: dict[str, tuple[Path, str]] = {}
    for root in roots:
        for k, v in automatic(root).items():
            skills.setdefault(k, v)
    fm = read_frontmatter((target_dir / "SKILL.md").read_text())
    target = str(fm.get("name") or target_dir.name)
    skills[target] = (target_dir, f"{target} {listing_description(fm)}")
    near = rank(target, {k: v[1] for k, v in skills.items()})[:top]
    evals = list(load_evals(target_dir))
    for name, _ in near:
        pos = [e for e in load_evals(skills[name][0]) if e.get("should_trigger")]
        for e in pos[:per]:
            evals.append(
                {
                    "query": e["query"],
                    "should_trigger": False,
                    "bucket": "negative",
                    "source": f"sibling:{name}",
                }
            )
    return target, [(n, s, skills[n][0]) for n, s in near], evals


def score(eval_set: Path, probes: list[Path]) -> int:
    source = {
        e["query"]: str(e.get("source", "")) for e in json.loads(eval_set.read_text())
    }
    for p in probes:
        out = json.loads(p.read_text())
        rows = [
            r
            for part in ("train", "test")
            if out.get(part)
            for r in out[part]["results"]
        ]
        groups = {"trigger": [], "not": [], "sibling": []}
        for r in rows:
            if r["should_trigger"]:
                key = "trigger"
            elif source.get(r["query"], "").startswith("sibling:"):
                key = "sibling"
            else:
                key = "not"
            if r.get("pass") is not None:
                groups[key].append(bool(r["pass"]))
        cells = "  ".join(f"{k} {sum(v)}/{len(v)}" for k, v in groups.items())
        print(f"{len(out.get('description', '')):>5} chars  {cells}  {p}")
    return 0


def selfcheck() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        def plant(name, desc, evals=None, extra=""):
            d = root / name
            (d / "references").mkdir(parents=True)
            (d / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {desc}\n{extra}---\n\nBody.\n"
            )
            if evals is not None:
                (d / "references" / "trigger-evals.json").write_text(json.dumps(evals))

        q = lambda s, t=True: {"query": s, "should_trigger": t}  # noqa: E731
        plant("redis-ops", "Redis Sentinel failover and replication.", [q("redis x")])
        plant(
            "valkey-move",
            "Migrate Redis to Valkey with Sentinel replication.",
            [q("move to valkey"), q("not me", False)],
        )
        plant("cooking", "Recipes for bread and soup.", [q("bake bread")])
        plant(
            "hidden",
            "Redis Sentinel too.",
            [q("h")],
            "disable-model-invocation: true\n",
        )
        target, near, evals = build(root / "redis-ops", [root], 2, 3)
        assert target == "redis-ops"
        assert near[0][0] == "valkey-move", near
        assert "hidden" not in [n for n, _, _ in near]
        negs = [e for e in evals if str(e.get("source", "")).startswith("sibling:")]
        assert {"query": "move to valkey", "should_trigger": False} in [
            {k: e[k] for k in ("query", "should_trigger")} for e in negs
        ]
        assert all(e["query"] != "not me" for e in negs)
        assert evals[0]["query"] == "redis x"
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("skill", nargs="?", type=Path)
    ap.add_argument("--root", action="append", type=Path)
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--per-neighbour", type=int, default=3)
    ap.add_argument("--eval-out", type=Path)
    ap.add_argument("--score", nargs="+", type=Path, metavar="FILE")
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()
    if a.selfcheck:
        return selfcheck()
    if a.score:
        if len(a.score) < 2:
            ap.error("--score takes an eval set and at least one probe result")
        return score(a.score[0], a.score[1:])
    if not a.skill:
        ap.error("give a skill directory")
    skill = a.skill.expanduser().resolve()
    roots = [r.expanduser() for r in (a.root or [skill.parent])]
    _, near, evals = build(skill, roots, a.top, a.per_neighbour)
    for name, sim, path in near:
        n = sum(1 for e in evals if e.get("source") == f"sibling:{name}")
        print(f"{sim:.3f}  {name:<40} {n} queries  {path}")
    print("probe-trigger.py args: " + " ".join(f"--neighbour {p}" for _, _, p in near))
    if a.eval_out:
        a.eval_out.write_text(json.dumps(evals, indent=2) + "\n")
        print(f"wrote {a.eval_out}: {len(evals)} queries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
