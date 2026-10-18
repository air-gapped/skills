# vLLM server security — auth, advisories, floors

Load when deciding whether `--api-key` is enough, setting a security floor for
an image, or reading a vLLM advisory.

## `VLLM_API_KEY` / `--api-key` is not an authentication boundary

Treat the key as client wiring, not access control. Front vLLM with a real
authenticating proxy that validates the `Host:` header. Three independent
reasons:

| Reason | Affected | Action |
|---|---|---|
| **CVE-2026-48746 / GHSA-94f4-hr76-p5j6, CRITICAL** — a `Host:` header carrying `/` or `?` steers the path starlette rebuilds from the request scope, so `AuthenticationMiddleware` checks a different path than FastAPI routes; the caller reaches `/v1` without the key | `>= 0.3.0, < 0.22.0` | Run v0.22.0+. v0.22.0 authorises on the raw ASGI `scope["path"]`, which no header reaches |
| **The key gates only `/v1`, `/v2` and `/inference`** (documented from v0.28.0, #51999) | v0.32.0 | `/invocations` stays open — block it at the proxy |
| **CVE-2026-22778, CRITICAL** — a malicious video URL chains a PIL error-message address leak (ASLR bypass) with a JPEG2000 `cdef`-box heap overflow in the OpenCV/FFmpeg decoder; RCE **pre-auth** via `/invocations` even with `--api-key` set | `>= 0.8.3, < 0.14.1`, **only deployments serving a video model** | v0.22.0+ clears it. Do not raise a fleet-wide floor on it — check what the model consumes first |

Instances behind an RFC-conforming server such as nginx were never exposed to
CVE-2026-48746: it rejects the malformed `Host:` before vLLM sees it. A proxy
that forwards `Host:` verbatim without validating it does not give that
protection.

## Reading an advisory's affected range

- **Read the global record**, `gh api /advisories/<GHSA-id>`, not the repository
  advisory. For GHSA-94f4-hr76-p5j6 the global record carries
  `>= 0.3.0, < 0.22.0`; the repository record still shows an unbounded `>=0.3.0`.
- **A bounded range: the upper bound is the floor.** The usual case.
- **An unbounded `vulnerable_version_range` plus a null `first_patched_version`
  is not a floor** — nothing satisfies it. Do not report "no safe version".
  Take the fix PR from the advisory's References and find the first tag that
  carries its merge commit:

  ```bash
  gh pr view <N> --repo <org>/<repo> --json mergeCommit --jq '.mergeCommit.oid'
  git -C <clone> fetch --tags --quiet
  git -C <clone> tag --contains <sha> | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | head -1
  ```

- `first_patched_version` is null on most vLLM advisories. Derive floors from
  the range, never from that field.
