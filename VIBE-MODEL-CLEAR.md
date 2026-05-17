---
name: vibe-model-clear
description: Remove the Vibe model override and return to the config default (deepseek-flash).
user-invocable: true
allowed-tools:
  - bash
---

Run: `rm -f ~/.local/share/vibe-model.flag`

Then reply: "Model override cleared — vibe will use deepseek-flash (config default)."
