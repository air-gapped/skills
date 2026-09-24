#!/usr/bin/env python3
"""Machine-owned compatibility data for k8s-components-checker.

  compat.py sync           regenerate references/compat/generated.json (needs gh + network)
  compat.py sync --check   regenerate in memory, print drift vs the committed file, exit 1 on drift
  compat.py check ...      evaluate a target stack against generated.json (offline)
  compat.py selfcheck      run the built-in assertions

generated.json holds only what can be read mechanically: per-line release ceilings
(community edition for Rancher), Rancher's own k8s window (chart kubeVersion),
which RKE2 versions each Rancher line can provision (KDM), RKE2 bundled component
versions (release body tables), rancher-logging gates (catalog annotations) and
Harvester's embedded RKE2/Rancher (harvester-installer pins). Judgment — breaking
changes, upgrade order, vendor matrix pages — stays in the compat/*.md prose.
"""

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

GEN = (
    Path(__file__).resolve().parent.parent / "references" / "compat" / "generated.json"
)

# name -> release source. min = lowest tracked line (matches the compat/*.md min_tracked_version).
COMPONENTS = {
    "rke2": {"gh": "rancher/rke2", "min": "1.31", "edition": "suse"},
    "rancher": {"gh": "rancher/rancher", "min": "2.11", "edition": "suse"},
    "harvester": {"gh": "harvester/harvester", "min": "1.5"},
    "cilium": {"gh": "cilium/cilium", "min": "1.17"},
    "tetragon": {"gh": "cilium/tetragon", "min": "1.5"},
    "cert-manager": {"gh": "cert-manager/cert-manager", "min": "1.17"},
    "kyverno": {"gh": "kyverno/kyverno", "min": "1.16"},
    "keda": {"gh": "kedacore/keda", "min": "2.17"},
    "argo-cd": {"gh": "argoproj/argo-cd", "min": "3.0"},
    "harbor": {"gh": "goharbor/harbor", "min": "2.11"},
    "traefik": {"gh": "traefik/traefik", "min": "2.11"},
    "rook": {"gh": "rook/rook", "min": "1.17"},
    "ceph": {"git": "https://github.com/ceph/ceph", "min": "18", "ceph": True},
    "openebs-lvm-localpv": {
        "gh": "openebs/lvm-localpv",
        "min": "1.5",
        "alt_prefix": "lvm-localpv-",
    },
    "gitlab-chart": {"gitlab": "gitlab-org/charts/gitlab", "min": "8.11"},
    "nvidia-gpu-operator": {"gh": "NVIDIA/gpu-operator", "min": "25.3"},
    "eck": {"gh": "elastic/cloud-on-k8s", "min": "2.16"},
    "zalando-postgres-operator": {"gh": "zalando/postgres-operator", "min": "1.13"},
    "mimir-chart": {
        "git": "https://github.com/grafana/mimir",
        "prefix": "mimir-distributed-",
        "min": "5.7",
    },
}
BUNDLE_LINES = 4  # newest RKE2 lines whose release-body component tables are recorded

VER = re.compile(
    r"v?(\d+)\.(\d+)(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?(?:\+([0-9A-Za-z.-]+))?$"
)


# --- versions -------------------------------------------------------------------------------


def parse(v):
    m = VER.match(v.strip())
    if not m:
        return None
    major, minor, patch, pre, build = m.groups()
    return int(major), int(minor), int(patch or 0), pre, build


def _ids(s):
    return tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in s.split("."))


def vkey(v):
    """Sort key: prerelease < release; RKE2 build suffix (+rke2rN) breaks ties."""
    p = parse(v)
    if not p:
        return (-1,)
    major, minor, patch, pre, build = p
    build_n = int(re.sub(r"\D", "", build) or 0) if build else 0
    return (major, minor, patch, 0 if pre else 1, _ids(pre) if pre else (), build_n)


def satisfies(version, constraint):
    """Helm/semver-style constraint, space-separated ANDed clauses: '>= 1.34.0-0 < 1.37.0-0'."""
    k = vkey(version)
    for op, ver in re.findall(
        r"(>=|<=|>|<|=|!=)?\s*v?(\d+\.\d+(?:\.\d+)?(?:-[0-9A-Za-z.-]+)?)", constraint
    ):
        c = vkey(ver)
        ok = {
            ">=": k >= c,
            "<=": k <= c,
            ">": k > c,
            "<": k < c,
            "!=": k != c,
            "=": k == c,
            "": k == c,
        }[op]
        if not ok:
            return False
    return True


