#!/usr/bin/env bash
#
# check-amplification.sh — measure Socket.IO PUBLISH rate on Valkey/Redis
# during an active Open WebUI chat stream, to verify whether
# CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE is in effect.
#
# Usage:
#   ./check-amplification.sh <valkey-host> [<duration-seconds>]
#
# Args:
#   valkey-host       host:port for the WebSocket Valkey master
#                     (the one WEBSOCKET_REDIS_URL points at; if Sentinel,
#                      ask Sentinel which host is master first)
#   duration-seconds  how long to sample. Default 30.
#
# Output:
#   Total PUBLISH ops on the Socket.IO channel
#   Ops per second (rough)
#   Estimated CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE bracket
#
# How to interpret:
#   Have a real user chat-stream a long response (>500 tokens) during the sample
#   window. With CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE=1 (default), expect
#   ~10-50 publishes per second per active stream. With =10, expect ~1-5/sec
#   per stream. With =20, ~0.5-2/sec per stream. Multiply by concurrent streams
#   to get total expected rate.
#
# Requires: valkey-cli (or redis-cli — the binary is symlinked).
#
# Exit codes:
#   0 — sample completed successfully
#   1 — valkey-cli not found
#   2 — connection to Valkey failed

set -euo pipefail

VALKEY_HOST="${1:-}"
DURATION="${2:-30}"

if [[ -z "$VALKEY_HOST" ]]; then
    echo "Usage: $0 <valkey-host:port> [<duration-seconds>]" >&2
    echo "Example: $0 valkey-master.valkey:6379 30" >&2
    exit 1
fi

CLI=""
if command -v valkey-cli >/dev/null 2>&1; then
    CLI="valkey-cli"
elif command -v redis-cli >/dev/null 2>&1; then
    CLI="redis-cli"
else
    echo "ERROR: neither valkey-cli nor redis-cli found in PATH" >&2
    exit 1
fi

HOST="${VALKEY_HOST%:*}"
PORT="${VALKEY_HOST##*:}"
[[ "$PORT" == "$HOST" ]] && PORT=6379

# Sanity check: can we reach Valkey?
if ! "$CLI" -h "$HOST" -p "$PORT" PING >/dev/null 2>&1; then
    echo "ERROR: cannot reach Valkey at $HOST:$PORT" >&2
    exit 2
fi

echo "Sampling PUBLISH ops on $HOST:$PORT for ${DURATION}s..."
echo "(have a long chat stream running during this window)"
echo

# MONITOR every command in real-time. Count PUBLISH ops on Socket.IO channels.
# Socket.IO via python-socketio AsyncRedisManager publishes to channels prefixed
# with "flask-socketio" by default. Open WebUI may also use other prefixes;
# the broad regex catches both.
TMPFILE="$(mktemp)"
trap 'rm -f "$TMPFILE"' EXIT

timeout "$DURATION" "$CLI" -h "$HOST" -p "$PORT" MONITOR 2>/dev/null \
    | grep -E '"PUBLISH"' \
    > "$TMPFILE" || true

TOTAL=$(wc -l < "$TMPFILE")
PER_SEC=$(awk -v t="$TOTAL" -v d="$DURATION" 'BEGIN { printf "%.1f", t/d }')

echo "Total PUBLISH ops:        $TOTAL"
echo "Ops per second (mean):    $PER_SEC"
echo

# Heuristic estimate. Assumes 1 active stream during the sample.
# IMPORTANT: these brackets are per single active stream. With N concurrent
# streams, divide TOTAL (and the bracket thresholds) by N before interpreting —
# e.g. 10 concurrent streams at chunk-size 10 produce roughly the same total
# PUBLISH count as 1 stream at chunk-size 1. Sample with a known stream count.
# These thresholds match the empirical table in references/issue-23733.md.
if [[ "$TOTAL" -lt 60 ]]; then
    echo "Estimate: CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE looks tuned (~10 or higher)."
    echo "          (or no active streams during sample)"
elif [[ "$TOTAL" -lt 300 ]]; then
    echo "Estimate: CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE looks moderate (~5)."
elif [[ "$TOTAL" -lt 1000 ]]; then
    echo "Estimate: CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE may be 1-3 — bump to 10."
else
    echo "Estimate: CHAT_RESPONSE_STREAM_DELTA_CHUNK_SIZE is almost certainly 1 (default)."
    echo "          Set to 10 immediately. See references/issue-23733.md."
fi
echo
echo "Top channels by frequency:"
awk '{
  # MONITOR format: <ts> [<db> <addr>] "<cmd>" "<arg1>" ...
  # We want arg1 (the channel) on lines where cmd is PUBLISH.
  for (i=1;i<=NF;i++) if ($i == "\"PUBLISH\"") { print $(i+1); next }
}' "$TMPFILE" | sort | uniq -c | sort -rn | head -5
