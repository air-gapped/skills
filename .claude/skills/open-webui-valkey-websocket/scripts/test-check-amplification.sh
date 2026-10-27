#!/usr/bin/env bash
#
# test-check-amplification.sh — offline self-test for check-amplification.sh.
# Runs it against a stub valkey-cli and asserts the exit code per case:
#   refused MONITOR (Sentinel port / no +monitor ACL) -> 3, empty sample -> 4,
#   planted 1500 PUBLISH ops -> 0 with the "almost certainly 1" verdict.
# Run after editing check-amplification.sh. Needs bash and coreutils only.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
STUB_DIR="$(mktemp -d)"
trap 'rm -rf "$STUB_DIR"' EXIT

cat > "$STUB_DIR/valkey-cli" <<'STUB'
#!/usr/bin/env bash
cmd="${*: -1}"
if [[ "$cmd" == "PING" ]]; then echo PONG; exit 0; fi
case "$STUB_MODE" in
  refuse) echo "ERR unknown command 'MONITOR', with args beginning with: "; exit 1;;
  empty)  echo OK;;
  hot)    echo OK
          for i in $(seq 1 1500); do
            echo "1730000000.$i [1 10.0.0.5:4242] \"PUBLISH\" \"socketio#/#user:abc\" \"{}\""
          done;;
esac
STUB
chmod +x "$STUB_DIR/valkey-cli"

FAIL=0
check() {  # <mode> <expected-exit> [<expected-output-substring>]
    local out rc=0
    out="$(PATH="$STUB_DIR:$PATH" STUB_MODE="$1" "$HERE/check-amplification.sh" stub:6379 1 2>&1)" || rc=$?
    if [[ "$rc" -ne "$2" ]] || [[ -n "${3:-}" && "$out" != *"$3"* ]]; then
        echo "FAIL $1: exit $rc (want $2)"; FAIL=1
    else
        echo "ok   $1: exit $rc"
    fi
}

check refuse 3 "MONITOR refused"
check empty  4 "inconclusive"
check hot    0 "almost certainly 1"
exit "$FAIL"
