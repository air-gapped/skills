# Sources

Freshened: 2026-09-22 — every row probed; NetBox 4.7.1 and the social-auth pins reproduce. The chart line moved past the gap this file recorded: 8.3.78 (2026-09-16) is the first chart pinning 4.7.1, so the staging advice no longer has to stop at a 4.7.0 chart.

**One cited source path is gone**: `netbox/api/authentication.py` no longer exists on `main`. Relocate it before trusting the row that reads token behaviour from it.

**A real dependency break landed in 4.7.0** that this file did not capture: `social-auth-core` was unpinned from `4.8.7` to `5.1.0` (a major), alongside `social-auth-app-django` to v6.0. Re-verified at both tags. The OIDC behaviour cited here is byte-identical between 4.8.7 and 5.1.0, so the guidance holds — but anyone pinning the old version is now off the shipped set.

Line anchors into `netbox/netbox/authentication/__init__.py` and `settings.py` have drifted substantially — find those symbols by name, not by line.

Dated index of every external source backing this skill's claims.

## ⚠ Version-lookup trap — `releases/latest` on `netbox-chart` returns the *operator*

The `netbox-community/netbox-chart` repo publishes **two products into one
release stream**: `netbox-<chart>` and `netbox-operator-<chart>`. As of
2026-10-27 the `isLatest` release is **`netbox-operator-1.2.199`**, while the
newest NetBox chart is **`netbox-8.3.96`** (2026-10-27).

So `gh release view --repo netbox-community/netbox-chart` reports an *operator*
version that looks nothing like a chart version, and enumerating without
filtering interleaves the two. Read the Helm index instead — it separates them
cleanly and carries `appVersion`:

```bash
curl -s https://charts.netbox.oss.netboxlabs.com/index.yaml \
  | yq '.entries.netbox[0] | {version, appVersion, created}'
# chart 8.3.96 / app v4.7.3 / 2026-10-27
```

