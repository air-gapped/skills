#!/usr/bin/env python3
"""Regenerate Claude Code plugin marketplace manifest.

Writes only .claude-plugin/marketplace.json at repo root. Each plugin
entry uses strict: false so the marketplace row is the full plugin
definition — no per-skill plugin.json files needed or emitted.

Plugins are either grouped (multiple skills bundled under one plugin
name via GROUPS) or standalone (one plugin per leftover skill dir
under .claude/skills/).

Version scheme: 0.YYYYMMDD.N where
- YYYYMMDD = UTC date of the last commit touching any member skill dir
- N = unique commit count touching any member skill dir
.claude-plugin/ subtree is excluded from pathspec so regenerations
don't self-bump.
"""

import datetime
import fnmatch
import json
import pathlib
import re
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
MARKETPLACE_FILE = REPO_ROOT / ".claude-plugin" / "marketplace.json"

MARKETPLACE_NAME = "air-gapped-marketplace"
OWNER_NAME = "air-gapped"
AUTHOR_NAME = "Jörgen"
LICENSE = "MIT"
MARKETPLACE_DESC = (
    "Reference skills for vLLM, Kubernetes, observability, agent "
    "workflows, and developer tooling. Grouped suites."
)
TAGLINE_CAP = 200

# Group definitions. Each group becomes one plugin bundling multiple
# skills. A group matches skills via `glob` (fnmatch on dir name) or
# `members` (explicit dir-name list). Skills matching no group become
# standalone plugins.
GROUPS: dict[str, dict] = {
    "inference-cache": {
        # Engine-agnostic KV-cache + transport siblings: separate-pod
        # LMCache MP server and NIXL transport used by Dynamo/vLLM/
        # SGLang. SGLang-side caching (HiCache) lives in the `sglang`
        # suite. vllm-caching stays in the `vllm` suite.
        "members": ["lmcache-mp", "nvidia-nixl"],
        "description": (
            "Inference KV-cache and transport suite — LMCache multiprocess "
            "(MP) standalone-server mode (DaemonSet + Deployment K8s "
            "pattern, ZMQ connector, L1 + L2 NIXL/POSIX/GDS/HF3FS/fs/s3/"
            "mooncake adapters) and NVIDIA NIXL transfer library "
            "(UCX/GDS/Mooncake/libfabric/HF3FS/S3 plugins, agent API, "
            "telemetry) used by Dynamo/vLLM/SGLang. Pairs with the "
            "vllm-caching skill in the `vllm` suite and sglang-hicache "
            "in the `sglang` suite."
        ),
        "category": "inference",
        "tags": [
            "kv-cache",
            "lmcache",
            "nixl",
            "vllm",
            "sglang",
            "dynamo",
            "offload",
            "prefix-caching",
            "disaggregated-prefill",
            "kubernetes",
        ],
    },
    "sglang": {
        # SGLang operator suite — SGLang-side reference for HiCache
        # (hierarchical KV cache) and the Model Gateway (Rust router
        # fronting vLLM/SGLang workers on K8s). Mirrors the `vllm`
        # suite pattern.
        "members": ["sglang-hicache", "sglang-model-gateway"],
        "description": (
            "SGLang operator reference suite — HiCache (three-tier "
            "hierarchical prefix cache: GPU HBM → host DRAM → "
            "distributed L3 via Mooncake/3FS/NIXL/AIBrix/EIC/SiMM/"
            "file/LMCache) and the SGLang Model Gateway "
            "(`sgl-model-gateway`, formerly `sgl-router`) — Rust "
            "router fronting vLLM/SGLang inference workers on "
            "Kubernetes with cache-aware/prefix-hash/consistent-hash "
            "routing, K8s label-selector service discovery, "
            "PD-disaggregation, and `--enable-mesh` CRDT sync between "
            "gateway replicas. Pairs with the `vllm` suite for vLLM-"
            "side reference and `inference-cache` for engine-agnostic "
            "KV-cache transport."
        ),
        "category": "inference",
        "tags": [
            "sglang",
            "llm",
            "inference",
            "kubernetes",
            "router",
            "model-gateway",
            "kv-cache",
            "hicache",
            "cache-aware",
            "prefix-caching",
        ],
    },
    "vllm": {
        "glob": "vllm-*",
        "description": (
            "vLLM operator reference suite — deployment, configuration, "
            "quantization, caching, KV, tool parsers, reasoning parsers, "
            "chat templates, benchmarking, performance tuning, "
            "observability, omni, input modalities, speculative decoding, "
            "and NVIDIA hardware."
        ),
        "category": "inference",
        "tags": [
            "vllm",
            "llm",
            "inference",
            "kubernetes",
            "nvidia",
            "gpu",
            "quantization",
            "kv-cache",
        ],
    },
    "k8s": {
        "members": ["helm", "keda", "openshift-app"],
        "description": (
            "Kubernetes suite — Helm chart authoring, KEDA event-driven "
            "autoscaling, OpenShift application packaging."
        ),
        "category": "kubernetes",
        "tags": [
            "kubernetes",
            "helm",
            "keda",
            "openshift",
            "autoscaling",
            "ocp",
        ],
    },
    "agent": {
        "members": ["autoresearch", "skill-improver"],
        "description": (
            "Agent workflow suite — Karpathy-pattern autoresearch "
            "(hill-climbing, multi-agent research) and skill-improver "
            "(Claude Code skill optimization loop)."
        ),
        "category": "ai-workflow",
        "tags": [
            "autoresearch",
            "agents",
            "claude-code",
            "skills",
            "hill-climbing",
            "optimization",
        ],
    },
    "dev": {
        "members": [
            "baml-expert",
            "jinja-expert",
            "makefile-best-practices",
            "transformers-config-tokenizers-expert",
        ],
        "description": (
            "Developer tooling suite — BAML (typed LLM functions), Jinja2 "
            "templates (HuggingFace chat templates, Ansible), GNU Make "
            "best practices, and HuggingFace transformers config/tokenizer "
            "preflight (vLLM/sglang engine bridge)."
        ),
        "category": "developer-tools",
        "tags": [
            "baml",
            "jinja",
            "makefile",
            "gnu-make",
            "chat-templates",
            "huggingface",
            "ansible",
            "typed-prompts",
            "transformers",
            "tokenizers",
            "preflight",
        ],
    },
    "observability": {
        "members": ["prometheus-mimir-grafana"],
        "description": (
            "Observability suite — Prometheus, Grafana Mimir, and Grafana "
            "reference for agents querying metrics, writing PromQL, "
            "building and fixing dashboards, and reasoning about SLOs, "
            "KPIs, and burn-rate alerting."
        ),
        "category": "observability",
        "tags": [
            "prometheus",
            "mimir",
            "grafana",
            "promql",
            "observability",
            "metrics",
            "slo",
            "sre",
        ],
    },
    "open-webui": {
        "members": ["open-webui-embeddings"],
        "description": (
            "Open WebUI operator suite — wiring HuggingFace embedding "
            "and reranker models into Open WebUI's RAG pipeline via "
            "LiteLLM in front of HuggingFace Text Embeddings Inference "
            "(TEI). Covers exact wire shapes, LiteLLM ↔ TEI gotchas, "
            "TEI configuration cliffs, and end-to-end production "
            "configuration. BGE-M3 and BGE-Reranker-v2-m3 are the "
            "worked examples; patterns generalise to any TEI-served "
            "encoder."
        ),
        "category": "ai-workflow",
        "tags": [
            "open-webui",
            "rag",
            "embeddings",
            "reranker",
            "litellm",
            "tei",
            "huggingface",
            "bge-m3",
        ],
    },
}

