"""Run with: python3 -m unittest discover tests"""
import unittest

from czgram.analyze import analyze
from czgram.htmlread import to_lines


def first(line):
    return analyze([line])[0]


class Gaps(unittest.TestCase):
    def test_listed_words_take_y(self):
        for line in ("Maminka b_dlí doma.", "Na stole leží m_š.", "To je s_r.", "v_soký strom", "jaz_k je"):
            self.assertEqual(first(line)["suggest"], "y", line)

    def test_unlisted_word_defaults_to_i(self):
        self.assertEqual(first("Musíme v_dět dál.")["suggest"], "i")

    def test_homophones_are_left_open(self):
        self.assertEqual(first("Chci b_t doma.")["suggest"], "both")

    def test_hard_and_soft_consonants(self):
        self.assertEqual(first("Je to ch_ba.")["suggest"], "y")
        self.assertEqual(first("Je to č_slo.")["suggest"], "i")

    def test_d_t_n_decided_by_sound(self):
        self.assertEqual(first("Je to t_cho.")["suggest"], "")

    def test_topics(self):
        cases = {"Kluci běhal_ po hřišti.": "shoda", "Zapo_ěl jsem to.": "me_mne", "Dej to _ě.": "me_mne",
                 "ob_ekt": "be_bje", "Mluví o (mě/mně) a o tobě.": "me_mne", "(s/z)míchat těsto": "s_z_predpony"}
        for line, topic in cases.items():
            self.assertEqual(first(line)["topic"], topic, line)

    def test_shows_only_the_relevant_letter_row(self):
        text = first("Maminka b_dlí doma.")["text"]
        self.assertIn("B: být", text)
        self.assertNotIn("M: my", text)

    def test_czech_output(self):
        self.assertTrue(analyze(["Chci b_t doma."], "cs")[0]["hint"].startswith("Doplň"))


class Questions(unittest.TestCase):
    def test_matched_to_topic(self):
        cases = {"Co je přísudek?": "vetne_cleny", "Který pád je použit?": "pady",
                 "Urči slovní druh slova rychle.": "slovni_druhy", "Jaký je rod slova žena?": "rod"}
        for line, topic in cases.items():
            self.assertEqual(first(line)["topic"], topic, line)

    def test_short_keys_need_whole_words(self):
        self.assertEqual(first("Kam jela rodina?")["topic"], "")


class Ignored(unittest.TestCase):
    def test_not_exercises(self):
        for line in ("user_name = get_value()", "__init__.py", "See section ....... 12",
                     "Hello what is this?", "Rodina jela na výlet", "Doplňovací cvičení",
                     "https://example.com/some_page_name"):
            self.assertEqual(analyze([line]), [], line)

    def test_instruction_own_choice_is_not_a_target(self):
        self.assertEqual([i["snippet"] for i in analyze(["Doplňte i/y: Maminka b_dlí doma."])], ["b_dlí"])


class Html(unittest.TestCase):
    def test_form_controls_become_gaps(self):
        lines = to_lines('<p>Vidím <input type="text" value=""> psa.</p>'
                         "<p>O <select><option>Vyberte</option><option>mě</option><option>mně</option></select></p>"
                         '<script>x</script><p>Už <input value="hotovo"></p>')
        self.assertEqual(lines, ["Vidím ___ psa.", "O (mě/mně)", "Už [hotovo]"])


if __name__ == "__main__":
    unittest.main()
