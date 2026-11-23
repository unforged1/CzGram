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

    def test_fedora_rhel_and_rebuilds(self):
        for text in ('ID=fedora\n', 'ID="rhel"\nID_LIKE="fedora"\n', 'ID="rocky"\nID_LIKE="rhel centos fedora"\n',
                     'ID="almalinux"\nID_LIKE="rhel centos fedora"\n', 'ID="centos"\nID_LIKE="rhel fedora"\n'):
            path = self.release(text)
            self.assertEqual(distro.family(path), "fedora", text)
            self.assertEqual(distro.pkg("tesseract-ocr-ces", path), "tesseract-langpack-ces")

    def test_opensuse_and_sles(self):
        for text in ('ID="opensuse-tumbleweed"\nID_LIKE="opensuse suse"\n',
                     'ID="opensuse-leap"\nID_LIKE="suse opensuse"\n', 'ID="sles"\nID_LIKE="suse"\n'):
            path = self.release(text)
            self.assertEqual(distro.family(path), "suse", text)
            self.assertEqual(distro.pkg("tesseract-ocr-ces", path), "tesseract-ocr-traineddata-czech")
            self.assertIn("pip install", distro.pkg("python3-anthropic", path))

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




class RpmPackage(unittest.TestCase):
    def test_spec_version_matches(self):
        from czgram import __version__
        top = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(top, "packaging", "rpm", "czgram.spec")) as f:
            self.assertIn("\nVersion:        %s\n" % __version__, f.read())

if __name__ == "__main__":
    unittest.main()
