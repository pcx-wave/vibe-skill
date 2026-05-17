---
name: vibestatus
description: Check whether vibe auto-mode is currently ON or OFF, and show active model override.
user-invocable: true
allowed-tools:
  - bash
---

Run both checks and report two lines:

```bash
test -f ~/.local/share/vibe-auto.flag && echo "Auto-vibe: ON" || echo "Auto-vibe: OFF"
if [ -f ~/.local/share/vibe-model.flag ]; then
  echo "Model: $(cat ~/.local/share/vibe-model.flag)  (override)"
else
  echo "Model: deepseek-flash  (config default)"
fi
```
