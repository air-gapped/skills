#!/usr/bin/env python3
"""Check the external links a skill cites, targeting the two classes that actually rot.

The skillevaluator gate has a dead-link check, but it only runs against skills
**staged for a commit** — so a citation can rot for months in a skill nobody is
editing. This sweeps the whole tree.

**Two classes rot; the rest mostly do not.** Measured on the fleet 2026-09-15,
2573 unique URLs:

  * **Documentation hosts** (322 checked, 7 dead). Doc sites reorganise. Worse,
    they reorganise *silently* — the old path 404s while the product is fine.
  * **GitHub `blob`/`tree` paths** (189 checked, 4 dead). GitHub redirects a
    renamed **repo**, but not a **moved file**. All four were relocations, not
    renames, so none was fixable by editing the path — each had to be searched
    for. When a project migrates its docs to a generated site, every deep link
    into the old tree dies at once.

GitHub issue/PR/release URLs and arXiv links were not worth sweeping: they are
stable by design, and they are most of the corpus.

**Two statuses are not findings, and treating them as such is the main way this
check wastes someone's morning:**

  * **403** is a refusal of *this fetcher*, not a missing page. Re-check by hand
    before believing it, and note there are two kinds. A plain user-agent block
    serves the real page to a bare `curl`. A **bot challenge does not** — the
    fleet's one standing 403 returns 403 to bare `curl` too, with
    `<title>Just a moment...`, which is an interstitial rather than the document.
    Neither is a dead link, but only the first can be confirmed from a terminal;
    the second needs a browser, so do not read "curl also failed" as "page gone".
  * **429** means *this sweep* tripped a rate limit — huggingface.co does at
    even modest concurrency. Lower `--workers` and re-run; do not record it.

Placeholder hosts (`localhost`, `example.com`, `host:port`) are skipped.

Usage:
    python3 check-links.py [root] [--all] [--workers N]
    python3 check-links.py --selfcheck

`--all` drops the class filter and checks every URL — slow, noisy, rarely worth it.

Exit: 0 clean, 1 dead links found, 2 usage error.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import re
import subprocess
import sys
from pathlib import Path

URL = re.compile(r"https?://[A-Za-z0-9._~:/?#@!$&*+,;=%-]+")
GH_FILE = re.compile(r"^https?://github\.com/[^/]+/[^/]+/(?:blob|tree)/")
PLACEHOLDER = re.compile(
    r"^https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|host:|<|\$|.*\bexample\.(?:com|org)\b"
    r"|.*\.example\b|my-|your-)",
    re.I,
)

# Hosts whose URLs move. Extend freely; a host absent here is simply not swept
# unless --all is given.
DOC_HOSTS = {
    "docs.vllm.ai",
    "docs.nvidia.com",
    "confluence.atlassian.com",
    "www.keycloak.org",
    "grafana.com",
    "docs.gitlab.com",
    "developers.redhat.com",
    "huggingface.co",
    "cert-manager.io",
    "docs.cilium.io",
    "rook.io",
    "kyverno.io",
    "keda.sh",
    "goharbor.io",
    "docs.openebs.io",
    "doc.traefik.io",
    "docs.openwebui.com",
    "ranchermanager.docs.rancher.com",
    "docs.rancher.com",
    "docs.harvesterhci.io",
    "openebs.io",
    "argo-cd.readthedocs.io",
    "docs.sglang.ai",
    "docs.lmcache.ai",
    "platform.openai.com",
    "docs.docker.com",
    "code.claude.com",
}


def collect(root: Path, everything: bool) -> list[str]:
    seen: set[str] = set()
    for md in sorted(root.rglob("*.md")):
        for m in URL.finditer(md.read_text(encoding="utf-8", errors="replace")):
            u = m.group(0).rstrip(".,;:)*`")
            if PLACEHOLDER.match(u):
                continue
            host = u.split("/")[2] if "://" in u else ""
            if everything or host in DOC_HOSTS or GH_FILE.match(u):
                seen.add(u)
    return sorted(seen)


def check(u: str) -> tuple[str, str]:
    for extra in (["-I"], []):
        r = subprocess.run(
            [
                "curl",
                "-sS",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                "-L",
                "--max-time",
                "30",
                *extra,
                u,
            ],
            capture_output=True,
            text=True,
        )
        code = (r.stdout or "").strip()
        if code and code[0] in "23":
            return u, code
        if code == "405" and extra:  # HEAD refused; retry with GET
            continue
        if not extra:
            return u, code or "ERR"
    return u, code or "ERR"


def selfcheck() -> int:
    assert PLACEHOLDER.match("http://localhost:8080/x")
    assert PLACEHOLDER.match("https://mimir.example.com/api")
    assert not PLACEHOLDER.match("https://docs.vllm.ai/en/stable/")
    assert GH_FILE.match("https://github.com/o/r/blob/main/a.py")
    assert GH_FILE.match("https://github.com/o/r/tree/main/dir")
    assert not GH_FILE.match("https://github.com/o/r/issues/1")
    assert not GH_FILE.match("https://github.com/o/r")
    print("selfcheck: all assertions passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("root", nargs="?", default=".claude/skills", type=Path)
    ap.add_argument(
        "--all", action="store_true", help="check every URL, not just rot-prone classes"
    )
    ap.add_argument(
        "--workers", type=int, default=8, help="concurrency (default 8; lower on 429)"
    )
    ap.add_argument("--selfcheck", action="store_true")
    a = ap.parse_args()

    if a.selfcheck:
        return selfcheck()
    if not a.root.is_dir():
        print(f"not a directory: {a.root}", file=sys.stderr)
        return 2

    targets = collect(a.root, a.all)
    print(
        f"checking {len(targets)} URLs under {a.root} "
        f"({'all' if a.all else 'doc hosts + github file paths'})\n",
        flush=True,
    )

    dead, blocked, limited = [], [], []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, (u, code) in enumerate(ex.map(check, targets), 1):
            if code and code[0] in "23":
                pass
            elif code == "403":
                blocked.append(u)
            elif code == "429":
                limited.append(u)
            else:
                dead.append((code, u))
            if i % 50 == 0:
                print(f"  ...{i}/{len(targets)}", flush=True)

    print(f"\n=== {len(dead)} dead ===")
    for code, u in sorted(dead):
        print(f"{code}  {u}")
    if not dead:
        print("none.")

    if blocked:
        print(
            f"\n=== {len(blocked)} returned 403 — usually a user-agent block, NOT a dead page ==="
        )
        for u in sorted(blocked):
            print(f"      {u}")
    if limited:
        print(
            f"\n=== {len(limited)} returned 429 — this sweep tripped a rate limit ==="
        )
        print(
            f"      Re-run with --workers {max(1, a.workers // 4)}; do not record these as dead."
        )
        for u in sorted(limited)[:10]:
            print(f"      {u}")

    return 1 if dead else 0


if __name__ == "__main__":
    sys.exit(main())