def line_of(v, ceph=False):
    p = parse(v)
    if p is None:
        raise ValueError(f"unparseable version {v!r}")
    return f"{p[0]}" if ceph else f"{p[0]}.{p[1]}"


def line_ge(line, floor):
    return vkey(line + ".0") >= vkey(
        floor + (".0" if floor.count(".") == 1 else ".0.0")
    )


# --- fetch ----------------------------------------------------------------------------------


def run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def gh_api(path, jq=None, paginate=False, raw=False):
    cmd = (
        ["gh", "api", path]
        + (["-H", "Accept: application/vnd.github.raw"] if raw else [])
        + (["--paginate"] if paginate else [])
        + (["--jq", jq] if jq else [])
    )
    return run(cmd)


def gh_file(repo, path, ref):
    return base64.b64decode(
        json.loads(gh_api(f"repos/{repo}/contents/{path}?ref={ref}"))["content"]
    ).decode()


def http(url):
    if not url.startswith("https://"):
        raise ValueError(f"refusing non-https URL {url!r}")
    try:
        return run(["curl", "-sSfL", "--max-time", "120", "--proto", "=https", url])
    except subprocess.CalledProcessError as e:
        raise OSError(f"GET {url}: curl exit {e.returncode}") from e


def releases_gh(repo, with_body):
    jq = (
        ".[] | {t: .tag_name, p: .prerelease, d: .draft, at: .published_at"
        + (", b: .body" if with_body else "")
        + "}"
    )
    out = gh_api(f"repos/{repo}/releases?per_page=100", jq=jq, paginate=True)
    rels = [json.loads(line) for line in out.splitlines() if line.strip()]
    return [r for r in rels if not r["d"]]


def tags_git(url, prefix=""):
    out = run(["git", "ls-remote", "--tags", url])
    tags = {
        ln.split("refs/tags/")[1].removesuffix("^{}")
        for ln in out.splitlines()
        if "refs/tags/" in ln
    }
    return [
        {"t": t[len(prefix) :], "p": False, "at": None}
        for t in tags
        if t.startswith(prefix)
    ]


def tags_gitlab(project):
    out, page = [], 1
    enc = project.replace("/", "%2F")
    while page <= 20:
        batch = json.loads(
            http(
                f"https://gitlab.com/api/v4/projects/{enc}/repository/tags?per_page=100&page={page}"
            )
        )
        if not batch:
            break
        out += [
            {
                "t": t["name"],
                "p": False,
                "at": (t.get("commit") or {}).get("created_at"),
            }
            for t in batch
            if t["name"].startswith("v")  # chart tags; app-era tags lack the prefix
        ]
        page += 1
    return out


# --- editions -------------------------------------------------------------------------------


def suse_edition(body):
    """'prime' | 'community' | None. Prime iff the body redirects to Prime docs or self-declares a
    Prime (not Community) release. An empty body is unclassifiable, not community."""
    body = (body or "").strip()
    if not body:
        return None
    if re.search(r"prime documentation|is a Prime-only release", body, re.I):
        return "prime"
    m = re.search(
        r"This is a (Community and Prime|Community|Prime) version release", body, re.I
    )
    return "prime" if m and "community" not in m.group(1).lower() else "community"


# --- sync -----------------------------------------------------------------------------------


def component_lines(spec):
    ceph = spec.get("ceph", False)
    if "gh" in spec:
        rels = releases_gh(spec["gh"], with_body=spec.get("edition") == "suse")
    elif "gitlab" in spec:
        rels = tags_gitlab(spec["gitlab"])
    else:
        rels = tags_git(spec["git"], spec.get("prefix", ""))
    stable, pre = {}, {}
    for r in rels:
        # some repos tag one line under two schemes (v1.6.1 and lvm-localpv-1.6.2)
        r["v"] = r["t"].removeprefix(spec.get("alt_prefix", ""))
        p = parse(r["v"])
        if not p:
            continue
        is_pre = r["p"] or bool(p[3]) or (ceph and p[1] != 2)
        ln = line_of(r["v"], ceph)
        (pre if is_pre else stable).setdefault(ln, []).append(r)
    lines = {}
    for ln, rs in stable.items():
        if not line_ge(ln, spec["min"]):
            continue
        rs.sort(key=lambda r: vkey(r["v"]), reverse=True)
        top = rs[0]
        pick, unclassified = top, []
        if spec.get("edition") == "suse":
            pick = None
            for r in rs:
                ed = suse_edition(r.get("b"))
                if ed == "community":
                    pick = r
                    break
                if ed is None:
                    unclassified.append(r["t"])
        rec = {
            "latest": pick["t"] if pick else None,
            "date": ((pick or {}).get("at") or "")[:10] or None,
        }
        if pick is not top:
            rec["top_tag"] = top["t"]  # newer tags on this line are a different edition
        if unclassified:
            rec["unclassified"] = unclassified  # empty release body: edition unknown
        lines[ln] = rec
    newest = max(lines, key=lambda x: vkey(x + ".0"), default=None)
    upcoming = {}
    for ln, rs in pre.items():
        if ln in stable or (newest and vkey(ln + ".0") <= vkey(newest + ".0")):
            continue
        rs.sort(key=lambda r: vkey(r["v"]), reverse=True)
        upcoming[ln] = rs[0]["t"]
    out = {"lines": lines}
    if upcoming:
        out["upcoming"] = upcoming
    return out


