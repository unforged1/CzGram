"""What quick mode counts as a new question, using markup copied from the real page's structure."""
import unittest

from czgram.analyze import describe_exercise
from czgram.htmlread import find_exercise
from czgram.watch import Watcher


def page(question, options=("i", "y"), answered=False):
    cards = " ".join('<span data-data="option"><span>%s</span></span>' % o for o in options)
    extra = "<exercise-explanation><span>Proč.</span></exercise-explanation>" if answered else ""
    return ('<div><h2>Nadpis</h2><div data-data="question"><span>%s</span></div>'
            "<div>%s</div>%s</div>" % (question, cards, extra))


def reply(*args, **kwargs):
    return {"frames": [page(*args, **kwargs)], "title": "Cvičení"}


class Reading(unittest.TestCase):
    def test_question_and_options(self):
        html = page('nápis: <span>Neklop<span>_</span>t</span>')
        self.assertEqual(find_exercise(html), {"question": "nápis: Neklop_t", "options": ["i", "y"],
                                               "context": "", "answered": False})

    def test_context_beside_the_question(self):
        html = ('<div data-data="wrapper"><div>sloveso</div><div>to strike</div>'
                '<div data-data="question"><span>b<span>_</span>t</span></div>'
                '<div><span data-data="option"><span>i</span></span>'
                '<span data-data="option"><span>y</span></span></div>'
                "<div>Nepřehlédni: význam rozhoduje.</div></div><footer>NAPIŠTE NÁM</footer>")
        ex = find_exercise(html)
        self.assertEqual(ex["question"], "b_t")
        self.assertEqual(ex["context"], "sloveso · to strike · Nepřehlédni: význam rozhoduje.")

    def test_page_explanation_is_not_context(self):
        html = ('<div data-data="wrapper"><div data-data="question">b_t</div>'
                '<span data-data="option">i</span><span data-data="option">y</span>'
                "<exercise-explanation><span>Vysvětlení</span></exercise-explanation></div>")
        ex = find_exercise(html)
        self.assertEqual(ex["context"], "")
        self.assertTrue(ex["answered"])

    def test_answered_by_explanation_or_next_button(self):
        self.assertTrue(find_exercise(page("x_y", answered=True))["answered"])
        html = page("x_y") + '<button data-data="next">Další</button>'
        self.assertTrue(find_exercise(html)["answered"])

    def test_not_an_exercise(self):
        self.assertIsNone(find_exercise("<p>Běžný text na stránce.</p>"))
        self.assertIsNone(find_exercise('<div data-data="question"></div>'))
        self.assertIsNone(find_exercise('<div data-data="question">Bez možností</div>'))


class Watching(unittest.TestCase):
    def setUp(self):
        self.w = Watcher("en")

    def settled(self, *args, **kwargs):
        """Two polls of the same page, as the loop would see it."""
        first = self.w.feed(reply(*args, **kwargs))
        self.assertIsNone(first)
        return self.w.feed(reply(*args, **kwargs))

    def test_new_question_after_two_polls(self):
        self.assertEqual(len(self.settled("Neklop_t")), 1)

    def test_unchanged_question_asks_once(self):
        self.settled("Neklop_t")
        for _ in range(5):
            self.assertIsNone(self.w.feed(reply("Neklop_t")))

    def test_filling_the_gap_is_not_a_new_question(self):
        self.settled("Neklop_t")
        for _ in range(4):
            self.assertIsNone(self.w.feed(reply("Neklopit", answered=True)))

    def test_flicker_during_a_swap_costs_nothing(self):
        self.settled("Neklop_t")
        self.assertIsNone(self.w.feed(reply("half-loaded")))
        self.assertIsNone(self.w.feed(reply("kop_to")))
        self.assertEqual(self.w.feed(reply("kop_to"))[0]["snippet"], "kop_to")

    def test_next_question_appears(self):
        self.settled("Neklop_t")
        self.w.feed(reply("Neklopit", answered=True))
        self.assertEqual(self.settled("kop_to")[0]["snippet"], "kop_to")

    def test_same_question_again_later_is_shown_again(self):
        self.settled("kop_to")
        self.w.feed(reply("kopyto", answered=True))
        self.assertIsNotNone(self.settled("kop_to"))

    def test_other_sites_use_the_general_reader(self):
        frame = {"frames": ["<p>Maminka b<input type='text' value=''>dlí doma.</p>"]}
        self.assertIsNone(self.w.feed(frame))
        self.assertEqual(self.w.feed(frame)[0]["suggest"], "y")

    def test_page_without_questions(self):
        frame = {"frames": ["<p>Rodina jela na výlet.</p>"]}
        self.assertIsNone(self.w.feed(frame))
        self.assertIsNone(self.w.feed(frame))


