"""The Windows pieces: pipes, the browser bridge, the npm shim, locking, the clipboard, the timer.

These run only on Windows (the CI job on windows-latest); tests/win_smoke.py drives the
whole app there: hotkey, screenshot, OCR, the bar and the browser connector.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from czgram import bridge, claude_code, deadline, usage  # noqa: E402

WINDOWS = unittest.skipUnless(os.name == "nt", "Windows only")


class TempRuntime(unittest.TestCase):
    """Points every per-user folder at a temporary one."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        patch = mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": self.tmp, "XDG_STATE_HOME": self.tmp,
                                             "XDG_CONFIG_HOME": self.tmp})
        patch.start()
        self.addCleanup(patch.stop)


@WINDOWS
class Pipes(TempRuntime):
    def test_round_trip(self):
        from czgram import windows
        desc = os.path.join(self.tmp, "t.json")
        srv = windows.serve(desc)
        got = []

        def serve():
            conn = srv.accept()
            got.append(conn.recv_bytes())
            conn.send_bytes(b"pong")
            conn.close()

        t = threading.Thread(target=serve)
        t.start()
        conn = windows.connect(desc)
        conn.send_bytes(b"ping")
        self.assertEqual(conn.recv_bytes(), b"pong")
        conn.close()
        t.join(5)
        srv.close()
        self.assertEqual(got, [b"ping"])

    def test_wrong_key_is_refused(self):
        from czgram import windows
        desc = os.path.join(self.tmp, "t.json")
        srv = windows.serve(desc)

        def accept():
            try:
                srv.accept()
            except Exception:  # noqa: BLE001  the server side refuses the client too
                pass

        threading.Thread(target=accept, daemon=True).start()
        with open(desc, encoding="utf-8") as f:
            data = json.load(f)
        data["key"] = "00" * 32
        with open(desc, "w", encoding="utf-8") as f:
            json.dump(data, f)
        with self.assertRaises(ConnectionError):
            windows.connect(desc)
        srv.close()

    def test_bar_command_reaches_a_listener(self):
        from czgram import config, ipc, windows
        srv = windows.serve(config.ui_socket())
        got = []

        def serve():
            conn = srv.accept()
            got.append(conn.recv_bytes())
            conn.close()

        t = threading.Thread(target=serve)
        t.start()
        self.assertTrue(ipc.send("reload"))
        t.join(5)
        srv.close()
        self.assertEqual(got, [b"reload"])
        os.unlink(config.ui_socket())
        self.assertFalse(ipc.send("reload"))