def parse_tables(body):
    """Every '| name | value | …' row of a markdown release body -> {name: value}; links flattened."""
    rows = {}
    for ln in (body or "").splitlines():
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if (
            len(cells) < 2
            or not cells[0]
            or set(cells[0]) <= set("-: ")
            or cells[0].lower() == "component"
        ):
            continue
        val = (
            re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cells[1])
            .replace("<br/>", " / ")
            .strip()
        )
        # first table wins: component tables precede known-issue / docs tables
        rows.setdefault(re.sub(r"\s*\(Default\)", "", cells[0]), val)
    return rows


def index_entry(index_yaml, chart):
    """Newest entry of <chart> in a Helm index.yaml -> {version, kube-version, rancher-version}."""
    m = re.search(
        rf"\n  {re.escape(chart)}:\n(.*?)(?=\n  [A-Za-z0-9-]+:\n|\ngenerated:|\Z)",
        index_yaml,
        re.S,
    )
    if not m:
        return None
    best = None
    for item in re.split(r"\n  - ", "\n" + m.group(1))[1:]:
        ver = re.search(r"^\s*version: (\S+)", item, re.M)
        if not ver:
            continue
        rec = {"version": ver.group(1).strip("'\"")}
        for key in ("kube-version", "rancher-version"):
            a = re.search(rf"catalog\.cattle\.io/{key}: (.+)", item)
            if a:
                rec[key] = a.group(1).strip().strip("'\"")
        if best is None or vkey(rec["version"].split("+")[0]) > vkey(
            best["version"].split("+")[0]
        ):
            best = rec
    return best


def edges_rancher(rancher_lines):
    mgmt, manages, logging = {}, {}, {}
    for ln, rec in rancher_lines.items():
        tag = rec.get("latest")
        if not tag:
            continue
        try:
            chart = gh_file("rancher/rancher", "chart/Chart.yaml", tag)
            kv = re.search(r"^kubeVersion:\s*(.+)$", chart, re.M)
            mgmt[ln] = {
                "rancher": tag,
                "kubeVersion": kv.group(1).strip().strip("'\"") if kv else None,
            }
        except subprocess.CalledProcessError:
            mgmt[ln] = {"rancher": tag, "kubeVersion": None}
        try:
            kdm = json.loads(
                http(
                    f"https://raw.githubusercontent.com/rancher/kontainer-driver-metadata/release-v{ln}/data/data.json"
                )
            )
            per_line = {}
            for r in kdm.get("rke2", {}).get("releases", []):
                lo, hi = (
                    r.get("minChannelServerVersion"),
                    r.get("maxChannelServerVersion"),
                )
                if lo and hi and satisfies(tag, f">= {lo} <= {hi}"):
                    rl = line_of(r["version"])
                    if rl not in per_line or vkey(r["version"]) > vkey(per_line[rl]):
                        per_line[rl] = r["version"]
            manages[ln] = {
                "rancher": tag,
                "rke2": dict(sorted(per_line.items(), key=lambda x: vkey(x[0] + ".0"))),
            }
        except OSError as e:
            manages[ln] = {"rancher": tag, "error": f"KDM release-v{ln}: {e}"}
        try:
            idx = http(
                f"https://raw.githubusercontent.com/rancher/charts/release-v{ln}/index.yaml"
            )
            logging[ln] = index_entry(idx, "rancher-logging")
        except OSError as e:
            logging[ln] = {"error": f"rancher/charts release-v{ln}: {e}"}
    return mgmt, manages, logging


