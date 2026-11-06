"""Manual mode and the ignored site furniture."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

from czgram.analyze import analyze, describe_selection, is_ignored
from czgram.htmlread import find_selection, to_lines
from czgram.watch import Watcher

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Ignored(unittest.TestCase):
    def test_contact_button_in_any_spelling(self):
        for line in ("NAPIŠTE NÁM", "Napište nám", "NAPISTE NAM", "  napište  nám. "):
            self.assertTrue(is_ignored(line), line)
            self.assertEqual(analyze([line]), [], line)

    def test_real_instructions_still_count(self):
        self.assertFalse(is_ignored("Napište slovo."))
        self.assertEqual(len(analyze(["Napište správný tvar slova."])), 1)

    def test_real_page_text_without_structure(self):
        # The page's text as read from the live site, with no question markup.
        lines = ["Vyjmenovaná slova po P (těžké)", "nápis: Neklop_t", "i", "y", "NAPIŠTE NÁM"]
        self.assertEqual([i["snippet"] for i in analyze(lines)], ["Neklop_t"])

    def test_costs_quick_mode_nothing(self):
        w = Watcher("en")
        frame = {"frames": ["<div><a>NAPIŠTE NÁM</a></div>"]}
        self.assertIsNone(w.feed(frame))
        self.assertIsNone(w.feed(frame))

    def test_as_a_selection(self):
        self.assertEqual(describe_selection("NAPIŠTE NÁM"), [])


class Snapshot(unittest.TestCase):
    PAGE = ('<czgram-selection data-context="Maminka bydlí &amp; vaří.">bydlí</czgram-selection>'
            "<p>Maminka bydlí &amp; vaří.</p>")

    def test_selection_and_sentence(self):
        self.assertEqual(find_selection(self.PAGE), ("bydlí", "Maminka bydlí & vaří."))

    def test_nothing_selected(self):
        self.assertEqual(find_selection("<p>text</p>"), ("", ""))

    def test_does_not_leak_into_normal_reading(self):
        self.assertEqual(to_lines(self.PAGE), ["Maminka bydlí & vaří."])


class Words(unittest.TestCase):
    def one(self, text, **kw):
        items = describe_selection(text, **kw)
        self.assertEqual(len(items), 1)
        return items[0]

    def test_listed_word_shows_its_row(self):
        item = self.one("bydlí")
        self.assertEqual((item["topic"], item["kind"]), ("vyjmenovana", "word"))
        self.assertIn("B: být", item["text"])
        self.assertNotIn("M: my", item["text"])
        self.assertIn("byd", item["hint"])

    def test_hard_and_soft(self):
        self.assertEqual(self.one("chyba")["topic"], "tvrde_mekke")
        self.assertEqual(self.one("číslo")["topic"], "tvrde_mekke")

    def test_unknown_word_says_so(self):
        item = self.one("dům")
        self.assertEqual((item["topic"], item["title"]), ("", "Selected word"))

    def test_grammar_term(self):
        self.assertEqual(self.one("přísudek")["topic"], "vetne_cleny")

    def test_gap_line_is_read_as_exercise(self):
        item = self.one("b_dlí")
        self.assertEqual((item["suggest"], item["kind"]), ("y", "gap"))

    def test_context_kept(self):
        item = self.one("bydlí", context="Maminka bydlí doma.")
        self.assertEqual((item["context"], item["line"]), ("Maminka bydlí doma.", "Maminka bydlí doma."))
        self.assertTrue(item["selected"])

    def test_czech_output(self):
        self.assertEqual(self.one("dům", lang="cs")["title"], "Vybrané slovo")

    def test_empty(self):
        for text in ("", "   ", "123 ...", "---"):
            self.assertEqual(describe_selection(text), [], text)


class Process(unittest.TestCase):
    def run_scan(self, stdin):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(tmp + "/czgram")
            with open(tmp + "/czgram/config.json", "w") as f:
                json.dump({"detection": "manual"}, f)
            res = subprocess.run([sys.executable, "-m", "czgram.scan", "--manual"], input=stdin, text=True,
                                 capture_output=True, timeout=20,
                                 env=dict(os.environ, XDG_CONFIG_HOME=tmp, XDG_RUNTIME_DIR=tmp, PYTHONPATH=REPO))
        return [json.loads(l) for l in res.stdout.splitlines()]

    def test_selected_word(self):
        out = self.run_scan("bydlí")
        self.assertEqual(out[0], {"event": "captured"})
        self.assertEqual(out[1]["items"][0]["snippet"], "bydlí")

    def test_nothing_selected(self):
        out = self.run_scan("")
        self.assertEqual(out[1]["items"], [])
        self.assertEqual(out[1]["empty_title"], "Nothing selected")


if __name__ == "__main__":
    unittest.main()