| Source | What it backs | Last verified |
|---|---|---|
| https://github.com/netbox-community/netbox/releases/tag/v4.7.0 | 4.7.0 upgrade gates in SKILL.md: PostgreSQL 14 dropped (15+, upgrade script aborts — 4.6 warned only); `ltree` extension required (trusted, auto-installed, no superuser); Redis 5.x dropped (6.0+); selection custom fields return `{value,label}` on read in REST and GraphQL, writes unchanged; `ipam.Service` `protocol`/`ports` → `port_mappings` (legacy pair still accepted by REST, ORM-read-only). Published 2026-09-02. | 2026-09-15 |
| netbox `docs/release-notes/version-4.7.md` @v4.7.3 (+ `version-4.6.md`) | 4.7.0–4.7.3: #23196 token plaintexts in job results (4.7.0–4.7.1, fixed 4.7.2, replace affected tokens); `ltree` needs `CREATE` on the DB (owner suffices); mptt → ltree migration holds `ACCESS EXCLUSIVE` while backfilling; `upgrade.sh` runs `rebuild_config_context_cache` (deferrable, on-demand fallback); `housekeeping` deprecated 4.6 (#21304), removed 4.7 (#21565); 11 hierarchical models | 2026-10-27 |
| netbox `docs/release-notes/version-4.7.md` @v4.7.3 (#23288) + commit 9674a8887, `docs/integrations/rest-api.md` | `?exclude=config_context` ignored on 4.7 (4.7.0 breaking change); `omit`/`fields` are generic REST params; 4.7.3 skips the config-context annotation when it is omitted (`test_config_context_not_loaded_when_omitted`) | 2026-10-27 |
| netbox `netbox/account/views.py:194` @v4.7.3 (`SocialAuthBeginView`) | #23112 fix: `POST /oauth/begin/<backend>/` returns the IdP URL as JSON for script navigation | 2026-10-27 |
| netbox `requirements.txt:38-39` @v4.7.3, @v4.7.0, @v4.6.10 | social-auth-app-django 5.9.0 → 6.0.1 → 6.1.0, social-auth-core 4.8.7 → 5.1.0 → 5.2.0 | 2026-10-27 |
| netbox `settings.py` @v4.6.0, @v4.7.3 (`LOGIN_REQUIRED` FutureWarning; default `SOCIAL_AUTH_PIPELINE` :739-749) + `authentication/__init__.py` @v4.7.3 | `LOGIN_REQUIRED` deprecated since 4.6.0, removal 5.0; default pipeline unchanged in 4.7.3; `configure_groups` / `_is_superuser` / `_is_staff` / `user_default_groups_handler` still present (find by name) | 2026-10-27 |
| python-social-auth/social-core `open_id_connect.py` @ tag 5.2.0 | OIDC defaults unchanged from 4.8.7: `DEFAULT_USE_PKCE = False` [:101], `JWT_ALGORITHMS = ["RS256"]` [:79], `USERNAME_KEY = "preferred_username"` [:74], `ID_KEY = "sub"` [:73] | 2026-10-27 |
| python-social-auth/social-app-django `social_django/views.py:36` @ tag 6.1.0 + CHANGELOG 6.0.0 | `auth` view is `@require_POST`; "Login views now always require POST requests" (6.0.0) → GET login start = 405 | 2026-10-27 |
| netbox-community/netbox-docker `docker/docker-entrypoint.sh` @ main | entrypoint runs `migrate`, `trace_paths`, `remove_stale_contenttypes`, `clearsessions`, `reindex --lazy` — no `rebuild_config_context_cache` | 2026-10-27 |
| netbox-chart `values.yaml` @netbox-8.3.77 / @netbox-8.3.96, `templates/configmap.yaml:87` | `housekeeping.enabled: false` default from 8.3.77, CronJob command `manage.py housekeeping`; `LOGIN_REQUIRED: {{ toJson .Values.loginRequired }}`, `loginRequired: false` default | 2026-10-27 |
| https://netboxlabs.com/docs/netbox/getting-started/planning/ | SoT definition, 16-step order | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/release-notes/version-4.2 | MACAddress objects | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/release-notes/version-4.3 | module profiles, Service API break | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/release-notes/version-4.4 | VLAN-to-site deprecation (#19738) | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/release-notes/version-4.5 | v2 tokens (#20210), PortMapping (#20564), cable-terminations read-only | 2026-06-12 |
| https://github.com/netbox-community/netbox/blob/main/docs/release-notes/version-4.6.md | RackGroup (#20961), v1 deprecation (#22128, removal v5.0), plaintext-once (#22062/#22081) | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/models/dcim/moduletypeprofile/ | profile JSON schema rules | 2026-06-12 |
| https://netboxlabs.com/docs/netbox/models/dcim/devicebay/ + modulebay/ | bay distinction rule | 2026-06-12 |
| github.com/netbox-community/netbox-chart `charts/netbox/templates/` | lookup preservation, api_token generation+mount, PLUGINS toJson, secret key projections | 2026-06-12 (clone @ 2026-06-09) |
| netbox-chart `templates/secret.yaml`, `templates/worker/deployment.yaml`, `templates/deployment.yaml` @netbox-8.3.97 + two `helm template` renders | `api_token: {{ .Values.superuser.apiToken \| default uuidv4 }}` has no `lookup`; the worker's `checksum/secret` is `sha256sum` of all of `secret.yaml` (changes per render unless `superuser.apiToken` is set), the web Deployment's uses `common.utils.checksumTemplate` (`fromYaml`, first document only — stable); netbox-docker `super_user.py` creates a token only when both `superuser_api_token` and `superuser_api_key` exist, and the chart mounts no key | 2026-10-27 |
| github.com/netbox-community/netbox-docker/wiki/Using-Netbox-Plugins | §5 plugin install: image lineage (ghcr netbox image is built by netbox-docker), plugin_requirements.txt/Dockerfile-Plugins is compose-only, PLUGINS module-name vs PyPI dist-name | 2026-06-14 |
| github.com/netbox-community/netbox-chart `values.yaml` (image.registry/repository=ghcr.io/netbox-community/netbox) | §5 chart pulls the netbox-docker-built image; §5 init-container pip path | 2026-06-14 (live values 8.3.14) |
| github.com/netbox-community/netbox `netbox/api/authentication.py` | nbt_ prefix version inference, "Invalid v1 token" | 2026-06-12 (read in v4.6.2 container) |
| github.com/netbox-community/netbox `netbox/netbox/authentication/__init__.py` | sso-hardening: REMOTE_AUTH_SUPERUSER/STAFF/GROUP_SYNC are RemoteUserBackend-only (`_is_superuser`/`_is_staff`/`configure_groups` L163-262); `user_default_groups_handler` assigns flat REMOTE_AUTH_DEFAULT_GROUPS, no flag mapping (L383-401) | 2026-06-14 (main @ gh api) |
| github.com/netbox-community/netbox `netbox/netbox/settings.py` | sso-hardening: default SOCIAL_AUTH_PIPELINE (L716-726), only NetBox step is user_default_groups_handler | 2026-06-14 (main @ gh api) |
| netboxlabs.com/docs/.../authentication/overview, hull.au/blog/netbox-authentik-oidc-sso, docs.goauthentik.io/integrations/services/netbox | sso-hardening: SOCIAL_AUTH_PROTECTED_USER_FIELDS=['groups'] sign-in workaround, SOCIAL_AUTH_REDIRECT_IS_HTTPS, groups-claim prerequisite, usersocialauth linking | 2026-06-14 |
| helm repo charts.netbox.oss.netboxlabs.com | **latest chart 8.3.96 / app v4.7.3** (2026-10-27) — still 8.x (no major) | 2026-10-27 |
| github.com/netbox-community/netbox releases | **NetBox v4.7.3** (2026-10-13) is latest; 4.7.x is GA, no 5.0 yet, so the v1-token-removal-at-v5.0 claim stands | 2026-10-27 |
| netbox-chart `charts/netbox/docs/auth.md` + `docs/extra.md` | §9 chart SSO docs exist (Keycloak/GitLab examples, pipeline-mount pattern, extraConfig `*.yaml`-key mechanics); dated-example findings (legacy /auth URLs, KeycloakOAuth2 pasted key, associate_by_email) | 2026-07-30 (clone @ HEAD, post-8.3.57) |
| netbox-chart `files/configuration.py` + `templates/configmap.yaml` | §9.1 extraConfig deep-merge loader (`/run/config/extra/*/*.yaml` → module globals), remoteAuth → REMOTE_AUTH_* rendering (configmap.yaml:107-108) | 2026-07-30 (clone @ HEAD) |
| netbox-chart issue #987 (closed 2026-01) | §9.1 maintainers declined dedicated OIDC values — extraConfig is the supported path | 2026-07-30 (gh) |
| netbox-chart issue #945 (closed 2026-01) | §9.4 Python-literal-in-extraConfig pod crash; SOCIAL_AUTH_BACKEND_ATTRS YAML shape | 2026-07-30 (gh) |
| github.com/netbox-community/netbox `netbox/netbox/urls.py:23`, `settings.py:754`, `requirements.txt:39` | §9 /oauth/ mount → redirect URI shape; JSONFIELD_ENABLED already set; social-auth-core pin 4.8.7 | 2026-07-30 (clone @ HEAD) |
| github.com/python-social-auth/social-core `social_core/backends/open_id_connect.py` @ tag 4.8.7 | sso-hardening OIDC gotchas: `name = "oidc"`, `USERNAME_KEY = preferred_username`, `JWT_ALGORITHMS = ["RS256"]`, `OpenIdConnectAuth(BaseOAuth2PKCE)` [:48] but `DEFAULT_USE_PKCE = False` [:94] — PKCE supported, **not** on by default; opt in via `SOCIAL_AUTH_OIDC_USE_PKCE = True` [:59]. **Corrected 2026-08-18** — the previous row said `True` and read as "works out of the box", which is backwards | 2026-08-18 (gh api @ tag) |
| python-social-auth.readthedocs.io/en/latest/backends/oidc.html | SOCIAL_AUTH_OIDC_* setting names (ENDPOINT/KEY/SECRET/SCOPE/USERNAME_KEY/JWT_ALGORITHMS) | 2026-07-30 |
| netbox discussion #19584 (+ younsl.github.io blog, **now 404 — dropped**) | corroboration: group-mapping-needs-custom-pipeline on k8s, pipeline ConfigMap-mount pattern in the wild. Discussion #19584 still live; the blog corroboration is gone, so the claim now rests on the discussion plus the in-tree pipeline source | 2026-08-18 |
| netbox v4.7.1 release notes + issues #23112, #23130 | 4.7.0 SSO login button broken under `form-action` CSP; 4.7.0 `pg_dump` cannot restore the ltree cascade triggers; both fixed 4.7.1 (2026-09-15) | 2026-09-15 |
| netbox `docs/release-notes/version-4.5.md` @v4.7.3 (#16137) + commit c0e4d1c1e (PR #20306) | `User.is_staff` removed in 4.5.0, together with `REMOTE_AUTH_STAFF_GROUPS`/`_STAFF_USERS` (settings.py, remote-authentication.md); `RemoteUserBackend._is_staff` returns `is_superuser` @v4.7.3; `User(AbstractUser)` still has it @v4.4.0 | 2026-10-27 |
| netbox issue #23196 (milestone v4.7.2, closed 2026-09-24) | async bulk API writes stored plaintext v2 tokens in `Job.data` on 4.7.0–4.7.1 | 2026-10-27 |
| netbox-chart Helm index (`index.yaml`, `.entries.netbox[]`) | chart→app pins: 8.3.66 → 4.6.10 (last 4.6), 8.3.67–8.3.77 → 4.7.0, 8.3.78–8.3.90 → 4.7.1, 8.3.91 → 4.7.2, 8.3.92–8.3.96 → 4.7.3 | 2026-10-27 |

Refresh cadence: run `/skill-improver freshen netbox-best-practices` when a new
NetBox minor (4.7/5.0) or netbox-chart major lands — the v1-token removal
(rescheduled to v5.0) and the PortMapping template-endpoint nuance are the two
claims most likely to change.

**2026-07-21 pass: the trigger did not fire.** NetBox is still on **4.6.x**
(v4.6.8) and the chart is still **8.x** (8.3.57, 2026-08-18), so no
version-delta claim was invalidated and the v5.0-token-removal schedule stands.
What did change: 23 chart patches and 3 NetBox patches. Also documented the
`netbox-chart` two-products-one-release-stream trap above — `releases/latest`
there returns `netbox-operator`, not the chart.
