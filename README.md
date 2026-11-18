<p align="center">
  <img src="docs/banner.png" alt="CzGram: Czech grammar on the PrintScreen key" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.8.0-D97757?style=for-the-badge" alt="Version 1.8.0">
  <img src="https://img.shields.io/badge/Debian%20%7C%20Ubuntu%20%7C%20Kali-supported-A81D33?style=for-the-badge&logo=debian&logoColor=white" alt="Debian-based: supported">
  <img src="https://img.shields.io/badge/Arch%20%7C%20Manjaro%20%7C%20EndeavourOS-supported-1793D1?style=for-the-badge&logo=archlinux&logoColor=white" alt="Arch-based: supported">
  <img src="https://img.shields.io/badge/macOS-experimental-999999?style=for-the-badge&logo=apple&logoColor=white" alt="macOS: experimental">
  <img src="https://img.shields.io/badge/license-MIT-4FA8FF?style=for-the-badge" alt="MIT license">
</p>

<p align="center">
  <b>Press PrintScreen while solving Czech grammar. CzGram finds the gap, names the rule, and an animated mascot explains it.</b>
</p>

---

CzGram is an AI-powered helper for Czech grammar exercises. Its offline rulebook is filled with rules and examples, and it
reads exercises from a screenshot (OCR with Tesseract), straight from the page's HTML, or from a word you highlight. You
pick the method in settings. It can also ask an AI for a specific answer: through your Claude account, an Anthropic API
key, or any OpenAI-compatible provider, including a self-hosted one.

## ✨ Features

| Feature | What it does |
| --- | --- |
| 📸 **Screenshot OCR** | Finds gaps like `b_dlí`, `Vidím ___ psa` and `(mě/mně)` anywhere on screen. |
| 🌐 **Page reading** | Reads the browser tab's HTML directly, with automatic fallback either way. |
| 🖱️ **Manual mode** | Highlight any word and press PrintScreen to get the rule behind it. |
| ⚡ **Quick mode** | Watches the page and answers each new question as it appears. It never clicks for you. |
| 📚 **Offline rules** | Listed words (vyjmenovaná slova), hard/soft consonants, s/z/vz, z/ze, s/se, capital letters and more. |
| 🤖 **AI answers** | Optional. Your Claude plan, an Anthropic key, or another provider, at about 960 input tokens per lookup. |
| 🔥 **Speed mode** | With Opus or Fable the bar turns blue and the mascot catches fire and runs. |
| 🔢 **Token tracking** | See what CzGram's Claude lookups have used today, this week and overall. |

## 🐧 Supported systems

