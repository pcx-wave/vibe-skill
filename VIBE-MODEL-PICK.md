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

If no alias is provided, first read the available models from `~/.vibe/config.toml`:

```bash
python3 -c "
import tomllib, os
with open(os.path.expanduser('~/.vibe/config.toml'), 'rb') as f:
    cfg = tomllib.load(f)
active = cfg.get('active_model', '')
for m in cfg.get('models', []):
    alias = m.get('alias', m.get('name', ''))
    provider = m.get('provider', '')
    note = ' (current default)' if alias == active else ''
    print(f'{alias}|{provider}{note}')
"
```

Then use AskUserQuestion with a single-select question built from that output:
- Question: "Which Vibe model do you want to use?"
- One option per line: label = alias, description = provider + note

Then write the selected alias to the flag file and confirm.
