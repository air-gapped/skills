# Improvement backlog

Open ceiling findings and follow-ups that need either author input, on-cluster verification, or upstream movement before the skill can address them in a single iteration.

## Open

*(empty — all seven carried items were closed on 2026-08-19; see below. An entry
belongs here only when something specific and external prevents doing it now,
named in the entry. "Needs author judgement" is a decision, not a blocker.)*

## Resolved — 2026-08-19 (backlog drain)

Four fixes, three withdrawals. The headline: the oldest item was blocked on a
premise that was false.

- **The Dell item was never login-walled, and the KB was misattributed.** The
  2026-05-28 verdict recorded both Dell claims as UNVERIFIABLE because "Dell
  release notes / Redfish OEM docs sit behind the support-portal login". They do
  not. Both driver-details pages (`driverid=xrg43`, `driverid=662gc`) and the KB
  are publicly readable — the earlier 403 was curl-specific, not authentication.
  Reading them settles both halves: **v1.4.30 is still the newest GA baseboard
  firmware** for XE9780/XE9785 (page dated 2026-04-14), and the ExtendedReset
  requirement is unresolved (KB last updated 2026-05-23, still "a limitation in
  iDRAC", no fixed-in version; iDRAC10 release-notes index KB 000305325 claims no
  fix). **And KB 000355295 is titled for XE9680L/XE9685L — not XE9780/XE9785.**
  The skill had been citing it as authority for the B300 SKUs for three months.
  Both `dell-firmware.md` passages now carry the scope correction and label the
  application to XE9780/XE9785 as read-across rather than a Dell statement.
- **MOK per-host vs site-wide: decision criteria written.** Both options were
  already documented; the defect was Option B ending in a pointer at this backlog
  file — a shipped skill telling the reader to consult an internal to-do about an
  unanswered question. `secure-boot.md` now carries a four-row comparison (blast
  radius, enrollment events, rotation cost, practical ceiling) and names the
  condition that selects each, plus the two invariants that hold either way.
- **DOCA overwriting `/etc/modules-load.d/ib_umad.conf`: answered from dpkg
  semantics, no sandbox needed.** `troubleshooting.md` now gives the two commands
  that settle it on any box (`dpkg -S`, `dpkg-query -W -f='${Conffiles}'`) and the
  rule they resolve to: dpkg never deletes a file it does not ship, and never
  silently replaces a modified conffile — the real exposure is an unattended
  pipeline running `--force-confnew`. Belt-and-braces filename suggested.
- **NVLSM↔driver coherence: documented as unenforced.** `packages.md` now states
  that `nvlink5-<branch>` declares `nvlsm (>= …)` — a floor, not a pin — so apt
  will drift the pair with no complaint, in contrast to FM↔driver which aborts on
  mismatch. NVIDIA publishes no compatibility matrix, so the entry gives the
  post-upgrade check (`dpkg -l`, `systemctl is-active`, the FM journal line, the
  `nvidia-smi` Fabric state) and warns against pre-emptive `apt-mark hold`.
- **WITHDRAWN — gpu-operator #2231.** Duplicate bookkeeping: the issue is tracked
  in `sources.md`, which the freshen cycle re-probes. It closed 2026-07-27 and
  `sources.md` already records that with the correct caveat (maintainer closed it
  asserting B300 support but named no fix PR).
- **WITHDRAWN — NVL72 / NMX multi-node.** `SKILL.md:114` declares it hard
  out-of-scope. A conditional "worth considering if the fleet expands" is a wish,
  not carried work; it reappears if the fleet actually changes.
- **WITHDRAWN — non-Dell vendor firmware paths.** Already done: `dell-firmware.md`
  carries the per-vendor sidebar (Supermicro SUM/BMC, HPE Cray SAT/FAS, Lenovo
  XCC/OneCLI) with the shared AC-cycle requirement. The entry described a gap that
  had been filled.

## Resolved — 2026-07-21 (freshen)

The headline is a **packaging-scheme change** that the previous pass's own
conclusion got backwards.

- **"580 remains current production branch; no 590/600 GA supersedes it" is
  wrong.** Branches **590, 595 and 610** are all published in the Ubuntu 24.04
  CUDA repo, newest `610.43.02-1ubuntu1`. The 2026-05-28 pass re-confirmed the
  no-590/600 claim and re-stamped it; this pass overturns it.
