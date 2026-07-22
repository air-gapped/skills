#!/bin/bash
# Usage: source owui-curl.sh; owui GET /api/version; owui POST /api/v1/groups/create '{"name":"x","description":"y"}'
# Requires: OWUI_URL, OWUI_TOKEN env vars; curl + jq.
# Wraps every call with the two checks scripted Open WebUI work needs:
#   1. HTTP 2xx — non-2xx aborts and prints the response body
#   2. Content-Type is JSON — defeats the SPA HTML-200 trap (typo'd paths return index.html with 200)
# Exit codes: 0 ok, 22 HTTP error, 65 non-JSON response (HTML trap), 64 usage error.

owui() {
  local method=$1 path=$2 body=${3-}
  [[ -n "${OWUI_URL:-}" && -n "${OWUI_TOKEN:-}" ]] || { echo "owui: set OWUI_URL and OWUI_TOKEN" >&2; return 64; }
  local args=(-sS -X "$method" -H "Authorization: Bearer $OWUI_TOKEN" -w '\n%{http_code}\t%{content_type}')
  [[ -n "$body" ]] && args+=(-H 'Content-Type: application/json' -d "$body")
  local out; out=$(curl "${args[@]}" "${OWUI_URL%/}$path") || return $?
  local meta=${out##*$'\n'} resp=${out%$'\n'*}
  local code=${meta%%$'\t'*} ctype=${meta#*$'\t'}
  if [[ $code != 2* ]]; then
    echo "owui: HTTP $code on $method $path" >&2; echo "$resp" >&2; return 22
  fi
  if [[ $ctype != application/json* && $ctype != */*ndjson* ]]; then
    echo "owui: non-JSON response ($ctype) on $method $path — SPA HTML-200 trap, check the path" >&2; return 65
  fi
  printf '%s\n' "$resp"
}

# Preflight: verify instance + token before scripted work. Usage: owui_preflight [expected-role]
owui_preflight() {
  local want_role=${1:-admin} v role
  v=$(owui GET /api/version | jq -er .version) || { echo "owui: version probe failed" >&2; return 1; }
  role=$(owui GET /api/v1/auths/ | jq -er .role) || { echo "owui: auth probe failed (key disabled/expired?)" >&2; return 1; }
  echo "owui: instance v$v, token role=$role"
  [[ $role == "$want_role" ]] || { echo "owui: need role '$want_role'" >&2; return 1; }
}