def edges_rke2(rke2_lines):
    out = {}
    for ln in sorted(rke2_lines, key=lambda x: vkey(x + ".0"))[-BUNDLE_LINES:]:
        tag = rke2_lines[ln]["latest"]
        body = gh_api(f"repos/rancher/rke2/releases/tags/{tag}", jq=".body")
        out[ln] = {"rke2": tag, "components": parse_tables(body)}
    return out


def edges_harvester(harvester_lines):
    """Embedded stack from each Harvester release body's 'Component Versions' table."""
    out = {}
    for ln, rec in harvester_lines.items():
        tag = rec["latest"]
        body = gh_api(f"repos/harvester/harvester/releases/tags/{tag}", jq=".body")
        # earlier tables in the notes (known issues, docs links) reuse component names
        at = re.search(r"^#+\s*Component Versions", body, re.M | re.I)
        rows = parse_tables(body[at.start() :] if at else body)
        pick = {"harvester": tag}
        for key, pat in (
            ("rke2", r"^rke2$"),
            ("rancher", r"rancher"),
            ("kubevirt", r"kubevirt"),
            ("longhorn", r"longhorn"),
        ):
            pick[key] = next(
                (v for k, v in rows.items() if re.search(pat, k, re.I)), None
            )
        out[ln] = pick
    return out


def html_table_after(html, anchor):
    """Rows (lists of cell text) of the first <table> after `anchor` in an HTML page."""
    i = html.find(anchor)
    if i < 0:
        return []
    seg = html[i : html.find("</table>", i)]
    rows = []
    for tr in re.findall(r"<tr.*?</tr>", seg, re.S):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        rows.append([" ".join(re.sub(r"<[^>]+>", " ", c).split()) for c in cells])
    return rows


def edges_harvester_rancher(harvester_lines):
    """SUSE support matrix: which Rancher line manages each Harvester line, and the
    RKE2 versions its Node Driver supports for guest clusters."""
    out = {}
    for ln in harvester_lines:
        url = f"https://www.suse.com/suse-harvester/support-matrix/all-supported-versions/harvester-v{ln.replace('.', '-')}-x/"
        try:
            rows = html_table_after(http(url), 'id="harvester-rancher-support-matrix"')
        except OSError as e:
            out[ln] = {"error": str(e)}
            continue
        out[ln] = [
            {
                "harvester": r[0],
                "rancher": r[1],
                "node_driver": r[2] if len(r) > 2 else None,
            }
            for r in rows
            if len(r) >= 2 and r[0].lower().startswith("v")
        ]
    return out


def minmax(versions):
    vs = sorted({v.strip().lstrip("v") for v in versions}, key=lambda x: vkey(x + ".0"))
    return [vs[0], vs[-1]] if vs else None


def raw_gh(repo, path, ref):
    return gh_api(f"repos/{repo}/contents/{path}?ref={ref}", jq=None, raw=True)


def windows_per_tag(lines, repo, path, extract):
    out = {}
    for ln, rec in lines.items():
        try:
            w = extract(raw_gh(repo, path, rec["latest"]), ln)
        except subprocess.CalledProcessError:
            w = None
        out[ln] = (
            {"k8s": w, "source": f"{repo}/{path}@{rec['latest']}"}
            if w
            else {"k8s": None}
        )
    return out


