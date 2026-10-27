# Sources

Freshened: 2026-09-23 — every row probed at creation.

| Source | URL | Last verified | Notes |
|---|---|---|---|
| RGW options | https://github.com/ceph/ceph/blob/v20.2.4/src/common/options/rgw.yaml.in | 2026-09-23 | Same at v19.2.6: `rgw_dynamic_resharding` true, `rgw_max_objs_per_shard` 100000, `rgw_max_dynamic_shards` 1999, `rgw_sigv4_insecure` false, `rgw_s3_client_max_sig_ver` -1, `rgw_lifecycle_work_time` 00:00-06:00, `rgw_lc_max_worker` 3, `rgw_gc_obj_min_wait` 2h. |
| Large omap threshold | https://github.com/ceph/ceph/blob/v19.2.6/src/common/options/osd.yaml.in | 2026-09-23 | `osd_deep_scrub_large_omap_object_key_threshold` 200000. |
| CVE-2026-54330 | https://docs.ceph.com/en/latest/security/CVE-2026-54330/ | 2026-09-23 | SigV4 unsigned `x-amz-*` headers; fixed 19.2.6 / 20.2.4. |
| CVE-2026-39944 | https://docs.ceph.com/en/latest/security/CVE-2026-39944/ | 2026-09-23 | STS token CBC bit-flip → admin; fixed 19.2.6 / 20.2.4. |
| Combo release | https://ceph.io/en/news/blog/2026/v20-2-4-v19-2-6-combo-released/ | 2026-09-23 | 2026-08-19; multisite `rgw_sigv4_insecure` note. |
| Presigned PUT regression | https://tracker.ceph.com/issues/79674 | 2026-10-27 | Resolved. Squid backport 79723 (pr#71296) Released In v19.2.7; tentacle backport 79725 merged (Fixed In v20.2.4-294), no Tentacle release after 20.2.4 yet. CVE-2026-54330 page: affects boto3 presigned PUTs with a content type, aws-sdk-php, minio-go (thanos-io/objstore: Thanos, Loki, Mimir); "upgrade directly to 19.2.7"; `debug_rgw` 5 logs `Signature rejected`; unsigned other `x-amz-*` headers are rejected by AWS too, so not a regression. |
| Unsigned x-amz-content-sha256 regression | https://tracker.ceph.com/issues/79803 | 2026-10-27 | Backporting. Squid 79873 (pr#71360) Released In v19.2.7; tentacle 79871 QA Testing. |
| Multisite forwarding regression | https://tracker.ceph.com/issues/79698 | 2026-10-27 | Duplicate of 74579 (Resolved, pr#67083). Squid backport 75193 (pr#69003) Released In v19.2.7; tentacle 75194 Released In v20.2.2. Maintainer note 2026-08-27: "the regression was only on squid". Rook CI on a 19.2.6 build with the fix passed with both settings removed. |
| Multisite upgrade rule | https://docs.ceph.com/en/latest/security/CVE-2026-54330/ | 2026-10-27 | "The REST client used in multisite was generating improperly signed requests ... set rgw_sigv4_insecure to true before you begin to upgrade. After all clusters are upgraded, set the option to false again." Same text in the combo-release blog. |
| Rook multisite doc | https://github.com/rook/rook/blob/v1.21.1/Documentation/Storage-Configuration/Object-Storage-RGW/ceph-object-multisite.md | 2026-10-27 | Warning in v1.21.0+ (absent through v1.20.9): set `rgw_sigv4_insecure: "true"` + `rgw_s3_client_max_sig_ver: "2"` in `gateway.rgwConfig`, revert to `"false"` / `"-1"`. Names 19.2.6 and 20.2.4; the Ceph tracker scopes the forwarding break to Squid. |
| CRC64NVME | https://tracker.ceph.com/issues/70040 | 2026-09-23 | Fixed via ceph/ceph#61878 in Tentacle 20.2.0. |
| CRC64NVME Squid backport | https://tracker.ceph.com/issues/70736 | 2026-09-23 | Status New — not shipped. |
| bypass-gc corruption | https://tracker.ceph.com/issues/73348 | 2026-10-27 | Resolved (pr#65772). Backports Released In: squid 73598 v19.2.4, tentacle 73596 v20.2.1, reef 73597 v18.2.8. Reported on 17.2.6, 17.2.8, 19.2.2. |
| Multisite sync status | https://github.com/ceph/ceph/blob/v20.2.4/doc/radosgw/multisite.rst | 2026-10-03 | §Checking the Sync Status (behind vs recovery shards); §Changing the Metadata Master Zone (wait for metadata sync before promoting, else changes lost); `sync error list` in `doc/man/8/radosgw-admin.rst`. |
| Dynamic resharding doc | https://docs.ceph.com/en/squid/radosgw/dynamicresharding/ | 2026-09-23 | "Cleanup of stale instances should not be done in a multisite deployment." |
| Resharding without pausing | https://ceph.io/en/news/blog/2026/rgw-improved-resharding/ | 2026-09-23 | Tentacle two-phase reshard. |
| Tentacle release notes | https://docs.ceph.com/en/latest/releases/tentacle/ | 2026-09-23 | LastModified truncation; GetObjectAttributes; tenant IAM and STS Lite deprecated; ISA-L default. |
| Rook object accounts | https://github.com/rook/rook/blob/v1.20.7/Documentation/Storage-Configuration/Object-Storage-RGW/ceph-object-accounts.md | 2026-09-23 | Experimental; only `quay.ceph.io/ceph-ci/ceph:main`. |
| Rook COSI | https://github.com/rook/rook/blob/v1.20.7/Documentation/Storage-Configuration/Object-Storage-RGW/cosi.md | 2026-09-23 | Experimental. |
| Rook notifications | https://github.com/rook/rook/blob/v1.20.7/Documentation/Storage-Configuration/Object-Storage-RGW/ceph-object-bucket-notifications.md | 2026-09-23 | Kafka `mechanism`, secret refs. |
| Rook v1.17.0 notes | https://github.com/rook/rook/releases/tag/v1.17.0 | 2026-09-23 | Undeclared CephObjectStoreUser S3 credentials purged. |
| Rook Squid→Tentacle RGW early roll | https://github.com/rook/rook/issues/18367 | 2026-09-23 | Closed. |
