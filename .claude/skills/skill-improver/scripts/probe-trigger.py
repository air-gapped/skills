#!/usr/bin/env python3
"""Probe whether a Claude Code skill description triggers on a given query set.

Adapted from anthropics/skills skill-creator/scripts/run_eval.py — keeps the
core trigger-detection loop, drops the improvement / report machinery (the
parent skill-improver loop is the brain).

Mechanism: write the candidate description to a fresh `.claude/commands/<id>.md`
slash-command file (so it appears in claude's available_skills list for the
session), shell out to `claude -p <query> --output-format stream-json
--include-partial-messages`, parse the stream for a tool_use of `Skill` or
`Read` whose target name matches our synthetic id. Each query runs N times to
measure trigger rate; rate >= threshold counts as triggered.

Output: JSON — per-query pass/fail plus aggregate train/test scores when a
holdout is requested. The parent loop reads this and decides what to mutate.

Usage:
  probe-trigger.py --skill-path <dir> --eval-set <eval.json> [--description <override>]
                   [--runs-per-query 3] [--trigger-threshold 0.5] [--timeout 30]
                   [--num-workers 6] [--holdout 0.4] [--seed 42] [--model <id>]

Eval-set JSON shape:
  [{"query": "user phrasing", "should_trigger": true},
   {"query": "should not fire", "should_trigger": false}, ...]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import select
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path


def parse_skill_md(skill_dir: Path) -> tuple[str, str]:
    """Return (name, description) from SKILL.md frontmatter.

    description includes any when_to_use field concatenated, since that is
    how Claude Code presents them in the listing (combined cap of 1,536 chars).
    """
    text = (skill_dir / "SKILL.md").read_text()
    fm_match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not fm_match:
        raise ValueError(f"No YAML frontmatter found in {skill_dir}/SKILL.md")
    frontmatter = fm_match.group(1)

    name = _yaml_scalar(frontmatter, "name") or skill_dir.name
    description = _yaml_scalar(frontmatter, "description") or ""
    when_to_use = _yaml_scalar(frontmatter, "when_to_use") or ""
    if when_to_use:
        description = f"{description.rstrip()} {when_to_use.lstrip()}".strip()
    return name, description


def _yaml_scalar(frontmatter: str, field: str) -> str | None:
    """Pull a single YAML scalar by name. Handles `field: value`, `field: >-`,
    and `field: |` block forms. Doesn't handle nested mappings."""
    pat = rf"^{field}:\s*(>-|>|\|)?\s*(.*?)(?=\n[a-zA-Z_-]+:|\Z)"
    m = re.search(pat, frontmatter, re.MULTILINE | re.DOTALL)
    if not m:
        return None
    style, body = m.group(1), m.group(2)
    if style in (">-", ">"):
        return " ".join(
            line.strip() for line in body.strip().splitlines() if line.strip()
        )
    if style == "|":
        return "\n".join(line.strip() for line in body.strip().splitlines())
    return body.strip().strip("'\"")


def _project_root() -> Path:
    """Walk up looking for `.claude/`. Mirrors how Claude Code finds its root."""
    for parent in [Path.cwd(), *Path.cwd().parents]:
        if (parent / ".claude").is_dir():
            return parent
    return Path.cwd()


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    model: str | None,
) -> bool:
    """Run one query against a synthetic skill installation. Return True if
    the skill name appeared in a Skill or Read tool_use stream event."""
    unique_id = uuid.uuid4().hex[:8]
    clean_name = f"{skill_name}-probe-{unique_id}"
    cmd_dir = Path(project_root) / ".claude" / "commands"
    cmd_file = cmd_dir / f"{clean_name}.md"
    try:
        cmd_dir.mkdir(parents=True, exist_ok=True)
        indented = "\n  ".join(skill_description.split("\n"))
        cmd_file.write_text(
            f"---\ndescription: |\n  {indented}\n---\n\n"
            f"# {skill_name}\n\nThis skill handles: {skill_description}\n"
        )

        cmd = [
            "claude",
            "-p",
            query,
            "--output-format",
            "stream-json",
            "--verbose",
            "--include-partial-messages",
        ]
        if model:
            cmd.extend(["--model", model])

        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=project_root,
            env=env,
        )

        start = time.time()
        buf = ""
        pending_tool = None
        accum_json = ""
        try:
            while time.time() - start < timeout:
                if proc.poll() is not None:
                    rest = proc.stdout.read()
                    if rest:
                        buf += rest.decode("utf-8", errors="replace")
                    break
                ready, _, _ = select.select([proc.stdout], [], [], 1.0)
                if not ready:
                    continue
                chunk = os.read(proc.stdout.fileno(), 8192)
                if not chunk:
                    break
                buf += chunk.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("type") == "stream_event":
                        se = event.get("event", {})
                        se_type = se.get("type", "")
                        if se_type == "content_block_start":
                            cb = se.get("content_block", {})
                            if cb.get("type") == "tool_use":
                                tool = cb.get("name", "")
                                if tool in ("Skill", "Read"):
                                    pending_tool = tool
                                    accum_json = ""
                                else:
                                    return False
                        elif se_type == "content_block_delta" and pending_tool:
                            d = se.get("delta", {})
                            if d.get("type") == "input_json_delta":
                                accum_json += d.get("partial_json", "")
                                if clean_name in accum_json:
                                    return True
                        elif se_type in ("content_block_stop", "message_stop"):
                            if pending_tool:
                                return clean_name in accum_json
                            if se_type == "message_stop":
                                return False
                    elif event.get("type") == "assistant":
                        for c in event.get("message", {}).get("content", []):
                            if c.get("type") != "tool_use":
                                continue
                            t = c.get("name", "")
                            inp = c.get("input", {})
                            if t == "Skill" and clean_name in inp.get("skill", ""):
                                return True
                            if t == "Read" and clean_name in inp.get("file_path", ""):
                                return True
                        return False
                    elif event.get("type") == "result":
                        return False
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        return False
    finally:
        if cmd_file.exists():
            cmd_file.unlink()