def k8s_windows(comps):
    L = {n: c["lines"] for n, c in comps.items()}
    W = {}

    def cilium(t, _ln):
        m = re.search(r"^\|\s*(1\.\d+(?:,\s*1\.\d+)*)\s*\|", t, re.M)
        return minmax(m.group(1).split(",")) if m else None

    W["cilium"] = windows_per_tag(
        L["cilium"],
        "cilium/cilium",
        "Documentation/network/kubernetes/compatibility.rst",
        cilium,
    )

    def argo(t, ln):
        m = re.search(rf"^\|\s*{re.escape(ln)}\s*\|([^|]+)\|", t, re.M)
        return minmax(re.findall(r"1\.\d+", m.group(1))) if m else None

    W["argo-cd"] = windows_per_tag(
        L["argo-cd"],
        "argoproj/argo-cd",
        "docs/operator-manual/tested-kubernetes-versions.md",
        argo,
    )

    def rook(t, _ln):
        m = re.search(r"v(1\.\d+)\*\* through \*\*v(1\.\d+)", t)
        return [m.group(1), m.group(2)] if m else None

    W["rook"] = windows_per_tag(
        L["rook"],
        "rook/rook",
        "Documentation/Getting-Started/Prerequisites/prerequisites.md",
        rook,
    )

    # one page carries every line
    def table_windows(name, text, row_re, src):
        found = {}
        for m in re.finditer(row_re, text, re.M):
            found[m.group(1)] = minmax(re.findall(r"1\.\d+", m.group(2)))
        W[name] = {
            ln: ({"k8s": found[ln], "source": src} if found.get(ln) else {"k8s": None})
            for ln in L[name]
        }

    keda_newest = max(L["keda"], key=lambda x: vkey(x + ".0"))
    kp = f"content/docs/{keda_newest}/operate/cluster.md"
    table_windows(
        "keda",
        raw_gh("kedacore/keda-docs", kp, "main"),
        r"^\|\s*v(\d+\.\d+)\s*\|([^|]+)\|",
        f"kedacore/keda-docs/{kp}@main",
    )

    cp = "content/docs/releases/README.md"
    table_windows(
        "cert-manager",
        raw_gh("cert-manager/website", cp, "master"),
        r"^\|\s*\[?(\d+\.\d+)\]?(?:\[\])?\s*\|[^|]*\|[^|]*\|([^|/]+)",
        f"cert-manager/website/{cp}@master",
    )

    vt = raw_gh("kyverno/website", "src/constants/version.ts", "main")
    ky = {}
    for m in re.finditer(
        r"kyverno:\s*'(\d+\.\d+)\.x',\s*minKubernetes:\s*'([\d.]+)',\s*maxKubernetes:\s*'([\d.]+)'",
        vt,
    ):
        ky[m.group(1)] = [m.group(2), m.group(3)]
    W["kyverno"] = {
        ln: (
            {"k8s": ky[ln], "source": "kyverno/website/src/constants/version.ts@main"}
            if ln in ky
            else {"k8s": None}
        )
        for ln in L["kyverno"]
    }

    et = raw_gh("elastic/docs-content", "deploy-manage/deploy/cloud-on-k8s.md", "main")
    blocks = re.findall(
        r"applies-item\}\s*eck:\s*ga\s*(=?)(\d+\.\d+)(\+?)(.*?):::", et, re.S
    )
    ek = {}
    for ln in L["eck"]:
        best = None
        for eq, ver, plus, body in blocks:
            m = re.search(r"\{\{k8s\}\}\s*(1\.\d+)-(1\.\d+)", body)
            if not m:
                continue
            if (eq and ver == ln) or (plus and vkey(ver + ".0") <= vkey(ln + ".0")):
                if best is None or eq:
                    best = [m.group(1), m.group(2)]
        ek[ln] = (
            {
                "k8s": best,
                "source": "elastic/docs-content/deploy-manage/deploy/cloud-on-k8s.md@main",
            }
            if best
            else {"k8s": None}
        )
    W["eck"] = ek

    nv = {}
    for ln in L["nvidia-gpu-operator"]:
        url = f"https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/{ln}/platform-support.html"
        try:
            ranges = re.findall(
                r"(1\.\d+)\s*(?:—|–|&#8212;|&mdash;|---)\s*(1\.\d+)", http(url)
            )
        except OSError:
            ranges = []
        if ranges:
            lo, hi = max(
                set(ranges), key=ranges.count
            )  # the k8s column repeats per OS row
            nv[ln] = {"k8s": [lo, hi], "source": url}
        else:
            nv[ln] = {"k8s": None}
    W["nvidia-gpu-operator"] = nv
    return W


def edges_gitlab(chart_lines):
    """GitLab chart: k8s status table + chart->GitLab version for the newest chart release."""
    newest = max(chart_lines, key=lambda x: vkey(x + ".0"))
    tag = "v" + chart_lines[newest]["latest"].lstrip("v")
    base = "https://gitlab.com/api/v4/projects/gitlab-org%2Fcharts%2Fgitlab/repository/files"
    cloud = http(f"{base}/doc%2Finstallation%2Fcloud%2F_index.md/raw?ref={tag}")
    table = {
        m.group(1): {"status": m.group(2).strip(), "min_gitlab": m.group(3).strip()}
        for m in re.finditer(
            r"^\|\s*(1\.\d+)\s*\|\s*([A-Za-z]+)\s*\|\s*([\d.]+)\s*\|", cloud, re.M
        )
    }
    maps = http(f"{base}/doc%2Finstallation%2Fversion_mappings.md/raw?ref={tag}")
    m = re.search(
        rf"^\|\s*{re.escape(tag.lstrip('v'))}\s*\|\s*([\d.]+)\s*\|", maps, re.M
    )
    return {"chart": tag, "gitlab": m.group(1) if m else None, "k8s": table}