# Per-skill category/tags overrides for standalone plugins (skills not
# matched by any GROUPS entry). Empty by default — add entries here only
# when a new skill lands that isn't assigned to a suite.
STANDALONE_META: dict[str, dict] = {}


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    lines = m.group(1).splitlines()
    result: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        kv = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if not kv:
            i += 1
            continue
        key, val = kv.group(1), kv.group(2).strip()
        if val in {">-", ">", "|-", "|"}:
            buf = []
            i += 1
            while i < len(lines) and (lines[i].startswith(" ") or lines[i] == ""):
                buf.append(lines[i].strip())
                i += 1
            result[key] = " ".join(b for b in buf if b)
        else:
            if (val.startswith('"') and val.endswith('"')) or (
                val.startswith("'") and val.endswith("'")
            ):
                val = val[1:-1]
            result[key] = val
            i += 1
    return result


def tagline(desc: str) -> str:
    desc = re.sub(r"\s+", " ", desc.strip())
    m = re.search(r"(\. |\? |! | — | - Triggers )", desc)
    if m:
        desc = desc[: m.start()].rstrip(" .")
    if len(desc) <= TAGLINE_CAP:
        return desc
    return desc[:TAGLINE_CAP].rsplit(" ", 1)[0] + "…"


def run_git(*args: str) -> str:
    r = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    return r.stdout


def _pathspec(skill_dirs: list[pathlib.Path]) -> list[str]:
    """Pathspec covering the given skill dirs but excluding each
    `.claude-plugin/` subtree, so generator runs don't self-bump."""
    specs: list[str] = []
    for d in skill_dirs:
        rel = str(d.relative_to(REPO_ROOT))
        specs.append(rel)
        specs.append(f":(exclude){rel}/.claude-plugin")
    return specs


