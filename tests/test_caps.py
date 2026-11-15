"""Capital letters (velká písmena): rules, choices, buttons, selections and OCR repair."""
import unittest

from czgram import caps
from czgram.analyze import analyze, describe_exercise, describe_selection
from czgram.ocr import repair_choices


def first(line):
    return analyze([line])[0]


class Rules(unittest.TestCase):
    def test_upper(self):
        cases = {"Řeka (V/v)ltava teče.": "V", "O (v/V)ánocích jsme doma.": "V", "Jeho otec je (Č/č)ech.": "Č",
                 "Přišli V/vánoce a sníh.": "V", "Šli jsme přes (k/K)arlův most.": "K",
                 "Jeli jsme na (š/Š)umavu.": "Š"}
        for line, answer in cases.items():
            self.assertEqual(first(line)["suggest"], answer, line)

    def test_lower(self):
        cases = {"V (p/P)ondělí jdeme do školy.": "p", "Studuje (č/Č)eštinu.": "č", "Mluví (č/Č)esky.": "č",
                 "Bydlí v (č/Č)eské republice.": "č", "Narodil se v (l/L)ednu.": "",
                 "Je to (p/P)ražský hrad.": "p"}
        for line, answer in cases.items():
            self.assertEqual(first(line)["suggest"], answer, line)

    def test_sentence_start_wins(self):
        self.assertEqual(first("(p/P)ondělí bylo deštivé.")["suggest"], "P")
        self.assertEqual(first("Bylo pozdě. (p/P)ondělí začalo.")["suggest"], "P")

    def test_meaning_stays_open(self):
        for line in ("Večer svítil (m/M)ěsíc.", "Obíhá kolem (s/S)lunce.", "Děkuji (v/V)ám za dopis."):
            item = first(line)
            self.assertEqual((item["suggest"], item["topic"]), ("", "velka_pismena"), line)
            self.assertIn("meaning", item["hint"])

    def test_unknown_word_gets_the_rule_only(self):
        item = first("Je to (d/D)ům.")
        self.assertEqual((item["suggest"], item["topic"]), ("", "velka_pismena"))

    def test_reason_names_the_category(self):
        self.assertIn("inhabitants", first("Jeho otec je (Č/č)ech.")["hint"])
        self.assertIn("svátky", analyze(["O (v/V)ánocích."], "cs")[0]["hint"])

    def test_not_a_case_pair(self):
        self.assertFalse(caps.is_case_pair(["V", "W"]))
        self.assertFalse(caps.is_case_pair(["v", "v"]))
        self.assertEqual(first("Musíme (s/z)míchat těsto.")["topic"], "s_z_predpony")


class Buttons(unittest.TestCase):
    def test_letter_buttons(self):
        item = describe_exercise("Přišly _ánoce.", ["V", "v"], "en")
        self.assertEqual((item["suggest"], item["topic"]), ("V", "velka_pismena"))

    def test_size_buttons(self):
        self.assertEqual(describe_exercise("Přišly vánoce.", ["velké písmeno", "malé písmeno"])["suggest"],
                         "velké písmeno")
        self.assertEqual(describe_exercise("Bylo to v pondělí.", ["Velké", "Malé"])["suggest"], "Malé")


class Selection(unittest.TestCase):
    def test_capital_words_explain_the_capital_rule(self):
        self.assertEqual(describe_selection("Vánoce")[0]["topic"], "velka_pismena")
        self.assertEqual(describe_selection("pondělí")[0]["topic"], "velka_pismena")

    def test_other_words_keep_their_rule(self):
        self.assertEqual(describe_selection("bydlí")[0]["topic"], "vyjmenovana")
        # An adjective like "český" is no reason to talk about capitals on its own.
        self.assertNotEqual(describe_selection("vysoký")[0]["topic"], "velka_pismena")


class OcrRepair(unittest.TestCase):
    def test_misreads(self):
        cases = {"Řeka (V/v)Itava teče": "Řeka (V/v)ltava teče", "Jeho otec je (Č/čJech.": "Jeho otec je (Č/č)ech.",
                 "(Kik)arlův most": "(K/k)arlův most", "V (pP)ondělí jdeme": "V (p/P)ondělí jdeme",
                 "Přišli Vývánoce a sníh.": "Přišli V/vánoce a sníh.", "Řeka (V/)ltava teče": "Řeka (V/v)ltava teče",
                 "Studuje (/Č)eštinu": "Studuje (Č/č)eštinu", "O (vánocích jsme byli doma.": "O (V/v)ánocích jsme byli doma.",
                 "Bydlí v (č/ČJeské republice.": "Bydlí v (č/Č)eské republice.",
                 "Řeka (V/v)itava teče.": "Řeka (V/v)ltava teče."}
        for read, fixed in cases.items():
            self.assertEqual(repair_choices(read), fixed, read)

    def test_real_text_is_left_alone(self):
        for line in ("Viděl Kiki a Lili.", "Zavolej (prosím) Vivaldiho.", "Byl v (Praze) a Brně",
                     "(viz obrázek na straně", "Jedli (jsme) a pili.", "Je to (Vv) model",
                     "Jsou to (V/v)ideo a (K/k)ino."):
            self.assertEqual(repair_choices(line), line, line)


if __name__ == "__main__":
    unittest.main()