def build():
    comps = {}
    for name, spec in COMPONENTS.items():
        print(f"  {name}", file=sys.stderr)
        comps[name] = component_lines(spec)
    print("  edges", file=sys.stderr)
    mgmt, manages, logging = edges_rancher(comps["rancher"]["lines"])
    return {
        "schema": 1,
        "generated_by": "scripts/compat.py sync — do not edit by hand",
        "components": comps,
        "edges": {
            "rancher_mgmt_k8s": mgmt,
            "rancher_provisions_rke2": manages,
            "rancher_logging": logging,
            "rke2_bundles": edges_rke2(comps["rke2"]["lines"]),
            "harvester_embeds": edges_harvester(comps["harvester"]["lines"]),
            "harvester_rancher": edges_harvester_rancher(comps["harvester"]["lines"]),
            "gitlab_k8s": edges_gitlab(comps["gitlab-chart"]["lines"]),
            "k8s_windows": k8s_windows(comps),
        },
    }


def diff(old, new, path=""):
    if isinstance(old, dict) and isinstance(new, dict):
        out = []
        for k in sorted(set(old) | set(new), key=str):
            p = f"{path}.{k}" if path else str(k)
            if k not in old:
                out.append(f"+ {p}: {json.dumps(new[k])[:200]}")
            elif k not in new:
                out.append(f"- {p}: {json.dumps(old[k])[:200]}")
            else:
                out += diff(old[k], new[k], p)
        return out
    return (
        []
        if old == new
        else [f"~ {path}: {json.dumps(old)[:100]} -> {json.dumps(new)[:100]}"]
    )


def dump(data):
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def cmd_sync(check):
    new = build()
    old = json.loads(GEN.read_text()) if GEN.exists() else {}
    changes = diff(old, new)
    for c in changes:
        print(c)
    if check:
        print(
            f"{len(changes)} drift item(s)" if changes else "no drift", file=sys.stderr
        )
        return 1 if changes else 0
    GEN.write_text(dump(new))
    print(f"wrote {GEN} ({len(changes)} change(s))", file=sys.stderr)
    return 0


# --- check ----------------------------------------------------------------------------------


