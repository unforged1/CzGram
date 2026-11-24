# CzGram 2.1.1: setup note

CzGram is a Czech grammar helper. Press PrintScreen while solving an exercise, and a small bar at the top of the screen shows the rule for what it finds. It can also suggest an answer.

This is an early test version. It has only been tested on one computer (Kali Linux with GNOME), so something may not work on yours.

## Before you start

- You need Debian, Ubuntu or a similar system.
- Saving the settings replaces your PrintScreen shortcut on GNOME and XFCE. You can undo this (see "Removing it").
- On other desktops, such as KDE, set up the key yourself: add a keyboard shortcut for PrintScreen that runs `czgram --trigger`.

## Install

Open a terminal in the folder holding the file, then run:

```bash
sudo apt install ./czgram_2.1.1_all.deb
```

Open **CzGram** from your applications menu, choose your settings and press **Save**.

## Try it

Open a Czech exercise and press **PrintScreen**. The bar appears at the top of the screen. Press ✕ to close it.

By default, everything stays on your computer and you get general rules. The first screenshot may ask for permission or take a few seconds.

## Ways to detect exercises

- **Screenshot:** reads the screen. This is the default and needs no extra setup.
- **Page code:** reads the browser tab directly. It needs the browser extension below.
- **Selected word (manual):** highlight a word in any app, then press PrintScreen.
- **Quick mode:** keeps reading the page and looks up each new question by itself. It needs the browser extension, and you still click the answers.
- **Bulk mode:** when a page holds a whole set of questions, the bar offers to answer them all in one request. Double-tap **Alt** in the browser to accept (the bar's white button names the key; you can change it in settings). Each answer appears as you answer the one before. It needs the browser extension.

## Browser extension (optional)

Only add this if you want page code or quick mode. Save your settings first, because that connects CzGram to your browsers.

- **Chromium, Chrome or Brave:** go to `chrome://extensions`, turn on Developer mode, press **Load unpacked** and choose `/usr/share/czgram/extension/chromium`.
- **Firefox:** go to `about:debugging`, then **This Firefox**, press **Load Temporary Add-on** and choose `/usr/share/czgram/extension/firefox/manifest.json`. Firefox removes it when it restarts.

The extension can read any site you have open, but only when CzGram asks. Any other program running under your account could also ask it for the active tab, including a banking page. If that bothers you, skip it or remove it when you're done.

## AI answers (optional)

These are off by default. Turn them on under **AI answers** and choose one connection:

- **Your Claude plan:** press **Sign in** and use your own Claude account. Lookups count toward your plan's limits.
- **Anthropic API key:** billed per use. First run `sudo apt install python3-anthropic`.
- **Another provider:** any OpenAI-compatible service. Enter its address and key, then press **Load models**.

With AI answers on, the recognised text of each item you view goes to the service you chose, under its privacy terms. Free services and proxies may pass it on to other companies, so don't use them for anything private. API keys are stored unencrypted in `~/.config/czgram/config.json`, in a file only your account can read.

## Good to know

- Answers can be wrong, both the offline hints and the AI's, so check them when a mistake matters.
- If you use this on graded work, check what your school allows.
- `czgram --usage` shows how many Claude tokens CzGram has used.

## Removing it

Run these in order. The first one matters, because otherwise your PrintScreen key will stop doing anything:

```bash
czgram --restore-shortcut
```

```bash
sudo apt remove czgram
```

Then remove the browser extension if you added it. To also delete your settings, API keys and token counts:

```bash
rm -rf ~/.config/czgram ~/.local/state/czgram
```

## If something goes wrong

Tell whoever sent you this what happened, which Linux and desktop you're using, and what the bar said.
