#!/usr/bin/env bash
# Remove scratch homes left by isolated-run.sh (OC_CI_KEEP=1 or a killed run).
set -euo pipefail

mapfile -t homes < <(find /tmp -maxdepth 1 -type d -name 'oc-ci-*' 2>/dev/null)
echo "Found ${#homes[@]} scratch homes"
((${#homes[@]})) && rm -rf -- "${homes[@]}"
echo "Cleanup done."
