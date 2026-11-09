#!/usr/bin/env python3
"""Self-test for probe-endpoint.sh against a local mock server.

Usage: selftest-probe-endpoint.py [path/to/probe-endpoint.sh]
Exit 0 when every scenario produces the expected exit code and marks.

Scenarios: a pooling server (planted positive), a generate-only server,
an auth wall, a gateway that answers 502 to everything, and a dead server.
"""

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPT = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(__file__).with_name("probe-endpoint.sh")
)

POOLING = {"/v1/embeddings", "/v2/embed", "/rerank", "/score"}
STT = {"/v1/audio/transcriptions", "/v1/audio/translations"}
CHAT = {"/v1/chat/completions"}

# scenario -> (routes answering 422, status for every other POST, health status)
SCENARIOS = {
    "pooling": (POOLING, 404, 200),
    "stt": (STT | CHAT, 404, 200),
    "generate-only": (CHAT, 404, 200),
    "auth-wall": (set(), 401, 200),
    "bad-gateway": (set(), 502, 200),
    "unhealthy": (set(), 404, 503),
}

# scenario -> (expected exit code, substrings that must appear, must not appear)
EXPECT = {
    "pooling": (0, ["✓ Embeddings (OpenAI v1)", "✗ Speech-to-text"], []),
    "stt": (0, ["✓ Speech-to-text", "✗ Embeddings (OpenAI v1)"], []),
    "generate-only": (2, ["✗ Embeddings (OpenAI v1)", "✗ Rerank"], ["✓ Embeddings"]),
    "auth-wall": (3, ["401"], ["✓ Embeddings", "✓ Rerank", "✓ Speech"]),
    "bad-gateway": (3, ["502"], ["✓ Embeddings", "✓ Rerank", "✓ Speech"]),
    "unhealthy": (1, ["/health failed"], ["✓ Embeddings"]),
}


def make_handler(live: set[str], other: int, health: int):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def _send(self, code: int, body: dict):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                self._send(health, {})
            elif self.path == "/v1/models" and other != 401:
                self._send(200, {"data": [{"id": "mock-model"}]})
            else:
                self._send(other, {"detail": "Not Found"})

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if self.path in live:
                self._send(422, {"detail": "invalid body"})
            else:
                self._send(other, {"detail": "Not Found"})

    return Handler


def run(name: str) -> bool:
    live, other, health = SCENARIOS[name]
    server = HTTPServer(("127.0.0.1", 0), make_handler(live, other, health))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}"
    try:
        proc = subprocess.run(
            ["bash", str(SCRIPT), url], capture_output=True, text=True, timeout=60
        )
    finally:
        server.shutdown()
    out = proc.stdout + proc.stderr
    code, must, must_not = EXPECT[name]
    problems = []
    if proc.returncode != code:
        problems.append(f"exit {proc.returncode}, expected {code}")
    problems += [f"missing {m!r}" for m in must if m not in out]
    problems += [f"unexpected {m!r}" for m in must_not if m in out]
    print(
        f"{'PASS' if not problems else 'FAIL'}  {name}: {'; '.join(problems) or 'ok'}"
    )
    return not problems


if __name__ == "__main__":
    results = [run(name) for name in SCENARIOS]
    sys.exit(0 if all(results) else 1)
