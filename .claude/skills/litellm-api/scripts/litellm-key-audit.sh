#!/usr/bin/env bash
# litellm-key-audit.sh — find virtual keys whose effective model access is "everything".
#
# Usage: litellm-key-audit.sh <base-url> <admin-key>
# Exit:  0 = no key flagged, 2 = at least one key flagged, 1 = error (bad response, auth, usage).
#
# Flags keys where:
#   A. models==[] AND no team_id            -> ALL models (auth_checks.py empty-list rule)
#   B. models==[] AND team_id set           -> inherits team list; ALL models if the team's list is empty
#   C. access_group_ids set AND models==[]  -> groups are ADDITIVE grants (issue #34296): still ALL models
#   D. models contains "all-proxy-models" or "*"
#   E. models contains "all-team-models" AND no team_id -> resolves to [] = ALL models
#
# Caveat: on proxies with litellm.default_key_generate_params.models configured, empty models at
# CREATE time was replaced server-side; this audit reads the stored row, which reflects that.
#
# Requires: curl, jq. Pages through /key/list (size cap is 100 server-side).
# Test: scripts/test-litellm-key-audit.sh (no proxy needed).

set -euo pipefail

if [ $# -ne 2 ]; then
  echo "usage: $0 <base-url> <admin-key>" >&2
  exit 1
fi
BASE="${1%/}"
KEY="$2"
command -v jq >/dev/null || { echo "jq required" >&2; exit 1; }

page=1
total_flagged=0
total_seen=0

while :; do
  resp="$(curl -sS -H "Authorization: Bearer ${KEY}" \
    "${BASE}/key/list?return_full_object=true&include_team_keys=true&size=100&page=${page}")"
  if ! printf '%s' "$resp" | jq -e '.keys | type == "array"' >/dev/null 2>&1; then
    echo "Unexpected response on page ${page}: $(printf '%s' "$resp" | head -c 300)" >&2
    exit 1
  fi
  # Bare token strings mean the proxy ignored return_full_object: models are not visible, so
  # every key would look unrestricted. Refuse rather than report false positives.
  if printf '%s' "$resp" | jq -e 'any(.keys[]; type != "object")' >/dev/null; then
    echo "Page ${page} lists keys without their objects (return_full_object ignored); cannot audit." >&2
    exit 1
  fi
  count="$(printf '%s' "$resp" | jq '.keys | length')"
  [ "$count" -eq 0 ] && break
  total_seen=$((total_seen + count))

  flagged="$(printf '%s' "$resp" | jq -r '
    .keys[]
    | . as $k
    | ($k.models // []) as $models
    | ($k.access_group_ids // []) as $groups
    | (
        if ($models | index("all-proxy-models")) or ($models | index("*")) then "D:all-proxy-models"
        elif ($models | index("all-team-models")) and ($k.team_id == null) then "E:all-team-models-no-team=ALL"
        elif ($models | length) == 0 and (($groups | length) > 0) then "C:access-groups-with-empty-models(#34296)"
        elif ($models | length) == 0 and ($k.team_id == null) then "A:empty-models-no-team=ALL"
        elif ($models | length) == 0 then "B:empty-models-inherits-team(\($k.team_id))"
        else empty
        end
      ) as $reason
    | [$reason, ($k.key_alias // "-"), ($k.token // $k.key_name // "?"), ($k.user_id // "-")]
    | @tsv
  ')"
  if [ -n "$flagged" ]; then
    printf '%s\n' "$flagged"
    total_flagged=$((total_flagged + $(printf '%s\n' "$flagged" | wc -l)))
  fi
  # Stop on the last page when the proxy reports it, so a server that ignores `page` cannot loop forever.
  total_pages="$(printf '%s' "$resp" | jq -r '.total_pages // empty')"
  if [ -n "$total_pages" ] && [ "$page" -ge "$total_pages" ]; then
    break
  fi
  page=$((page + 1))
done

echo
echo "Scanned ${total_seen} keys; flagged ${total_flagged}."
echo "Reasons: A/D/E = unrestricted now. B = as restricted as its team (verify the team's models list"
echo "is non-empty via GET /team/info). C = unrestricted despite access groups — set"
echo 'models: ["no-default-models"] alongside access_group_ids to scope the key (see access-model.md).'
[ "$total_flagged" -eq 0 ] || exit 2