def cmd_check(a):
    d = json.loads(GEN.read_text())
    comps, e = d["components"], d["edges"]
    res = []

    def say(level, msg):
        res.append(level)
        print(f"{level:5} {msg}")

    def line_state(name, ln):
        c = comps[name]
        if ln in c["lines"]:
            return "ga"
        return "upcoming" if ln in c.get("upcoming", {}) else "unknown"

    for name, ln in (
        ("rancher", a.rancher),
        ("rke2", a.downstream_rke2),
        ("harvester", a.harvester),
    ):
        if ln:
            st = line_state(name, ln)
            if st == "ga":
                say(
                    "OK",
                    f"{name} {ln}: GA, latest {comps[name]['lines'][ln]['latest']}",
                )
            else:
                say(
                    "BLOCK",
                    f"{name} {ln}: {st} — {comps[name].get('upcoming', {}).get(ln, 'no release found')}",
                )

    if a.rancher:
        mg = e["rancher_mgmt_k8s"].get(a.rancher, {})
        if a.mgmt_k8s and mg.get("kubeVersion"):
            ok = satisfies(a.mgmt_k8s + ".0", mg["kubeVersion"])
            say(
                "OK" if ok else "BLOCK",
                f"Rancher {mg['rancher']} on a k8s {a.mgmt_k8s} management cluster (chart kubeVersion '{mg['kubeVersion']}')",
            )
        prov = e["rancher_provisions_rke2"].get(a.rancher, {})
        if a.downstream_rke2 and "rke2" in prov:
            top = prov["rke2"].get(a.downstream_rke2)
            if top:
                say(
                    "OK",
                    f"Rancher {prov['rancher']} provisions RKE2 {a.downstream_rke2} (KDM up to {top})",
                )
            else:
                say(
                    "BLOCK",
                    f"Rancher {prov['rancher']} KDM has no RKE2 {a.downstream_rke2}; provisionable lines: {', '.join(prov['rke2'])}",
                )
        lg = e["rancher_logging"].get(a.rancher) or {}
        for label, k in (("management", a.mgmt_k8s), ("downstream", a.downstream_rke2)):
            if k and lg.get("kube-version"):
                ok = satisfies(k + ".0", lg["kube-version"])
                say(
                    "OK" if ok else "WARN",
                    f"rancher-logging {lg['version']} on {label} k8s {k} (kube-version '{lg['kube-version']}')",
                )

    if a.downstream_rke2 and a.downstream_rke2 in e["rke2_bundles"]:
        b = e["rke2_bundles"][a.downstream_rke2]
        keep = (
            "Kubernetes",
            "Containerd",
            "Etcd",
            "Cilium",
            "Calico",
            "Traefik",
            "Ingress-Nginx",
            "CoreDNS",
        )
        say(
            "INFO",
            f"RKE2 {b['rke2']} ships "
            + ", ".join(
                f"{k} {b['components'][k]}" for k in keep if k in b["components"]
            ),
        )

    if a.harvester:
        h = e["harvester_embeds"].get(a.harvester, {})
        say(
            "INFO",
            f"Harvester {h.get('harvester')} embeds RKE2 {h.get('rke2')} + Rancher {h.get('rancher')}",
        )
        rows = e.get("harvester_rancher", {}).get(a.harvester)
        if not isinstance(rows, list) or not rows:
            say(
                "WARN",
                f"Harvester {a.harvester}: no SUSE Harvester–Rancher matrix row found",
            )
        else:
            ranchers = [r["rancher"].lstrip("v") for r in rows]
            if a.rancher:
                ok = a.rancher in ranchers
                say(
                    "OK" if ok else "BLOCK",
                    f"Rancher {a.rancher} manages Harvester {a.harvester} (SUSE matrix: Rancher {', '.join(ranchers)})",
                )
            if a.downstream_rke2:
                nd = " ".join(r.get("node_driver") or "" for r in rows)
                ok = a.downstream_rke2 in re.findall(r"1\.\d+", nd)
                say(
                    "OK" if ok else "BLOCK",
                    f"Harvester {a.harvester} Node Driver provisions RKE2 {a.downstream_rke2} guest clusters ({nd.strip()})",
                )

    k8s = a.k8s or a.downstream_rke2
    for spec in a.with_ or []:
        name, _, ln = spec.partition("=")
        if not k8s:
            say("WARN", f"{spec}: give --k8s (or --downstream-rke2) to test its window")
            continue
        if name == "gitlab-chart":
            g = e.get("gitlab_k8s", {})
            row = g.get("k8s", {}).get(k8s)
            if not row:
                say(
                    "BLOCK",
                    f"GitLab chart {g.get('chart')}: k8s {k8s} not in its support table",
                )
            else:
                ok = row["status"] == "Supported" and vkey(
                    g.get("gitlab") or "0.0"
                ) >= vkey(row["min_gitlab"])
                say(
                    "OK" if ok else "BLOCK",
                    f"GitLab chart {g.get('chart')} (GitLab {g.get('gitlab')}) on k8s {k8s}: {row['status']}, needs GitLab ≥ {row['min_gitlab']}",
                )
            continue
        w = e.get("k8s_windows", {}).get(name, {}).get(ln)
        if not w or not w.get("k8s"):
            say(
                "WARN",
                f"{name} {ln}: no machine-read k8s window — read compat/{name}.md",
            )
            continue
        lo, hi = w["k8s"]
        ok = vkey(lo + ".0") <= vkey(k8s + ".0") <= vkey(hi + ".0")
        say(
            "OK" if ok else "BLOCK",
            f"{name} {ln} on k8s {k8s} (supported {lo}–{hi}; {w['source']})",
        )
    return 1 if "BLOCK" in res else 0


# --- selfcheck ------------------------------------------------------------------------------


