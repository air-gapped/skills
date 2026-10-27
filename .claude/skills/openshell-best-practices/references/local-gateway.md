# Local gateway — workstation installs (0.1.x)

Verified against `v0.1.6` (`docs/about/installation.mdx`, `docs/how-it-works/sandboxes/runtimes.mdx`,
`install.sh`) and field reports.

## Contents

- Install
- Upgrading off 0.0.x (clean reinstall)
- Runtime selection
- Platform problems

## Install

`curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh` picks a
package for the host: **RPM** (Fedora/RHEL), **deb** (Debian/Ubuntu), **Homebrew** (macOS);
`OPENSHELL_INSTALL_METHOD=snap` for the snap, `OPENSHELL_VERSION=v0.1.6` to pin. For
reproducible or air-gapped installs, download the release assets and verify them against
`openshell-checksums-sha256.txt` / `openshell-gateway-checksums-sha256.txt` instead of piping
`main/install.sh` (the RPMs are unsigned; trust comes from the checksum file).

Packages: `openshell` (CLI), `openshell-gateway` (pins `openshell = <same version>`),
`openshell-prover` (optional policy checker). The gateway runs as a systemd **user** service
(`openshell-gateway.service`; brew service on macOS) on `https://127.0.0.1:17670` with
config `~/.config/openshell/gateway.toml` and state `~/.local/state/openshell/`. Register it
with `openshell gateway add https://127.0.0.1:17670 --local --name openshell` (auth: mTLS).

- `sudo loginctl enable-linger $USER` on servers, or the user gateway stops at logout.
- Only one user per host can run the user gateway (fixed port).
- Snap: needs non-snap Docker; `snap refresh --hold openshell` to stop surprise upgrades;
  refreshes have reset `gateway.toml` (#3786).
- Since 0.1.6 the gateway refuses to start without user auth; package installs use mTLS, so
  only hand-rolled plaintext gateways need `[openshell.gateway.auth] allow_unauthenticated_users = true`.
- Telemetry is on by default: `OPENSHELL_TELEMETRY_ENABLED=false` in `~/.config/openshell/gateway.env`.

## Upgrading off 0.0.x (clean reinstall)

0.0.x → 0.1.x is not an in-place upgrade (`docs/upgrade/0-1-0.mdx`). On a workstation:

1. Export any provider profiles you want to keep (`openshell provider profile export <id> -o yaml --global`).
2. Delete every sandbox (`openshell sandbox delete <name>`), then
   `systemctl --user disable --now openshell-gateway`.
3. Remove both packages in one transaction — the gateway package pins the exact CLI version,
   so upgrading the CLI alone fails dependency resolution:
   `dnf remove openshell-gateway openshell` (or `apt remove`, `brew uninstall`).
4. `rm -rf ~/.local/state/openshell` (old DB, certs, KEK). If `~/.config/openshell/gateway.toml`
   is the old packaged default (v1 schema), remove `~/.config/openshell` too; otherwise migrate
   it to schema v2 (`version = 2`, `compute_driver = "podman"`, driver tables) and run
   `openshell-gateway config preflight --path ~/.config/openshell/gateway.toml`.
5. Install 0.1.x, `systemctl --user daemon-reload && systemctl --user enable --now openshell-gateway`,
   register with `gateway add … --local --name openshell`, `openshell status`.
6. Import profiles and recreate providers and sandboxes.

Note the 0.1.6 RPM default config listens on `127.0.0.1` only (0.0.x defaults bound `0.0.0.0`).

## Runtime selection

With `compute_driver` unset the gateway auto-detects **Kubernetes → Podman → Docker**; the
VM (libkrun) driver is never auto-selected. Pin it in gateway.toml:
`[openshell.gateway] compute_driver = "podman"`. Changing drivers later deletes stopped
sandboxes created by the previous driver after ~1 minute (#4769) — move data out first.

## Platform problems

| Platform | Symptom | Fix |
|---|---|---|
| Docker Desktop (macOS, WSL2) | Sandbox never Ready: `Docker supervisor exited before becoming ready` / `Startup configuration fetch failed after 5 attempts` (#3880, #4683) | `[openshell.drivers.docker] supervisor_network_mode = "bridge"` (0.1.5+), or enable Docker Desktop host networking, or `grpc_endpoint = "https://host.docker.internal:17670"`; restart gateway, recreate sandbox |
| Docker Desktop old VM kernels, SLES 15 SP7 | `fully incompatible access-rights` / Landlock probe failures | Kernel needs Landlock ABI ≥ 3, nested seccomp user-notify + `ADDFD`, `process_vm_readv`, `SO_BINDTODEVICE` — "kernel version alone does not establish support". `openshell doctor check` does not test this (#4133) |
| WSL2 mirrored networking | `seccomp notification probe: Resource busy (os error 16)` (#3842, #4902) | `networkingMode=nat` in `.wslconfig`, `wsl --shutdown` |
| Docker Desktop macOS VirtioFS | EACCES on bind-mounted files while Ready | Switch file sharing to gRPC FUSE |
| Podman rootless | stale supervisor binary after upgrade (ELF/version errors) | Delete `~/.local/share/openshell/podman-supervisor/` |
| Podman | watch hangs with > 256 existing sandbox snapshots (#4717) | Prune old sandboxes |
| Docker GPU | no GPU in sandbox | NVIDIA CDI specs: `docker info --format '{{json .DiscoveredDevices}}'` must list `nvidia.com/gpu=all`; enable `nvidia-cdi-refresh` |
| Windows native | — | No Windows release binaries; WSL2 (experimental) or build `openshell.exe` from the `windows` branch (unsigned) |
