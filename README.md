<!-- Suggested GitHub topics: claude-code, llm-tools, mistral, gemini-cli, ai-coding, shell, developer-tools, vibe-coding -->

# vibe-skill

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg) ![Shell](https://img.shields.io/badge/language-Shell-green.svg) ![GitHub stars](https://img.shields.io/github/stars/pcx-wave/vibe-skill?style=social) ![Claude Code skill](https://img.shields.io/badge/-Claude%20Code%20skill-CC785C)

**Claude orchestrates. Vibe does the heavy lifting. You review the diff, save tokens, costs and avoid hitting limits!**
Claude sees only ~500–1500 tokens per run regardless of how many file reads Vibe performs internally — massive savings on exploratory and implementation tasks.

Summary:
1. User types `/vibe <instruction>` in Claude Code
2. Claude decomposes the task and writes a prompt
3. `vibe-delegate` runs Mistral Vibe in a pseudo-TTY
4. The delegate reports tool calls, token counts, and `git diff --stat`
5. Claude reviews the diff and summarizes the result

---

## Why

| Scenario | Claude-only cost | With vibe-skill |
|----------|-------------------|-----------------|
| Simple 1-file tweak (800 tokens) | ~$0.003 | ~$0.002 |
| 6-read implementation task (4,800 tokens) | ~$0.018 | ~$0.009 |
| Complex multi-file refactor (12,000 tokens) | ~$0.045 | ~$0.012 |

> Claude token usage for orchestration overhead: ~0.4 tokens (negligible cost). Vibe consumes Mistral tokens; Claude only sees the compressed final output.

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
git clone https://github.com/pcx-wave/vibe-skill.git && cd vibe-skill && mkdir -p ~/tools && cp tools/vibe-delegate ~/tools/ && chmod +x ~/tools/vibe-delegate && mkdir -p ~/.claude/skills/vibe && cp SKILL.md ~/.claude/skills/vibe/SKILL.md
```

### Step-by-step

```bash
# 1. Clone this repo
git clone https://github.com/pcx-wave/vibe-skill.git
cd vibe-skill

# 2. Install the delegate script
mkdir -p ~/tools
cp tools/vibe-delegate ~/tools/vibe-delegate
chmod +x ~/tools/vibe-delegate

# 3. Install the skill for Claude Code
mkdir -p ~/.claude/skills/vibe
cp SKILL.md ~/.claude/skills/vibe/SKILL.md

# 4. Edit the "Known projects" table in ~/.claude/skills/vibe/SKILL.md
#    to list your own projects with their paths.
```

Verify with `~/tools/vibe-delegate /tmp "Say hello in one sentence." 3`

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

---

## Terminal output

Sample output from a real run:

```
=== VIBE START ===
Workdir : /path/to/project
Agent   : default
Turns   : 10
Timeout : 180s
Prompt  : Stack: Python/Flask. File: app.py ...
===================
  [read]  app.py
  [tool]  file: app.py
  [tool]  search_replace [OK] ...
  [vibe]  Done. Converted date to datetime.date in fetch_data().
Tool calls: 5
Mistral tokens (real): 4,800  (4,600 prompt + 200 completion)  |  cost ~$0.0086
Claude Sonnet 4.6 eq: same tokens would cost ~$0.0168  (ratio x2.0)
=== VIBE DONE (exit: 0) ===
=== SYNTAX OK (1 file(s) checked) ===

=== UNCOMMITTED CHANGES ===
 app.py | 4 ++--
[log] → ~/.local/share/delegate-runs.jsonl  (4800 tokens, exit 0, 34.2s)
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

---

## Token economics

Vibe's internal turns (file reads, search/replace attempts) consume **Mistral tokens**, not Claude tokens.
For a task with 6 reads of an 800-line file: ~4800 tokens on Mistral's side, effectively 0 on Claude's.
Real advantage on exploratory/implementation tasks.

---

## Customization

Edit `~/.claude/skills/vibe/SKILL.md`: adjust **Known projects**, **Max turns**, and **Agents**.

---

## Examples

- `examples/good-prompts.md` — prompt patterns that reliably work
- `examples/anti-patterns.md` — what fails and why, with fixes

---

## Sister project

A parallel delegate using **Gemini CLI** is available at [pcx-wave/gemini-skill](https://github.com/pcx-wave/gemini-skill). Same orchestration pattern, same run log format — different model and trade-offs.

## Cross-delegate benchmarking

vibe-skill and gemini-skill share the same `~/.local/share/delegate-runs.jsonl` schema, so you can run the same task on both delegates and compare cost, duration, and tool_calls side by side.

Useful queries:

```bash
# Success rate
jq -r '[.exit_code] | @tsv' ~/.local/share/delegate-runs.jsonl | sort | uniq -c

# Total cost
jq -r '.cost_usd' ~/.local/share/delegate-runs.jsonl \
  | awk '{sum+=$1} END {printf "Total: $%.4f\n", sum}'
```

---

## Feedback

See [`docs/feedback-claude-sonnet.md`](docs/feedback-claude-sonnet.md) for original feedback from Claude after hours of practice that drove the iterations on `vibe-delegate` — real bugs hit, root causes, and the fixes applied.

---

## License

MIT
