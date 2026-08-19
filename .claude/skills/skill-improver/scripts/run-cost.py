#!/usr/bin/env python3
"""Token and cost accounting for a Claude Code session, read from its transcript.

The agent cannot see its own spend at runtime. The harness writes every API
call's `usage` block to the session transcript, so cost is recoverable after
the fact -- per model, per subagent, per phase.

Two facts about the transcript format drive this script:

  1. One API request appears as SEVERAL records, one per content block, each
     carrying an IDENTICAL copy of the same `usage`. Summing records instead
     of requests overcounts by 2x or more. Records are deduplicated on
     `requestId`.
  2. Subagents do NOT appear in the main transcript. They live in
     `<project>/<session-id>/subagents/agent-*.jsonl`, each with a sibling
     `.meta.json` naming its `agentType` and task `description`.

Usage:
    run-cost.py                          # newest session for the cwd's project
    run-cost.py --session <id|path>
    run-cost.py --project <dir> --list   # enumerate sessions, newest first
    run-cost.py --since 2026-08-19       # only calls at/after this date
    run-cost.py --json

Costs are Claude API first-party list rates from `model-rates.json`, shown to
size a run against other runs. A subscription is not billed this way.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from statistics import median
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
RATES_FILE = Path(__file__).with_name("model-rates.json")

TOKEN_FIELDS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)


# --------------------------------------------------------------------------
# locating transcripts
# --------------------------------------------------------------------------


def project_dir_for(path: Path) -> Path:
    """Claude Code mangles a cwd into a project dir name by replacing every
    non-alphanumeric run with a dash."""
    return PROJECTS / re.sub(r"[^a-zA-Z0-9]+", "-", str(path))


def find_sessions(proj: Path) -> list[Path]:
    if not proj.is_dir():
        return []
    return sorted(proj.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)


def resolve_session(arg: str | None, proj: Path) -> Path:
    if arg:
        p = Path(arg)
        if p.is_file():
            return p
        for cand in (proj / f"{arg}.jsonl", Path(f"{arg}.jsonl")):
            if cand.is_file():
                return cand
        hits = list(PROJECTS.glob(f"*/{arg}.jsonl"))
        if hits:
            return hits[0]
        sys.exit(f"run-cost: no transcript found for session '{arg}'")
    sessions = find_sessions(proj)
    if not sessions:
        sys.exit(
            f"run-cost: no transcripts under {proj}\n"
            "  Sessions are scoped to the working directory they ran in.\n"
            "  Pass --project <dir> for another directory, or --session <id>."
        )
    return sessions[0]


def subagent_files(session: Path) -> list[tuple[Path, dict]]:
    """Return [(jsonl, meta)] for every subagent spawned by this session."""
    sub = session.with_suffix("") / "subagents"
    out = []
    if not sub.is_dir():
        return out
    for f in sorted(sub.glob("agent-*.jsonl")):
        meta_path = f.with_suffix(".meta.json")
        meta = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        out.append((f, meta))
    return out


# --------------------------------------------------------------------------
# pricing
# --------------------------------------------------------------------------


def normalize_model(model: str) -> str:
    """`claude-opus-5[1m]`, `claude-haiku-4-5-20251001` -> `claude-haiku-4-5`."""
    m = re.sub(r"\[.*?\]$", "", model or "")
    m = re.sub(r"-\d{8}$", "", m)
    return m


class Rates:
    def __init__(self, data: dict):
        self.data = data
        self.mult = data["multipliers"]
        self.models = data["models"]
        self.fast = data.get("fast_mode", {})
        self.unpriced: set[str] = set()

    def cost(self, model: str, u: dict, *, geo: str = "", speed: str = "") -> float:
        key = normalize_model(model)
        table = self.fast if speed == "fast" and key in self.fast else self.models
        rate = table.get(key)
        if rate is None:
            if key:
                self.unpriced.add(key)
            return 0.0

        inp, out = rate["input"] / 1e6, rate["output"] / 1e6

        # Cache writes are billed at different rates by TTL. The nested
        # `cache_creation` block splits them; fall back to the flat 5m figure.
        cc = u.get("cache_creation") or {}
        w5 = cc.get("ephemeral_5m_input_tokens")
        w1h = cc.get("ephemeral_1h_input_tokens", 0)
        if w5 is None:
            w5, w1h = u.get("cache_creation_input_tokens", 0), 0

        total = (
            u.get("input_tokens", 0) * inp
            + u.get("cache_read_input_tokens", 0) * inp * self.mult["cache_read"]
            + w5 * inp * self.mult["cache_write_5m"]
            + w1h * inp * self.mult["cache_write_1h"]
            + u.get("output_tokens", 0) * out
        )
        if geo == "us":
            total *= self.mult["inference_geo_us"]
        return total


# --------------------------------------------------------------------------
# aggregation
# --------------------------------------------------------------------------


class Bucket:
    __slots__ = (
        "calls", "toks", "thinking", "searches", "cost", "models", "effort",
        "latencies", "first_ts", "last_ts",
    )  # fmt: skip

    def __init__(self):
        self.latencies: list[float] = []
        self.first_ts = ""
        self.last_ts = ""
        self.calls = 0
        self.toks = defaultdict(int)
        self.thinking = 0
        self.searches = 0
        self.cost = 0.0
        self.models = set()
        self.effort = set()

    @property
    def input_total(self) -> int:
        return (
            self.toks["input_tokens"]
            + self.toks["cache_creation_input_tokens"]
            + self.toks["cache_read_input_tokens"]
        )

    @property
    def gen_tps(self) -> float:
        """Output tokens per second of model turnaround.

        Derived from consecutive transcript timestamps, so it measures
        request-to-response wall time -- prefill, generation, and network
        together -- not decode speed alone. Good for comparing models on the
        same workload; not a decode benchmark.
        """
        t = sum(self.latencies)
        return self.toks["output_tokens"] / t if t else 0.0

    @property
    def wall_s(self) -> float:
        if not (self.first_ts and self.last_ts):
            return 0.0
        try:
            a = datetime.fromisoformat(self.first_ts.replace("Z", "+00:00"))
            b = datetime.fromisoformat(self.last_ts.replace("Z", "+00:00"))
            return (b - a).total_seconds()
        except ValueError:
            return 0.0

    @property
    def hit_rate(self) -> float:
        tot = self.input_total
        return self.toks["cache_read_input_tokens"] / tot if tot else 0.0


def scan(path: Path, rates: Rates, since: str | None, seen: set[str]):
    """Yield one (record, usage, cost) per DISTINCT request in `path`."""
    try:
        fh = path.open()
    except OSError as e:
        print(f"run-cost: cannot read {path}: {e}", file=sys.stderr)
        return
    prev_ts = ""
    with fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = rec.get("timestamp") or ""
            msg = rec.get("message") or {}
            usage = msg.get("usage")
            if not usage:
                if ts:
                    prev_ts = ts  # a user turn / tool result: starts the clock
                continue
            # `<synthetic>` records are harness-local, never a billed API call.
            if msg.get("model") == "<synthetic>":
                continue
            if since and (rec.get("timestamp") or "") < since:
                continue
            rid = rec.get("requestId") or msg.get("id") or rec.get("uuid")
            if rid in seen:
                continue
            seen.add(rid)
            lat = 0.0
            if prev_ts and ts:
                try:
                    a = datetime.fromisoformat(prev_ts.replace("Z", "+00:00"))
                    b = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    d = (b - a).total_seconds()
                    # Guard the gap where a human was thinking, not the model.
                    lat = d if 0 < d < 600 else 0.0
                except ValueError:
                    lat = 0.0
            rec["_latency_s"] = lat
            prev_ts = ts
            cost = rates.cost(
                msg.get("model", ""),
                usage,
                geo=(usage.get("inference_geo") or ""),
                speed=(msg.get("speed") or rec.get("speed") or ""),
            )
            yield rec, msg, usage, cost


def add(bucket: Bucket, rec, msg, usage, cost):
    lat = rec.get("_latency_s") or 0.0
    if lat:
        bucket.latencies.append(lat)
    ts = rec.get("timestamp") or ""
    if ts:
        bucket.first_ts = min(bucket.first_ts or ts, ts)
        bucket.last_ts = max(bucket.last_ts, ts)
    bucket.calls += 1
    bucket.cost += cost
    for f in TOKEN_FIELDS:
        bucket.toks[f] += usage.get(f, 0)
    bucket.thinking += (usage.get("output_tokens_details") or {}).get(
        "thinking_tokens", 0
    )
    bucket.searches += (usage.get("server_tool_use") or {}).get(
        "web_search_requests", 0
    )
    if msg.get("model"):
        bucket.models.add(normalize_model(msg["model"]))
    if rec.get("effort"):
        bucket.effort.add(rec["effort"])


# --------------------------------------------------------------------------
# output
# --------------------------------------------------------------------------


def fmt_usd(x: float) -> str:
    return f"${x:,.2f}" if x >= 0.005 else f"${x:.4f}"


def render(session: Path, total: Bucket, by_model, by_agent, rates: Rates, args):
    search_cost = total.searches * rates.data["web_search_per_1k_searches"] / 1000
    grand = total.cost + search_cost

    print(f"\nSession   {session.stem}")
    print(f"Project   {session.parent.name}")
    print(f"Rates     list, verified {rates.data['verified']}\n")

    print(f"{'':22}{'tokens':>14}{'share':>9}{'cost':>12}")
    print("-" * 57)
    rows = [
        ("cache read", total.toks["cache_read_input_tokens"]),
        ("cache write", total.toks["cache_creation_input_tokens"]),
        ("input (uncached)", total.toks["input_tokens"]),
        ("output", total.toks["output_tokens"]),
    ]
    grand_toks = sum(v for _, v in rows)
    for label, v in rows:
        share = v / grand_toks * 100 if grand_toks else 0
        print(f"{label:22}{v:>14,}{share:>8.1f}%")
    print("-" * 57)
    print(f"{'total':22}{grand_toks:>14,}{'':>9}{fmt_usd(grand):>12}")
    if total.thinking:
        print(f"{'  (thinking)':22}{total.thinking:>14,}")
    if total.searches:
        print(
            f"{'  web searches':22}{total.searches:>14,}{'':>9}{fmt_usd(search_cost):>12}"
        )
    p50 = median(total.latencies) if total.latencies else 0.0
    busy = sum(total.latencies)
    wall = total.wall_s
    print(
        f"\n{total.calls} API requests · cache hit rate {total.hit_rate:.0%}"
        f" · {fmt_usd(grand / total.calls) if total.calls else '$0'} per request"
    )
    print(
        f"latency p50 {p50:.1f}s · {total.gen_tps:.1f} output tok/s"
        f" · {busy / 60:.0f}m in-model of {wall / 60:.0f}m wall"
        + (f" ({busy / wall:.1f}x concurrency)" if wall > 0 and busy > wall else "")
    )

    if len(by_model) > 1 or args.verbose:
        print(
            f"\n{'model':22}{'calls':>7}{'in':>13}{'out':>10}"
            f"{'p50 s':>8}{'tok/s':>8}{'cost':>11}"
        )
        print("-" * 79)
        for name, b in sorted(by_model.items(), key=lambda kv: -kv[1].cost):
            p50 = median(b.latencies) if b.latencies else 0.0
            print(
                f"{name:22}{b.calls:>7}{b.input_total:>13,}"
                f"{b.toks['output_tokens']:>10,}{p50:>8.1f}{b.gen_tps:>8.1f}"
                f"{fmt_usd(b.cost):>11}"
            )

    if by_agent:
        print(f"\n{'agent':30}{'calls':>7}{'in':>13}{'out':>10}{'cost':>11}")
        print("-" * 71)
        for name, b in sorted(by_agent.items(), key=lambda kv: -kv[1].cost):
            print(
                f"{name[:29]:30}{b.calls:>7}{b.input_total:>13,}"
                f"{b.toks['output_tokens']:>10,}{fmt_usd(b.cost):>11}"
            )
        sub = sum(b.cost for n, b in by_agent.items() if n != "main")
        if sub:
            print(f"\nsubagents are {sub / grand:.0%} of spend" if grand else "")

    if rates.unpriced:
        print(
            f"\nunpriced models (counted, not costed): {', '.join(sorted(rates.unpriced))}"
        )
    print("\nList API rates. A subscription is not billed this way — read the")
    print("dollar figures as relative sizing between runs, not as an invoice.\n")


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--session", help="session id, or path to a transcript")
    ap.add_argument("--project", help="working directory whose project to read")
    ap.add_argument("--since", help="ISO timestamp/date floor, e.g. 2026-08-19")
    ap.add_argument("--list", action="store_true", help="list sessions and exit")
    ap.add_argument("--no-subagents", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--rates", help="override model-rates.json")
    args = ap.parse_args()

    rates = Rates(json.loads(Path(args.rates or RATES_FILE).read_text()))
    proj = project_dir_for(Path(args.project or os.getcwd()).resolve())

    if args.list:
        sessions = find_sessions(proj)
        if not sessions:
            print(f"no transcripts under {proj}", file=sys.stderr)
            return
        for s in sessions:
            ts = datetime.fromtimestamp(s.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"{ts}  {s.stem}")
        return

    session = resolve_session(args.session, proj)

    total, by_model, by_agent = Bucket(), defaultdict(Bucket), {}
    seen: set[str] = set()

    main_b = Bucket()
    for rec, msg, usage, cost in scan(session, rates, args.since, seen):
        for b in (total, main_b, by_model[normalize_model(msg.get("model", "?"))]):
            add(b, rec, msg, usage, cost)
    if main_b.calls:
        by_agent["main"] = main_b

    if not args.no_subagents:
        for f, meta in subagent_files(session):
            b = Bucket()
            for rec, msg, usage, cost in scan(f, rates, args.since, seen):
                for tgt in (total, b, by_model[normalize_model(msg.get("model", "?"))]):
                    add(tgt, rec, msg, usage, cost)
            if not b.calls:
                continue
            atype = meta.get("agentType", "agent")
            desc = meta.get("description", "")
            label = f"{atype}: {desc}" if desc else f"{atype} {f.stem[6:14]}"
            while label in by_agent:
                label += "'"
            by_agent[label] = b

    if not total.calls:
        sys.exit("run-cost: no usage records matched")

    if args.json:
        search_cost = total.searches * rates.data["web_search_per_1k_searches"] / 1000
        print(
            json.dumps(
                {
                    "session": session.stem,
                    "project": session.parent.name,
                    "rates_verified": rates.data["verified"],
                    "requests": total.calls,
                    "tokens": dict(total.toks),
                    "thinking_tokens": total.thinking,
                    "web_searches": total.searches,
                    "cache_hit_rate": round(total.hit_rate, 4),
                    "latency_p50_s": round(
                        median(total.latencies) if total.latencies else 0.0, 2
                    ),
                    "output_tokens_per_s": round(total.gen_tps, 2),
                    "in_model_s": round(sum(total.latencies), 1),
                    "wall_s": round(total.wall_s, 1),
                    "cost_usd": round(total.cost + search_cost, 4),
                    "by_model": {
                        k: {
                            "calls": v.calls,
                            "cost_usd": round(v.cost, 4),
                            "input": v.input_total,
                            "output": v.toks["output_tokens"],
                            "output_tokens_per_s": round(v.gen_tps, 2),
                            "latency_p50_s": round(
                                median(v.latencies) if v.latencies else 0.0, 2
                            ),
                        }
                        for k, v in by_model.items()
                    },
                    "by_agent": {
                        k: {
                            "calls": v.calls,
                            "cost_usd": round(v.cost, 4),
                            "models": sorted(v.models),
                            "effort": sorted(v.effort),
                            "input": v.input_total,
                            "output": v.toks["output_tokens"],
                        }
                        for k, v in by_agent.items()
                    },
                    "unpriced_models": sorted(rates.unpriced),
                },
                indent=2,
            )
        )
        return

    render(session, total, by_model, by_agent, rates, args)


if __name__ == "__main__":
    main()
