# CzGram
CzGram is an AI-powered tool for solving Czech grammar tasks. The tesseract is filled with rules and examples. OCR reading, source code reading and manual selection are all supported, the method of usage can be changed in the config. CzGram also supports AI answers that come from either your Claude account/API key, or a self hosted AI.


Press **PrintScreen** while solving Czech grammar. CzGram finds gaps (`b_dlí`, `Vidím ___ psa`,
`(mě/mně)`) and Czech questions on screen, and a small bar at the top of the screen shows the
rule, with an animated mascot explaining it.

## Install

```bash
sudo apt install ./dist/czgram_1.8.0~exp1_all.deb
```

Then open **CzGram** from the applications menu (or run `czgram`), choose your settings and press **Save**.

On GNOME and XFCE, saving replaces the desktop's PrintScreen shortcut. To get it back, untick the option
in settings or run the command below. **Run this before uninstalling**, because the shortcut is a per-user
setting that package removal can't reach:

```bash
czgram --restore-shortcut
```

## Settings

| Option | What it does |
| --- | --- |
| Screenshot (OCR) | Reads the screen with Tesseract. |
| Switch to page code automatically | Reads the page's HTML if the screenshot can't be read or has no exercise in it. |
| Page code (HTML) | Reads the active browser tab directly. Falls back to the screenshot if no browser answers. |
| Selected word (manual) | Explains the word you highlighted. See below. |
| Quick mode | Reads the page continuously and answers each new question. See below. |
| Speed mode | Blue look and instant text with Opus or Fable. See below. |
| Minimize RAM usage | Closes the bar when dismissed and skips 2x OCR upscaling. |
| Claude mascot | Animated, typed-out explanation. Click it to skip the animation. |
| Language | Explanations in English or Czech. |
| AI answers | Optional, off by default. Gives a specific answer in place of the general rule, through your Claude plan, an Anthropic key or another provider. |

## Manual mode

Choose **Selected word (manual)** in settings, highlight a word with the mouse in any app, and press PrintScreen. CzGram
explains that word, or the whole line if you highlight an exercise line with a gap. No screenshot is taken. In the browser,
with the connector active, it also reads the sentence around the word and gives it to the AI for context. Manual
detection turns quick mode off. Like all AI answers, the highlighted text and sentence go to the service you chose.

## Quick mode

Tick **Quick mode** in settings, then press PrintScreen to turn it on, and again (or ✕) to turn it off. While
it's on, the mascot looks busy, the bar reads the active tab's HTML about twice a second, and each new question
gets an answer on its own: from your AI service if AI answers are on, otherwise from the offline rules.

It only reads the page. It never clicks or types, so you choose every answer. It recognises the question and answer
buttons on the Umíme sites, and an already answered question costs no further requests. Elsewhere it uses the general
page reader. Offline suggestions can be wrong on harder levels, so use AI answers where a mistake costs you progress.

Answers with long vowels (`í`, `ý`) are matched exactly, and any extra word or sentence beside the question is shown in
the bar and given to the AI, because it can change which rule applies. The offline rules can't weigh that kind of note or
pick a vowel length when both are offered, so they tell you to check. AI answers handle these cases better.

After installing this version, reload the extension once: press Reload on it in `chrome://extensions`, or load it again
in Firefox. Quick mode can't tell questions from answers with the older extension.

## Page code: the browser connector

Reading HTML needs a small extension, added once. The app's settings can open its folder
(`/usr/share/czgram/extension`). Save settings first: that registers the connector with your browsers.

- **Chromium, Chrome, Brave:** `chrome://extensions` → Developer mode → Load unpacked → the `chromium` folder.
- **Firefox:** `about:debugging` → This Firefox → Load Temporary Add-on → `firefox/manifest.json`.
  Firefox removes temporary add-ons when it restarts; a permanent install requires signing the add-on.

The extension acts only when you press the key, reads only the active tab's visible content, and
sends it only to the local app. It does need permission to read all sites to be able to do that.

## Privacy

Offline by default: screenshots stay in memory and aren't saved. (The Wayland portal writes a file,
which is deleted immediately.) If you turn on AI answers, the recognised text of each item you view is sent
to the service you chose. Only that text is sent, never the image.

## AI answers: three ways to connect

Pick the service and its model under **AI answers** in settings. Each service remembers its own model.

