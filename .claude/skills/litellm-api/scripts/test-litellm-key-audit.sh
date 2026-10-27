#!/usr/bin/env bash
# test-litellm-key-audit.sh — run litellm-key-audit.sh against fixture /key/list pages.
# No proxy needed: a stub `curl` on PATH serves page<N>.json from the case directory.
# Usage: test-litellm-key-audit.sh   (exit 0 = all cases pass)

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT="${HERE}/litellm-key-audit.sh"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/bin"
cat >"$WORK/bin/curl" <<'EOF'
#!/usr/bin/env bash
url="${*: -1}"
page="$(printf '%s' "$url" | sed -n 's/.*[?&]page=\([0-9]*\).*/\1/p')"
f="${FIXTURE_DIR}/page${page}.json"
if [ -f "$f" ]; then cat "$f"; else printf '{"keys": [], "total_pages": null}'; fi
EOF
chmod +x "$WORK/bin/curl"

fail=0
run_case() { # name expected_exit [required-output-patterns...]
  local name="$1" want="$2"; shift 2
  local out rc
  out="$(FIXTURE_DIR="$WORK/$name" PATH="$WORK/bin:$PATH" "$AUDIT" http://stub sk-test 2>&1)"
  rc=$?
  if [ "$rc" -ne "$want" ]; then
    echo "FAIL $name: exit $rc, want $want"; printf '%s\n' "$out" | sed 's/^/  | /'; fail=1; return
  fi
  for p in "$@"; do
    if [[ "$p" == '!'* ]]; then
      if printf '%s' "$out" | grep -q -- "${p#!}"; then echo "FAIL $name: unexpected '${p#!}'"; fail=1; fi
    elif ! printf '%s' "$out" | grep -q -- "$p"; then
      echo "FAIL $name: missing '$p'"; fail=1
    fi
  done
  echo "ok   $name (exit $rc)"
}

# Planted positive: one key per flag class across two pages, plus a properly scoped key.
mkdir -p "$WORK/positive"
cat >"$WORK/positive/page1.json" <<'EOF'
{"keys": [
  {"token": "h-a", "key_alias": "plant-A", "models": [], "team_id": null},
  {"token": "h-b", "key_alias": "plant-B", "models": [], "team_id": "team-1"},
  {"token": "h-c", "key_alias": "plant-C", "models": [], "team_id": null, "access_group_ids": ["g1"]},
  {"token": "h-safe", "key_alias": "scoped", "models": ["gpt-4o"], "team_id": null}
], "total_pages": 2}
EOF
cat >"$WORK/positive/page2.json" <<'EOF'
{"keys": [
  {"token": "h-d", "key_alias": "plant-D", "models": ["*"], "team_id": "team-1"},
  {"token": "h-e", "key_alias": "plant-E", "models": ["all-team-models"], "team_id": null},
  {"token": "h-deny", "key_alias": "denied", "models": ["no-default-models"], "access_group_ids": ["g1"]}
], "total_pages": 2}
EOF
run_case positive 2 "A:empty-models-no-team" "B:empty-models-inherits-team(team-1)" \
  "C:access-groups-with-empty-models" "D:all-proxy-models" "E:all-team-models-no-team" \
  "Scanned 7 keys; flagged 5." '!scoped' '!denied'

# Clean proxy: nothing to flag -> exit 0.
mkdir -p "$WORK/clean"
printf '{"keys": [{"token": "h1", "key_alias": "scoped", "models": ["gpt-4o"]}], "total_pages": 1}' \
  >"$WORK/clean/page1.json"
run_case clean 0 "Scanned 1 keys; flagged 0."

# Error-shaped inputs -> exit 1, never a clean report.
mkdir -p "$WORK/autherror" "$WORK/tokensonly" "$WORK/html"
printf '{"error": {"message": "Authentication Error, Invalid proxy server token passed", "type": "auth_error", "code": "401"}}' \
  >"$WORK/autherror/page1.json"
printf '{"keys": ["sk-hash-1", "sk-hash-2"], "total_pages": 1}' >"$WORK/tokensonly/page1.json"
printf '<html><body>502 Bad Gateway</body></html>' >"$WORK/html/page1.json"
run_case autherror 1 "Unexpected response" '!Scanned'
run_case tokensonly 1 "without their objects" '!Scanned'
run_case html 1 "Unexpected response" '!Scanned'

exit "$fail"
