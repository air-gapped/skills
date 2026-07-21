# Sources

Dated index of every external source backing this skill's claims. `[live]`
claims were additionally verified on a production install (chart 8.3.14 /
NetBox v4.6.2, 2026-06-12). **The `[live]` labels have not been re-verified
since** — upstream is now at chart 8.3.37 / v4.6.5 (2026-07-21 probe), so treat
them as observed-on-4.6.2 rather than confirmed-current.

## ⚠ Version-lookup trap — `releases/latest` on `netbox-chart` returns the *operator*

The `netbox-community/netbox-chart` repo publishes **two products into one
release stream**: `netbox-<chart>` and `netbox-operator-<chart>`. As of
2026-07-21 the `isLatest` release is **`netbox-operator-1.2.128`** (2026-07-20),
while the newest NetBox chart is **`netbox-8.3.37`** (2026-07-15).

So `gh release view --repo netbox-community/netbox-chart` reports an *operator*
version that looks nothing like a chart version, and enumerating without
filtering interleaves the two. Read the Helm index instead — it separates them
cleanly and carries `appVersion`:

```bash
curl -s https://charts.netbox.oss.netboxlabs.com/index.yaml \
  | yq '.entries.netbox[0] | {version, appVersion, created}'
# chart 8.3.37 / app v4.6.5 / 2026-07-15
```

| Source | What it backs | Last verified |
|---|---|---|
| https://netboxlabs.com/docs/netbox/getting-started/planning/ | SoT definition, 16-step order | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/release-notes/version-4.2 | MACAddress objects | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/release-notes/version-4.3 | module profiles, Service API break | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/release-notes/version-4.4 | VLAN-to-site deprecation (#19738) | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/release-notes/version-4.5 | v2 tokens (#20210), PortMapping (#20564), cable-terminations read-only | 2026-06-12 |
| https://github.com/netbox-community/netbox/blob/main/docs/release-notes/version-4.6.md | RackGroup (#20961), v1 deprecation (#22128, removal v5.0), plaintext-once (#22062/#22081) | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/models/dcim/moduletypeprofile/ | profile JSON schema rules | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/models/dcim/devicebay/ + modulebay/ | bay distinction rule | 2026-06-12 |
| github.com/netbox-community/netbox-chart `charts/netbox/templates/` | lookup preservation, api_token generation+mount, PLUGINS toJson, secret key projections | 2026-06-12 (clone @ 2026-06-09) |
| github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins | §5 plugin install: image lineage (ghcr netbox image is built by netbox-docker), plugin_requirements.txt/Dockerfile-Plugins is compose-only, PLUGINS module-name vs PyPI dist-name | 2026-06-14 |
| github.com/netbox-community/netbox-chart `values.yaml` (image.registry/repository=ghcr.io/netbox-community/netbox) | §5 chart pulls the netbox-docker-built image; §5 init-container pip path | 2026-06-14 (live values 8.3.14) |
| github.com/netbox-community/netbox `netbox/api/authentication.py` | nbt_ prefix version inference, "Invalid v1 token" | 2026-06-12 (read in v4.6.2 container) |
| github.com/netbox-community/netbox `netbox/netbox/authentication/__init__.py` | sso-hardening: REMOTE_AUTH_SUPERUSER/STAFF/GROUP_SYNC are RemoteUserBackend-only (`_is_superuser`/`_is_staff`/`configure_groups` L163-262); `user_default_groups_handler` assigns flat REMOTE_AUTH_DEFAULT_GROUPS, no flag mapping (L383-401) | 2026-06-14 (main @ gh api) |
| github.com/netbox-community/netbox `netbox/netbox/settings.py` | sso-hardening: default SOCIAL_AUTH_PIPELINE (L716-726), only NetBox step is user_default_groups_handler | 2026-06-14 (main @ gh api) |
| netboxlabs.com/docs/.../authentication/overview, hull.au/blog/netbox-authentik-oidc-sso, docs.goauthentik.io/integrations/services/netbox | sso-hardening: SOCIAL_AUTH_PROTECTED_USER_FIELDS=['groups'] sign-in workaround, SOCIAL_AUTH_REDIRECT_IS_HTTPS, groups-claim prerequisite, usersocialauth linking | 2026-06-14 |
| helm repo charts.netbox.oss.netboxlabs.com | **latest chart 8.3.37 / app v4.6.5** (2026-07-15), up from 8.3.14 / v4.6.2 — 23 chart patches, still 8.x (no major) | 2026-07-21 |
| github.com/netbox-community/netbox releases | **NetBox v4.6.5** (2026-07-14) is latest; the line is still **4.6.x — no 4.7, no 5.0**. The refresh trigger ("new NetBox minor") has **not** fired, so `version-deltas.md` and the v1-token-removal-at-v5.0 claim stand | 2026-07-21 |
| Production install (chart 8.3.14 / v4.6.2) | all `[live]` labels: token provision flow, PG name collision, sentinel wiring, first-boot timing, template-API legacy shape, module-type slug absence, enum case validation | 2026-06-12 |

Refresh cadence: run `/skill-improver freshen netbox-best-practices` when a new
NetBox minor (4.7/5.0) or netbox-chart major lands — the v1-token removal
(rescheduled to v5.0) and the PortMapping template-endpoint nuance are the two
claims most likely to change.

**2026-07-21 pass: the trigger did not fire.** NetBox is still on **4.6.x**
(v4.6.5, 2026-07-14) and the chart is still **8.x** (8.3.37, 2026-07-15), so no
version-delta claim was invalidated and the v5.0-token-removal schedule stands.
What did change: 23 chart patches and 3 NetBox patches since the live
verification, which is why the `[live]` labels are now scoped to
"observed on 4.6.2" rather than left implying currency. Also documented the
`netbox-chart` two-products-one-release-stream trap above — `releases/latest`
there returns `netbox-operator`, not the chart.
