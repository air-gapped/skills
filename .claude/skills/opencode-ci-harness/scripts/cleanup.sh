#!/usr/bin/env bash
# Remove scratch homes left by isolated-run.sh (OC_CI_KEEP=1 or a killed run).
# A home that a live process still has as OPENCODE_TEST_HOME belongs to a run
# in progress (possibly another session's) and is left alone.
set -euo pipefail

mapfile -t homes < <(find /tmp -maxdepth 1 -type d -name 'oc-ci-*' 2>/dev/null)
echo "Found ${#homes[@]} scratch homes"
removed=0 in_use=0
for home in "${homes[@]}"; do
  if grep -qzFx -- "OPENCODE_TEST_HOME=$home" /proc/[0-9]*/environ 2>/dev/null; then
    echo "In use, kept: $home"
    in_use=$((in_use + 1))
  else
    rm -rf -- "$home"
    removed=$((removed + 1))
  fi
done
echo "Cleanup done: $removed removed, $in_use in use."
