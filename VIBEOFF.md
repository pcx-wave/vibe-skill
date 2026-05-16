---
name: vibeoff
description: Disable vibe auto-mode — return to normal Claude behaviour.
user-invocable: true
allowed-tools:
  - bash
---

Run: `rm -f ~/.local/share/vibe-auto.flag`

Then reply: "Auto-vibe OFF — Claude will handle requests normally."
