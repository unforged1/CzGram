import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from czgram import distro  # noqa: E402


class Distro(unittest.TestCase):
    """Linux families. The platform is set here, since on a Mac family() is always "macos"."""

    def setUp(self):
        patch = mock.patch.object(distro.sys, "platform", "linux")
        patch.start()
        self.addCleanup(patch.stop)

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


class Mac(unittest.TestCase):
    def test_mac_names_whatever_os_release_says(self):
        with mock.patch.object(distro.sys, "platform", "darwin"):
            self.assertEqual(distro.family("/etc/os-release"), "macos")
            self.assertEqual(distro.pkg("tesseract-ocr-ces"), "tesseract-lang (Homebrew)")
            self.assertEqual(distro.pkg("python3-anthropic"), "anthropic (pip3 install anthropic)")
            self.assertEqual(distro.pkg("something-else"), "something-else")


class ArchPackage(unittest.TestCase):
    def test_pkgbuild_version_matches(self):
        from czgram import __version__
        top = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(top, "packaging", "arch", "PKGBUILD")) as f:
            self.assertIn("pkgver=%s\n" % __version__, f.read())


if __name__ == "__main__":
    unittest.main()
