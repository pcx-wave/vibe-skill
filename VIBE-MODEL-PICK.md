---
name: vibe-model-pick
description: Override the Vibe model for all subsequent delegations. Usage: /vibe-model-pick <alias>. Available aliases: deepseek-flash, mistral-medium-3.5, devstral-small, local.
user-invocable: true
allowed-tools:
  - bash
---

Extract the alias from the user's arguments. Then run:

```bash
echo "<alias>" > ~/.local/share/vibe-model.flag
```

Then reply: "Model set to `<alias>` — all vibe delegations will use this model until /vibe-model-clear."

If no alias is provided, list the available aliases and ask the user to pick one:
- `deepseek-flash` — DeepSeek v4 Flash (fast, cheap, config default)
- `mistral-medium-3.5` — Mistral Medium 3.5 (stronger reasoning)
- `devstral-small` — Devstral Small (lighter Mistral model)
- `local` — local llamacpp server on :8080
