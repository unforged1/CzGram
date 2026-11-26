"""Pointing to the Internetová jazyková příručka: the setting, the prompt, and the "IJP: word" line."""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from czgram import ai, ijp  # noqa: E402


class Words(unittest.TestCase):
    def test_only_words_become_links(self):
        self.assertEqual(ijp.clean("bydlet"), "bydlet")
        self.assertEqual(ijp.clean(" „Vánoce“. "), "Vánoce")
        self.assertEqual(ijp.clean("bez ohledu"), "bez ohledu")
        self.assertEqual(ijp.clean("sci-fi"), "sci-fi")
        for bad in ("", "http://evil.example", "a<b>", "slovo2", "x" * 41, "a b c d", "bydlet?slovo=x"):
            self.assertIsNone(ijp.clean(bad), bad)

    def test_url(self):
        self.assertEqual(ijp.url("být"), "https://prirucka.ujc.cas.cz/?slovo=b%C3%BDt")
        self.assertEqual(ijp.url("bez ohledu"), "https://prirucka.ujc.cas.cz/?slovo=bez%20ohledu")


class Instructions(unittest.TestCase):
    def test_modes(self):
        self.assertEqual(ijp.instruction({"ijp_check": "off"}), "")
        self.assertIn("add a last line: IJP:", ijp.instruction({"ijp_check": "always"}))
        auto = ijp.instruction({"ijp_check": "auto"})
        self.assertIn("aren't sure", auto)
        self.assertNotIn("couldn't decide", auto)
        self.assertIn("couldn't decide", ijp.instruction({"ijp_check": "auto"}, unsure=True))
        self.assertEqual(ijp.mode({"ijp_check": "sometimes"}), "auto")
        for mode in ("auto", "always"):
            self.assertIn("never say you checked", ijp.instruction({"ijp_check": mode}))
            self.assertIn("never say you checked", ijp.bulk_instruction({"ijp_check": mode}))

    def test_prompts_carry_it(self):
        req = {"snippet": "b_dlí", "line": "Maminka b_dlí doma."}
        _, system = ai.build(req, "en", ijp.instruction({"ijp_check": "always"}))
        self.assertIn("Internetová jazyková příručka", system)
        _, plain = ai.build(req, "en")
        self.assertNotIn("Internetová", plain)
        _, bulk = ai.build_bulk({"bulk": [req, dict(req, snippet="m_dlo", line="m_dlo")]}, "en",
                                ijp.bulk_instruction({"ijp_check": "auto"}))
        self.assertIn("(IJP: word)", bulk)


class Lines(unittest.TestCase):
    def run_filter(self, chunks):
        out = []
        f = ijp.LineFilter(out.append)
        for c in chunks:
            f.feed(c)
        word = f.finish()  # before reading the output: finishing can release the last line
        return "".join(out), word, out

    def test_line_is_taken_out_even_when_split(self):
        text, word, _ = self.run_filter(["Odp", "ověď: y, bydlet je vyjmenované.\nIJ", "P: byd", "let"])
        self.assertEqual(text, "Odpověď: y, bydlet je vyjmenované.")
        self.assertEqual(word, "bydlet")

    def test_bold_and_trailing_newline(self):
        text, word, _ = self.run_filter(["y.\n", "**IJP:** bydlet\n"])
        self.assertEqual((text, word), ("y.", "bydlet"))

    def test_other_text_passes_unchanged(self):
        reply = "It is y.\nIn the IJP: no.\nI think so."
        text, word, _ = self.run_filter([reply[:7], reply[7:20], reply[20:]])
        self.assertEqual((text, word), (reply, None))

    def test_a_bad_word_stays_text(self):
        text, word, _ = self.run_filter(["y.\nIJP: http://evil.example"])
        self.assertEqual((text, word), ("y.\nIJP: http://evil.example", None))

    def test_chunks_stay_whole(self):
        _, _, out = self.run_filter(["Doplň y, ", "protože"])
        self.assertEqual(out, ["Doplň y, ", "protože"])

    def test_word_comes_before_done(self):
        got = []
        emit = ai.with_ijp(lambda **m: got.append(m))
        emit(text="y.\nIJP: bydlet")
        emit(usage_seen=True)
        emit(done=True)
        self.assertEqual(got, [{"text": "y."}, {"usage_seen": True}, {"ijp": "bydlet"}, {"done": True}])


class Bulk(unittest.TestCase):
    def test_suffix_becomes_the_link(self):
        self.assertEqual(ijp.split_suffix("y – bydlet je vyjmenované (IJP: bydlet)"),
                         ("y – bydlet je vyjmenované", "bydlet"))
        self.assertEqual(ijp.split_suffix("y – plain"), ("y – plain", None))
        buf = io.StringIO()
        with redirect_stdout(buf):
            s = ai.BulkSplitter(lambda **m: None)
            s.emit(text="[1] y – byt je vyjmenované (IJP: byt)\n[2] i – mi")
            s.finish()
        msgs = [json.loads(line) for line in buf.getvalue().splitlines()]
        self.assertEqual(msgs, [{"answer": 1, "text": "y – byt je vyjmenované", "ijp": "byt"},
                                {"answer": 2, "text": "i – mi"}])


if __name__ == "__main__":
    unittest.main()
