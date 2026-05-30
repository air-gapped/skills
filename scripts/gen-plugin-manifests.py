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
  (today while the dir has pending uncommitted changes — the version this
  commit will carry)
- N = unique commit count touching any member skill dir, plus 1 while the
  dir has pending changes (staged OR unstaged), so the predicted bump is
  stable across the stage/commit dance and the pre-commit hook converges.
.claude-plugin/ subtree is excluded from pathspec so regenerations don't
self-bump. On regeneration the hook git-adds the manifest so the bump lands
in the same commit (one-pass) instead of forcing an add-then-recommit dance.
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
    "inference-host": {
        # Host-level (below-the-framework) bring-up + tuning suite.
        # Sits beneath any inference engine (vLLM, sglang, TensorRT-
        # LLM) — about the Linux/GPU host, not the framework. Two
        # phases: nvidia-datacenter-bringup gets the host from a
        # clean OS install to a usable driver state; gpu-host-tuning
        # tunes the working host. Room for future siblings: NIC/
        # fabric tuning, NUMA pinning, IRQ affinity, BIOS audit.
        "members": ["nvidia-datacenter-bringup", "gpu-host-tuning"],
        "description": (
            "Inference host bring-up + tuning suite — Linux/GPU "
            "bare-metal host work that sits beneath any inference "
            "framework (vLLM, sglang, TensorRT-LLM). Two phases. "
            "Bring-up (nvidia-datacenter-bringup): Ubuntu 24.04 LTS "
            "from clean OS to gpu-operator cuda-validator passing — "
            "B300/B200/H100/A100/L40S/L4 driver + fabricmanager + "
            "NVLSM + DOCA-OFED install order, NVIDIA CUDA repo + DOCA "
            "repo + air-gap mirror, MOK + DKMS sign-on-build under "
            "Secure Boot, Dell PowerEdge XE9780/XE9785 baseboard "
            "firmware via iDRAC Redfish DellOemChassis.ExtendedReset, "
            "gpu-operator pre-installed-driver-mode integration. "
            "Tuning (gpu-host-tuning): read-only snapshot of CPU "
            "power state, C-states, NUMA topology, PCIe link state, "
            "GPU settings, kernel boot params, sysctl, ulimits, IRQ "
            "affinity, container runtime; optional pinned-host↔GPU "
            "memcpy bench (torch + numactl); per-lever cheat-sheets "
            "to flip settings (governor, EPP, cpuidle, persistence, "
            "ECC, hugepages, intel_iommu, NCCL env, tuned-adm "
            "profiles, BIOS guidance for Dell XE / SMC / HPE). "
            "Surfaces config gaps that bottleneck LMCache CPU-tier "
            "throughput, KV offload, NCCL bandwidth, prefix-cache "
            "rebuild."
        ),
        "category": "inference",
        "tags": [
            "gpu",
            "host-tuning",
            "nvidia",
            "hgx",
            "dgx",
            "b300",
            "blackwell",
            "fabricmanager",
            "nvlsm",
            "doca-ofed",
            "secure-boot",
            "mok",
            "dkms",
            "ubuntu-24.04",
            "air-gap",
            "dell-poweredge",
            "idrac",
            "numa",
            "pcie",
            "bios",
            "nccl",
            "tuned-adm",
            "performance",
            "bare-metal",
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
        "members": [
            "argo-cd-apps",
            "helm",
            "k8s-components-checker",
            "keda",
            "keycloak-iam",
            "openshift-app",
        ],
        "description": (
            "Kubernetes suite — Argo CD application authoring (GitOps "
            "Application/ApplicationSet manifests, sync policies, "
            "AppProjects), Helm chart authoring, KEDA event-driven "
            "autoscaling, Keycloak IAM (Operator + CRDs, realm/client "
            "configuration, OIDC/SAML integration, security hardening), "
            "OpenShift application packaging, and k8s-components-checker "
            "(cross-component compatibility registry for RKE2 community "
            "stacks — kubectl/helm/pluto cluster survey, structured "
            "verdict + pre-upgrade report wrapper, skill-improver freshen "
            "and operator floor-override flows; covers 18 components: "
            "RKE2, Rancher, Harvester, Cilium, cert-manager, Kyverno, "
            "KEDA, Argo CD, Harbor, Traefik, Rook, Ceph, OpenEBS, GitLab, "
            "ECK, Zalando postgres-operator, Grafana Mimir, NVIDIA GPU "
            "Operator)."
        ),
        "category": "kubernetes",
        "tags": [
            "kubernetes",
            "argo-cd",
            "argocd",
            "gitops",
            "applicationset",
            "helm",
            "keda",
            "keycloak",
            "iam",
            "oidc",
            "saml",
            "openshift",
            "autoscaling",
            "ocp",
            "rke2",
            "rancher",
            "harvester",
            "rook",
            "ceph",
            "cilium",
            "cert-manager",
            "compatibility",
            "upgrade-planning",
            "version-skew",
            "drift-review",
            "pluto",
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
    "dell": {
        # Dell hardware operator suite — iDRAC BMC automation and
        # PowerEdge server tooling. Room for siblings: iDRAC RACADM,
        # PowerEdge BIOS attribute reference, OpenManage Enterprise,
        # Dell DUP catalog tooling, Dell Repository Manager, etc.
        "members": ["ansible-idrac-9-10"],
        "description": (
            "Dell hardware suite — Ansible automation against Dell "
            "PowerEdge iDRAC 9 (14G–16G) and iDRAC 10 (17G) BMCs via "
            "the `dellemc.openmanage` collection. Covers the iDRAC 10 "
            "/ iDRAC 9 ≥ 7.30.10.50 `BasicAuthState: Unadvertised` "
            "default that silently 401s `ansible.builtin.uri`, the "
            "canonical `idrac_session` + `x_auth_token` lifecycle, "
            "iDRAC 10 attribute registry deltas (renamed groups, "
            "deprecated `vFlashSD*`/`Telemetry*`/`GroupManager`, the "
            "BIOS→`System.ServerPwr.*` move), iDRAC 9-only modules to "
            "avoid on 17G, WS-MAN removal on 17G, and the upstream "
            "bug catalog. Room for sibling skills covering RACADM, "
            "OpenManage Enterprise, DUP catalogs, and PowerEdge BIOS "
            "tuning."
        ),
        "category": "infrastructure",
        "tags": [
            "dell",
            "poweredge",
            "idrac",
            "idrac9",
            "idrac10",
            "17g",
            "bmc",
            "redfish",
            "racadm",
            "ansible",
            "dellemc-openmanage",
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
        "members": ["open-webui-embeddings", "open-webui-valkey-websocket"],
        "description": (
            "Open WebUI operator suite — RAG pipeline wiring "
            "(HuggingFace embedding + reranker via LiteLLM in front of "
            "HuggingFace Text Embeddings Inference; exact wire shapes, "
            "LiteLLM ↔ TEI gotchas, TEI configuration cliffs, end-to-end "
            "production config; BGE-M3 + BGE-Reranker-v2-m3 worked "
            "examples) and multi-pod deployment with WebSockets + Valkey "
            "Sentinel at 1000+ user scale (the structural Socket.IO + "
            "Redis frame-amplification bug #23733 and the "
            "CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE mitigation, all "
            "multi-pod env vars, custom-model-icon perf history, helm "
            "chart gaps, full known-issues catalog with fix status)."
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
            "websocket",
            "valkey",
            "redis",
            "sentinel",
            "multi-pod",
            "kubernetes",
            "socket-io",
            "scaling",
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


def dir_has_pending_changes(skill_dirs: list[pathlib.Path]) -> bool:
    """True if any member skill dir has uncommitted changes — staged OR
    unstaged OR untracked. Index-independent on purpose: the predicted
    version must be identical whether the skill files are staged yet or
    not, so the regenerate-and-fail / re-add / re-commit loop converges to
    a fixed point instead of flipping the version each pass."""
    rels = [str(d.relative_to(REPO_ROOT)) for d in skill_dirs]
    skip_prefixes = [r + "/.claude-plugin/" for r in rels]
    prefixes = [r + "/" for r in rels]
    out = run_git("status", "--porcelain", "--untracked-files=all")
    for line in out.splitlines():
        path = line[3:] if len(line) > 3 else ""
        if " -> " in path:  # rename: take the destination path
            path = path.split(" -> ", 1)[1]
        if any(path.startswith(sp) for sp in skip_prefixes):
            continue
        if path in rels or any(path.startswith(p) for p in prefixes):
            return True
    return False


def today_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")


def version_for(skill_dirs: list[pathlib.Path]) -> str:
    count = commit_count(skill_dirs)
    date = last_commit_date(skill_dirs) or today_utc()
    if dir_has_pending_changes(skill_dirs):
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
    if changed:
        # Stage the regenerated manifest so the version bump rides along in
        # this commit (one-pass) rather than landing as an unstaged change
        # that fails the hook and forces a re-add / re-commit.
        run_git("add", "--", str(MARKETPLACE_FILE.relative_to(REPO_ROOT)))
    if removed:
        print(f"removed {removed} legacy plugin.json files")
    if changed:
        print(f"regenerated marketplace for {len(plugins)} plugins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
