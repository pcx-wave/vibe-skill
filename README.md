<!-- Suggested GitHub topics: claude-code, llm-tools, mistral, gemini-cli, ai-coding, shell, developer-tools, vibe-coding -->

# vibe-skill

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg) ![Shell](https://img.shields.io/badge/language-Shell-green.svg) ![GitHub stars](https://img.shields.io/github/stars/pcx-wave/vibe-skill?style=social) ![Claude Code skill](https://img.shields.io/badge/-Claude%20Code%20skill-CC785C)

**Claude orchestrates. Vibe does the heavy lifting. You review the diff, save tokens, costs and avoid hitting limits!**

Claude sees only ~500–1500 tokens per run regardless of how many file reads Vibe performs internally — massive savings on exploratory and implementation tasks.

Note that Vibe works natively with Mistral models which are capable and significantly cheaper than Claude, but Vibe can also be configured to use any other provider/model instead. Eg you can use a deepseek model with vibe tooling. 

Summary:
1. User types `/vibe <instruction>` in Claude Code
2. Claude decomposes the task and writes a prompt
3. `vibe-delegate` runs Mistral Vibe in a pseudo-TTY
4. The delegate reports tool calls, token counts, and `git diff --stat`
5. Claude reviews the diff and summarizes the result

---

## Why

**Cost savings** — Vibe's file reads and edits consume cheap delegate tokens (or whatever model you configure), not Claude tokens:

| Scenario | Claude Sonnet 4.6 | Mistral Medium 3.5 | DeepSeek V4 Flash |
|----------|-------------------|--------------------|-------------------|
| Simple 1-file tweak (800 tokens) | ~$0.004 | ~$0.002 | ~$0.0001 |
| 6-read implementation task (4,800 tokens) | ~$0.023 | ~$0.012 | ~$0.0008 |
| Complex multi-file refactor (12,000 tokens) | ~$0.058 | ~$0.029 | ~$0.002 |

> Costs based on official pricing (May 2026): Claude $3/$15 per M tokens, Mistral Medium 3.5 $1.50/$7.50, DeepSeek V4 Flash $0.14/$0.28. Assumes ~85% input / 15% output, typical for coding tasks. Claude orchestration overhead: ~500 tokens per run (negligible).

**Context window protection** — On long coding sessions, every file read, function body, and debug loop burns Claude's context. Delegating to Vibe keeps that budget free. Claude enters the task, hands off, and comes back only to review the result — no context bleed from Vibe's internal turns.

**Built-in quality gate** — Claude doesn't just fire and forget. After each Vibe run, Claude reads the `git diff`, checks for syntax errors, and summarizes what changed before reporting back to you. You get a second pair of eyes on every delegation without lifting a finger.

---

## Prerequisites

- [Mistral Vibe](https://vibe.mistral.ai/) CLI installed and authenticated (`vibe --version`)
- [Claude Code](https://claude.ai/code) with skills enabled
- `script` command available (GNU/Linux or BSD/macOS variant)
- `timeout` command available; on macOS install GNU coreutils for `gtimeout` (or ensure your chosen `timeout` fallback is set up)
- `python3` and optionally `node` for syntax checks
- A git repository to work in

---

## Installation

```bash
git clone https://github.com/pcx-wave/vibe-skill.git && cd vibe-skill && mkdir -p ~/tools ~/.claude/skills/vibe ~/.claude/skills/vibeon ~/.claude/skills/vibeoff ~/.claude/skills/vibestatus ~/.claude/skills/vibe-model-pick ~/.claude/skills/vibe-model-clear ~/.claude/skills/geminion ~/.claude/skills/geminioff ~/.claude/skills/geministatus && ln -sf "$(pwd)/tools/vibe-delegate" ~/tools/vibe-delegate && ln -sf "$(pwd)/tools/delegate-report" ~/tools/delegate-report && chmod +x ~/tools/vibe-delegate ~/tools/delegate-report && ln -sf "$(pwd)/SKILL.md" ~/.claude/skills/vibe/SKILL.md && ln -sf "$(pwd)/VIBEON.md" ~/.claude/skills/vibeon/SKILL.md && ln -sf "$(pwd)/VIBEOFF.md" ~/.claude/skills/vibeoff/SKILL.md && ln -sf "$(pwd)/VIBESTATUS.md" ~/.claude/skills/vibestatus/SKILL.md && ln -sf "$(pwd)/VIBE-MODEL-PICK.md" ~/.claude/skills/vibe-model-pick/SKILL.md && ln -sf "$(pwd)/VIBE-MODEL-CLEAR.md" ~/.claude/skills/vibe-model-clear/SKILL.md && ln -sf "$(pwd)/GEMINION.md" ~/.claude/skills/geminion/SKILL.md && ln -sf "$(pwd)/GEMINIOFF.md" ~/.claude/skills/geminioff/SKILL.md && ln -sf "$(pwd)/GEMINISTATUS.md" ~/.claude/skills/geministatus/SKILL.md
```

### Step-by-step

```bash
# 1. Clone this repo
git clone https://github.com/pcx-wave/vibe-skill.git
cd vibe-skill

# 2. Install the scripts (symlinks — stay in sync with git pull)
mkdir -p ~/tools
ln -sf "$(pwd)/tools/vibe-delegate" ~/tools/vibe-delegate
ln -sf "$(pwd)/tools/delegate-report" ~/tools/delegate-report
chmod +x ~/tools/vibe-delegate ~/tools/delegate-report

# 3. Install the skills for Claude Code
mkdir -p ~/.claude/skills/vibe ~/.claude/skills/vibeon ~/.claude/skills/vibeoff ~/.claude/skills/vibestatus \
         ~/.claude/skills/vibe-model-pick ~/.claude/skills/vibe-model-clear \
         ~/.claude/skills/geminion ~/.claude/skills/geminioff ~/.claude/skills/geministatus
ln -sf "$(pwd)/SKILL.md" ~/.claude/skills/vibe/SKILL.md
ln -sf "$(pwd)/VIBEON.md" ~/.claude/skills/vibeon/SKILL.md
ln -sf "$(pwd)/VIBEOFF.md" ~/.claude/skills/vibeoff/SKILL.md
ln -sf "$(pwd)/VIBESTATUS.md" ~/.claude/skills/vibestatus/SKILL.md
ln -sf "$(pwd)/VIBE-MODEL-PICK.md" ~/.claude/skills/vibe-model-pick/SKILL.md
ln -sf "$(pwd)/VIBE-MODEL-CLEAR.md" ~/.claude/skills/vibe-model-clear/SKILL.md
ln -sf "$(pwd)/GEMINION.md" ~/.claude/skills/geminion/SKILL.md
ln -sf "$(pwd)/GEMINIOFF.md" ~/.claude/skills/geminioff/SKILL.md
ln -sf "$(pwd)/GEMINISTATUS.md" ~/.claude/skills/geministatus/SKILL.md

# 4. (Optional) Enable auto-mode — Claude delegates all code tasks automatically
#    without requiring /vibe each time. Toggle with /vibeon and /vibeoff.
grep -q "vibe auto-mode" ~/.claude/CLAUDE.md 2>/dev/null || cat >> ~/.claude/CLAUDE.md << 'EOF'

# vibe auto-mode
At the start of every user request that involves writing, editing, or fixing code:
1. Run `test -f ~/.local/share/vibe-auto.flag` (silent, no output to user).
2. If the flag exists → automatically invoke the `vibe` skill exactly as if the user had typed `/vibe <their full instruction>`. Do NOT ask first, do NOT explain — just delegate.
3. If the flag is absent → proceed normally.

The flag is toggled by `/vibeon` and `/vibeoff`.
EOF

```

Verify with `~/tools/vibe-delegate /tmp "Say hello in one sentence." 3`

### Updating

Because both installs use symlinks, a `git pull` is all you need:

```bash
cd ~/vibe-skill && git pull
```

`~/tools/vibe-delegate` and `~/.claude/skills/vibe/SKILL.md` are automatically up to date — no re-copy needed.

> **Migrating from a previous `cp`-based install?** Replace the copies with symlinks:
> ```bash
> cd ~/vibe-skill
> ln -sf "$(pwd)/tools/vibe-delegate" ~/tools/vibe-delegate
> ln -sf "$(pwd)/SKILL.md" ~/.claude/skills/vibe/SKILL.md
> ```

---

## Usage

In a Claude Code session:

```
/vibe add a dark mode toggle to the settings page
```

```
/vibe the login form is not validating the email field — fix it
```

```
/vibe add pagination to the GET /posts route, 20 items per page
```

Claude decomposes the task, writes the Vibe prompt, supervises execution, and reports the diff.

### Model selection

By default, Vibe uses whatever `active_model` is set in `~/.vibe/config.toml`. You can override it per-session without touching that file:

```
/vibe-model-pick              — interactive menu built from your config.toml models
/vibe-model-pick devstral-small  — switch directly by alias
/vibe-model-clear             — remove the override, return to config default
/vibestatus                   — shows both auto-mode state and active model override
```

The override is stored in `~/.local/share/vibe-model.flag` and is picked up by `vibe-delegate` on every run. It persists across sessions until you clear it.

### Vibe-auto mode

For frictionless delegation, enable auto-mode once in your Claude Code session:

```
/vibeon      — every code request is automatically delegated to Vibe, no /vibe prefix needed
/vibeoff     — return to normal Claude behaviour
/vibestatus  — auto-mode state + active model override
```

With `vibeon` active, just talk to Claude normally:

```
add pagination to the /posts route
fix the broken email validation
refactor the auth middleware into its own module
```

Claude intercepts any request that involves writing, editing, or fixing code and delegates it to Vibe transparently. Pure questions and conversations still go directly to Claude — only code tasks are delegated.

---

## Terminal output

Sample output from a real run:

```
=== VIBE START ===
Workdir : /path/to/project
Agent   : default
Model   : deepseek-flash  (config default)
Turns   : 10
Timeout : 180s
Prompt  : Stack: Python/Flask. File: app.py ...
===================
  [read]  app.py
  [tool]  file: app.py
  [tool]  search_replace [OK] ...
  [vibe]  Done. Converted date to datetime.date in fetch_data().
Tool calls: 5  |  warns: 0  |  sr_fails: 0
Model               : deepseek-flash
Delegate tokens (run): 4,800  (last turn: 4,600+200)  |  cost ~$0.0007
Claude Sonnet 4.6 eq: same tokens would cost ~$0.0168  (ratio x24.0)
=== VIBE DONE (exit: 0) ===
=== SYNTAX OK (1 file(s) checked) ===

=== UNCOMMITTED CHANGES ===
 app.py | 4 ++--
[log] → ~/.local/share/delegate-runs.jsonl  (4800 tokens, exit 0, 34.2s, saved ~$0.0161 vs Claude)
```

---

## How vibe-delegate works

```
Claude Code
  └─ /vibe <instruction>
       └─ SKILL.md logic
            └─ ~/tools/vibe-delegate <workdir> <prompt> [turns] [agent] [timeout]
                 ├─ writes prompt to temp file (avoids shell injection with UTF-8/emoji)
                 ├─ generates a temp shell script for the vibe command
                 ├─ runs: script -q -c "<vibe-script>" /dev/null (Linux)
                 │        or script -q /dev/null "<vibe-script>" (macOS)
                 │         └─ allocates pseudo-TTY (required — vibe hangs without one)
                 ├─ pipes JSON streaming output through Python parser
                 │         └─ prints [read] / [write] / [WARN] / [vibe] lines
                 ├─ reads real token counts from Mistral session log
                 ├─ runs syntax checks on modified .py and .js files
                 ├─ prints git diff --stat
                 └─ appends JSON entry to ~/.local/share/delegate-runs.jsonl
```

The `script ... /dev/null` trick allocates a pseudo-TTY on both Linux and macOS; prompt via temp file avoids shell injection with UTF-8/emoji.

**Shell vs Python split** — `vibe-delegate` started as pure shell. Python is now embedded in four places where shell falls short:

| What | Why Python |
|------|-----------|
| JSON stream parser (live output) | Vibe emits a JSON stream; shell can't reliably parse it line by line without race conditions |
| Token count + cost calculation | Reads `~/.vibe/config.toml` (TOML parsing), looks up per-model pricing, handles float arithmetic |
| Syntax check (`py_compile`) | stdlib module — one line, no dependencies |
| Run log writer | Builds a structured JSON entry with multiple computed fields; shell heredoc+`jq` would be fragile |

`delegate-report` is fully Python: it aggregates, sorts, and formats tabular data across hundreds of log entries — the kind of work where shell pipelines become unmaintainable.

---

## Examples

- `examples/good-prompts.md` — prompt patterns that reliably work
- `examples/anti-patterns.md` — what fails and why, with fixes

---

## Sister project

A parallel delegate using **Gemini CLI** is available at [pcx-wave/gemini-skill](https://github.com/pcx-wave/gemini-skill). Same orchestration pattern, same run log format — different model and trade-offs.

## Reporting

Every run is logged to `~/.local/share/delegate-runs.jsonl` with tokens, cost, model, and failure details. Query it with `~/tools/delegate-report [--since N] [--project NAME] [--fails]` or from Claude Code: `/vibe-report [args]`.

---

## Feedback

See [`docs/feedback-claude-sonnet.md`](docs/feedback-claude-sonnet.md) for original feedback from Claude after hours of practice that drove the iterations on `vibe-delegate` — real bugs hit, root causes, and the fixes applied.

---

## License

MIT