- **Why it was missed — and why I nearly repeated it.** The HTML directory
  listing shows branch-*suffixed* filenames, and those stop at 580. Reading the
  listing, the honest conclusion is "nothing past 580 exists" — which is what I
  concluded on my first probe this pass too. The `Packages.gz` index tells a
  different story: 590/595/610 ship through **unsuffixed** package names with
  the branch encoded in the *version*. `sources.md` now says to read
  `Packages.gz`, not the listing.
- **The branch-suffix cliff, documented in [[packages]].** Suffixed builds stop
  at **580** for `nvidia-driver-<b>` / `-open` / `nvidia-open-<b>` /
  `cuda-drivers-<b>` / `nvlink5-<b>`, and at **575** for
  `nvidia-fabricmanager-<b>` / `cuda-drivers-fabricmanager-<b>` /
  `libnvidia-nscq-<b>` / `libnvsdm-<b>` / `nvidia-imex-<b>`. So
  `apt install nvidia-open-<branch>` is not a general recipe above 580; pinning
  above it goes via `nvidia-driver-pinning-<branch>` (590/595/610 present) plus
  the unsuffixed meta. The 580 recipes in [[recipe]] / [[hopper-recipe]] still
  work **because 580 is the last suffixed branch — luck, not design.**
- **Three table ranges in [[packages]] corrected**: `nvidia-fabricmanager-<b>`
  and `cuda-drivers-fabricmanager-<b>` were "535–595", actually 550–575;
  `libnvidia-nscq-<b>` claimed 580/590/595 entries that do not exist. Also
  `nvidia-container-toolkit` 1.19.0-1 → 1.19.1-1 and `nvlsm` 2025.10.12-1 →
  2025.10.14-1. Corollary: the 2026-05-28 note below claiming "branches 550-595
  all ship `nvidia-imex-XXX`" is wrong — suffixed imex stops at 575.
- **gpu-operator v26.3.1 → v26.3.3** (2026-06-25), via v26.3.2 (2026-05-29).
  **v26.3.2 shipped a regression** that unconditionally enabled `MOFED_ENABLED`
  / `GDS_ENABLED`, injecting unintended network interfaces and breaking RDMA
  workloads; v26.3.3 fixes it. On an RDMA chassis that is a skip-26.3.2
  instruction, so it is called out in [[gpu-operator]] rather than left as a
  version number. Helm `--version` flags and the air-gap mirror image list
  updated to v26.3.3.
- **Issue #2463 (CONFIG_MEMORY_HOTPLUG) closed 2026-07-07**; annotated. Issue
  **#2231 (B300 PCI 0x3182 validator) still open** two months on — the B300
  validator workaround the skill documents is still load-bearing.

**Not verified:** which of 590/595/610 carries NVIDIA's *Production Branch*
designation (vs New Feature / LTS). The driver-lifecycle page did not yield it
in this pass, so the skill states repo contents only and makes no
branch-designation claim.

## Resolved — 2026-05-28

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

### Skill-improver freshen pass (2026-05-28)

- Re-confirmed CURRENT online and re-stamped `Last verified: 2026-05-28` on three [[sources]] rows: NVIDIA open-kernel-modules-mandatory blog, gpu-operator issue #2231 (still open, no merged fix), and the CUDA repo row (580 remains the current production branch; no 590/600 GA supersedes it).
- Two Dell-specific claims left UNCHANGED — baseboard firmware floor v1.4.30 and the `DellOemChassis.ExtendedReset` Redfish OEM action — both verdict UNVERIFIABLE (Dell release notes / Redfish OEM docs sit behind the support-portal login, not web-indexed). Carried forward in Open per freshen rules (do not guess).
- No SKILL.md improve mutation applied: the highest-leverage recon hypothesis (split the oversized `description` into `description` + `when_to_use`) was already present on disk (description 931 chars, under the 1024 cap; `when_to_use` already a separate field). The decision-tree "skip fabricmanager/DOCA/NVLSM" dedup hypothesis was rejected because each row's skip-set is genuinely distinct (8-GPU keeps FM via meta but skips nvlink5/NVLSM/DOCA; 4-GPU and PCIe-only skip FM too) — collapsing them would lose hardware-class precision.
