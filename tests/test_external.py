"""Runs the external-provider route against a local fake server."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from czgram import external

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sse(*chunks):
    lines = ["data: " + json.dumps({"choices": [{"delta": {"content": c}}]}) for c in chunks]
    return ("\n\n".join(lines + ["data: [DONE]"]) + "\n\n").encode()


class Server:
    def __init__(self):
        self.seen, self.reply, self.other_hits = [], None, []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, status, ctype, body, extra=()):
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                for k, v in extra:
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                outer.seen.append((self.path, self.headers.get("Authorization"), None))
                self._send(*outer.reply)

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                outer.seen.append((self.path, self.headers.get("Authorization"), json.loads(self.rfile.read(n))))
                self._send(*outer.reply)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/v1" % self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class External(unittest.TestCase):
    def setUp(self):
        self.srv = Server()
        self.addCleanup(self.srv.close)

    def run_it(self, reply, model="auto", url=None, key="secret-key"):
        self.srv.reply = reply
        out = []
        external.run("the prompt", "the system", lambda **m: out.append(m), url or self.srv.url, key, model)
        return out

    def text(self, out):
        return "".join(m.get("text", "") for m in out)

    def test_streams_and_sends_the_right_request(self):
        out = self.run_it((200, "text/event-stream", sse("Dopl", "ň y")))
        self.assertEqual(out, [{"text": "Dopl"}, {"text": "ň y"}, {"done": True}])
        path, auth, body = self.srv.seen[0]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(auth, "Bearer secret-key")
        self.assertEqual(body["model"], "auto")
        self.assertEqual([m["role"] for m in body["messages"]], ["system", "user"])

    def test_non_streaming_answer(self):
        body = json.dumps({"choices": [{"message": {"content": "Celá odpověď"}}]}).encode()
        out = self.run_it((200, "application/json", body))
        self.assertEqual(out, [{"text": "Celá odpověď"}, {"done": True}])

    def test_reasoning_is_hidden_even_when_split_across_chunks(self):
        out = self.run_it((200, "text/event-stream", sse("<thi", "nk>tajné", " úvahy</th", "ink>\n\nOdpo", "věď a<b")))
        self.assertEqual(self.text(out), "Odpověď a<b")
        self.assertEqual(out[-1], {"done": True})

    def test_only_reasoning_counts_as_empty(self):
        self.assertIn("empty", self.run_it((200, "text/event-stream", sse("<think>jen úvahy")))[-1]["error"])

    def test_errors(self):
        cases = [(401, "API key"), (403, "API key"), (404, "address"), (429, "rate limit")]
        for code, word in cases:
            self.assertIn(word, self.run_it((code, "application/json", b"{}"))[0]["error"], code)
        body = json.dumps({"error": {"message": "boom"}}).encode()
        self.assertIn("boom", self.run_it((500, "application/json", body))[0]["error"])

    def test_error_inside_stream(self):
        reply = (200, "text/event-stream", b'data: {"error":{"message":"all providers down"}}\n\n')
        self.assertIn("all providers down", self.run_it(reply)[0]["error"])

    def test_key_is_never_shown_in_errors(self):
        body = json.dumps({"error": {"message": "nope"}}).encode()
        out = self.run_it((500, "application/json", body))
        self.assertNotIn("secret-key", json.dumps(out))

    def test_redirects_are_not_followed(self):
        other = Server()
        self.addCleanup(other.close)
        other.reply = (200, "text/event-stream", sse("leak"))
        srv = self.srv
        self.srv.reply = (200, "text/plain", b"")
        orig = self.srv.httpd.RequestHandlerClass.do_POST

        def do_post(handler):
            handler.rfile.read(int(handler.headers.get("Content-Length", 0)))
            handler._send(302, "text/plain", b"", [("Location", other.url + "/chat/completions")])
        self.srv.httpd.RequestHandlerClass.do_POST = do_post
        self.addCleanup(lambda: setattr(srv.httpd.RequestHandlerClass, "do_POST", orig))
        out = []
        external.run("p", "s", lambda **m: out.append(m), srv.url, "secret-key", "m")
        self.assertIn("redirected", out[0]["error"])
        self.assertEqual(other.seen, [])

    def test_no_model(self):
        self.assertIn("Choose a model", self.run_it((200, "text/plain", b""), model="")[0]["error"])

    def test_unreachable(self):
        srv = Server()
        url = srv.url
        srv.close()
        out = []
        external.run("p", "s", lambda **m: out.append(m), url, "", "m")
        self.assertIn("Can't reach", out[0]["error"])

    def test_no_key_sends_no_header(self):
        self.run_it((200, "text/event-stream", sse("x")), key="")
        self.assertIsNone(self.srv.seen[0][1])

    def test_list_models(self):
        body = json.dumps({"data": [{"id": "b"}, {"id": "a"}, {"id": "b"}]}).encode()
        self.srv.reply = (200, "application/json", body)
        self.assertEqual(external.list_models(self.srv.url, "k"), ["a", "b"])
        self.assertEqual(self.srv.seen[0][0], "/v1/models")

    def test_list_models_empty_and_garbage(self):
        for body in (b'{"data":[]}', b"<html>"):
            self.srv.reply = (200, "application/json", body)
            with self.assertRaises(external.ExternalError):
                external.list_models(self.srv.url, "k")

    def test_through_the_real_child_process(self):
        self.srv.reply = (200, "text/event-stream", sse("Doplň y."))
        with tempfile.TemporaryDirectory() as cfg:
            os.makedirs(cfg + "/czgram")
            with open(cfg + "/czgram/config.json", "w") as f:
                json.dump({"claude_backend": "custom", "custom_base_url": self.srv.url + "/",
                           "custom_api_key": "k", "custom_model": "auto", "language": "cs"}, f)
            res = subprocess.run([sys.executable, "-m", "czgram.ai"], text=True, capture_output=True,
                                 input=json.dumps({"snippet": "b_dlí", "line": "b_dlí", "topic": ""}),
                                 env=dict(os.environ, XDG_CONFIG_HOME=cfg, PYTHONPATH=REPO), timeout=20)
        self.assertEqual([json.loads(l) for l in res.stdout.splitlines()],
                         [{"text": "Doplň y."}, {"done": True}])
        self.assertIn("Czech", self.srv.seen[0][2]["messages"][0]["content"])


class Addresses(unittest.TestCase):
    def test_normalize(self):
        for given in ("http://x:1/v1", "http://x:1/v1/", " http://x:1/v1/chat/completions ", "http://x:1/v1/models"):
            self.assertEqual(external.normalize(given), "http://x:1/v1")
        for bad in ("x:1/v1", "ftp://x/v1", "", "file:///etc/passwd"):
            with self.assertRaises(external.ExternalError):
                external.normalize(bad)

    def test_unencrypted_warning(self):
        self.assertTrue(external.is_unencrypted("http://example.com/v1"))
        self.assertFalse(external.is_unencrypted("http://localhost:3001/v1"))
        self.assertFalse(external.is_unencrypted("http://127.0.0.1:3001/v1"))
        self.assertFalse(external.is_unencrypted("https://example.com/v1"))


if __name__ == "__main__":
    unittest.main()
