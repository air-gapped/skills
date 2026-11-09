#!/usr/bin/env bash
#
# Self-test for check-config.sh: runs it against a local mock server with
# planted positives and error-shaped responses, and asserts the exit code and
# the lines it must print. Needs python3, curl, jq. Exit 0 = all cases pass.

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK="${HERE}/check-config.sh"
PORT_OK=18470
PORT_LOCKED=18471
PORT_HTML=18472

mock() { # port mode
  python3 -I - "$1" "$2" <<'PY' &
import json, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
port, mode = int(sys.argv[1]), sys.argv[2]
MODELS = json.dumps({"data": [{"id": "planted-model", "owned_by": "vllm"}]})
METRICS = (
    'vllm:cache_config_info{block_size="16",cache_dtype="auto",enable_prefix_caching="True",engine="0"} 1.0\n'
    'vllm:prefix_cache_queries_total{engine="0"} 4242.0\n'
)
HTML = "<html><body>502 Bad Gateway</body></html>"
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, body):
        data = body.encode()
        self.send_response(code)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path == "/health":
            self.send(200, "")
        elif mode == "html":
            self.send(200, HTML)
        elif self.path == "/metrics":
            self.send(200, METRICS)
        elif self.path == "/v1/models":
            authed = self.headers.get("Authorization") == "Bearer planted-key"
            if mode == "locked" and not authed:
                self.send(401, json.dumps({"error": "Unauthorized"}))
            else:
                self.send(200, MODELS)
        else:
            self.send(404, "")
HTTPServer(("127.0.0.1", port), H).serve_forever()
PY
  pids+=("$!")
}

pids=()
cleanup() {
  local p
  for p in ${pids[@]+"${pids[@]}"}; do kill "$p" 2>/dev/null; done
}
trap cleanup EXIT
mock "$PORT_OK" ok
mock "$PORT_LOCKED" locked
mock "$PORT_HTML" html
for _ in $(seq 1 50); do
  curl -fsS -m 1 "http://127.0.0.1:${PORT_HTML}/health" >/dev/null 2>&1 && break
  sleep 0.1
done

failed=0
case_() { # name, expected exit, expected line (regex), then VAR=value ... -- url
  local name="$1" want_rc="$2" want_re="$3"
  shift 3
  local envs=()
  while [ "$1" != "--" ]; do
    envs+=("$1")
    shift
  done
  shift
  local out rc
  out="$(env -i PATH="$PATH" HOME="${HOME:-/tmp}" ${envs[@]+"${envs[@]}"} bash "$CHECK" "$@" 2>&1)"
  rc=$?
  if [ "$rc" -eq "$want_rc" ] && printf '%s\n' "$out" | grep -Eq -- "$want_re"; then
    echo "ok    ${name}"
  else
    echo "FAIL  ${name}: exit ${rc} (want ${want_rc}), or no line matching /${want_re}/"
    printf '%s\n' "$out" | sed 's/^/      /'
    failed=$((failed + 1))
  fi
}

OK="http://127.0.0.1:${PORT_OK}"
case_ "clean server, empty env"       0 'id: planted-model' -- "$OK"
case_ "resolved CacheConfig printed"  0 'block_size="16"' -- "$OK"
case_ "secrets redacted"              0 'HF_TOKEN=<redacted>' HF_TOKEN=hf_planted -- "$OK"
case_ "VLLM_PORT is a URI"            2 "WARN: VLLM_PORT='tcp://" VLLM_PORT=tcp://10.0.0.5:8000 -- "$OK"
case_ "service links present"         2 'WARN: VLLM_SERVICE_HOST' VLLM_SERVICE_HOST=10.0.0.5 -- "$OK"
case_ "deprecated cache var"          2 'WARN: TRANSFORMERS_CACHE' TRANSFORMERS_CACHE=/x -- "$OK"
case_ "HF_ENDPOINT trailing slash"    2 'WARN: HF_ENDPOINT' HF_ENDPOINT=https://m.example.com/ -- "$OK"
case_ "usage-stats opt-out as true"   2 "WARN: VLLM_NO_USAGE_STATS='true'" VLLM_NO_USAGE_STATS=true -- "$OK"
case_ "boolean word on a VLLM_ var"   2 "WARN: VLLM_SERVER_DEV_MODE='true'" VLLM_SERVER_DEV_MODE=true -- "$OK"
case_ "true accepted where it works"  0 'VLLM_USE_MODELSCOPE=true' VLLM_USE_MODELSCOPE=true -- "$OK"
case_ "key required, none given"      1 'FAIL: /v1/models returned 401' -- "http://127.0.0.1:${PORT_LOCKED}"
case_ "key required, key in env"      0 'id: planted-model' VLLM_API_KEY=planted-key -- "http://127.0.0.1:${PORT_LOCKED}"
case_ "proxy error page, HTTP 200"    1 'FAIL: /v1/models returned 200 but no model entries' -- "http://127.0.0.1:${PORT_HTML}"
case_ "proxy page instead of metrics" 1 'WARN: /metrics has no vllm: series' -- "http://127.0.0.1:${PORT_HTML}"
case_ "unreachable server"            1 'FAIL: cannot reach' -- "http://127.0.0.1:1"

echo
if [ "$failed" -gt 0 ]; then
  echo "${failed} case(s) failed"
  exit 1
fi
echo "all cases passed"
