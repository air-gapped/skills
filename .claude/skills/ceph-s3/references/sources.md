# Sources

Freshened: 2026-09-23 — every row probed at creation.

| Source | URL | Last verified | Notes |
|---|---|---|---|
| RGW options | https://github.com/ceph/ceph/blob/v20.2.4/src/common/options/rgw.yaml.in | 2026-09-23 | Same at v19.2.6: `rgw_dynamic_resharding` true, `rgw_max_objs_per_shard` 100000, `rgw_max_dynamic_shards` 1999, `rgw_sigv4_insecure` false, `rgw_s3_client_max_sig_ver` -1, `rgw_lifecycle_work_time` 00:00-06:00, `rgw_lc_max_worker` 3, `rgw_gc_obj_min_wait` 2h. |
| Large omap threshold | https://github.com/ceph/ceph/blob/v19.2.6/src/common/options/osd.yaml.in | 2026-09-23 | `osd_deep_scrub_large_omap_object_key_threshold` 200000. |
| CVE-2026-54330 | https://docs.ceph.com/en/latest/security/CVE-2026-54330/ | 2026-09-23 | SigV4 unsigned `x-amz-*` headers; fixed 19.2.6 / 20.2.4. |
| CVE-2026-39944 | https://docs.ceph.com/en/latest/security/CVE-2026-39944/ | 2026-09-23 | STS token CBC bit-flip → admin; fixed 19.2.6 / 20.2.4. |
| Combo release | https://ceph.io/en/news/blog/2026/v20-2-4-v19-2-6-combo-released/ | 2026-09-23 | 2026-08-19; multisite `rgw_sigv4_insecure` note. |
| Presigned PUT regression | https://tracker.ceph.com/issues/79674 | 2026-09-23 | Unsigned Content-Type rejected; ceph-users 2026-08-31 workaround `rgw_sigv4_insecure` until 19.2.7 / 20.2.5. |
| Multisite forwarding regression | https://tracker.ceph.com/issues/79698 | 2026-09-23 | Closed as duplicate of 74579; both settings needed. |
| Rook multisite doc | https://github.com/rook/rook/blob/master/Documentation/Storage-Configuration/Object-Storage-RGW/ceph-object-multisite.md | 2026-09-23 | Warning added after v1.20.7: set `rgw_sigv4_insecure: "true"` + `rgw_s3_client_max_sig_ver: "2"`, revert to `"false"` / `"-1"`. |
| CRC64NVME | https://tracker.ceph.com/issues/70040 | 2026-09-23 | Fixed via ceph/ceph#61878 in Tentacle 20.2.0. |
| CRC64NVME Squid backport | https://tracker.ceph.com/issues/70736 | 2026-09-23 | Status New — not shipped. |
| bypass-gc corruption | https://tracker.ceph.com/issues/73348 | 2026-09-23 | Server-side copy + `--bypass-gc`; affected 17.2.6, 17.2.8, 19.2.2 per tracker. |
| Dynamic resharding doc | https://docs.ceph.com/en/squid/radosgw/dynamicresharding/ | 2026-09-23 | "Cleanup of stale instances should not be done in a multisite deployment." |
| Resharding without pausing | https://ceph.io/en/news/blog/2026/rgw-improved-resharding/ | 2026-09-23 | Tentacle two-phase reshard. |
| Tentacle release notes | https://docs.ceph.com/en/latest/releases/tentacle/ | 2026-09-23 | LastModified truncation; GetObjectAttributes; tenant IAM and STS Lite deprecated; ISA-L default. |
| Rook object accounts | https://github.com/rook/rook/blob/v1.20.7/Documentation/Storage-Configuration/Object-Storage-RGW/ceph-object-accounts.md | 2026-09-23 | Experimental; only `quay.ceph.io/ceph-ci/ceph:main`. |
| Rook COSI | https://github.com/rook/rook/blob/v1.20.7/Documentation/Storage-Configuration/Object-Storage-RGW/cosi.md | 2026-09-23 | Experimental. |
| Rook notifications | https://github.com/rook/rook/blob/v1.20.7/Documentation/Storage-Configuration/Object-Storage-RGW/ceph-object-bucket-notifications.md | 2026-09-23 | Kafka `mechanism`, secret refs. |
| Rook v1.17.0 notes | https://github.com/rook/rook/releases/tag/v1.17.0 | 2026-09-23 | Undeclared CephObjectStoreUser S3 credentials purged. |
| Rook Squid→Tentacle RGW early roll | https://github.com/rook/rook/issues/18367 | 2026-09-23 | Closed. |
