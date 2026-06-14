# Sources

Dated index of every external source backing this skill's claims. `[live]`
claims were additionally verified on a production install (chart 8.3.14 /
NetBox v4.6.2, 2026-06-12).

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
| helm repo charts.netbox.oss.netboxlabs.com | latest chart 8.3.14 / app v4.6.2 | 2026-06-12 |
| Production install (chart 8.3.14 / v4.6.2) | all `[live]` labels: token provision flow, PG name collision, sentinel wiring, first-boot timing, template-API legacy shape, module-type slug absence, enum case validation | 2026-06-12 |

Refresh cadence: run `/skill-improver freshen netbox-best-practices` when a new
NetBox minor (4.7/5.0) or netbox-chart major lands — the v1-token removal
(rescheduled to v5.0) and the PortMapping template-endpoint nuance are the two
claims most likely to change.