def selfcheck():
    assert vkey("v2.15.0-alpha1") < vkey("v2.15.2") < vkey("v2.15.99")
    assert vkey("v1.33.13+rke2r1") < vkey("v1.33.13+rke2r2") < vkey("v1.33.14+rke2r1")
    assert vkey("v1.37.0-rc1+rke2r1") < vkey("v1.37.0+rke2r1")
    assert satisfies("1.36.0", "< 1.37.0-0") and not satisfies("1.37.0", "< 1.37.0-0")
    assert not satisfies("1.33.0", ">= 1.34.0-0 < 1.37.0-0") and satisfies(
        "1.34.0", ">= 1.34.0-0 < 1.37.0-0"
    )
    assert satisfies("v2.15.2", ">= v2.15.0-alpha1 <= v2.15.99") and not satisfies(
        "v2.16.0", ">= v2.15.0-alpha1 <= v2.15.99"
    )
    assert line_of("v20.2.4", ceph=True) == "20" and line_of("v1.36.4+rke2r1") == "1.36"
    assert (
        line_ge("1.37", "1.31") and not line_ge("2.10", "2.11") and line_ge("20", "18")
    )
    assert (
        suse_edition("Please refer to our [Prime Documentation](https://x)") == "prime"
    )
    assert (
        suse_edition("# Release v2.11.4\n\nThis is a Prime version release.") == "prime"
    )
    assert suse_edition("This is a Community and Prime version release.") == "community"
    assert suse_edition("# Release v2.11.1\n\nlegacy body") == "community"
    assert suse_edition("") is None and suse_edition(None) is None
    assert (
        suse_edition("> [!NOTE]\n> `v1.31.14+rke2r2` is a Prime-only release.")
        == "prime"
    )
    body = (
        "## Packaged Component Versions\n| Component | Version |\n| --- | --- |\n"
        "| Kubernetes | [v1.37.0](https://k8s) |\n| Containerd | [v2.3.4-k3s1](https://c) |\n"
        "### Available CNIs\n| Component | Version | FIPS Compliant |\n| --- | --- | --- |\n"
        "| Canal (Default) | [Flannel v0.28.9](https://f)<br/>[Calico v3.32.2](https://c) | Yes |\n"
        "| Cilium | [v1.20.1](https://ci) | No |\n"
    )
    t = parse_tables(body)
    assert (
        t["Kubernetes"] == "v1.37.0"
        and t["Cilium"] == "v1.20.1"
        and t["Canal"] == "Flannel v0.28.9 / Calico v3.32.2"
    )
    idx = (
        "entries:\n  rancher-logging:\n  - annotations:\n      catalog.cattle.io/kube-version: '>= 1.34.0-0 < 1.37.0-0'\n"
        "      catalog.cattle.io/rancher-version: '>= 2.15.0-0 < 2.16.0-0'\n    version: 110.0.0+up4.10.0\n"
        "  - annotations:\n      catalog.cattle.io/kube-version: '>= 1.33.0-0 < 1.36.0-0'\n    version: 109.0.1+up4.10.0\n"
        "  rancher-monitoring:\n  - version: 1.0.0\ngenerated: x\n"
    )
    e = index_entry(idx, "rancher-logging")
    assert e == {
        "version": "110.0.0+up4.10.0",
        "kube-version": ">= 1.34.0-0 < 1.37.0-0",
        "rancher-version": ">= 2.15.0-0 < 2.16.0-0",
    }
    assert diff({"a": {"b": 1}}, {"a": {"b": 2, "c": 3}}) == [
        "~ a.b: 1 -> 2",
        "+ a.c: 3",
    ]
    html = (
        '<h2 id="m">Matrix</h2><table><thead><tr><th>Harvester Version</th><th>Rancher Version</th></tr></thead>'
        "<tbody><tr><td><p>v1.9</p></td><td><p>v2.15</p></td></tr></tbody></table><table><tr><td>x</td></tr></table>"
    )
    assert html_table_after(html, 'id="m"') == [
        ["Harvester Version", "Rancher Version"],
        ["v1.9", "v2.15"],
    ]
    assert (
        minmax([" 1.36", "1.33", "v1.34 "]) == ["1.33", "1.36"] and minmax([]) is None
    )
    t = parse_tables(
        "| Component | Version |\n| Longhorn | [v1.12.1](u) |\n\n| Longhorn | GitHub issue |\n"
    )
    assert t["Longhorn"] == "v1.12.1"  # first table wins
    print("selfcheck ok")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync", help="regenerate generated.json from upstream")
    s.add_argument(
        "--check",
        action="store_true",
        help="report drift, do not write; exit 1 on drift",
    )
    c = sub.add_parser("check", help="evaluate a target stack (offline)")
    c.add_argument("--rancher", help="Rancher minor, e.g. 2.15")
    c.add_argument(
        "--mgmt-k8s", help="k8s minor of the cluster Rancher runs on, e.g. 1.36"
    )
    c.add_argument(
        "--downstream-rke2", help="RKE2 minor of clusters Rancher provisions, e.g. 1.37"
    )
    c.add_argument("--harvester", help="Harvester minor, e.g. 1.9")
    c.add_argument(
        "--k8s",
        help="k8s minor to test --with components against (default: --downstream-rke2)",
    )
    c.add_argument(
        "--with",
        dest="with_",
        action="append",
        metavar="COMPONENT=LINE",
        help="component line to test against --k8s, e.g. cilium=1.20 (repeatable)",
    )
    sub.add_parser("selfcheck")
    a = ap.parse_args()
    if a.cmd == "sync":
        return cmd_sync(a.check)
    if a.cmd == "check":
        return cmd_check(a)
    return selfcheck()


if __name__ == "__main__":
    sys.exit(main())
