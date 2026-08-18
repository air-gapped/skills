# SSO / OIDC group→role mapping and hardening

This file covers the **one gap** the official `netbox-administration` skill
leaves on authentication. That skill already has the base config for every
backend (local, LDAP, header/proxy, social-auth SAML/OIDC), the Gunicorn
underscore-header gotcha, and login-button styling — **consult it first** for
how to turn OIDC on. What follows is only the part it is thin on: how IdP
groups become NetBox roles, and how not to lock yourself out.

## The trap: group→role mapping is backend-specific

NetBox has two *different* group/role mapping mechanisms, and the settings of
one silently do nothing under the other. This is the single most common OIDC
misconfiguration.

| Setting | Works with | Does NOT work with |
|---|---|---|
| `REMOTE_AUTH_GROUP_SYNC_ENABLED`, `REMOTE_AUTH_GROUP_HEADER`, `REMOTE_AUTH_SUPERUSER_GROUPS`, `REMOTE_AUTH_STAFF_GROUPS`, `REMOTE_AUTH_SUPERUSERS` | `RemoteUserBackend` (header / reverse-proxy auth) | social-auth (OIDC / SAML) — **ignored** |
| `REMOTE_AUTH_DEFAULT_GROUPS` + `SOCIAL_AUTH_PIPELINE` | social-auth (OIDC / SAML) | — |

Why: those `REMOTE_AUTH_SUPERUSER_GROUPS`/`_STAFF` settings are consumed inside
`RemoteUserBackend._is_superuser()` / `._is_staff()` / `.configure_groups()`,
which only the header backend calls. The social-auth login path never touches
them. [source: netbox/netbox/authentication/__init__.py:163-262]

### What native OIDC/SAML actually does out of the box

The default pipeline is:

```python
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'netbox.authentication.user_default_groups_handler',   # <-- the only NetBox step
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)
```
[source: netbox/netbox/settings.py:716-726]

`user_default_groups_handler` assigns **one flat list** —
`REMOTE_AUTH_DEFAULT_GROUPS` — to *every* SSO user, regardless of their IdP
groups, and never sets `is_staff`/`is_superuser`. It looks groups up by name
and logs an error if a named group doesn't exist (so pre-create them).
[source: authentication/__init__.py:383-401]

So with stock config, **every OIDC user lands in the same groups with the same
(non-admin) privileges**. Dynamic per-user role mapping from IdP claims does
not exist until you add it.

## Mapping IdP groups → NetBox groups / is_staff / is_superuser (OIDC)

You need a **custom pipeline function**. Two prerequisites first:

1. Configure the IdP client to emit a `groups` claim and request the scope
   (e.g. Authentik "groups" scope, Keycloak group/client-scope mapper, Entra
   "groups" claim). The claim arrives as `response['groups']` in the pipeline.
2. Work around a known sign-in crash on group writes:
   ```python
   SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['groups']
   ```
   [docs: community-confirmed across Authentik/Keycloak writeups]

Then add a handler and reference it in the pipeline (insert after
`associate_user`, replacing or following `user_default_groups_handler`):

```python
# configuration.py
from django.contrib.auth.models import Group

def map_groups(backend, user, response, *args, **kwargs):
    idp_groups = response.get('groups', []) or []
    # role flags
    user.is_staff      = 'netbox-staff'  in idp_groups or 'netbox-admins' in idp_groups
    user.is_superuser  = 'netbox-admins' in idp_groups
    user.save()
    # mirror IdP groups onto NetBox groups that already exist (don't auto-create)
    wanted = Group.objects.filter(name__in=idp_groups)
    user.groups.set(wanted)

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'configuration.map_groups',            # <-- your function (module path must be importable)
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)
```

Notes:
- **On the helm chart, `configuration.map_groups` does NOT work as written** —
  `configuration.py` there is the chart-managed YAML loader you don't edit, and
  `extraConfig` is YAML-only (it can set the `SOCIAL_AUTH_PIPELINE` string list
  but can never carry the function). Mount the function as its own module via
  `extraVolumes`/`extraVolumeMounts` to `/opt/netbox/netbox/netbox/<name>.py`
  and reference `netbox.<name>.<func>`. Full wiring + worked example:
  `helm-chart-gotchas.md` §9.3 and the chart repo's `charts/netbox/docs/auth.md`.
  The snippet above as-is applies to installs that own `configuration.py`
  (VM / netbox-docker).
- NetBox **object permissions** are attached to the local `Group` objects, not
  carried in the token. SSO decides *which groups* a user is in; you still
  define what those groups *can do* in NetBox. Pre-create the groups + perms.
- `user.groups.set(...)` makes membership authoritative on every login (removal
  in the IdP propagates on next login). Use `.add(...)` if you want SSO to be
  additive-only over locally-assigned groups.
- Re-deriving flags every login means an IdP demotion takes effect next login —
  but an already-issued NetBox **API token keeps working**; SSO never expires
  tokens (see below).

## OIDC backend gotchas (social-core `OpenIdConnectAuth`, NetBox 4.6 pins social-auth-core 4.8.7)