class Describing(unittest.TestCase):
    def test_gap_with_two_options(self):
        item = describe_exercise("kop_to koně", ["i", "y"], "en", "Cvičení")
        self.assertEqual((item["suggest"], item["topic"], item["options"]), ("y", "vyjmenovana", ["i", "y"]))
        self.assertEqual(item["exercise"], "Cvičení")

    def test_no_listed_word(self):
        self.assertEqual(describe_exercise("neuchop_telný", ["i", "y"], "en")["suggest"], "i")

    def test_klopit_is_not_klopytat(self):
        # Found on the real site: the listed word klopýtat doesn't make "Neklopit" take y.
        self.assertEqual(describe_exercise("nápis: Neklop_t", ["i", "y"], "en")["suggest"], "i")
        self.assertEqual(describe_exercise("kl_pýtat", ["o", "a"], "en")["suggest"], "")
        self.assertEqual(describe_exercise("klop_tat", ["i", "y"], "en")["suggest"], "y")

    def test_long_options_are_matched_exactly(self):
        self.assertEqual(describe_exercise("kop_to", ["í", "ý"], "en")["suggest"], "ý")
        self.assertEqual(describe_exercise("neuchop_telný", ["í", "ý"], "en")["suggest"], "í")
        self.assertEqual(describe_exercise("kop_to", ["i", "y"], "en")["suggest"], "y")

    def test_both_lengths_stay_open(self):
        item = describe_exercise("kop_to", ["i", "í", "y", "ý"], "en")
        self.assertEqual(item["suggest"], "y")
        self.assertIn("length", item["hint"])

    def test_length_in_brackets_elsewhere(self):
        from czgram.analyze import analyze
        self.assertEqual(analyze(["Na stole je s(í/ý)r."])[0]["suggest"], "ý")

    def test_context_is_kept_and_flagged(self):
        item = describe_exercise("kop_to", ["i", "y"], "en", "", "sloveso")
        self.assertEqual(item["context"], "sloveso")
        self.assertIn("sloveso", item["line"])
        self.assertIn("Check", item["hint"])
        self.assertNotIn("Check", describe_exercise("kop_to", ["i", "y"], "en")["hint"])

    def test_same_question_with_new_context_is_new(self):
        w = Watcher("en")
        one = {"frames": ['<div data-data="wrapper"><div>význam: bydlet</div>' + page("m_t") + "</div>"]}
        two = {"frames": ['<div data-data="wrapper"><div>význam: umývat</div>' + page("m_t") + "</div>"]}
        w.feed(one)
        self.assertIsNotNone(w.feed(one))
        w.feed(two)
        self.assertIsNotNone(w.feed(two))

    def test_other_options(self):
        self.assertEqual(describe_exercise("Mluví o _ a o tobě.", ["mě", "mně"], "en")["topic"], "me_mne")

    def test_question_without_gap(self):
        item = describe_exercise("Který pád je použit?", ["2.", "4."], "en")
        self.assertEqual(item["topic"], "pady")


if __name__ == "__main__":
    unittest.main()
