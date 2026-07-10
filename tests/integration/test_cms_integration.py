import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import socketserver
import time

from src.agent.config import Settings
from src.agent.tools.cms_coverage import CMSCoverageTool


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


class CMSStubHandler(BaseHTTPRequestHandler):
    # shared state across requests
    state = {"data_calls": 0}

    def _send_json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/v1/metadata/license-agreement"):
            payload = {"data": [{"token": "integration-token"}]}
            self._send_json(200, payload)
            return

        if self.path.startswith("/v1/data/lcd/"):
            # simulate transient 500 on first call, then success
            CMSStubHandler.state["data_calls"] += 1
            if CMSStubHandler.state["data_calls"] == 1:
                self._send_json(500, {"error": "temporary"})
                return
            payload = {"data": [{"lcd_id": "lcd-int-1", "cms_cov_policy": "integration policy text"}]}
            self._send_json(200, payload)
            return

        # default
        self._send_json(404, {"error": "not found"})

    def log_message(self, format, *args):
        return


def run_server(server):
    try:
        server.serve_forever()
    finally:
        server.server_close()


def test_integration_token_and_retry():
    settings = Settings(env="test")

    server = ThreadingHTTPServer(("127.0.0.1", 0), CMSStubHandler)
    host, port = server.server_address
    thread = threading.Thread(target=run_server, args=(server,), daemon=True)
    thread.start()

    try:
        tool = CMSCoverageTool(settings)
        # point to local stub
        tool.BASE_URL = f"http://{host}:{port}"
        # reduce backoff for test speed
        settings.retries["cms_tool"] = 3
        settings.cms["retry_backoff_seconds"] = 0.1
        settings.cms["max_backoff_seconds"] = 0.5

        out = tool.run({"code": "lcd-int-1", "policy_type": "lcd"})
        assert isinstance(out, list)
        assert len(out) == 1
        assert out[0]["source_id"] == "lcd-int-1" or "lcd-int-1" in out[0]["excerpt"]
    finally:
        server.shutdown()
        thread.join(timeout=2)
