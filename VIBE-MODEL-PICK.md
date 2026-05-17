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

If no alias is provided, use AskUserQuestion with a single-select question:

Question: "Which Vibe model do you want to use?"
Options:
- label: "deepseek-flash", description: "DeepSeek v4 Flash — fast, cheap (config default)"
- label: "mistral-medium-3.5", description: "Mistral Medium 3.5 — stronger reasoning"
- label: "devstral-small", description: "Devstral Small — lighter Mistral model"
- label: "local", description: "Local llamacpp server on :8080"

Then write the selected alias to the flag file and confirm.
