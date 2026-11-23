"""Runs the Claude Code route against a fake CLI that speaks the real stream format."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENT = '{"type":"stream_event","event":{"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"%s"}}}'
INIT = '{"type":"system","subtype":"init","tools":%s,"mcp_servers":[]}'
OK = '{"type":"result","subtype":"success","is_error":false,"result":"x"}'
SIGNED_OUT = '{"type":"result","subtype":"success","is_error":true,"result":"Not logged in · Please run /login"}'

# The fake CLI is a shebang script and the tests isolate it with HOME, neither of which Windows uses.
POSIX_ONLY = unittest.skipIf(os.name == "nt", "fake CLI needs POSIX; tests/test_windows.py covers Windows")


@POSIX_ONLY
class ClaudeCode(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.home = self.dir.name
        self.bin = os.path.join(self.home, ".local/bin")
        os.makedirs(self.bin)
        self.record = os.path.join(self.home, "record.json")

    def fake(self, body):
        path = os.path.join(self.bin, "claude")
        with open(path, "w") as f:
            f.write(textwrap.dedent("""\
                #!%s
                import json, os, sys
                json.dump({"argv": sys.argv[1:], "env": sorted(os.environ), "cwd": os.getcwd(),
                           "pid": os.getpid(), "stdin": sys.stdin.read()}, open(%r, "w"))
                """) % (sys.executable, self.record) + textwrap.dedent(body))
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)

    def lookup(self, wait=True):
        env = dict(os.environ, HOME=self.home, XDG_CONFIG_HOME=os.path.join(self.home, "cfg"),
                   PATH="/usr/bin:/bin", ANTHROPIC_API_KEY="must-not-leak", PYTHONPATH=REPO)
        proc = subprocess.Popen([sys.executable, "-m", "czgram.ai"], env=env, text=True,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        proc.stdin.write(json.dumps({"snippet": "b_dlí", "line": "Maminka b_dlí doma.", "topic": ""}))
        proc.stdin.close()
        if not wait:
            return proc
        out = [json.loads(l) for l in proc.stdout]
        proc.wait()
        return out

    def script(self, *lines):
        return "".join("print(%r, flush=True)\n" % l for l in lines)

    def test_streams_text(self):
        self.fake(self.script(INIT % "[]", EVENT % "Dopl", EVENT % "ň y", OK))
        self.assertEqual(self.lookup(), [{"text": "Dopl"}, {"text": "ň y"}, {"done": True}])

    def test_runs_locked_down_without_api_key(self):
        self.fake(self.script(INIT % "[]", OK))
        self.lookup()
        rec = json.load(open(self.record))
        argv = rec["argv"]
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "")
        for flag in ("--strict-mcp-config", "--disable-slash-commands", "--no-session-persistence"):
            self.assertIn(flag, argv)
        self.assertNotIn("ANTHROPIC_API_KEY", rec["env"])
        self.assertIn("<exercise>", rec["stdin"])
        self.assertNotIn("b_dlí", " ".join(argv))  # screen text goes by stdin, not the command line
        self.assertEqual(os.listdir(rec["cwd"]) if os.path.exists(rec["cwd"]) else [], [])

    def test_bold_markers_are_removed_even_when_split(self):
        self.fake(self.script(INIT % "[]", EVENT % "**Odp", EVENT % "ověď*", EVENT % "* je y, 2 * 3", OK))
        text = "".join(m.get("text", "") for m in self.lookup())
        self.assertEqual(text, "Odpověď je y, 2 * 3")

    def test_model_choice(self):
        self.fake(self.script(INIT % "[]", OK))
        self.lookup()
        self.assertNotIn("--model", json.load(open(self.record))["argv"])  # "default" adds no flag
        os.makedirs(os.path.join(self.home, "cfg/czgram"))
        json.dump({"code_model": "haiku"}, open(os.path.join(self.home, "cfg/czgram/config.json"), "w"))
        self.lookup()
        argv = json.load(open(self.record))["argv"]
        self.assertEqual(argv[argv.index("--model") + 1], "haiku")

    def test_stops_if_tools_are_enabled(self):
        self.fake(self.script(INIT % '["Bash"]', EVENT % "should not appear", OK))
        out = self.lookup()
        self.assertEqual(len(out), 1)
        self.assertIn("tools enabled", out[0]["error"])

    def test_signed_out(self):
        self.fake(self.script(INIT % "[]", SIGNED_OUT))
        self.assertIn("Sign in", self.lookup()[0]["error"])

    def test_usage_limit(self):
        self.fake(self.script(INIT % "[]", SIGNED_OUT.replace("Not logged in · Please run /login", "Usage limit reached")))
        self.assertIn("usage limit", self.lookup()[0]["error"])

    def test_crash(self):
        self.fake("sys.exit(1)\n")
        self.assertIn("without answering", self.lookup()[0]["error"])

    def test_missing(self):
        self.assertIn("wasn't found", self.lookup()[0]["error"])

    def test_dismissing_the_bar_stops_the_cli(self):
        self.fake("import time\n" + self.script(INIT % "[]") + "time.sleep(60)\n")
        proc = self.lookup(wait=False)
        for _ in range(100):
            if os.path.exists(self.record) and os.path.getsize(self.record):
                break
            time.sleep(0.05)
        time.sleep(0.2)
        pid = json.load(open(self.record))["pid"]
        proc.terminate()
        proc.wait(timeout=5)
        proc.stdout.close()
        time.sleep(0.2)
        state = ""
        try:
            state = open("/proc/%d/stat" % pid).read().split()[2]
        except OSError:
            pass
        self.assertIn(state, ("", "Z"))


class Find(unittest.TestCase):
    def test_prefers_newest_desktop_copy(self):
        from czgram import claude_code
        with tempfile.TemporaryDirectory() as home:
            for version in ("2.1.9", "2.1.317", "2.0.50"):
                d = os.path.join(home, "Claude/claude-code", version, "abc")
                os.makedirs(d)
                p = os.path.join(d, "claude")
                open(p, "w").close()
                os.chmod(p, 0o755)
            old = {k: os.environ.get(k) for k in ("XDG_CONFIG_HOME", "PATH", "HOME")}
            os.environ.update(XDG_CONFIG_HOME=home, PATH="/nonexistent", HOME=home)
            try:
                self.assertIn("/2.1.317/", claude_code.find().replace("\\", "/"))
            finally:
                for k, v in old.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
