"""Bulk mode: finding a set of questions, the offer, following the user's answers, one AI request."""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from czgram import ai  # noqa: E402
from czgram.analyze import analyze_in_order  # noqa: E402
from czgram.htmlread import find_state  # noqa: E402
from czgram.watch import Bulk  # noqa: E402

SHEET = ("<h1>Doplňte i/y</h1><p>1. Musíme b_dlet v Praze.</p><p>2. Vrátil se (z/ze) školy.</p>"
         "<p>3. Ch_ba je v textu.</p><p>4. Přijdu v (p/P)ondělí.</p>")


def page(alt=0, answers=0, body=SHEET, url="https://example.cz/list"):
    state = '<czgram-state data-alt="%d" data-answers="%d"></czgram-state>' % (alt, answers)
    return {"url": url, "title": "Pracovní list", "frames": [state + body]}


class PageState(unittest.TestCase):
    def test_counters(self):
        self.assertEqual(find_state(page(2, 5)["frames"][0]), (2, 5))
        self.assertEqual(find_state("<p>older extension</p>"), (0, 0))


class InOrder(unittest.TestCase):
    def test_page_order_without_instructions(self):
        items = analyze_in_order(["Doplňte i/y:", "1. Musíme b_dlet v Praze.", "2. Vrátil se (z/ze) školy.",
                                  "3. Ch_ba je v textu.", "Kdo bydlí v Praze?", "def snake_case(): pass"])
        self.assertEqual([i["snippet"] for i in items], ["b_dlet", "(z/ze)", "Ch_ba", "Kdo bydlí v Praze?"])

    def test_same_gap_on_two_lines_stays_twice(self):
        items = analyze_in_order(["1. b_dlí v domě.", "2. b_dlí v bytě."])
        self.assertEqual(len(items), 2)


class Tracker(unittest.TestCase):
    def test_offer_accept_follow_finish(self):
        b = Bulk("en")
        self.assertEqual(b.look(page()), [{"event": "bulk_offer", "count": 4}])
        self.assertEqual(b.look(page()), [])                     # no repeat offer
        self.assertEqual(b.watch(page()), [])                    # nothing pressed yet
        on = b.watch(page(alt=1))
        self.assertEqual(on[0]["event"], "bulk_on")
        self.assertEqual([i["snippet"] for i in on[0]["items"]], ["b_dlet", "(z/ze)", "Ch_ba", "(p/P)ondělí"])
        self.assertEqual(b.look(page(alt=1)), [])                # no offers while it's on
        self.assertEqual(b.watch(page(alt=1, answers=1)), [{"event": "bulk_next", "index": 1}])
        self.assertEqual(b.watch(page(alt=1, answers=1)), [])
        self.assertEqual(b.watch(page(alt=1, answers=3)), [{"event": "bulk_next", "index": 3}])
        self.assertEqual(b.watch(page(alt=1, answers=4))[0]["event"], "bulk_end")
        self.assertEqual(b.look(page(alt=1, answers=4)), [])     # a finished set isn't offered again
        self.assertIn(("Ch_ba", "3. Ch_ba je v textu."), b.answered)  # and quick mode won't redo it

    def test_answers_before_accepting_dont_count(self):
        b = Bulk("en")
        b.look(page(answers=2))
        b.watch(page(alt=1, answers=2))
        self.assertEqual(b.watch(page(alt=1, answers=3)), [{"event": "bulk_next", "index": 1}])

    def test_leaving_the_page(self):
        b = Bulk("en")
        b.look(page())
        self.assertEqual(b.watch(page(url="https://example.cz/other")), [{"event": "bulk_offer_end"}])
        b.look(page())
        b.watch(page(alt=1))
        self.assertEqual(b.watch(page(alt=1, url="https://example.cz/other"))[0]["event"], "bulk_end")

    def test_one_question_is_not_a_set(self):
        self.assertEqual(Bulk("en").look(page(body="<p>Musíme b_dlet v Praze.</p>")), [])

    def test_offer_withdrawn_when_set_disappears(self):
        b = Bulk("en")
        b.look(page())
        self.assertEqual(b.look(page(body="<p>Hotovo</p>")), [{"event": "bulk_offer_end"}])