def commit_count(skill_dirs: list[pathlib.Path]) -> int:
    out = run_git("log", "--oneline", "--", *_pathspec(skill_dirs))
    return sum(1 for line in out.splitlines() if line.strip())


def last_commit_date(skill_dirs: list[pathlib.Path]) -> str | None:
    out = run_git(
        "log",
        "-1",
        "--format=%cd",
        "--date=format-local:%Y%m%d",
        "--",
        *_pathspec(skill_dirs),
    ).strip()
    return out or None


def staged_touches(skill_dirs: list[pathlib.Path]) -> bool:
    rels = [str(d.relative_to(REPO_ROOT)) for d in skill_dirs]
    skip_prefixes = [r + "/.claude-plugin/" for r in rels]
    prefixes = [r + "/" for r in rels]
    out = run_git("diff", "--cached", "--name-only")
    for f in out.splitlines():
        if any(f.startswith(sp) for sp in skip_prefixes):
            continue
        if f in rels or any(f.startswith(p) for p in prefixes):
            return True
    return False


def today_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")


def version_for(skill_dirs: list[pathlib.Path]) -> str:
    count = commit_count(skill_dirs)
    date = last_commit_date(skill_dirs) or today_utc()
    if staged_touches(skill_dirs):
        count += 1
        date = today_utc()
    if count == 0:
        count = 1
    return f"0.{date}.{count}"


def gather_skills() -> list[pathlib.Path]:
    return sorted(p.parent for p in SKILLS_DIR.glob("*/SKILL.md"))


def plugin_entry(
    name: str,
    description: str,
    skill_dirs: list[pathlib.Path],
    category: str | None,
    tags: list[str],
) -> dict:
    entry = {
        "name": name,
        "source": "./",
        "description": description,
        "version": version_for(skill_dirs),
        "author": {"name": AUTHOR_NAME},
        "license": LICENSE,
        "skills": ["./" + str(d.relative_to(REPO_ROOT)) for d in skill_dirs],
        "strict": False,
    }
    if category:
        entry["category"] = category
    if tags:
        entry["tags"] = list(tags)
    return entry


def build_plugins() -> list[dict]:
    all_skills = gather_skills()

    group_members: dict[str, list[pathlib.Path]] = {g: [] for g in GROUPS}
    standalone: list[pathlib.Path] = []
    for skill_dir in all_skills:
        for gname, gcfg in GROUPS.items():
            glob = gcfg.get("glob")
            members = gcfg.get("members")
            if glob and fnmatch.fnmatch(skill_dir.name, glob):
                group_members[gname].append(skill_dir)
                break
            if members and skill_dir.name in members:
                group_members[gname].append(skill_dir)
                break
        else:
            standalone.append(skill_dir)

    plugins: list[dict] = []

    for gname in sorted(GROUPS):
        members = group_members[gname]
        if not members:
            continue
        gcfg = GROUPS[gname]
        plugins.append(
            plugin_entry(
                name=gname,
                description=gcfg["description"],
                skill_dirs=members,
                category=gcfg.get("category"),
                tags=gcfg.get("tags", []),
            )
        )

    for skill_dir in standalone:
        fm = parse_frontmatter((skill_dir / "SKILL.md").read_text())
        meta = STANDALONE_META.get(skill_dir.name, {})
        plugins.append(
            plugin_entry(
                name=fm.get("name", skill_dir.name),
                description=tagline(fm.get("description", "")),
                skill_dirs=[skill_dir],
                category=meta.get("category"),
                tags=meta.get("tags", []),
            )
        )

    return plugins


def write_marketplace(plugins: list[dict]) -> bool:
    data = {
        "name": MARKETPLACE_NAME,
        "owner": {"name": OWNER_NAME},
        "metadata": {"description": MARKETPLACE_DESC},
        "plugins": plugins,
    }
    MARKETPLACE_FILE.parent.mkdir(parents=True, exist_ok=True)
    new = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if MARKETPLACE_FILE.exists() and MARKETPLACE_FILE.read_text() == new:
        return False
    MARKETPLACE_FILE.write_text(new)
    return True


def remove_legacy_plugin_jsons() -> int:
    count = 0
    for pj in SKILLS_DIR.glob("*/.claude-plugin/plugin.json"):
        pj.unlink()
        parent = pj.parent
        try:
            parent.rmdir()
        except OSError:
            pass
        count += 1
    return count


def main() -> int:
    plugins = build_plugins()
    if not plugins:
        print("error: no plugins", file=sys.stderr)
        return 2
    removed = remove_legacy_plugin_jsons()
    changed = write_marketplace(plugins)
    if removed:
        print(f"removed {removed} legacy plugin.json files")
    if changed:
        print(f"regenerated marketplace for {len(plugins)} plugins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
