---
name: geminioff
description: Disable gemini auto-mode — return to normal Claude behaviour.
user-invocable: true
allowed-tools:
  - bash
---

Run: `rm -f ~/.local/share/gemini-auto.flag`

Then reply: "Auto-gemini OFF — Claude will handle requests normally."
