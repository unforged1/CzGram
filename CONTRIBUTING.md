# Contributing to CzGram

Thanks for helping. Bug reports, new grammar rules, OCR fixes and ports are all welcome.

## Before you start

- **Bugs and ideas:** open an issue using the templates. Search first, since someone may already have reported it.
- **Security problems:** don't open a public issue. Follow [SECURITY.md](SECURITY.md).
- **Larger changes** such as a new detection mode, a new platform or a new AI service: open an issue first, so we
  can agree on the approach before you write the code.

## Which branch

| Branch | What's on it | Open pull requests against it for |
| --- | --- | --- |
| `main` | The Debian/Ubuntu version, the default | Anything that applies everywhere |
| `arch-based` | `main` plus the Arch Linux `PKGBUILD` | Arch packaging |
| `rpm-based` | `arch-based` plus the RPM spec for Fedora, RHEL and openSUSE | RPM packaging |
| `macos` | `arch-based` plus the macOS port and its CI | macOS code and the macOS installer |
| `windows` | `main` plus the Windows port and its CI (experimental; may be dropped) | Windows code and the Windows installer |
| `experimental` | Work in progress | Only when asked |

Fixes to shared code go to `main`. The maintainer carries them to the other branches.

## Running from source

You need Python 3.9 or later, Tk, Pillow and Tesseract with Czech data. On Debian or Ubuntu:

```bash
sudo apt install python3-tk python3-pil python3-gi tesseract-ocr tesseract-ocr-ces
```

On Arch, install `tk python-pillow python-gobject tesseract tesseract-data-ces`. On macOS, use the install script on
the `macos` branch. On Windows, run `packaging\windows\install.ps1` on the `windows` branch once for Tesseract and the
Czech data, then `py -m czgram` from the repository folder. Then, from the repository folder:

```bash
python3 -m czgram
```

## Tests

Every change needs the tests to pass:

```bash
python3 -m unittest discover -s tests
```

Add a test for what you fixed or added. If you touch OCR or the analyzer, also run the benchmarks and say in your
pull request whether the numbers changed:

```bash
python3 tests/render_sz.py
```

```bash
python3 tests/render_caps.py
```

## Code guidelines

- **Standard library first.** The bar stays small in memory, so heavy imports (the AI SDKs, GObject) live in
  short-lived child processes. Don't add new dependencies without discussing it.
- **Grammar rules must be correct.** Cite the rule (for example from the Internetová jazyková příručka) in your
  pull request. A rule that only gives the general rule is better than one that guesses an answer.
- **Never click for the user.** CzGram only reads and explains. Pull requests that answer, click or submit
  exercises automatically won't be accepted.
- **Treat everything on screen as untrusted.** Page text, OCR output and AI answers are data, never instructions or
  code. Keep secrets out of logs and error messages.
- **Keep both languages in step.** User-facing explanations exist in English and Czech.
- **Keep the packages in step.** On the `arch-based` and `macos` branches, files are installed through
  `packaging/stage.sh`, which both the Debian and Arch packages use. On `main`, `packaging/build_deb.sh` installs them.

## Commits and pull requests

- One topic per pull request, with a short description of what changed and why.
- Write commit messages in the imperative ("Fix s/z repair for slz"), with detail in the body when it helps.
- Never commit API keys, `~/.config/czgram/config.json`, usage files, screenshots of real accounts or SSH keys.
  `.gitignore` covers the usual ones, but check `git status` before you commit.

By contributing, you agree that your work is released under the project's [MIT license](LICENSE), and you agree to
follow the [code of conduct](CODE_OF_CONDUCT.md).