class OneRequest(unittest.TestCase):
    items = [{"snippet": "b_dlet", "line": "1. Musíme b_dlet v Praze.", "options": []},
             {"snippet": "(z/ze)", "line": "2. Vrátil se (z/ze) školy.", "options": []},
             {"snippet": "p_sk", "line": "3. Velký p_sk.", "options": ["i", "y"]}]

    def test_prompt_numbers_every_item(self):
        prompt, system = ai.build_bulk({"bulk": self.items, "exercise": "Pracovní list"}, "en")
        for n in (1, 2, 3):
            self.assertIn("[%d] " % n, prompt)
        self.assertIn("(gap: p_sk)", prompt)
        self.assertIn("(options: i | y)", prompt)
        # One listed-words block holding the B and P rows, plus the s/z rule, each once.
        self.assertEqual(system.count("Listed words"), 1)
        self.assertIn("B: být", system)
        self.assertIn("P: pýcha", system)
        self.assertNotIn("M: my", system)
        self.assertEqual(system.count("Prefixes:"), 1)

    def test_answers_arrive_one_by_one(self):
        out, passed = io.StringIO(), []
        splitter = ai.BulkSplitter(lambda **m: passed.append(m))
        with redirect_stdout(out):
            for chunk in ("[1] y – byd", "let is listed\n[2] **ze** – before š", "\n[3] y – pysk\n", "junk line\n"):
                splitter.emit(text=chunk)
            first = [json.loads(line) for line in out.getvalue().splitlines()]
            splitter.emit(done=True)
        self.assertEqual(first, [{"answer": 1, "text": "y – bydlet is listed"},
                                 {"answer": 2, "text": "ze – before š"},
                                 {"answer": 3, "text": "y – pysk"}])
        self.assertEqual(passed, [{"done": True}])

    def test_last_answer_without_newline(self):
        out = io.StringIO()
        splitter = ai.BulkSplitter(lambda **m: None)
        with redirect_stdout(out):
            splitter.emit(text="[1] y – a\n[2] i – b")
            splitter.emit(done=True)
        self.assertEqual(len(out.getvalue().splitlines()), 2)



class BulkKey(unittest.TestCase):
    """The confirm shortcut: set in config, carried to the extension, never anything but a known key."""

    def test_config_falls_back_to_alt(self):
        from czgram import config
        self.assertEqual(config.bulk_key({"bulk_key": "Shift"}), "Shift")
        for bad in ("", "Enter", "Alt; alert(1)", None):
            self.assertEqual(config.bulk_key({"bulk_key": bad}), "Alt")
        self.assertEqual(config.bulk_key({}), "Alt")

    def test_host_passes_only_known_keys(self):
        from czgram import nmhost
        msg = nmhost.snapshot_request(b"snapshot full armed key=Control".split(), 7)
        self.assertEqual(msg, {"id": 7, "cmd": "snapshot", "full": True, "armed": True, "key": "Control"})
        self.assertEqual(nmhost.snapshot_request([b"snapshot"], 1)["key"], "Alt")
        self.assertEqual(nmhost.snapshot_request([b"snapshot", b'key="});x'], 1)["key"], "Alt")

    def test_bridge_sends_the_key(self):
        from unittest import mock
        from czgram import bridge
        sent = []
        with mock.patch.object(bridge.glob, "glob", return_value=["/x/bridge-1.sock"]), \
                mock.patch.object(bridge, "_ask", lambda path, timeout, request: sent.append(request) or {"url": "u"}):
            bridge.read_page(armed=True, key="Shift")
        self.assertEqual(sent, [b"snapshot armed key=Shift"])


if __name__ == "__main__":
    unittest.main()
