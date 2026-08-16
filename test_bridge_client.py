import asyncio
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from bridge_client import AzControlBridge


class BridgeHandler(BaseHTTPRequestHandler):
    results = []
    action = "prepare_505f"

    def do_GET(self):
        body = json.dumps({"actions": [{"id": 7, "action": BridgeHandler.action, "payload": json.dumps({"source": "test"})}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        BridgeHandler.results.append(json.loads(self.rfile.read(length)))
        self.send_response(200)
        self.end_headers()

    def log_message(self, *_args):
        return


class BridgeClientIntegration(unittest.TestCase):
    def run_action(self, action_name):
        BridgeHandler.action = action_name
        server = ThreadingHTTPServer(("127.0.0.1", 0), BridgeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old_url = os.environ.get("AZ_CONTROL_API_URL")
        old_token = os.environ.get("AZ_CONTROL_BRIDGE_TOKEN")
        os.environ["AZ_CONTROL_API_URL"] = f"http://127.0.0.1:{server.server_port}"
        os.environ["AZ_CONTROL_BRIDGE_TOKEN"] = "integration-token"

        async def handler(_action):
            return {"detail": f"{action_name}=accepted_for_test"}

        try:
            client = AzControlBridge(handler)
            actions = client._get_actions()
            asyncio.run(client._process(actions[0]))
            self.assertEqual(BridgeHandler.results[-1]["status"], "succeeded")
            self.assertIn(action_name, BridgeHandler.results[-1]["details"])
        finally:
            server.shutdown()
            server.server_close()
            if old_url is None:
                os.environ.pop("AZ_CONTROL_API_URL", None)
            else:
                os.environ["AZ_CONTROL_API_URL"] = old_url
            if old_token is None:
                os.environ.pop("AZ_CONTROL_BRIDGE_TOKEN", None)
            else:
                os.environ["AZ_CONTROL_BRIDGE_TOKEN"] = old_token

    def test_pull_and_report_505f(self):
        self.run_action("prepare_505f")

    def test_pull_and_report_505c(self):
        self.run_action("prepare_505c")


if __name__ == "__main__":
    unittest.main(verbosity=2)
