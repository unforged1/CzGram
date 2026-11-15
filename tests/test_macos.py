"""macOS code paths that can be checked on any system. The real ones run in macOS CI."""
import os
import plistlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from czgram import capture, install, macos, shortcuts  # noqa: E402


class KeyNames(unittest.TestCase):
    def test_printscreen_becomes_the_mac_shortcut(self):
        with mock.patch.object(macos, "IS_MAC", True):
            self.assertEqual(macos.key_text("Press PrintScreen now"), "Press ⌃⌥G now")
        with mock.patch.object(macos, "IS_MAC", False):
            self.assertEqual(macos.key_text("Press PrintScreen now"), "Press PrintScreen now")


class LaunchAgent(unittest.TestCase):
    def test_plist(self):
        data = plistlib.loads(macos.agent_plist(["/opt/homebrew/bin/czgram", "--hotkey-daemon"], "/opt/homebrew/bin:/usr/bin"))
        self.assertEqual(data["Label"], "cz.czgram.hotkey")
        self.assertEqual(data["ProgramArguments"], ["/opt/homebrew/bin/czgram", "--hotkey-daemon"])
        self.assertTrue(data["RunAtLoad"])
        self.assertFalse(data["KeepAlive"])  # a taken hotkey mustn't restart in a loop
        self.assertEqual(data["LimitLoadToSessionType"], "Aqua")

    def test_settings_install_and_remove_the_agent(self):
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(install, "install_native_host"), \
                mock.patch.object(macos, "install_agent", return_value=(True, "⌃⌥G and F13 are set")) as add, \
                mock.patch.object(macos, "remove_agent", return_value=(True, "⌃⌥G is free again")) as rm:
            self.assertEqual(install.apply({"bind_printscreen": True}), [(True, "⌃⌥G and F13 are set.")])
            self.assertEqual(add.call_args[0][0][-1], "--hotkey-daemon")
            self.assertEqual(install.apply({"bind_printscreen": False}), [(True, "⌃⌥G is free again.")])
            rm.return_value = (True, "nothing to restore")
            self.assertEqual(install.apply({"bind_printscreen": False}), [])

    def test_restore_shortcut_removes_the_agent(self):
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(macos, "remove_agent", return_value=(True, "⌃⌥G is free again")):
            self.assertEqual(shortcuts.restore(), (True, "⌃⌥G is free again"))


class Paths(unittest.TestCase):
    def test_browser_hosts_live_in_application_support(self):
        with mock.patch.object(sys, "platform", "darwin"):
            dirs = install.native_host_dirs()
        support = os.path.expanduser("~/Library/Application Support")
        self.assertIn(os.path.join(support, "Google/Chrome", "NativeMessagingHosts"), dirs["chromium"])
        self.assertEqual(dirs["firefox"], [os.path.join(support, "Mozilla", "NativeMessagingHosts")])

    def test_capture_uses_screencapture(self):
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(capture, "_capture_macos", return_value=b"pgm") as mac:
            self.assertEqual(capture.capture(), b"pgm")
            mac.assert_called_once()

    def test_package_hints(self):
        from czgram import distro
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(distro.family(), "macos")
            self.assertIn("tesseract-lang", distro.pkg("tesseract-ocr-ces"))


@unittest.skipUnless(sys.platform == "darwin", "needs macOS")
class OnMac(unittest.TestCase):
    def test_hotkeys_register(self):
        lib, refs, _cb = macos.register_hotkeys(lambda: None)
        self.assertEqual(len(refs), 2)
        for ref in refs:
            lib.UnregisterEventHotKey(ref)


if __name__ == "__main__":
    unittest.main()