def stratified_split(
    items: list[dict], holdout: float, seed: int
) -> tuple[list[dict], list[dict]]:
    """60/40-style split, stratified on should_trigger so both classes appear in test."""
    rng = random.Random(seed)
    pos = [e for e in items if e["should_trigger"]]
    neg = [e for e in items if not e["should_trigger"]]
    rng.shuffle(pos)
    rng.shuffle(neg)
    n_pos_test = max(1, int(len(pos) * holdout)) if pos else 0
    n_neg_test = max(1, int(len(neg) * holdout)) if neg else 0
    test = pos[:n_pos_test] + neg[:n_neg_test]
    train = pos[n_pos_test:] + neg[n_neg_test:]
    return train, test


def score_set(
    items: list[dict],
    skill_name: str,
    description: str,
    runs_per_query: int,
    trigger_threshold: float,
    timeout: int,
    num_workers: int,
    project_root: Path,
    model: str | None,
) -> dict:
    triggers: dict[str, list[bool]] = {}
    by_query: dict[str, dict] = {}
    with ProcessPoolExecutor(max_workers=num_workers) as ex:
        futs = {}
        for item in items:
            for _ in range(runs_per_query):
                fut = ex.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    model,
                )
                futs[fut] = item
        for fut in as_completed(futs):
            item = futs[fut]
            q = item["query"]
            by_query[q] = item
            triggers.setdefault(q, [])
            try:
                triggers[q].append(fut.result())
            except Exception as e:
                print(f"warn: query failed: {e}", file=sys.stderr)
                triggers[q].append(False)

    results = []
    for q, runs in triggers.items():
        rate = sum(runs) / len(runs)
        item = by_query[q]
        passed = (
            (rate >= trigger_threshold)
            if item["should_trigger"]
            else (rate < trigger_threshold)
        )
        results.append(
            {
                "query": q,
                "should_trigger": item["should_trigger"],
                "trigger_rate": rate,
                "triggers": sum(runs),
                "runs": len(runs),
                "pass": passed,
            }
        )
    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r["pass"]),
        "failed": sum(1 for r in results if not r["pass"]),
    }
    return {"description": description, "results": results, "summary": summary}


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--skill-path", required=True)
    p.add_argument("--eval-set", required=True)
    p.add_argument(
        "--description",
        default=None,
        help="Override description (defaults to SKILL.md frontmatter)",
    )
    p.add_argument("--runs-per-query", type=int, default=3)
    p.add_argument("--trigger-threshold", type=float, default=0.5)
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--num-workers", type=int, default=6)
    p.add_argument(
        "--holdout",
        type=float,
        default=0.0,
        help="Stratified train/test split. 0 = single set.",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--model", default=None)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    skill_dir = Path(args.skill_path).expanduser().resolve()
    if not (skill_dir / "SKILL.md").exists():
        print(f"error: no SKILL.md at {skill_dir}", file=sys.stderr)
        sys.exit(1)

    items = json.loads(Path(args.eval_set).read_text())
    name, fm_desc = parse_skill_md(skill_dir)
    description = args.description if args.description is not None else fm_desc
    project_root = _project_root()

    if args.holdout > 0:
        train, test = stratified_split(items, args.holdout, args.seed)
    else:
        train, test = items, []

    if args.verbose:
        print(
            f"skill={name} train={len(train)} test={len(test)} runs/query={args.runs_per_query}",
            file=sys.stderr,
        )

    train_out = score_set(
        train,
        name,
        description,
        args.runs_per_query,
        args.trigger_threshold,
        args.timeout,
        args.num_workers,
        project_root,
        args.model,
    )
    test_out = (
        score_set(
            test,
            name,
            description,
            args.runs_per_query,
            args.trigger_threshold,
            args.timeout,
            args.num_workers,
            project_root,
            args.model,
        )
        if test
        else None
    )

    output = {
        "skill_name": name,
        "description": description,
        "train": train_out,
        "test": test_out,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
