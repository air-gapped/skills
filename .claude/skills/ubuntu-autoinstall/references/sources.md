# Sources — ubuntu-autoinstall

Authoritative references behind this skill's factual claims, with verification dates.
Re-probe with `skill-improver freshen ubuntu-autoinstall`. All claims here were
verified against the **canonical/subiquity** source repo (the authoritative
implementation) and the GitHub release/tag list.

| Ref | URL / location | Pinned | Last verified | Verified claim |
|---|---|---|---|---|
| subiquity repo | https://github.com/canonical/subiquity | `main` | 2026-07-21 | Live (**pushed 2026-07-20** — actively developed), not archived, default branch `main`. |
| Latest release | https://github.com/canonical/subiquity/releases | `26.04` | 2026-07-21 | **Still `26.04`** (2026-04-23) — no new release in the three months since the last pass, despite active `main` development. 24.04 + 26.04 LTS targeting unchanged. |
| Release tags | https://github.com/canonical/subiquity/tags | — | 2026-07-21 | Tags `24.04.1`–`24.04.4.1`, `24.10.1`, `25.04`, `25.10`, `26.04`, `26.10-devel` all exist. |
| autoinstall schema | `autoinstall-schema.json` (repo root) | `main` | 2026-07-21 | Present; regenerated via `make schema`. Schema `version` still constrained to **exactly 1** (`{type: integer, minimum: 1, maximum: 1}`). **32 top-level keys on `main`; all 32 are documented in `schema.md`** — diffed programmatically, zero undocumented. |
| Validator script | `scripts/validate-autoinstall-user-data.py` | `main` | 2026-07-21 | Present in the repo's `scripts/` (NOT bundled in this skill) — basis for the Dim 8 provenance note. |
| `kernel-crash-dumps` / `zdevs` gating | `autoinstall-schema.json` @ `24.04.1` vs `main` | — | 2026-07-21 | Top-level keys `kernel-crash-dumps` and `zdevs` present in `main`, **absent in `24.04.1`** → "24.10+ only". |
| 24.04 → 26.04 top-level delta | schema diff `24.04.1` vs `26.04`/`main` | — | 2026-07-21 | Exactly two keys added (`kernel-crash-dumps`, `zdevs`); none removed. `26.04` top-level keys **identical to `main`**. |
| `apt.fallback` enum | `autoinstall-schema.json` | `main` | 2026-07-21 | Re-extracted from the live schema: `['abort', 'continue-anyway', 'offline-install']`. Unchanged. |
| `kernel.flavor` resolution | `subiquity/server/kernel.py` `flavor_to_pkgname()` (L19-29) | `main` | 2026-07-21 | Re-read: `generic`→`linux-generic` (L20-21); `hwe`→ rewritten to `generic-hwe` (L22-23) → `linux-generic-hwe-<release>`; else `f"linux-{flavor}-{release}"` (L29). Unchanged. No pre-check that the package exists. |
| `ubuntu-advantage` alias | `subiquity/server/controllers/ubuntu_pro.py` **L75-76** | `main` | 2026-07-21 | Re-confirmed: `autoinstall_key = "ubuntu-pro"` / `autoinstall_key_alias = "ubuntu-advantage"`; both keys present in the schema. |
| On-media "only autoinstall" rule | `subiquity/server/server.py` **L741** | `main` | 2026-07-21 | Fatal string re-confirmed verbatim: "No other keys may be present alongside 'autoinstall' at …". |
| Autoinstall docs | https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html | — | 2026-07-21 | Reference docs live in the repo `doc/` tree (`autoinstall-reference.rst`, `autoinstall-schema.rst`, `cloudinit-autoinstall-interaction.rst`). |

<!-- Grounding note: this skill was authored 2026-07-21 against a local checkout of
canonical/subiquity @ main (HEAD ~fb7a09c8, June 2026). The two delegation boundaries
(network: → netplan v2, user-data: → cloud-init) are cross-checked in the sibling
skills ubuntu-netplan and ubuntu-cloud-init, which carry their own sources.md. -->


## 2026-07-21 freshen — verified unchanged, checked mechanically

`main` is actively developed (**pushed 2026-07-20**) yet **`26.04` remains the
latest release** (2026-04-23) — three months of commits without a cut. That
combination is the thing to watch: the schema this skill documents tracks
`main`, so it can move without a release to signal it. This pass therefore
diffed the artifact rather than trusting the release tag.

**Method, so a future pass can repeat it cheaply:**

```bash
gh api repos/canonical/subiquity/contents/autoinstall-schema.json \
  --header "Accept: application/vnd.github.raw" > /tmp/ai.json
python3 -c "import json;d=json.load(open('/tmp/ai.json'));print(len(d['properties']),sorted(d['properties']))"
```

then diff that key set against the backticked identifiers in `schema.md`.

**Result: nothing moved.**

- Schema `version` still pinned to exactly 1 (`minimum: 1, maximum: 1`).
- **32 top-level keys, and all 32 already appear in `schema.md`** — programmatic
  diff, zero undocumented keys. The `kernel-crash-dumps` / `zdevs` "24.10+ only"
  gating still holds.
- `apt.fallback` enum unchanged: `abort`, `continue-anyway`, `offline-install`.
- All three code-behaviour claims re-read at source and unchanged, now with line
  anchors: `flavor_to_pkgname()` (kernel.py L19-29), the on-media fatal string
  (server.py **L741**), and the `ubuntu-pro` / `ubuntu-advantage` alias pair
  (ubuntu_pro.py **L75-76**).
