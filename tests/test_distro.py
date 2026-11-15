import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from czgram import distro  # noqa: E402


class Distro(unittest.TestCase):
    def release(self, text):
        f = tempfile.NamedTemporaryFile("w", delete=False)
        f.write(text)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_arch_and_derivatives(self):
        for text in ('ID=arch\n', 'ID=manjaro\nID_LIKE=arch\n', 'ID=endeavouros\nID_LIKE="arch"\n'):
            path = self.release(text)
            self.assertEqual(distro.family(path), "arch", text)
            self.assertEqual(distro.pkg("tesseract-ocr-ces", path), "tesseract-data-ces")

    def test_debian_family_and_missing_file(self):
        path = self.release('ID=kali\nID_LIKE=debian\n')
        self.assertEqual(distro.pkg("python3-anthropic", path), "python3-anthropic")
        self.assertEqual(distro.family("/nonexistent"), "debian")


class ArchPackage(unittest.TestCase):
    def test_pkgbuild_version_matches(self):
        from czgram import __version__
        top = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(top, "packaging", "arch", "PKGBUILD")) as f:
            self.assertIn("pkgver=%s\n" % __version__, f.read())


if __name__ == "__main__":
    unittest.main()
