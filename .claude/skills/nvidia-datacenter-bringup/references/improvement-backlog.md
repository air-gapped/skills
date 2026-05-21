# Improvement backlog

Open ceiling findings and follow-ups that need either author input, on-cluster verification, or upstream movement before the skill can address them in a single iteration.

## Open

### Dell baseboard firmware activation: ExtendedReset vs FullPowerCycle drift

- **Affects:** [[dell-firmware]]
- **Question:** Dell KB 000355295 says `DellOemChassis.ExtendedReset` is required because standard `Chassis.Reset FullPowerCycle` doesn't propagate to the GPU baseboard. Unknown whether newer iDRAC 10.x firmware closes this gap on XE9780/XE9785, or whether the OEM path remains required indefinitely.
- **Why not in one iteration:** Needs Dell to confirm or new KB to land. Re-verify in 6 months.

### Per-host vs site-wide MOK threat model

- **Affects:** [[secure-boot]]
- **Question:** For fleets of 50+ B300 hosts, is a shared site-wide MOK (baked into the golden image) acceptable per the operator's threat model, or must each host carry a unique MOK to limit key-compromise blast radius?
- **Why not in one iteration:** Author judgment — depends on whether the threat model treats a stolen private key as a fleet-wide compromise risk. Document both options without recommending one.

### DOCA postinst overwriting `/etc/modules-load.d/ib_umad.conf`

- **Affects:** [[troubleshooting]]
- **Question:** If an operator works around the install-order trap with `echo ib_umad > /etc/modules-load.d/ib_umad.conf`, does a subsequent DOCA package upgrade overwrite that file?
- **Why not in one iteration:** Needs to test against a DOCA upgrade in a sandbox.

### gpu-operator issue #2231 status

- **Affects:** [[gpu-operator]]
- **Question:** B300 PCI ID 0x3182 missing from validator name table — last activity 2026-05-18, label `more-information-needed`. NVIDIA waiting on must-gather logs from reporter. Track when this gets fixed (likely 25.10.2 or 26.x bump).
- **Why not in one iteration:** Upstream-blocked. Re-check during freshen pass.

### Multi-node NVLink Switch (NVL72) bring-up

- **Affects:** scope of the skill
- **Question:** NVL72 / GB300 NVL72 rack-scale systems use NMX (NVLink Switch Management) — a superset of single-node FM/NVLSM. Currently explicitly out-of-scope. Worth considering a sibling skill or a section if the user's fleet expands.
- **Why not in one iteration:** Different architecture, separate doc set (https://docs.nvidia.com/mission-control/docs/systems-administration-guide/), would double the skill size.

### Vendor-non-Dell firmware paths

- **Affects:** [[dell-firmware]]
- **Question:** Supermicro NVIDIA HGX B300 (SUM/BMC bundles), HPE Cray (SAT/FAS), Lenovo ThinkSystem SR685a (XCC/OneCLI). All require an AC-class power cycle after GPU baseboard flash. Currently the skill defers to vendor docs with a one-line pointer.
- **Why not in one iteration:** Each vendor has its own KB ecosystem. Worth a per-vendor sidebar if the user's fleet broadens.

### Verify exact `nvlsm` versioning behaviour

- **Affects:** [[packages]]
- **Question:** apt-cache shows `nvlsm` as a single floating package (calver `2025.10.12-1`), not branch-versioned. The skill claims FM↔driver version match is enforced but NVLSM↔driver coherence is not. Confirm what happens when driver 580.126.20 is paired with `nvlsm 2025.10.12-1` (which is newer): does FM fail to start, warn, or work fine?
- **Why not in one iteration:** Requires either documentation from NVIDIA (none found) or empirical test on the user's box.

## Resolved this pass

### Initial authoring (2026-05-21)

First version of skill. Backlog seeded from the autoresearch synthesis and the live apt-cache inspection.

### Skill-improver improve+freshen pass (2026-05-21)

- **`nvlink5-580` dependency tree verified** via `apt-cache depends nvlink5-580` from clean ubuntu:24.04 docker container + CUDA repo. Captured in [[packages]] §"`nvlink5-<branch>` dependency tree (apt-cache-verified)". New packages surfaced: `nvidia-imex`, `collectx-bringup`, `mft`, `mft-oem`, `mft-autocomplete`. Recipe + SKILL.md updated to clarify `nvlink5-580` is compute-only; full userland needs `nvidia-open-580` AS WELL.
- Freshen probes (7 refs): all `fresh`. sources.md dates already 2026-05-21 (no change).
- Dim 3 (Writing Style): swept ~30 author-voice second-person occurrences across references → imperative/third-person.
- Dim 8 (Internal Consistency): unified `[[wikilink]]` path style to bare basename across all files.
- Dim 4 (Actionability): added expected-output samples to SKILL.md validation block.
- Dim 5 (Completeness): added decision-tree rows for H100/A100/L40S/L4 (non-Blackwell coverage).
- Dim 7 (Resource Quality): added `scripts/health-check.sh` (multi-platform smart, smoke-tested).
- Dim 6 (Simplicity): removed defensive boilerplate ("Cross-doc stitching is the value-add" paragraph).

### Hopper expansion pass (2026-05-21)

User feedback that the skill was too B300-focused for a fleet running H100 (XE8640 + XE9680) and H200 (XE9680). Five-iteration pass adding Hopper as a first-class citizen:

- **New [[hopper-recipe]]** — dedicated companion to [[recipe]] (which stays B300-centric). Topology→install matrix covers XE8640 (4-GPU HGX H100, **no NVSwitch, no FM**), XE9680 (8-GPU Hopper), GH200 (open mandatory), H200 NVL (PCIe), L40S/L4. XE8640 minimal install is 3 apt packages.
- **Decision tree split**: previous single "HGX H100/H200/H800" row was wrong because it conflated 4-GPU (no NVSwitch) and 8-GPU (3rd-gen NVSwitch). Now: separate rows for "HGX 4-GPU SXM (XE8640)" and "HGX 8-GPU SXM (XE9680)". Added Grace Hopper row (open mandatory).
- **Corrected min-driver versions**: H200 needs 535+ (not 525 as previously stated — H200 announced late 2023 after R525 line).
- **Hopper VBIOS gate** added to [[troubleshooting]]: R580 fails to init on Hopper subrev 3 silicon with VBIOS older than 96.00.68.00.xx (per NVIDIA 580.65.06 release notes).
- **XE9680/XE9640/XE8640 iDRAC Direct USB Port gotcha** documented in [[dell-firmware]] (Dell KB 000308105): GPU baseboard firmware updates fail silently if iDRAC Direct USB is disabled in BIOS.
- **Dell firmware bundle pointers**: added table mapping chassis SKU → Dell driver-page ID. XE9680 H200 = `driverid=mh92v`, XE9680 PCIe switch H100/A100 = `driverid=p9gg2`. Previously only B300 bundles (`xrg43`, `662gc`) were documented.
- **`nvidia-imex` scope correction** in [[packages]]: it's not Blackwell-specific. Branches 550-595 all ship `nvidia-imex-XXX` packages — useful on any NVLink-fabric chassis including XE9680 Hopper and XE8640 direct-mesh.
- [[sources]] updated with H200 baseboard firmware URL, XE9680 PCIe switch URL, KB 000308105, R580 release notes, NVIDIA HGX A100 Software Guide (which establishes the "4-GPU has no NVSwitch" rule).
