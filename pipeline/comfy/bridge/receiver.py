"""Loopback receiver that lets the studio's ComfyUI tab hand JSON to the shell without copy-paste.

    .venv\\Scripts\\python.exe pipeline\\comfy\\bridge\\receiver.py --out pipeline\\comfy\\incoming [--port 8199] [--max 10] [--timeout 900]

The page POSTs to http://127.0.0.1:<port>/put/<name>.json (see page_recipes.js: studio.send). The receiver:
- listens on 127.0.0.1 only and accepts requests only from the ComfyUI page's origin;
- writes only into --out, which must be inside this repo, with a sanitized file name;
- accepts only JSON objects up to 5 MB;
- exits after --max files or --timeout seconds, whichever comes first.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ORIGINS = {"http://127.0.0.1:8188", "http://localhost:8188"}
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,120}\.json$")
MAX_BYTES = 5 * 2**20


def make_handler(out: Path, state: dict):
    class Handler(BaseHTTPRequestHandler):
        def _cors(self):
            origin = self.headers.get("Origin", "")
            if origin in ORIGINS:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Private-Network", "true")

        def _reply(self, code: int, body: dict):
            data = json.dumps(body).encode()
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_OPTIONS(self):
            if self.headers.get("Origin", "") not in ORIGINS:
                return self._reply(403, {"error": "origin not allowed"})
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_POST(self):
            if self.headers.get("Origin", "") not in ORIGINS:
                return self._reply(403, {"error": "origin not allowed"})
            m = re.fullmatch(r"/put/(.+)", self.path)
            if not m or not NAME.match(m.group(1)):
                return self._reply(400, {"error": "bad file name"})
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= MAX_BYTES:
                return self._reply(413, {"error": "empty or too large"})
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return self._reply(400, {"error": "not JSON"})
            if not isinstance(data, dict):
                return self._reply(400, {"error": "expected a JSON object"})
            target = out / m.group(1)
            target.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", "utf-8", newline="\n")
            state["count"] += 1
            print(f"received {target.name} ({len(raw)} bytes)", flush=True)
            self._reply(200, {"saved": target.name, "sha256": hashlib.sha256(raw).hexdigest()})
            if state["count"] >= state["max"]:
                threading.Thread(target=self.server.shutdown, daemon=True).start()

        def log_message(self, *args):
            pass

    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--port", type=int, default=8199)
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--timeout", type=float, default=900)
    a = ap.parse_args(argv)
    out = a.out.resolve()
    if REPO not in out.parents and out != REPO:
        print(f"--out must be inside {REPO}")
        return 2
    out.mkdir(parents=True, exist_ok=True)
    state = {"count": 0, "max": a.max}
    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(out, state))
    timer = threading.Timer(a.timeout, server.shutdown)
    timer.daemon = True
    timer.start()
    print(f"receiver on http://127.0.0.1:{a.port}/put/<name>.json -> {out}", flush=True)
    server.serve_forever()
    timer.cancel()
    print(f"receiver stopped after {state['count']} file(s)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
