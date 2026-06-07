#!/usr/bin/env python3
"""Probe whether a Claude Code skill description triggers on a given query set.

Adapted from anthropics/skills skill-creator/scripts/run_eval.py — keeps the
core trigger-detection loop, drops the improvement / report machinery (the
parent skill-improver loop is the brain).

Mechanism: per query, create an isolated temp project dir and install the
candidate description as a real SKILL at `<tmp>/.claude/skills/<id>/SKILL.md`
(Claude Code auto-invokes skills; it does NOT auto-invoke `.claude/commands/`
entries, so a command synthetic never triggers). Each query gets its own temp
dir so concurrent workers don't see each other's identically-described
synthetics. Shell out to `claude -p <query> --output-format stream-json
--verbose --include-partial-messages`, and scan the whole turn for a `Skill`
or `Read` tool_use whose input references our synthetic id (do not bail on the
first other tool, and do not stop at message_stop — a tool-using turn spans
several messages). Each query runs N times; rate >= threshold counts as
triggered. The default `--timeout` is 180s because `claude -p` routinely takes
60-150s/call; a call killed before the model reaches the Skill reads as a miss,
so timed-out runs are tracked separately and surfaced as a warning — an all-0.0
result from premature kills must never be mistaken for genuine under-triggering.

Output: JSON — per-query pass/fail plus aggregate train/test scores when a
holdout is requested. The parent loop reads this and decides what to mutate.

Usage:
  probe-trigger.py --skill-path <dir> --eval-set <eval.json> [--description <override>]
                   [--runs-per-query 3] [--trigger-threshold 0.5] [--timeout 180]
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
import shutil
import subprocess
import tempfile
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


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    model: str | None,
) -> tuple[bool, bool]:
    """Run one query against a synthetic skill installation.

    Returns (triggered, timed_out):
      triggered — the skill name appeared in a Skill/Read tool_use event.
      timed_out — the `claude -p` subprocess was still running when `timeout`
                  elapsed and was killed. A timed-out run is NOT a genuine
                  non-trigger (the model may simply not have reached its tool
                  call yet); the caller surfaces timeouts so an all-0.0 result
                  from premature kills is never read as under-triggering."""
    unique_id = uuid.uuid4().hex[:8]
    safe = re.sub(r"[^a-z0-9-]+", "-", skill_name.lower()).strip("-") or "skill"
    clean_name = re.sub(r"-{2,}", "-", f"{safe}-probe-{unique_id}")
    if len(clean_name) > 64:
        clean_name = clean_name[:64].rstrip("-")
    # Install as a real SKILL (model auto-invokes skills) — NOT a slash-command.
    # Claude Code does not auto-invoke `.claude/commands/` entries, so a command
    # synthetic never triggers regardless of description quality.
    #
    # Each query gets its OWN isolated temp project dir. If concurrent workers
    # shared one project root, every `claude -p` would see all the identically
    # described synthetics at once and invoke an arbitrary one — query A (seeking
    # its uuid) misses when the model picks worker B's skill. Isolation also keeps
    # the probe from inheriting real project skills that compete with the synthetic.
    work_root = Path(tempfile.mkdtemp(prefix="sktrig-"))
    skill_dir = work_root / ".claude" / "skills" / clean_name
    cmd_file = skill_dir / "SKILL.md"
    try:
        skill_dir.mkdir(parents=True, exist_ok=True)
        indented = "\n  ".join(skill_description.split("\n"))
        cmd_file.write_text(
            f"---\nname: {clean_name}\ndescription: |\n  {indented}\n---\n\n"
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
            # Restrict skill discovery to THIS temp project. Without it, claude
            # loads the user's ~/.claude/skills/ too — so the synthetic competes
            # with the real skills (often symlinks of the very skill under test),
            # the model picks the real twin, and the probe sees our synthetic id
            # missing -> false 0.0. `--setting-sources project` loads only the
            # temp project's skills, which is the isolation the probe assumes.
            "--setting-sources",
            "project",
        ]
        if model:
            cmd.extend(["--model", model])
        # Hermetic probe: we only observe WHETHER the model would invoke the
        # Skill — the spawned agent must never carry out the task. A query like
        # "deploy my app to openshift" otherwise makes the nested agent try to
        # provision a real local OpenShift (crc/libvirt → host sudo/pkexec
        # password prompts) or run arbitrary Bash. Deny the whole side-effecting
        # surface; Skill + Read (what we detect) stay enabled. Deny rules take
        # precedence over any allow-list in the user's settings, so this holds
        # regardless of the host configuration. Kept LAST: --disallowedTools is
        # variadic, so trailing it prevents it swallowing other flags' values.
        cmd.extend(
            [
                "--disallowedTools",
                "Bash",
                "Edit",
                "Write",
                "NotebookEdit",
                "Task",
                "WebFetch",
                "WebSearch",
            ]
        )

        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=str(work_root),
            env=env,
        )
        assert proc.stdout is not None  # stdout=PIPE guarantees a pipe object

        start = time.time()
        buf = ""
        in_target = False
        accum_json = ""
        timed_out = False
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
                    # Scan the whole turn for a Skill/Read tool_use referencing our
                    # synthetic skill. Do NOT bail on the first other tool_use (current
                    # Claude often calls TodoWrite/etc. before the Skill), and do NOT
                    # stop at message_stop (a tool-using turn spans several messages).
                    # Only a `result` event (or EOF/timeout) ends the turn.
                    if event.get("type") == "stream_event":
                        se = event.get("event", {})
                        se_type = se.get("type", "")
                        if se_type == "content_block_start":
                            cb = se.get("content_block", {})
                            in_target = cb.get("type") == "tool_use" and cb.get(
                                "name"
                            ) in ("Skill", "Read")
                            accum_json = ""
                            if in_target and clean_name in json.dumps(
                                cb.get("input", "")
                            ):
                                return (True, False)
                        elif se_type == "content_block_delta" and in_target:
                            d = se.get("delta", {})
                            if d.get("type") == "input_json_delta":
                                accum_json += d.get("partial_json", "")
                                if clean_name in accum_json:
                                    return (True, False)
                        elif se_type == "content_block_stop":
                            in_target = False
                            accum_json = ""
                    elif event.get("type") == "assistant":
                        for c in event.get("message", {}).get("content", []):
                            if c.get("type") != "tool_use":
                                continue
                            if c.get("name", "") in (
                                "Skill",
                                "Read",
                            ) and clean_name in json.dumps(c.get("input", {})):
                                return (True, False)
                    elif event.get("type") == "result":
                        return (False, False)
            else:
                # The while condition went false without break/return: the
                # subprocess was still running when `timeout` elapsed and is
                # about to be killed below. This is NOT a genuine non-trigger.
                timed_out = True
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
        return (False, timed_out)
    finally:
        shutil.rmtree(work_root, ignore_errors=True)


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
    model: str | None,
) -> dict:
    # Per query: list of (triggered, timed_out) tuples, one per run.
    runs_by_query: dict[str, list[tuple[bool, bool]]] = {}
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
                    model,
                )
                futs[fut] = item
        for fut in as_completed(futs):
            item = futs[fut]
            q = item["query"]
            by_query[q] = item
            runs_by_query.setdefault(q, [])
            try:
                runs_by_query[q].append(fut.result())
            except Exception as e:
                # A crashed worker measured nothing — flag it as unreliable
                # (timed_out=True) rather than a confident non-trigger.
                print(f"warn: query failed: {e}", file=sys.stderr)
                runs_by_query[q].append((False, True))

    results = []
    total_timeouts = 0
    for q, runs in runs_by_query.items():
        n = len(runs)
        n_trig = sum(1 for triggered, _ in runs if triggered)
        n_to = sum(1 for _, to in runs if to)
        total_timeouts += n_to
        rate = n_trig / n
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
                "triggers": n_trig,
                "timeouts": n_to,
                "runs": n,
                "pass": passed,
            }
        )
    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r["pass"]),
        "failed": sum(1 for r in results if not r["pass"]),
        "timeouts": total_timeouts,
    }
    return {"description": description, "results": results, "summary": summary}


def main():
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n", 1)[0])
    p.add_argument("--skill-path", required=True)
    p.add_argument("--eval-set", required=True)
    p.add_argument(
        "--description",
        default=None,
        help="Override description (defaults to SKILL.md frontmatter)",
    )
    p.add_argument("--runs-per-query", type=int, default=3)
    p.add_argument("--trigger-threshold", type=float, default=0.5)
    p.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Per-run upper bound (s). Default 180 because `claude -p` here runs "
        "60-150s/call; this only caps a hung call (a fast call returns early), "
        "so raising it has no downside but prevents premature-kill false misses.",
    )
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

    # Guard the classic false-negative: a too-low --timeout (or a missing/broken
    # `claude -p`) kills the call before the model reaches its tool, so every
    # query reads 0.0 and the skill looks like it under-triggers when the probe
    # never actually measured. Make that failure mode loud, never silent.
    all_out = [o for o in (train_out, test_out) if o]
    total_timeouts = sum(o["summary"].get("timeouts", 0) for o in all_out)
    pos_results = [r for o in all_out for r in o["results"] if r["should_trigger"]]
    if total_timeouts:
        print(
            f"warn: {total_timeouts} run(s) hit the {args.timeout}s timeout and were "
            "killed before completing. These count as non-triggers but are NOT "
            "reliable — raise --timeout and re-run before trusting the scores.",
            file=sys.stderr,
        )
    if pos_results and not any(r["triggers"] > 0 for r in pos_results):
        print(
            "warn: NO should-trigger query fired even once. This almost always "
            "means the probe isn't measuring (timeout too low, or `claude -p` "
            "missing/unauthenticated) — NOT that the skill under-triggers. Verify "
            "`claude -p` works and raise --timeout before trusting these scores.",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
