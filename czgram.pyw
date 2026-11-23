"""Windows launcher: `pythonw czgram.pyw [option]` runs CzGram from this folder with no console.

The Start menu entry, the czgram command and the sign-in hotkey listener all use it, so none
of them depends on the working directory or on PYTHONPATH.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from czgram.__main__ import main  # noqa: E402

sys.exit(main(sys.argv[1:]))
