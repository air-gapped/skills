# The Patroni DCS: v1 Endpoints -> ConfigMaps

Verified **2026-08-25** against upstream at tag `v2.0.2` (`docs/migrate.md`,
`docs/administrator.md`), the v1.15.0 release notes, and issue #2946.

## Where the DCS actually lives

With `DCS_ENABLE_KUBERNETES_API=true` and no `KUBERNETES_USE_CONFIGMAPS`,
Patroni keeps the **leader lease** and **cluster config** as annotations on
`Endpoints` objects:

```
<cluster>          annotations: acquireTime, leader, optime, renewTime, transitions, ttl
<cluster>-config   annotations: config, history, initialize
```

## The deprecation is not a deadline

`core/v1 Endpoints` was deprecated in Kubernetes v1.33. **No removal is
planned or announced** — the Kubernetes blog states the type "will probably
never completely go away", and KEP-4974 targets the Endpoints *controller* and
the conformance requirement, not the API type.

So the deprecation warning is not a forcing function. The actual forcing
function is the **operator upgrade to v2**, which crosses the changed
`kubernetes_use_configmaps` default.

**EndpointSlice is not the fix and never will be.** Maintainer @FxKu: "likely
we cannot use EndpointSlices and have to switch to using configmaps." An
EndpointSlice is a derived, sharded projection of Service endpoints; it cannot
serve as a leader-lease object. The fix is ConfigMaps.

## The hazard

During a rolling update a leader Endpoint and a leader ConfigMap can exist
simultaneously — **split brain**. This is why the DCS switch must not be
bundled into the operator upgrade, and why `kubernetes_use_configmaps` is
worth pinning to `false` across the v2 hop and migrating separately.

Consider enabling `enable_patroni_failsafe_mode` (default `false`) *before*
this migration: with it off, DCS trouble can demote a healthy primary.

## Upstream migration procedure (docs/migrate.md, v2.0.2)

Global, not per-cluster — simpler than it first looks:

1. Set global `min_instances` and `max_instances` to `1` (and temporarily
   remove `ignore_instance_limits_annotation_key` if set), so every cluster
   scales in to a single primary.
2. Wait until all clusters are healthy, then set
   `kubernetes_use_configmaps: true`. This replaces the primary pod of every
   cluster — **downtime for as long as the pods reschedule and start**.
3. Confirm each cluster now has ConfigMaps named after it. Then revert step 1
   and scale back out.
4. Delete the orphaned Endpoints. They share the ConfigMaps' names and
   Kubernetes garbage collection will not remove them.

**Two documented discrepancies — verify empirically on the first cluster
rather than trusting either source.** The v1.15.0 release notes say the switch
creates `<cluster>-config` and `<cluster>-failover`; v2 `migrate.md` says three
ConfigMaps, adding `-leader`. The v1.15.0 notes also say leftover Endpoints
"do not cause any harm if you leave them", which is softer than `migrate.md`'s
instruction to delete them.

## Two lower-downtime paths that `docs/migrate.md` omits

The v1.15.0 release notes carry a fuller migration guide than the v2
`migrate.md` does. Beyond the in-place path above, there are two ways to avoid
migrating every cluster at once:

- **Per-cluster via `CONTROLLER_ID`.** Run a second operator instance with its
  own config (ConfigMaps enabled) and a `CONTROLLER_ID` set; annotate
  individual Postgres manifests with that controller id to move one cluster at
  a time. See `docs/administrator.md` §"Operators with defined ownership of
  certain Postgres clusters". Caveat: **#3151 (open)** — the operator skips a
  cluster update when the controller ID changes.
- **Via standby clusters** (lowest downtime). Second operator with ConfigMaps
  and a `CONTROLLER_ID`; create a standby cluster for each source, copy the
  source secrets beforehand to avoid connection issues, then stop writes and
  promote. Downtime reduces to roughly the application's redeploy time.
