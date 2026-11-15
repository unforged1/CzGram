"""Measures OCR on capital-letter (velká písmena) exercises, like render_sz.py does for s/z.

Usage: python3 tests/render_caps.py [-v]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_sz  # noqa: E402

render_sz.LINES = [
    "Doplňte velká a malá písmena:",
    "Řeka (V/v)ltava teče Prahou.",
    "O (v/V)ánocích jsme byli doma.",
    "V (p/P)ondělí jdeme do školy.",
    "Jeho otec je (Č/č)ech.",
    "Studuje (č/Č)eštinu na gymnáziu.",
    "Bydlí v (č/Č)eské republice.",
    "(K/k)arlův most je starý.",
    "Večer svítil (m/M)ěsíc.",
    "Přišli V/vánoce a sníh.",
    "_rno je velké město.",
]

if __name__ == "__main__":
    render_sz.main()
