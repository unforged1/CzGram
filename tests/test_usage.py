"""Token totals and what turns speed mode on."""
import datetime
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

from czgram import usage
from czgram.speed import configured_model, is_fast_model, should_run

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROW = {"model": "claude-opus-5-5", "input": 2, "output": 100, "thinking": 90, "cache_read": 10, "cache_write": 500}


class Totals(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        old = os.environ.get("XDG_STATE_HOME")
        os.environ["XDG_STATE_HOME"] = tmp.name
        self.addCleanup(lambda: os.environ.pop("XDG_STATE_HOME") if old is None
                        else os.environ.__setitem__("XDG_STATE_HOME", old))

    def test_adds_up_per_model(self):
        usage.record(ROW)
        usage.record(ROW)
        usage.record(dict(ROW, model="claude-haiku-5-5"))
        rows = usage.summary()
        self.assertEqual(rows["claude-opus-5-5"]["requests"], 2)
        self.assertEqual(rows["claude-opus-5-5"]["output"], 200)
        self.assertEqual(rows["claude-haiku-5-5"]["requests"], 1)

    def test_thinking_is_not_counted_twice(self):
        usage.record(ROW)
        self.assertEqual(usage.total(), 612)

    def test_periods(self):
        today = datetime.date(2026, 11, 10)
        usage.record(ROW, "2026-11-10")
        usage.record(ROW, "2026-11-04")
        usage.record(ROW, "2026-11-03")
        self.assertEqual(usage.total(1, today), 612)
        self.assertEqual(usage.total(7, today), 1224)
        self.assertEqual(usage.total(None, today), 1836)

    def test_stores_numbers_only(self):
        usage.record(ROW)
        with open(usage.path()) as f:
            data = json.load(f)
        self.assertEqual(sorted(data), ["days"])

    def test_damaged_file_starts_over(self):
        usage.record(ROW)
        with open(usage.path(), "w") as f:
            f.write("{not json")
        self.assertEqual(usage.total(), 0)
        usage.record(ROW)
        self.assertEqual(usage.total(), 612)

    def test_reset(self):
        usage.record(ROW)
        usage.reset()
        usage.reset()
        self.assertEqual(usage.total(), 0)

    def test_short(self):
        self.assertEqual([usage.short(n) for n in (5, 1200, 12400, 2500000)], ["5", "1.2k", "12.4k", "2.5M"])

    def test_report(self):
        usage.record(ROW)
        text = usage.report()
        self.assertIn("Today: 612 tokens, 1 lookups", text)
        self.assertIn("claude-opus-5-5", text)


class ThroughClaudeCode(unittest.TestCase):
    def run_fake(self, script_lines, cfg=None):
        with tempfile.TemporaryDirectory() as home:
            bin_dir = os.path.join(home, ".local/bin")
            os.makedirs(bin_dir)
            fake = os.path.join(bin_dir, "claude")
            with open(fake, "w") as f:
                f.write("#!%s\nimport sys\nsys.stdin.read()\n" % sys.executable)
                f.write("".join("print(%r, flush=True)\n" % json.dumps(l) for l in script_lines))
            os.chmod(fake, os.stat(fake).st_mode | stat.S_IXUSR)
            os.makedirs(os.path.join(home, "cfg/czgram"))
            with open(os.path.join(home, "cfg/czgram/config.json"), "w") as f:
                json.dump(cfg or {}, f)
            env = dict(os.environ, HOME=home, XDG_CONFIG_HOME=os.path.join(home, "cfg"),
                       XDG_STATE_HOME=os.path.join(home, "state"), PATH="/usr/bin:/bin", PYTHONPATH=REPO)
            res = subprocess.run([sys.executable, "-m", "czgram.ai"], env=env, text=True, capture_output=True,
                                 input=json.dumps({"snippet": "b_dlí", "line": "b_dlí", "topic": ""}), timeout=20)
            stored = None
            state = os.path.join(home, "state/czgram/usage.json")
            if os.path.exists(state):
                with open(state) as f:
                    stored = json.load(f)
        return [json.loads(l) for l in res.stdout.splitlines()], stored

    MODEL_USAGE = {"claude-opus-5-5": {"inputTokens": 2, "outputTokens": 728, "cacheReadInputTokens": 5,
                                       "cacheCreationInputTokens": 615, "thinkingTokens": 723}}

    def test_reports_model_and_records_tokens(self):
        out, stored = self.run_fake([
            {"type": "system", "subtype": "init", "tools": [], "mcp_servers": [], "model": "claude-opus-5-5"},
            {"type": "result", "is_error": False, "result": "x", "modelUsage": self.MODEL_USAGE}])
        self.assertEqual(out[0], {"model": "claude-opus-5-5"})
        self.assertEqual(out[1]["tokens"]["this"], 1350)
        self.assertEqual(out[-1], {"done": True})
        day = next(iter(stored["days"].values()))
        self.assertEqual(day["claude-opus-5-5"]["thinking"], 723)
        self.assertEqual(day["claude-opus-5-5"]["requests"], 1)

    def test_failed_lookup_with_usage_still_counts(self):
        out, stored = self.run_fake([
            {"type": "result", "is_error": True, "result": "Usage limit reached", "modelUsage": self.MODEL_USAGE}])
        self.assertIsNotNone(stored)
        self.assertIn("usage limit", out[-1]["error"])

    def test_nothing_reported_records_nothing(self):
        _out, stored = self.run_fake([{"type": "result", "is_error": False, "result": "x"}])
        self.assertIsNone(stored)


class Speed(unittest.TestCase):
    def test_fast_models(self):
        for name in ("opus", "fable", "claude-opus-5-5", "claude-fable-5-1", "anthropic/claude-opus-5", "OPUS"):
            self.assertTrue(is_fast_model(name), name)
        for name in ("haiku", "sonnet", "default", "claude-sonnet-5-5", "gemini-2.5-flash", "", None):
            self.assertFalse(is_fast_model(name), name)

    def test_model_per_connection(self):
        cfg = {"claude_backend": "code", "code_model": "opus", "model": "m2", "custom_model": "m3"}
        self.assertEqual(configured_model(cfg), "opus")
        self.assertEqual(configured_model(dict(cfg, claude_backend="api")), "m2")
        self.assertEqual(configured_model(dict(cfg, claude_backend="custom")), "m3")

    def test_needs_the_option_and_ai_answers(self):
        on = {"speed_mode": True, "use_claude": True, "claude_backend": "code", "code_model": "opus"}
        self.assertTrue(should_run(on))
        self.assertFalse(should_run(dict(on, speed_mode=False)))
        self.assertFalse(should_run(dict(on, use_claude=False)))
        self.assertFalse(should_run(dict(on, code_model="haiku")))

    def test_default_model_uses_what_claude_reports(self):
        cfg = {"speed_mode": True, "use_claude": True, "claude_backend": "code", "code_model": "default"}
        self.assertFalse(should_run(cfg))
        self.assertTrue(should_run(cfg, "claude-opus-5-5"))
        self.assertFalse(should_run(cfg, "claude-sonnet-5-5"))

    def test_chosen_model_outranks_stale_report(self):
        cfg = {"speed_mode": True, "use_claude": True, "claude_backend": "code", "code_model": "haiku"}
        self.assertFalse(should_run(cfg, "claude-opus-5-5"))


if __name__ == "__main__":
    unittest.main()
