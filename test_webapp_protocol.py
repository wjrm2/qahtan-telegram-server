import unittest

from webapp_protocol import MALICIOUS_ACTIONS, parse_webapp_payload, webapp_payload


class WebAppProtocolTests(unittest.TestCase):
    def test_isolated_webapp_payload_round_trip(self):
        action, payload = parse_webapp_payload(webapp_payload("request_health", {"source": "mini_app"}))
        self.assertEqual(action, "request_health")
        self.assertEqual(payload, {"source": "mini_app"})

    def test_malformed_webapp_payload_is_rejected(self):
        for raw in (None, "", "not-json", "[]", '{"action":"request_health","payload":[] }'):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "invalid_payload"):
                    parse_webapp_payload(raw)

    def test_sensitive_actions_never_cross_webapp_boundary(self):
        for action in sorted(MALICIOUS_ACTIONS):
            with self.subTest(action=action):
                with self.assertRaisesRegex(ValueError, "unsupported_action"):
                    parse_webapp_payload('{"action":"' + action + '"}')


if __name__ == "__main__":
    unittest.main()
