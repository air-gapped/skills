# autoinstall validation, debugging & version notes

Grounded in `canonical/subiquity` `doc/howto/autoinstall-validation.rst`,
`scripts/validate-autoinstall-user-data.py`, and `subiquity/server/`.

## Validating before you boot

The canonical pre-flight tool ships in the subiquity repo:

```bash
# clone subiquity + `make install_deps` first. NEVER run as sudo.
./scripts/validate-autoinstall-user-data.py user-data
./scripts/validate-autoinstall-user-data.py - < user-data        # stdin
```

- By default it expects a **`#cloud-config`-wrapped** file with an `autoinstall:` key.
- Pass **`--no-expect-cloudconfig`** for the on-media `autoinstall.yaml` form (with or
  without the top-level `autoinstall:` wrapper).
- Verbosity `-v`/`-vv`/`-vvv`; `-vvv` reproduces runtime errors verbatim. Exit 0 = ok,
  1 = fail.

Internally it checks the first line is `#cloud-config`, then validates against the JSON
schema with `jsonschema.validate`.

### Validate the cloud-config body too
The autoinstall validator does not deeply check the `#cloud-config` body or the nested
`user-data:`. Run cloud-init's own validator on those:
```bash
cloud-init schema -c user-data --annotate
```

### The JSON schema
`autoinstall-schema.json` lives at the subiquity repo root; regenerate with
`make schema`. It is rendered into the reference docs.

## Validator limitations

- Assumes the target is `ubuntu-server` and source id `synthesized`.
- Cannot validate storage/disk **match specs** or other runtime-only data.
- Cannot fully replicate the cloud-config *delivery* checks (e.g. the on-media
  "only the autoinstall key" rule) — those are enforced by the installer at boot.

## Runtime validation order

reporting → error-commands → early-commands → *run early-commands* → reload + validate
everything. So `early-commands` can rewrite `/autoinstall.yaml` before the full
validation pass.

## Logs

- Live install logs: `/var/log/installer/`.
- The delivered autoinstall (including the password hash) is saved to
  `/var/log/installer/autoinstall-user-data`.
- On shutdown the ephemeral `/var/log/cloud-init.log` is copied into
  `/var/log/installer`, and the whole directory is rsynced into the installed target.

## Common pitfalls

- **Missing `#cloud-config` header** → cloud-init ignores the file → installer goes
  fully interactive (not a crash). The validator catches it.
- **Misspelled / missing `autoinstall:` key** → interactive session.
- **Extra top-level keys beside `autoinstall:` in the on-media file** → fatal:
  *"autoinstall.yaml is not a valid cloud config datasource. No other keys may be
  present alongside 'autoinstall'."* (The `#cloud-config` delivery is the opposite —
  top-level cloud-config configures the installer environment.)
- **`interactive-sections: '*'`** (string) fails schema — use `['*']`. Any interactive
  section silently disables `reporting`.
- **identity vs user-data** — don't define the same user in both (install-time vs
  first-boot creation → duplicate/locked-account surprises). With only `user-data`,
  ensure a login path exists.
- **`network:` must be netplan v2** (`version: 2`); v1/ifupdown fails. `match:` accepts
  only name/macaddress/driver.
- **Air-gapped mirror/proxy:** forgetting `apt.geoip: false` → ~10 s hang on the geoip
  lookup; relying on the ambiguous `apt.fallback` default — set it explicitly. `proxy`
  is **not** applied to the geoip lookup.
- **`late-commands` run in the installer env**, target at `/target` — use
  `curtin in-target -- <cmd>` to run inside the installed system.
- **OEM + kernel conflict:** `oem.install: true` plus a pinned `kernel:` can fail.

## Version notes (24.04 LTS vs 26.04 LTS)

Verified against the subiquity tags (`24.04.x`, `24.10.1`, `25.04`, `25.10`, `26.04`,
and `main`):

- **New top-level keys after 24.04:** `kernel-crash-dumps` and `zdevs` are **absent
  from the 24.04 schema** and present from 24.10 onward. A config using them *warns*
  (v1 tolerates unknown keys) on 24.04 but functions on 24.10+.
- **`kernel-crash-dumps` default changed at 24.10:** default (`enabled: null`) =
  dynamic enablement on capable amd64/arm64/s390x (via `kdump-tools`); pre-24.10 it was
  disabled by default.
- **26.04 == current `main` for top-level schema purposes** (verified empty diff). The
  24.04 key set is a strict subset of 26.04's (only the two added keys differ).
- **Ordered storage match-spec lists** added in 24.08.1.
- **On-media `autoinstall:` wrapper** acceptance introduced in 24.04 (pre-24.04 ISOs
  need an installer refresh).
- **`ubuntu-advantage`** is the deprecated alias of `ubuntu-pro` (still accepted).
- **Unknown-key handling** remains a *warning* in v1 across all these releases
  (`additionalProperties: true`); documented to become fatal in a future schema
  version — not yet enforced.

> Caveat to pass on: the reference doc states two different defaults for `apt.fallback`
> (`offline-install` in the field doc vs `abort` in the default block). Always set
> `apt.fallback` explicitly rather than relying on the default.
