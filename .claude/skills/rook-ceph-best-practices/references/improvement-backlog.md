# Improvement backlog — rook-ceph-best-practices

## Open

- **Userspace mounters and AES256K on pre-7.0 kernels.** Whether rbd-nbd /
  ceph-fuse (librados in the cephcsi image) accept AES256K CSI keys on a
  kernel older than 7.0 is stated nowhere upstream (checked 2026-09-23: Rook
  cephx-key-rotation.md at v1.19.11 and v1.20.7, ceph-csi v3.16.3 notes,
  rook/rook and ceph/ceph-csi issues). Blocked on: a test cluster with a
  pre-7.0 node using the rbd-nbd or fuse mounter, or an upstream statement.
- **Ceph Umbrella (v21).** Not released on 2026-09-23. Blocked on: the
  release. Then add it to the version-gate table and re-check the AES256K
  floor Rook documents (21.2.0).
