# Improvement backlog — ubuntu-cloud-init

Carries ceiling findings and run history across skill-improver passes. Read in
Phase 0; update in Phase 6. Append-only history — do not drop prior dated sections.

## Resolved — 2026-07-21 (freshen)

**Five undocumented upstream breaking changes found — the pass's real output.**

The skill cited exactly two entries from `doc/rtd/reference/breaking_changes.rst`
(24.3 service rename, 24.1 `datasource_list` None). Reading the file end-to-end
showed it carries **nine** version entries; five were missing here: 26.1, 25.3,
**25.1.4**, 25.1, 24.4. Summarised in a new SKILL.md § *Upstream breaking
changes*.

The one that matters operationally is **25.1.4 — strict datasource identity
before network**. `ds-identify` now demands identification from DMI, the kernel
command line, or an explicit `datasource_list:`; the previous late-discovery
mode (bring networking up, probe well-known link-local IPs) was removed
specifically to stop a bad actor on the local network answering provisioning
requests. Two things make it worth prominent placement:

- it hits **Ec2 / OpenStack / AltCloud on non-x86**, where the kernel may not
  expose DMI; and
- the failure is quiet — with no datasource identified, **cloud-init stays
  disabled and configures nothing at boot**, so the symptom is "the machine came
  up unconfigured", not an error.

It also strengthens an existing recommendation: the air-gapped checklist already
says to pin `datasource_list: [NoCloud]`, previously justified only by probe
timeouts. It is now also the supported mitigation for this change.

**Verified unchanged:** netplan render target (`netplan.py` **L23**), NoCloud
optional seed list (`DataSourceNoCloud.py` **L102**), 26.1 ntp→ntpsec. Line
anchors added.

**Method note recorded in `sources.md`:** citing individual rows from a
changelog-style document gives no signal when new rows appear *above* them.
Diff the version headings
(`grep -nE '^[0-9]+\.[0-9]+' breaking_changes.rst`) instead of re-checking the
two already quoted. Same trap as the sibling pass's release-vs-`main` gap:
`main` here is active (pushed 2026-07-17) while the newest release is ~5 months
old, so a release-tag check would have reported nothing to do.


## Open

- **Dim 7 (Resource Quality) — no bundled scripts (by design).** cloud-init is a
  system command; the skill relies on `cloud-init` invocations + copy-paste examples.
  A bundled seed-builder helper is possible but likely over-engineering vs the
  examples. Author decides. (dir: `scripts/`, absent by design)
- **Trigger watch-item: cloud-init ↔ autoinstall conceptual overlap.** The negative
  "write an autoinstall.yaml…" triggers 0.33 on Opus (1/3) — it PASSES the 0.5
  threshold, but is the weakest negative because autoinstall is *delivered via*
  cloud-init NoCloud user-data, so there is genuine overlap. Already mitigated by the
  explicit "for the installer schema use the ubuntu-autoinstall skill" deferral in
  `description`. Not a mutation (passes); monitor on re-runs. If it ever crosses 0.5,
  add a "Do NOT use for the install schema — use ubuntu-autoinstall" line (Pattern T2).

## Resolved — 2026-06-14 (improve mode)

Blind baseline (Opus): 85/100. Top blind findings addressed:

- Dim 3: removed all 4 second-person slips → imperative ("modules you need" →
  "modules needed"; "your internal mirror"; "Bump it when you edit" → "whenever the
  config changes"; "unless you have a local store" → "unless … are available").
- Dim 1: split overloaded `description` into `description` (what + scope, incl. the
  public-cloud-pointers-only note and sibling delegation) + `when_to_use` (triggers).
  description 629 / combined 958.

**Declined (do NOT re-propose):** consolidating the inline module quick-reference vs
`modules.md` overlap (Dim 6) — the inline snippets are always-loaded quick-reference;
moving them to references only is net-negative (same rationale as ubuntu-autoinstall).

## Resolved — 2026-06-14 (freshen mode)

Dim 9 cap lifted (6 → 9). Created `references/sources.md`; all claims verified **fresh**
(online releases + local repo); no drift/deprecation/broken:

- cloud-init live; latest release 26.1 (2026-02-28) → "26.04 ≈ 26.1";
  `CLOUDINIT_NETPLAN_FILE=/etc/netplan/50-cloud-init.yaml`; NoCloud `network-config`
  optional; service rename 24.3; datasource `None` 24.1; ntp→ntpsec 26.1 (#6684);
  deb822 `ubuntu.sources`.

## Resolved — 2026-06-14 (trigger mode)

Converged at baseline — **no frontmatter mutation**.

- `references/trigger-evals.json`: 7 should-trigger / 6 should-not (sibling-boundary
  negatives for netplan & autoinstall, plus day-2/generic/install decoys).
- Haiku screen (runs 3): **12/13** — all 6 negatives 0.00; lone miss
  "validate my cloud-config…" (0.00) is Haiku's answer-directly false-negative.
- Opus confirm (5 queries): "validate…" 1.00, "#cloud-config ssh keys" 1.00,
  "first-boot script" 0.67, netplan-neg 0.00, autoinstall-neg 0.33 → **5/5 pass**.
  Effective Opus: 7/7 pos, 6/6 neg (autoinstall neg borderline — see watch-item).

`last_run`: 2026-06-14 · baseline = final (0 mutations) · haiku screen + opus confirm.

## Resolved — 2026-06-14 (final blind + follow-up)

**Final blind score (Opus): 87/100** (baseline blind 85 → 87). The scorer flagged one
concrete, valid gap (Dim 5): the user-data formats table lists `multipart/mixed` and
`## template: jinja`, but `examples.md` only showed the MIME *build command* and no
jinja payload. **Applied:** added a worked MIME-multipart resulting document (+ the
per-frequency `x-shellscript-*` subtypes) and a jinja-templated user-data example to
`references/examples.md` → closes the format-coverage trace (Dim 5 → 9; effective ~88).
Reference-only addition; SKILL.md body unchanged.