| System | Status | How to install |
| --- | --- | --- |
| <img src="https://cdn.simpleicons.org/debian/A81D33" width="16"> **Debian**, **Ubuntu**, **Kali**, Linux Mint, Pop!_OS | ✅ Supported, `.deb` package | [Debian-based](#install-debian) |
| <img src="https://cdn.simpleicons.org/archlinux/1793D1" width="16"> **Arch Linux**, **Manjaro**, **EndeavourOS**, Garuda | ✅ Supported, `PKGBUILD` | [Arch-based](#install-arch) |
| <img src="https://cdn.simpleicons.org/apple/999999" width="16"> **macOS** 11 or later (Apple silicon and Intel) | 🧪 Experimental, `macos` branch | [macOS](#install-macos) |
| Fedora, openSUSE and other Linux | ⚠️ No package yet | Not tested |
| Windows | ❌ Not supported | |

Tested on Kali Linux with GNOME, and in an Arch Linux container (build, install, offline OCR and all tests).

| Desktop | PrintScreen key | Screenshots |
| --- | --- | --- |
| GNOME, XFCE | ✅ Set up for you when you save settings | ✅ |
| KDE Plasma, Hyprland, Sway, Cinnamon, others | 🛠️ Add a shortcut that runs `czgram --trigger` | ✅ X11 directly, Wayland through `xdg-desktop-portal` |
| macOS | ✅ **⌃⌥G** (Control-Option-G), or F13 on extended keyboards | ✅ After you allow Screen Recording |

## 📦 Install

<a id="install-debian"></a>

### <img src="https://cdn.simpleicons.org/debian/A81D33" width="20"> Debian, Ubuntu, Kali and similar

```bash
git clone https://github.com/unforged1/CzGram.git
```

```bash
cd CzGram && sh packaging/build_deb.sh
```

```bash
sudo apt install ./dist/czgram_1.8.0_all.deb
```

Building needs `dpkg-deb` and `python3-pil`, which most Debian-based systems already have.

<a id="install-arch"></a>

### <img src="https://cdn.simpleicons.org/archlinux/1793D1" width="20"> Arch Linux, Manjaro, EndeavourOS and similar

The Arch package lives on the `arch-based` branch. You need `git` and `base-devel` (`sudo pacman -S --needed git base-devel`).

```bash
git clone -b arch-based https://github.com/unforged1/CzGram.git
```

```bash
cd CzGram/packaging/arch && makepkg -si
```

`makepkg -si` builds the package, installs every dependency from the official repositories (including
`tesseract-data-ces` for Czech) and installs CzGram with pacman. Optional extras:

| Package | For |
| --- | --- |
| `python-anthropic` | AI answers through an Anthropic API key |
| `xdg-desktop-portal` + your desktop's backend | Screenshots on Wayland |
| `xdg-utils` | Opening links from the settings window |

To update later, run `git pull` in the `CzGram` folder, then `makepkg -si` again in `packaging/arch`.

<a id="install-macos"></a>

### <img src="https://cdn.simpleicons.org/apple/999999" width="20"> macOS (experimental)

The macOS port lives on the `macos` branch. You need [Homebrew](https://brew.sh); the script installs Python, Tk,
Pillow and Tesseract with it, adds the Czech OCR data, and creates `~/Applications/CzGram.app` and a `czgram` command.

```bash
git clone -b macos https://github.com/unforged1/CzGram.git
```

```bash
cd CzGram && bash packaging/macos/install.sh
```

Macs have no PrintScreen key, so CzGram uses **⌃⌥G** (Control-Option-G), and F13 where your keyboard has one.
macOS asks for two permissions under **System Settings → Privacy & Security**:

| Permission | Needed for |
| --- | --- |
| Screen Recording | Reading the screen. Without it, screenshots show only the desktop background. |
| Accessibility | Selected word (manual) mode only: CzGram copies your selection with ⌘C. |

To remove it, run `bash packaging/macos/uninstall.sh`.

### 🚀 First start

Open **CzGram** from the applications menu (or run `czgram`), choose your settings and press **Save**. Then open a Czech
exercise and press **PrintScreen**. The bar appears at the top of the screen; press ✕ to close it.

> [!IMPORTANT]
> On GNOME and XFCE, saving replaces the desktop's PrintScreen shortcut. To get it back, untick the option in settings
> or run the command below. **Run it before uninstalling**, because the shortcut is a per-user setting that package
> removal can't reach.
>
> ```bash
> czgram --restore-shortcut
> ```

Uninstall with `sudo apt remove czgram` (Debian-based), `sudo pacman -R czgram` (Arch-based) or
`bash packaging/macos/uninstall.sh` (macOS).

## ⚙️ Settings

| Option | What it does |
| --- | --- |
| Screenshot (OCR) | Reads the screen with Tesseract. |
| Switch to page code automatically | Reads the page's HTML if the screenshot can't be read or has no exercise in it. |
| Page code (HTML) | Reads the active browser tab directly. Falls back to the screenshot if no browser answers. |
| Selected word (manual) | Explains the word you highlighted. |
| Quick mode | Reads the page continuously and answers each new question. |
| Speed mode | Blue look and instant text with Opus or Fable. |
| Minimize RAM usage | Closes the bar when dismissed and skips 2x OCR upscaling. |
| Claude mascot | Animated, typed-out explanation. Click it to skip the animation. |
| Language | Explanations in English or Czech. |
| AI answers | Optional, off by default. Gives a specific answer in place of the general rule. |

## 🧭 Modes

<details>
<summary><b>🖱️ Manual mode</b>: highlight a word, press PrintScreen</summary>

Choose **Selected word (manual)** in settings, highlight a word with the mouse in any app, and press PrintScreen. CzGram
explains that word, or the whole line if you highlight an exercise line with a gap. No screenshot is taken. In the browser,
with the connector active, it also reads the sentence around the word and gives it to the AI for context. Manual
detection turns quick mode off. Like all AI answers, the highlighted text and sentence go to the service you chose.
</details>

<details>
<summary><b>⚡ Quick mode</b>: answers each new question by itself</summary>

Tick **Quick mode** in settings, then press PrintScreen to turn it on, and again (or ✕) to turn it off. While
it's on, the mascot looks busy, the bar reads the active tab's HTML about twice a second, and each new question
gets an answer on its own: from your AI service if AI answers are on, otherwise from the offline rules.

It only reads the page. It never clicks or types, so you choose every answer. It recognises the question and answer
buttons on the Umíme sites, and an already answered question costs no further requests. Elsewhere it uses the general
page reader. Offline suggestions can be wrong on harder levels, so use AI answers where a mistake costs you progress.

Answers with long vowels (`í`, `ý`) are matched exactly, and any extra word or sentence beside the question is shown in
the bar and given to the AI, because it can change which rule applies. The offline rules can't weigh that kind of note or
pick a vowel length when both are offered, so they tell you to check. AI answers handle these cases better.

After installing a new version, reload the extension once: press Reload on it in `chrome://extensions`, or load it again
in Firefox.
</details>

<details>
<summary><b>🔥 Speed mode</b>: blue bar, running mascot</summary>

Tick **Speed mode** in settings. When the selected model is Opus or Fable, on any connection, the bar turns blue, the mascot
catches blue fire and runs, and answers appear at once instead of being typed out. With the `default` Claude model, the look
switches on once Claude reports which model it's using. It changes the look and the text speed, not how fast the model answers.
</details>

## 🌐 Page code: the browser connector

Reading HTML needs a small extension, added once. The app's settings can open its folder
(`/usr/share/czgram/extension`). Save settings first: that registers the connector with your browsers.

- **Chromium, Chrome, Brave:** `chrome://extensions` → Developer mode → Load unpacked → the `chromium` folder.
- **Firefox:** `about:debugging` → This Firefox → Load Temporary Add-on → `firefox/manifest.json`.
  Firefox removes temporary add-ons when it restarts; a permanent install requires signing the add-on.

The extension acts only when CzGram asks, reads only the active tab's visible content, and sends it only to the local app.
It does need permission to read all sites to be able to do that. It never reads password, card, one-time-code or hidden
fields, and it sends at most 1 MB per page.

## 🤖 AI answers: three ways to connect

Pick the service and its model under **AI answers** in settings. Each service remembers its own model.

The AI works out what each exercise tests by itself. CzGram adds a rule only when the gap's own text calls for it:
the listed-words row for the letter before an i/y gap, the s/z rules for an s/z choice, the capitals rules for a
V/v choice. This keeps a lookup to about 960 input tokens through Claude Code, down from about 1,840 in 1.7.

| Connection | Cost | Setup |
| --- | --- | --- |
| **Your Claude plan** (through Claude Code) | Counts toward your plan's limits | Press **Sign in** in settings |
| **Anthropic API key** | Billed per use | `python3-anthropic` (Debian) or `python-anthropic` (Arch) |
| **Another provider** (OpenAI-compatible) | Depends on the provider | Enter its address and key, press **Load models** |

<details>
<summary>More about each connection</summary>

**Your Claude plan, through Claude Code.** No API key or per-lookup charge; lookups count toward your plan's
usage limits. CzGram uses `claude` from your PATH, or else the copy inside the Claude desktop app. Press
**Sign in** in settings once; this signs Claude Code in separately from the desktop app. **Load models** asks
Claude Code what your plan offers, without using any quota. Lookups run at low effort. Each one starts
Claude Code, so it's slower and briefly uses far more memory than the offline rules. It runs with no tools, MCP
servers or settings, in an empty folder, so text on your screen can't make it do anything except answer.

**An Anthropic API key.** Billed per use from console.anthropic.com. If the key field is empty, the SDK's usual
credentials such as `ANTHROPIC_API_KEY` are used instead.

**Another provider.** Anything with an OpenAI-compatible API (`/chat/completions`, ideally `/models`), such as
[FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi), Groq, OpenRouter or a local server. Enter its address,
for example `http://localhost:3001/v1` for FreeLLMAPI, and its key (FreeLLMAPI's unified key comes from its
dashboard; not the upstream provider keys). Then press **Load models**. Recognised text goes to that provider
under its own privacy terms. A free-tier proxy may pass it on to several upstream companies, so don't use one for
anything private. An `http://` address that isn't on this computer isn't encrypted, and settings warns about it.

Keys are stored in `~/.config/czgram/config.json`, readable only by you.
</details>

### 🔢 Tracking Claude tokens

Settings shows the tokens CzGram's Claude lookups have used today, over 7 days and overall. The bar shows each answer's count,
and `czgram --usage` gives a breakdown by model. The numbers are the ones Claude reports, kept in
`~/.local/state/czgram/usage.json`, which holds only numbers. Other providers aren't counted. It covers CzGram only, so it
won't match your plan's overall usage, and it can't show how much of your plan's limit remains. Thinking tokens are part of output.

## 📚 Grammar topics

<details>
<summary><b>Prefixes and prepositions</b> (s/z/vz, z/ze, s/se)</summary>

Offline, CzGram suggests a prefix only for common words where one prefix is standard (smíchat, zmrznout, vzkvétat).
Where the meaning decides, as with sletět (fly down) and vzlétnout (fly up), it gives the rule instead. For the
prepositions s and z it reads the case from the next word's ending when the ending is clear (s kamarádem, z domů),
and it picks se/ze before s, š, z, ž and in set phrases like se mnou. OCR often reads these choices wrongly (`slz`,
`zíze`, `(2/ze)`), and CzGram repairs them, leaving real words such as *slz* (tears) alone. AI answers get a short
version of these rules when the gap is an s/z choice.
</details>

<details>
<summary><b>Capital letters</b> (velká písmena), new in 1.8</summary>

CzGram recognises capital-letter exercises: choices like `(V/v)ltava` or `V/vánoce`, buttons with the two letters
or with "velké / malé", and single highlighted words in manual mode. Offline it decides the common cases: the start
of a sentence, days and months, languages, inhabitants and nationalities, holidays, well-known places, possessive
adjectives from names (Karlův most) and adjectives from places (pražský). Where the meaning decides, as with
Země (the planet) and země (soil), it says so instead of guessing. OCR often misreads these choices (`(Č/čJech`,
`(Kik)arlův`, `Vývánoce`) and CzGram repairs them. AI answers get a short version of these rules when the gap is a
capital-letter choice.
</details>

## 🔒 Privacy

Offline by default: screenshots stay in memory and aren't saved. (The Wayland portal writes a file,
which is deleted immediately.) If you turn on AI answers, the recognised text of each item you view is sent
to the service you chose. Only that text is sent, never the image.

## ⚠️ Limits

- Offline answers are rule-based hints. A suggested letter comes only from a spelling rule that
  decides it; endings, cases and agreement get the rule but no answer. Turn on AI answers for specifics.
- The offline listed-words check covers common roots and can miss rare relatives.
- OCR reads the whole screen on Wayland, so other Czech text on screen can show up as items.
- The bar is an X11 window, shown through XWayland on Wayland.
- On macOS, the bar and settings window show a Python icon in the Dock while open, and manual mode replaces
  a non-text clipboard (such as a copied image) when it copies your selection.

## 🛠️ Development

```bash
python3 -m unittest discover tests
```

```bash
sh packaging/build_deb.sh
```

On the `arch-based` branch, the Arch package builds with the command below, and both packages install the same files
through `packaging/stage.sh`.

```bash
cd packaging/arch && makepkg -f
```

## 📄 License

MIT, © 2026 unforged1. See [LICENSE](LICENSE).
