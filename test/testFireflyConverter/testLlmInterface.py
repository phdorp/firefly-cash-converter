import unittest

import requests

from fireflyConverter import llmInterface as lli


class _StubResponse:
    """Minimal stand-in for a requests.Response."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


class _StubSession:
    """Records outgoing chat requests and returns scripted responses in order."""

    def __init__(self, responses):
        self._responses = responses if isinstance(responses, list) else [responses]
        self.requests = []
        self.headers = {}

    def post(self, url, json=None, timeout=None):
        self.requests.append((url, json, timeout))
        index = min(len(self.requests) - 1, len(self._responses) - 1)
        return self._responses[index]


class TestLlmInterface(unittest.TestCase):
    def _interfaceWith(self, response):
        interface = lli.LLMInterface(base_url="http://127.0.0.1:1234/v1", model="test-model")
        interface._session = _StubSession(response)
        return interface, interface._session

    def testChatReturnsMessageContent(self):
        response = _StubResponse({"choices": [{"message": {"content": '{"vendor": "ACME"}'}}]})
        interface, _ = self._interfaceWith(response)

        self.assertEqual(interface.chat([{"role": "user", "content": "read this bill"}]), '{"vendor": "ACME"}')

    def testChatTargetsCompletionsEndpointWithModelAndMessages(self):
        response = _StubResponse({"choices": [{"message": {"content": "{}"}}]})
        interface, session = self._interfaceWith(response)

        interface.chat([{"role": "user", "content": "hi"}])

        url, payload, _ = session.requests[0]
        self.assertTrue(url.endswith("/chat/completions"), url)
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "hi"}])
        self.assertEqual(payload["temperature"], 0.0)
        self.assertNotIn("response_format", payload)

    def testChatConstrainsOutputWithJsonSchema(self):
        response = _StubResponse({"choices": [{"message": {"content": "{}"}}]})
        interface, session = self._interfaceWith(response)

        interface.chat([{"role": "user", "content": "hi"}], response_schema={"type": "object"})

        _, payload, _ = session.requests[0]
        self.assertEqual(payload["response_format"]["json_schema"]["schema"], {"type": "object"})

    def testChatRaisesOnHttpError(self):
        response = _StubResponse({}, status_code=500)
        interface, _ = self._interfaceWith(response)

        with self.assertRaises(requests.HTTPError):
            interface.chat([{"role": "user", "content": "hi"}])

    def testChatRetriesWithoutSchemaWhenServerRejectsIt(self):
        responses = [
            _StubResponse({}, status_code=400),
            _StubResponse({"choices": [{"message": {"content": "{}"}}]}),
        ]
        interface, session = self._interfaceWith(responses)

        content = interface.chat([{"role": "user", "content": "hi"}], response_schema={"type": "object"})

        self.assertEqual(content, "{}")
        self.assertEqual(len(session.requests), 2)
        self.assertNotIn("response_format", session.requests[1][1])

    def testChatDoesNotRetryOnServerError(self):
        response = _StubResponse({}, status_code=500)
        interface, session = self._interfaceWith(response)

        with self.assertRaises(requests.HTTPError):
            interface.chat([{"role": "user", "content": "hi"}], response_schema={"type": "object"})

        self.assertEqual(len(session.requests), 1)

    def testChatDoesNotRetryWhenNoSchemaWasSent(self):
        response = _StubResponse({}, status_code=400)
        interface, session = self._interfaceWith(response)

        with self.assertRaises(requests.HTTPError):
            interface.chat([{"role": "user", "content": "hi"}])

        self.assertEqual(len(session.requests), 1)


if __name__ == "__main__":
    unittest.main()