- **Redirect URI must match exactly**: `https://<host>/oauth/complete/oidc/` —
  social_django is mounted under `/oauth/` [source: netbox/netbox/urls.py:23],
  the last segment is the backend's `name` attribute (`oidc`; `keycloak` for
  KeycloakOAuth2), trailing slash required. Wrong scheme (http behind a TLS
  proxy — see rule 3) and missing slash are the two common IdP rejections.
- **Username** comes from the `preferred_username` claim by default
  (`SOCIAL_AUTH_OIDC_USERNAME_KEY`) [source: open_id_connect.py@4.8.7:71] —
  the right default for Keycloak; override for IdPs that only send `sub`.
- **RS256 only by default**: `JWT_ALGORITHMS = ["RS256"]`
  [source: open_id_connect.py@4.8.7:72]. An IdP signing id_tokens with
  ES256/EdDSA fails token validation until
  `SOCIAL_AUTH_OIDC_JWT_ALGORITHMS = ['RS256', 'ES256']`.
- **PKCE is available but OFF by default — you must enable it.**
  `OpenIdConnectAuth` does inherit `BaseOAuth2PKCE`
  [source: open_id_connect.py@4.8.7:48], so the backend *supports* PKCE — but
  the class overrides the base default back to `DEFAULT_USE_PKCE = False`
  [source: open_id_connect.py@4.8.7:94], with the class docstring naming
  `SOCIAL_AUTH_OIDC_USE_PKCE = True` as the opt-in [:59]. Set
  `SOCIAL_AUTH_OIDC_USE_PKCE = True` explicitly; a PKCE-required client
  policy (e.g. Keycloak) fails the authorization request without it. The
  challenge method is already `S256` once enabled [:93].

## If you use the header / proxy backend instead

Then the `REMOTE_AUTH_*` group settings *do* work and you don't need a custom
pipeline:

```python
REMOTE_AUTH_GROUP_SYNC_ENABLED = True
REMOTE_AUTH_GROUP_HEADER   = 'HTTP_X_FORWARDED_GROUPS'
REMOTE_AUTH_GROUP_SEPARATOR = '|'
REMOTE_AUTH_SUPERUSER_GROUPS = ['netbox-admins']
REMOTE_AUTH_STAFF_GROUPS     = ['netbox-staff']
```
[source: authentication/__init__.py:202-262]

But this backend trusts HTTP headers blindly — see hardening rule 2.

## Hardening rules (apply regardless of backend)

1. **Keep a local break-glass superuser.** SSO misconfig, a pipeline typo, or
   an IdP outage will otherwise lock everyone out. The local
   `/admin`-capable account is your recovery path — never delete it, store its
   password in the vault. (NetBox tries backends in `REMOTE_AUTH_BACKEND` order
   and falls through to local `ModelBackend`.)

2. **Header/proxy auth: never expose NetBox's port directly.** With
   `RemoteUserBackend`, anyone who can reach NetBox bypassing the proxy can set
   `HTTP_REMOTE_USER`/`HTTP_X_FORWARDED_GROUPS` and become superuser. Bind
   NetBox to localhost / the proxy network only, and strip those inbound headers
   at the proxy edge. (Native OIDC doesn't have this exposure — prefer it.)

3. **Force HTTPS on the redirect** when behind a TLS-terminating proxy, or the
   callback URL is built as `http://` and the IdP rejects it:
   ```python
   SOCIAL_AUTH_REDIRECT_IS_HTTPS = True
   ```

4. **SSO ≠ API auth.** OIDC protects the *web* login only. Programmatic access
   still uses NetBox API tokens, which are independent of and **not revoked by**
   SSO/IdP state. Scope tokens, set expiries, and don't mint long-lived
   god-tokens just because the UI is behind SSO. (v2 `nbt_` tokens are
   plaintext-once — see `version-deltas.md`.)

5. **Pre-create groups; don't auto-create.** Leave
   `REMOTE_AUTH_AUTO_CREATE_GROUPS = False` (the default) in prod and create
   only the groups you attach permissions to — otherwise the IdP's entire group
   namespace materializes as empty NetBox groups, and
   `user_default_groups_handler` errors on any name that doesn't exist anyway.

6. **Least privilege default.** Point `REMOTE_AUTH_DEFAULT_GROUPS` at a
   read-only group; elevate only via explicit IdP-group membership in your
   mapping function. Never default new SSO users to a writable/admin group.

7. **Don't add `associate_by_email` to the pipeline** — the chart repo's
   `docs/auth.md` Keycloak/GitLab examples include it, but it links an incoming
   SSO identity to any existing local account with a matching email. With an
   IdP that doesn't verify email addresses this is account pre-hijack of local
   users — including the break-glass superuser if its email is guessable. Keep
   the default pipeline's create/associate steps; for one-time linking of
   existing local users, use `/admin/social_django/usersocialauth/` instead.

## Quick verification after wiring SSO

- Log in as a non-admin IdP user → confirm they are **not** staff/superuser and
  land in the read-only group.
- Log in as an `netbox-admins` IdP user → confirm `is_superuser` flips.
- Remove a user from the admin IdP group, re-login → confirm demotion (and that
  any issued API token of theirs still works — expected, revoke manually).
- Existing local users can be linked to an OIDC identity at
  `/admin/social_django/usersocialauth/`.
