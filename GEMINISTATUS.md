---
name: geministatus
description: Check whether gemini auto-mode is currently ON or OFF.
user-invocable: true
allowed-tools:
  - bash
---

Run: `test -f ~/.local/share/gemini-auto.flag && echo "Auto-gemini: ON" || echo "Auto-gemini: OFF"`

Report the result to the user.