@WINDOWS
class Bridge(TempRuntime):
    def host(self):
        """The real native host, started the way a browser starts it, with a fake browser on stdio."""
        proc = subprocess.Popen([sys.executable, "-u", os.path.join("czgram", "nmhost.py")],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                env=dict(os.environ))
        self.addCleanup(lambda: (proc.kill(), proc.wait()))
        for _ in range(100):
            if bridge.connected():
                return proc
            time.sleep(0.05)
        self.fail("the native host didn't register")

    def browser_answer(self, proc, reply_for):
        import struct

        def run():
            head = proc.stdout.read(4)
            msg = json.loads(proc.stdout.read(struct.unpack("=I", head)[0]))
            data = json.dumps(reply_for(msg)).encode()
            proc.stdin.write(struct.pack("=I", len(data)) + data)
            proc.stdin.flush()

        t = threading.Thread(target=run, daemon=True)
        t.start()
        return t

    def test_snapshot_through_the_native_host(self):
        proc = self.host()
        self.browser_answer(proc, lambda m: {"id": m["id"], "url": "https://x.cz", "title": "T",
                                             "frames": [{"html": "<p>Maminka b_dlí doma.</p>"}]})
        reply = bridge.read_page(timeout=5)
        self.assertEqual(reply.get("url"), "https://x.cz", reply)

    def test_host_removes_its_file_when_the_browser_leaves(self):
        proc = self.host()
        proc.stdin.close()
        proc.wait(timeout=5)
        self.assertFalse(bridge.connected())

    def test_stale_file_is_cleaned_up(self):
        from czgram import config
        path = os.path.join(config.runtime_dir(), "bridge-1.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"address": r"\\.\pipe\czgram-gone", "key": "00" * 32}, f)
        self.assertIn("error", bridge.read_page(timeout=1))
        self.assertFalse(os.path.exists(path))

    def test_huge_reply_is_refused(self):
        from czgram import windows
        path = os.path.join(self.tmp, "bridge-2.json")
        srv = windows.serve(path)

        def serve():
            conn = srv.accept()
            conn.recv_bytes()
            try:
                conn.send_bytes(b"x" * (bridge.MAX_REPLY + 10))
            except OSError:
                pass
            conn.close()

        t = threading.Thread(target=serve)
        t.start()
        with self.assertRaises(ValueError):
            bridge._ask(path, 5)
        t.join(5)
        srv.close()


@WINDOWS
class ClaudeCodeOnWindows(unittest.TestCase):
    def test_npm_shim_runs_the_script_under_node(self):
        with tempfile.TemporaryDirectory() as d:
            shim = os.path.join(d, "claude.cmd")
            open(shim, "w").close()
            script = os.path.join(d, "node_modules", "@anthropic-ai", "claude-code", "cli.js")
            os.makedirs(os.path.dirname(script))
            open(script, "w").close()
            node = os.path.join(d, "node.exe")
            open(node, "w").close()
            with mock.patch("shutil.which", lambda name, path=None: node if name == "node" else None):
                self.assertEqual(claude_code.command(shim), [node, script])

    def test_unknown_batch_file_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            shim = os.path.join(d, "claude.bat")
            open(shim, "w").close()
            with mock.patch("shutil.which", lambda name, path=None: None):
                self.assertIsNone(claude_code.command(shim))

    def test_environment_keeps_what_windows_needs_and_no_key(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "must-not-leak", "SYSTEMROOT": r"C:\Windows"}):
            env = claude_code.clean_env()
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertEqual(env["SYSTEMROOT"], r"C:\Windows")
        self.assertIn("PATH", env)


@WINDOWS
class BatchFiles(unittest.TestCase):
    def test_czech_folder_name_survives(self):
        from czgram import windows
        with tempfile.TemporaryDirectory() as d:
            folder = os.path.join(d, "Jiří Novák")
            os.makedirs(folder)
            script = os.path.join(folder, "s.py")
            with open(script, "w", encoding="utf-8") as f:
                f.write("print('ok')\n")
            bat = os.path.join(d, "run.bat")
            windows.write_batch(bat, '"%s" "%s"' % (sys.executable, script))
            out = subprocess.run(["cmd.exe", "/d", "/c", bat], capture_output=True, text=True, timeout=30)
            self.assertEqual(out.stdout.strip(), "ok", out.stderr)


@WINDOWS
class Locking(TempRuntime):
    def test_parallel_records_all_count(self):
        row = {"model": "m", "input": 1, "output": 1}
        threads = [threading.Thread(target=usage.record, args=(row,)) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(usage.summary(None)["m"]["requests"], 8)


@WINDOWS
class Clipboard(unittest.TestCase):
    def test_text_round_trip(self):
        from czgram import windows
        before = windows.get_clipboard_text()
        try:
            self.assertTrue(windows.set_clipboard_text("Maminka b_dlí doma. ěščřžýáíé"))
            self.assertEqual(windows.get_clipboard_text(), "Maminka b_dlí doma. ěščřžýáíé")
        finally:
            if before is not None:
                windows.set_clipboard_text(before)


class Deadline(unittest.TestCase):
    """Runs everywhere: the timer path is what Windows uses."""

    def test_timer_fires_and_cancel_stops_it(self):
        import types
        fired = threading.Event()
        with mock.patch.object(deadline, "signal", types.SimpleNamespace()):  # no SIGALRM, as on Windows
            token = deadline.start(0.05, fired.set)
            self.assertTrue(fired.wait(2))
            fired.clear()
            token = deadline.start(0.2, fired.set)
            deadline.cancel(token)
            self.assertFalse(fired.wait(0.4))


if __name__ == "__main__":
    unittest.main()
