# Model access semantics — sentinels, access groups, wildcards

Line numbers @ `4d543245` (v1.95.0-dev, 2026-07-29). The one docs page that gets the core right: `docs/proxy/key_auth_arch.md:24-36` (the three sentinels). Nearly everything else here is undocumented or contradicts observed behavior.

## The empty-list rule

`auth/auth_checks.py:2948-2951`:

```python
if (len(filtered_models) == 0 and len(models) == 0) or "*" in filtered_models:
    all_model_access = True
```

`GenerateRequestBase.models` defaults to `[]` (`_types.py:1036`) — so **both omitting `models` and sending `models: []` grant access to every model** at the key level. BerriAI's own `litellm-skills` templates (`add-key/SKILL.md:47`, `update-key/SKILL.md:49`) emit `"models": [<models_or_empty>]` — following them produces unrestricted keys.

One proxy-level modifier: `litellm.default_key_generate_params` fills `models` (and `max_budget`, `team_id`, `tpm_limit`, …) when the request sends `None`/`[]`/`{}` (`key_management_endpoints.py:790-805`) — on such a proxy, `[]` means "the default list", elsewhere it means "everything".

## Organizations — two asymmetries that bite

Verified against `organization_endpoints.py` @ v1.100.1.

**Deleting an org deletes its keys. Removing a member does not.**

| Call | What it removes |
|---|---|
| `DELETE /organization/delete` | every team in the org, every membership, **every key carrying that `organization_id`**, then the org row — four `delete_many` calls in sequence (`:949`–`:960`) |
| `DELETE /organization/member_delete` | the `OrganizationMembership` row and nothing else (`:1498`) — the member's keys, teams and budget row survive |

So off-boarding one person leaves their virtual keys live and callable; only tearing
down the whole org revokes keys, and it revokes them for everyone at once. Neither is
a soft delete.

**An org admin can do everything to an org except delete it.** `/organization/delete`
and `/organization/new` check `user_role != PROXY_ADMIN` inline and 401; every other
org route goes through `_verify_org_access`, which passes a proxy admin **or** an
`ORG_ADMIN` member of that specific org. So an org admin may update the org, add,
update and remove members — but cannot delete the org.

`member_add`, `member_update` and `member_delete` each carry an in-code note that the
org scoping "was never enforced" before being added: on older builds any authenticated
key could manage members of **any** org. Treat org-member isolation as a property of
recent versions, not of the API's design.

**The empty-list rule extends to orgs.** `org.models: []` means every model, by the
same `_check_model_access_helper` line quoted above — an org created without `models`
is unrestricted, not unprovisioned.

**Budget scopes are ANDed, not resolved.** Org, team, key, tag, user, team-member and
end-user budgets are each checked independently and the request fails if any one is
over (`auth_checks.py`, `asyncio.gather` over the budget coroutines). Nothing "wins";
a generous org budget does not lift a tight key budget. The org check is also
opportunistic — it skips silently when the org id cannot be resolved from the key or
its team, or when the org's `max_budget` is unset or `<= 0`.

## The three sentinels (`_types.py:3110-3113`)

| Sentinel | Behavior |
|---|---|
| `all-proxy-models` | unrestricted (`auth_checks.py:2952`); also grants direct access to every non-team model (`proxy_server.py:11309`) |
| `all-team-models` | inherit the team's list — **with no `team_id` it resolves to `[]` = unrestricted** (`auth_checks.py:3045-3060`) |
| `no-default-models` | hard deny; applies to the **user list only** (`auth_checks.py:3366`) |

`no-default-models` sharp edges: teams configured with `models: ["no-default-models"]` produce a `/v1/models` response containing the literal string `no-default-models` as a model entry (#31438/#34998 open family), and access-group names placed in `models` brick the key rather than resolving.

## Access groups are additive grants, NOT allow-lists (open #34296)

A key with `access_group_ids: [g1]` and `models: []` can call **everything** — the group *adds* models; the empty `models` still means all. To scope a key to exactly its groups: `models: ["no-default-models"], access_group_ids: [...]`. Compounding: the model access check ignores key-level `access_group_ids` in some paths (#28464 open), and assigning access groups on a wildcard model is premium-gated (`key_management_endpoints.py:3565-3579`).

## `/v1/models` is not an access oracle

- Never resolves `access_group_ids` — grouped models don't appear for the key that can use them (#31966/#31438/#34998/#25222/#21102 open cluster).
- Ignores user-level `models` restriction entirely (#26420 open).
- Leaks access-group names as model entries (#25550 open).
- `/team/info` leaks internal `model_name_{team_id}_{uuid}` routing keys, and `/team/update` round-trips them into persistent `team.models` corruption (#30798 open).
- v1.92.0 had a CPU-pegging regression listing wildcard routes (#33636, closed).

Verify access with a live completion attempt per model, not by listing.

## Wildcards

- `bedrock/*` prefix-matches sloppily — also matches `bedrockz/*` (#33030 open).
- Load-balancing can span deployments the key shouldn't access when wildcard model-groups mix (#21935 open).
- JWT `role_permissions.models` doesn't honor wildcards (#27536 open).

## Key inheritance chain

On `/key/generate` under a user: if the key request's `models` is empty and the user row has `models`, the key **inherits the user's list** (`key_management_endpoints.py:3826-3827`). `/user/new` auto-creates a key unless `auto_create_key: false` (`internal_user_endpoints.py:382`). So provisioning order (user-with-models first vs key first) changes effective access — script it deterministically: always set `models` explicitly on the key.
