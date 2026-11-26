# Security policy

CzGram reads your screen and, with the browser connector, your active tab. Security problems matter here, so
thank you for reporting them responsibly.

## Supported versions

The current release is **2.1.3** (browser extension 2.1.0).

| Version | Supported |
| --- | --- |
| 2.1.x (current: 2.1.3) | ✅ Security fixes |
| 2.0.x | ✅ Security fixes |
| 1.9.x | ✅ Security fixes |
| 1.8.x and older | ❌ Update to 2.1.3 |

Fixes are released on every branch that carries the affected code: `main` (Debian and Ubuntu), `arch-based`,
`rpm-based` (Fedora, RHEL and openSUSE), `macos`, and `windows` while the Windows port lasts (it's experimental and
may be dropped). The `experimental` branch is a work-in-progress snapshot and doesn't get fixes. After updating,
reload the browser extension too, since some fixes live there.

## Reporting a vulnerability

**Please don't open a public issue for a security problem.**

Report it privately through GitHub: on the repository's **Security** tab, choose **Report a vulnerability**.
If that button isn't available, contact the maintainer, [@unforged1](https://github.com/unforged1), on GitHub
and ask for a private way to send the details.

Please include:

- the CzGram version (`czgram --version`) and your system (Debian, Arch, Fedora, RHEL, openSUSE, macOS or
  Windows, and your desktop)
- what an attacker can do, and what they need first (a web page you visit, a program running as you, …)
- steps or a proof of concept that shows it
- anything you know about a fix

Leave out real API keys, tokens and personal data, including from screenshots and logs.

## What to expect

- An acknowledgement within 7 days.
- An assessment and a plan within 14 days.
- A fix released as soon as it's ready, with credit in the release notes if you'd like it.

Please give us a chance to release a fix before you publish details.

## What's in scope

- The app: OCR, page reading, the analyzer, the settings window and the bar.
- The browser extension and the native messaging host.
- The AI connections (Claude Code, the Anthropic API and OpenAI-compatible services) and how API keys are stored.
- The Debian, Arch, RPM (Fedora, RHEL, openSUSE) and macOS packages and installers, and the experimental Windows
  installer.

Out of scope: problems in Tesseract, Python, browsers, Claude Code or AI services themselves (report those to their
projects), and attacks that need an account that already has full control of yours, which can read your files anyway.

## Design notes

How CzGram protects keys, pages and local sockets, and what the November 2026 review fixed, is in the
[README's Security section](README.md#security).
