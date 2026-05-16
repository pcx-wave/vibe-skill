---
name: vibestatus
description: Check whether vibe auto-mode is currently ON or OFF.
user-invocable: true
allowed-tools:
  - bash
---

Run: `test -f ~/.local/share/vibe-auto.flag && echo "Auto-vibe: ON" || echo "Auto-vibe: OFF"`

Report the result to the user.
