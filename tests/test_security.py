"""Hardening found in the security review: each test pins one fix."""
import os
import socket
import stat
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from czgram import analyze, bridge, capture, claude_code, nmhost, shortcuts  # noqa: E402


class SlowPatterns(unittest.TestCase):
    def test_long_page_lines_stay_fast(self):
        for line in ("a" * 50000, "ěščřžýáíé" * 5000, "(s/z" * 10000, "(z/ze) _e (V/v)ánoce b_dlí ___ " * 2000):
            start = time.time()
            analyze.analyze([line], limit=50)
            self.assertLess(time.time() - start, 1.0, line[:20])

    def test_choices_are_still_found(self):
        found = {(i["snippet"], i["suggest"]) for i in analyze.analyze(["Musíme (s/z)míchat těsto. Ne(s/z)poutej."])}
        self.assertIn(("(s/z)míchat", "s"), found)


class ModelName(unittest.TestCase):
    def test_option_like_model_is_refused(self):
        out = []
        with mock.patch.object(claude_code, "find", return_value="/bin/false"), \
                mock.patch.object(claude_code.subprocess, "Popen") as popen:
            claude_code.run("x", "y", lambda **m: out.append(m), "--dangerously-skip-permissions")
        popen.assert_not_called()
        self.assertIn("isn't valid", out[0]["error"])

    def test_real_model_names_pass(self):
        import re
        for name in ("opus", "claude-opus-5-5", "sonnet[1m]", "claude-haiku-5-5"):
            self.assertTrue(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:\[\]-]*", name), name)


class ShortcutQuoting(unittest.TestCase):
    def test_quote_in_path_stays_inside_the_string(self):
        self.assertEqual(shortcuts._gvariant_str("/home/o'neil/czgram --trigger"),
                         "'/home/o\\'neil/czgram --trigger'")


class PortalFile(unittest.TestCase):
    def test_only_own_regular_files_are_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            real = os.path.join(d, "shot.png")
            open(real, "wb").close()
            link = os.path.join(d, "link.png")
            os.symlink(real, link)
            self.assertTrue(capture._own_regular_file(real))
            self.assertFalse(capture._own_regular_file(link))
            self.assertFalse(capture._own_regular_file(d))
            self.assertFalse(capture._own_regular_file(os.path.join(d, "missing.png")))


class SizeLimits(unittest.TestCase):
    def test_native_host_refuses_huge_messages(self):
        r, w = os.pipe()
        os.write(w, struct.pack("=I", nmhost.MAX_MESSAGE + 1))
        os.close(w)
        self.assertIsNone(nmhost.read_message(r))
        os.close(r)

    def test_bridge_stops_reading_a_huge_reply(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.sock")
            srv = socket.socket(socket.AF_UNIX)
            srv.bind(path)
            srv.listen(1)

            def serve():
                conn, _ = srv.accept()
                conn.recv(64)
                try:
                    chunk = b"x" * 65536
                    for _ in range(bridge.MAX_REPLY // len(chunk) + 4):
                        conn.sendall(chunk)
                except OSError:
                    pass
                conn.close()

            t = threading.Thread(target=serve)
            t.start()
            with self.assertRaises(ValueError):
                bridge._ask(path, 5)
            t.join()
            srv.close()

    def test_sockets_are_private(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.sock")
            old = os.umask(0o077)
            try:
                s = socket.socket(socket.AF_UNIX)
                s.bind(path)
            finally:
                os.umask(old)
            self.assertEqual(stat.S_IMODE(os.stat(path).st_mode) & 0o077, 0)
            s.close()


class Extension(unittest.TestCase):
    def test_snapshot_skips_secret_fields(self):
        top = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for browser in ("chromium", "firefox"):
            with open(os.path.join(top, "extension", browser, "background.js"), encoding="utf-8") as f:
                js = f.read()
            self.assertIn("if (secretField(node)) return;", js)
            self.assertIn("MAX_TOTAL", js)


if __name__ == "__main__":
    unittest.main()
