"""Command line entry. Imports stay inside each branch so `--trigger` starts fast."""
import sys

USAGE = """usage: czgram [option]
  (no option)          open settings
  --trigger            scan the screen now (what PrintScreen runs)
  --scan-file IMAGE    analyze an image and print the result as JSON
  --restore-shortcut   give PrintScreen back to your desktop
  --usage              print the tokens Claude lookups have used
  --version            print the version
"""


def main(argv):
    cmd = argv[0] if argv else "--config"
    if cmd == "--trigger":
        from . import config
        if not config.exists():
            from . import ui_config
            return ui_config.main()
        from . import ipc
        ipc.trigger()
        return 0
    if cmd == "--bar":
        from . import ui_bar
        return ui_bar.main()
    if cmd == "--config":
        from . import ui_config
        return ui_config.main()
    if cmd == "--hotkey-daemon":
        if sys.platform == "darwin":
            from . import macos
            return macos.run_hotkey_daemon()
        from . import hotkey
        return hotkey.run()
    if cmd == "--scan-file" and len(argv) == 2:
        from . import scan
        return scan.main(argv[1:])
    if cmd == "--restore-shortcut":
        from . import shortcuts
        ok, msg = shortcuts.restore()
        print(msg)
        return 0 if ok else 1
    if cmd == "--usage":
        from . import usage
        print(usage.report())
        return 0
    if cmd == "--version":
        from . import __version__
        print("czgram", __version__)
        return 0
    sys.stderr.write(USAGE)
    return 0 if cmd in ("-h", "--help") else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
