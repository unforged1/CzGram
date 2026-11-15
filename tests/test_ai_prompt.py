"""The AI prompt stays general and adds only the rules a target needs."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from czgram import ai  # noqa: E402


def rules(snippet, options=(), line=None):
    return " ".join(ai._rules({"snippet": snippet, "line": line or snippet, "options": list(options)}))


class Rules(unittest.TestCase):
    def test_listed_rows_only_for_the_letter_before_the_gap(self):
        text = rules("p_sk", ["i", "y"])
        self.assertIn("pysk", text)
        self.assertNotIn("bydlit", text)

    def test_hard_soft(self):
        self.assertIn("After h, ch", rules("ch_ba"))
        self.assertNotIn("Listed", rules("ch_ba"))

    def test_s_z(self):
        for target in ("s/z/vz létlo", "(z/ze) školy", "Přišel _e školy", "Led _mrzl"):
            self.assertIn("Prefixes", rules(target), target)
        self.assertNotIn("After h", rules("Přišel _e školy"))

    def test_capitals(self):
        for target, opts in (("(V/v)ánocích", ()), ("_", ("V", "v")), ("Vánoce", ("velké", "malé"))):
            self.assertIn("Capitals", rules(target, opts), target)

    def test_general_when_nothing_matches(self):
        self.assertEqual(rules("_", ["mě", "mně"]), "")

    def test_prompt_is_compact(self):
        prompt, system = ai.build({"snippet": "p_sk", "line": "p_sk", "options": ["i", "y"]}, "en")
        self.assertNotIn("Gap to solve", prompt)  # the line already is the gap
        self.assertLess(len(system), 1200)
        prompt, _ = ai.build({"snippet": "p_sk", "line": "Velký p_sk.", "options": []}, "cs")
        self.assertIn("Gap to solve: p_sk", prompt)


if __name__ == "__main__":
    unittest.main()
