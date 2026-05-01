"""
OpenWhisk-compatible HTTP server for DigitalOcean Functions custom Docker runtime.

DO Functions with a custom Dockerfile requires a container that:
  1. Listens on port 8080
  2. Handles POST /init  — called once on cold start, returns {"ok": true}
  3. Handles POST /run   — called for each invocation
                          receives {"value": {<args>}}
                          returns  {"result": {<return>}} or {"error": "<msg>"}

This is the standard OpenWhisk action container protocol that DO Functions uses
for custom Docker images.

Run with:
  python -m src.handlers.do_functions_server

The Dockerfile CMD should point here instead of __main__.py.
"""

import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

PORT = 8080


class ActionHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # suppress default access log noise
        logger.info(f"[{self.path}] {format % args}")

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw)

    def _send_json(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path == "/init":
            # Called once on cold start — nothing to initialise for a custom image
            self._send_json(200, {"ok": True})

        elif self.path == "/run":
            body = self._read_body()
            # OpenWhisk wraps the user args under "value"
            args = body.get("value", {})
            try:
                from src.handlers.do_functions_handler import main

                result = main(args)
                # OpenWhisk expects {"result": <return_value>}
                self._send_json(200, {"result": result})
            except Exception as exc:
                logger.exception(f"Action failed: {exc}")
                self._send_json(200, {"error": str(exc)})

        else:
            self._send_json(404, {"error": f"Unknown path: {self.path}"})


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), ActionHandler)
    logger.info(f"DO Functions action server listening on port {PORT}")
    server.serve_forever()
