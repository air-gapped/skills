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
| github.com/netbox-community/netbox `netbox/api/authentication.py` | nbt_ prefix version inference, "Invalid v1 token" | 2026-06-12 (read in v4.6.2 container) |
| helm repo charts.netbox.oss.netboxlabs.com | latest chart 8.3.14 / app v4.6.2 | 2026-06-12 |
| Production install (chart 8.3.14 / v4.6.2) | all `[live]` labels: token provision flow, PG name collision, sentinel wiring, first-boot timing, template-API legacy shape, module-type slug absence, enum case validation | 2026-06-12 |

Refresh cadence: run `/skill-improver freshen netbox-best-practices` when a new
NetBox minor (4.7/5.0) or netbox-chart major lands — the v1-token removal
(rescheduled to v5.0) and the PortMapping template-endpoint nuance are the two
claims most likely to change.
