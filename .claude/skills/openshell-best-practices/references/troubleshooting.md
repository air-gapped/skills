# Troubleshooting (0.1.x)

Symptom → cause → fix, from issues filed since 0.1.0. Upstream's `debug-openshell-cluster`
skill covers gateway health in depth; NVIDIA's playbook
(`build.nvidia.com/playbooks/openshell/troubleshooting`) has more entries. Platform-specific
install problems are in `local-gateway.md`, Kubernetes ones in `kubernetes-gateway.md`,
in-sandbox tool breakage in `sandboxes-and-agents.md`.

## Contents

- First moves
- Network denials
- Provisioning and lifecycle
- Auth
- Logs and audit

## First moves

```bash
openshell status                      # gateway, auth mode, version (CLI and gateway should match)
openshell gateway list                # which gateway is active (*); pin with -g <name>
openshell sandbox get <sb> -o json    # phase + conditions (ConfigurationInvalid, MainProcessFailed, ...)
openshell logs <sb> --tail --source sandbox
openshell policy get <sb> --full      # what is actually allowed
```

`openshell doctor check` only checks the container engine responds — it does not verify
Landlock, seccomp or host networking (#4133, #3694).

## Network denials

1. Find the denial: `openshell logs <sb> --tail --source sandbox`, look for
   `NET:OPEN [MED] DENIED <binary> -> host:port [reason:...]` or `HTTP:<METHOD> [MED] DENIED`.
   Policy events log at INFO — don't filter to warnings.
2. Read the `<binary>` in the line: that real path is what `binaries` must list. A denial that
   names `/usr/bin/node-24` when the profile lists `/usr/local/bin/node` is the symlink trap.
3. `credential_endpoint_mismatch`: policy allowed the request, but the credential's binding
   didn't (placeholder sent to a host its profile doesn't name). Fix the profile endpoints, not
   the policy.
4. `policy_dns_trusted_gateway_unavailable` on `host.openshell.internal`: the host alias isn't
   resolvable in this topology (seen with the Docker `grpc_endpoint` workaround).
5. Private IPs (in-cluster services) are blocked by the SSRF guard unless the endpoint lists
   `allowed_ips`; loopback and link-local are always blocked.
6. Plain-HTTP port-80 endpoints behind a CONNECT-only corporate proxy stall silently (#4278).
7. Pending proposals: `openshell rule get <sb> --status pending` → approve/reject. Remember
   filesystem/Landlock/process changes need a recreated sandbox.

## Provisioning and lifecycle

| Symptom | Cause / fix |
|---|---|
| `ConfigurationInvalid` → `ProvisioningTimedOut` after 300 s | Invalid image-baked or supplied policy (e.g. `tls: terminate` from the archived community `base` image, #4467). Pass a valid `--policy`; `policy set` on the stuck sandbox reports "unchanged" and doesn't recover it |
| `IdentityResolutionFailed … UID or GID zero` | Image runs as root (#4030): add a non-root `USER` |
| `ProvisioningTimedOut` with a large local image (VM driver) or slow runtime (Kata/CoCo) | Hard-coded 5-minute deadlines (#4364, #4771); warm the image cache with a throwaway sandbox |
| All sandboxes `Error (StartFailed)` after a gateway restart | #4910: `sandbox stop` + `sandbox start` each (workspace kept) |
| Sandbox stuck `Error` after a startup failure | 0.1.5+: stop/start recovers it; earlier versions needed delete |
| `missing field socket_loopback_confinement` after a gateway upgrade | Stale bootstrap image (fixed 0.1.4, #4376); upgrade supervisor and sandbox runtime together |
| Old sandboxes vanish after changing `compute_driver` | #4769: the new driver deletes the old driver's stopped sandboxes |
| `connect`/`exec`: `sandbox is not ready` | Main program exited (Completed/Error); use `download` or SSH (#4949), and detach next time instead of quitting |
| Orphaned shells pile up, then `failed to start boundary exec` | Dropped SSH sessions via `ssh-proxy` leave shells running (#4946); kill orphans |

## Auth

| Symptom | Cause / fix |
|---|---|
| Gateway won't start after upgrading to 0.1.6 | No user auth configured; configure OIDC/mTLS or set `allow_unauthenticated_users = true` (dev/trusted proxy only) |
| `grpc-status: 16 missing authorization header` through an ingress | Expected when unauthenticated — the route works; register the CLI with OIDC |
| `Unauthenticated` behind a TLS-terminating proxy with mTLS users | Client certificates don't survive termination; use OIDC or TLS passthrough |
| TUI: `invalid token: ExpiredSignature` minutes after start | The TUI never refreshes its token (`auth.md`); restart it or lengthen the CLI client's access-token lifespan |
| CI: `OIDC token refresh failed: no refresh token available` | Client-credentials renewal bug (#4287): re-run `gateway login` |
| Login works, every call refused | User has neither `admin_role` nor `user_role`, or token lacks the audience (`aud`) |
| OAuth callback in the browser fails for a login inside an agent | Redirect goes to your machine's 127.0.0.1 — use device-code login or `openshell forward start <port>` |

## Logs and audit

- Supervisor OCSF JSONL lives in the **supervisor** container's `/var/log` (tmpfs), not the
  workload: read it via the supervisor container's logs (also on stderr since 0.1.3). Files are
  `openshell-ocsf.YYYY-MM-DD.jsonl` since 0.1.5 (collectors matching `*.log` see nothing new).
  The VM driver writes no OCSF file (#3855).
- Landlock and process-launch events appear only in the workload container log.
- Gateway: OTLP traces (`openshell.gateway.otlp`), Prometheus metrics on 9090, and since 0.1.6
  OCSF audit events for authorization denials and accepted credentials, plus a High-severity
  finding when a sandbox credential looks misused.
