---
name: vibeoff
description: Disable Vibe auto-delegate mode — coding tasks are handled by Claude directly unless /vibe is explicitly invoked.
license: MIT
user-invocable: true
allowed-tools:
  - Bash
---

# /vibeoff

Run: `rm -f ~/.local/share/vibe-auto.flag`

Then confirm: "Auto-vibe OFF — Claude will handle coding tasks directly."
