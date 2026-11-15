#!/bin/bash
# Removes CzGram from macOS. Your settings stay in ~/.config/czgram unless you delete them.
set -u
BREW=$(brew --prefix 2>/dev/null || echo /opt/homebrew)
[ -x "$BREW/bin/czgram" ] && "$BREW/bin/czgram" --restore-shortcut
rm -f "$BREW/bin/czgram"
rm -rf "$HOME/Applications/CzGram.app" "$HOME/Library/Application Support/CzGram"
find "$HOME/Library/Application Support" -path "*NativeMessagingHosts/cz.czgram.bridge.json" -delete 2>/dev/null
echo "CzGram is removed. To delete settings and token counts too: rm -rf ~/.config/czgram ~/.local/state/czgram"