The AI works out what each exercise tests by itself. CzGram adds a rule only when the gap's own text calls for it:
the listed-words row for the letter before an i/y gap, the s/z rules for an s/z choice, the capitals rules for a
V/v choice. This keeps a lookup to about 960 input tokens through Claude Code, down from about 1,840 in 1.7.

**Your Claude plan, through Claude Code.** No API key or per-lookup charge; lookups count toward your plan's
usage limits. CzGram uses `claude` from your PATH, or else the copy inside the Claude desktop app. Press
**Sign in** in settings once; this signs Claude Code in separately from the desktop app. **Load models** asks
Claude Code what your plan offers, without using any quota. Lookups run at low effort. Each one starts
Claude Code, so it's slower and briefly uses far more memory than the offline rules. It runs with no tools, MCP
servers or settings, in an empty folder, so text on your screen can't make it do anything except answer.

**An Anthropic API key.** Billed per use from console.anthropic.com. Needs `sudo apt install python3-anthropic`.
If the key field is empty, the SDK's usual credentials such as `ANTHROPIC_API_KEY` are used instead.

**Another provider.** Anything with an OpenAI-compatible API (`/chat/completions`, ideally `/models`), such as
[FreeLLMAPI](https://github.com/tashfeenahmed/freellmapi), Groq, OpenRouter or a local server. Enter its address,
for example `http://localhost:3001/v1` for FreeLLMAPI, and its key (FreeLLMAPI's unified key comes from its
dashboard; not the upstream provider keys). Then press **Load models**. Recognised text goes to that provider
under its own privacy terms. A free-tier proxy may pass it on to several upstream companies, so don't use one for
anything private. An `http://` address that isn't on this computer isn't encrypted, and settings warns about it.

Keys are stored in `~/.config/czgram/config.json`, readable only by you.

## Speed mode

Tick **Speed mode** in settings. When the selected model is Opus or Fable, on any connection, the bar turns blue, the mascot
catches blue fire and runs, and answers appear at once instead of being typed out. With the `default` Claude model, the look
switches on once Claude reports which model it's using. It changes the look and the text speed, not how fast the model answers.

## Tracking Claude tokens

Settings shows the tokens CzGram's Claude lookups have used today, over 7 days and overall. The bar shows each answer's count,
and `czgram --usage` gives a breakdown by model. The numbers are the ones Claude reports, kept in
`~/.local/state/czgram/usage.json`, which holds only numbers. Other providers aren't counted. It covers CzGram only, so it
won't match your plan's overall usage, and it can't show how much of your plan's limit remains. Thinking tokens are part of output.

## Prefixes and prepositions (s/z/vz, z/ze, s/se)

Offline, CzGram suggests a prefix only for common words where one prefix is standard (smíchat, zmrznout, vzkvétat).
Where the meaning decides, as with sletět (fly down) and vzlétnout (fly up), it gives the rule instead. For the
prepositions s and z it reads the case from the next word's ending when the ending is clear (s kamarádem, z domů),
and it picks se/ze before s, š, z, ž and in set phrases like se mnou. OCR often reads these choices wrongly (`slz`,
`zíze`, `(2/ze)`), and CzGram repairs them, leaving real words such as *slz* (tears) alone. AI answers get a short
version of these rules when the gap is an s/z choice.

## Capital letters (velká písmena), experimental

CzGram recognises capital-letter exercises: choices like `(V/v)ltava` or `V/vánoce`, buttons with the two letters
or with "velké / malé", and single highlighted words in manual mode. Offline it decides the common cases: the start
of a sentence, days and months, languages, inhabitants and nationalities, holidays, well-known places, possessive
adjectives from names (Karlův most) and adjectives from places (pražský). Where the meaning decides, as with
Země (the planet) and země (soil), it says so instead of guessing. OCR often misreads these choices (`(Č/čJech`,
`(Kik)arlův`, `Vývánoce`) and CzGram repairs them. AI answers get a short version of these rules when the gap is a
capital-letter choice.

## Limits

- Offline answers are rule-based hints. A suggested letter comes only from a spelling rule that
  decides it; endings, cases and agreement get the rule but no answer. Turn on AI answers for specifics.
- The offline listed-words check covers common roots and can miss rare relatives.
- OCR reads the whole screen on Wayland, so other Czech text on screen can show up as items.
- The bar is an X11 window, shown through XWayland on Wayland.

## Development

```bash
python3 -m unittest discover tests
sh packaging/build_deb.sh
```
