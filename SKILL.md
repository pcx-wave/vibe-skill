---
name: vibe
description: >
  Delegate a coding task to Mistral Vibe and supervise the result via git diff.
  Trigger: /vibe <instruction>. Claude orchestrates, Vibe codes.
  Also handles /vibe-report [--since N] [--project NAME] [--fails] — token/cost/failure report.
license: MIT
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - grep
---

# Vibe Orchestrator

## /vibeon | /vibeoff | /vibestatus

Toggle auto-delegate mode — Vibe automatically handles coding tasks without requiring `/vibe` each time.

| Command | Action |
|---------|--------|
| `/vibeon` | `touch ~/.local/share/vibe-auto.flag` → confirm "Auto-vibe ON" |
| `/vibeoff` | `rm -f ~/.local/share/vibe-auto.flag` → confirm "Auto-vibe OFF" |
| `/vibestatus` | report auto-mode (ON/OFF) **and** active model override |

For `/vibestatus`, run both checks and print two lines:
```
Auto-vibe: ON | OFF
Model: <alias>  (override)  OR  Model: deepseek-flash  (config default)
```

### Auto-mode pre-filter (when flag is set)

When `vibe-auto.flag` exists, apply this gate **before** loading the full skill:

| Task signal | Action |
|---|---|
| 1 file, ≤10 lines, exact location already known | Edit directly — do NOT invoke the skill |
| Logic non-trivial, location unclear, multiple files, HTML/JS content, or >1 change | Invoke `/vibe` as normal |


---

## /vibe-report

If the user invokes `/vibe-report`, run `~/tools/delegate-report` with any flags
extracted from the arguments, display output verbatim, and stop.

| User says | Flag |
|-----------|------|
| "last 7 days", "7d" | `--since 7` |
| "last 30 days", "30d" | `--since 30` |
| "project foo" | `--project foo` |
| "only failures", "fails", "bugs" | `--fails` |
| (nothing) | (no flags — full report) |

---

## /vibe-model-pick | /vibe-model-clear

Override the Vibe model for all subsequent delegations without touching `~/.vibe/config.toml`.
Works via `VIBE_ACTIVE_MODEL` env var, which Vibe respects over the config file.

| Command | Action |
|---------|--------|
| `/vibe-model-pick <alias>` | `echo <alias> > ~/.local/share/vibe-model.flag` → confirm |
| `/vibe-model-clear` | `rm -f ~/.local/share/vibe-model.flag` → confirm "back to config default" |

**Available aliases** (from `~/.vibe/config.toml`):

| Alias | Model | Provider | Notes |
|-------|-------|----------|-------|
| `deepseek-flash` | deepseek-v4-flash | DeepSeek | Default — fast, cheap |
| `mistral-medium-3.5` | mistral-vibe-cli-latest | Mistral | Stronger reasoning |
| `devstral-small` | devstral-small-latest | Mistral | Lighter Mistral model |
| `local` | devstral (llamacpp) | Local | Requires local server on :8080 |

Run the bash command, print one confirmation line showing the active model, and stop.

---

When the user invokes `/vibe <instruction>`, Claude delegates the implementation
to Mistral Vibe via its programmatic mode, supervises in real time, and reports.

---

## Known Limits

Hard constraints — not config options. Full details in `SKILL-reference.md`.

- **UTF-8 / special chars** → silent `search_replace` match failure. Use `python3 str.replace()` for accented chars or emoji.
- **Code duplication** → Vibe may re-insert a block already written. Grep for duplicate definitions after every run.
- **HTML in prompt** → tags like `<div>` are shell redirects (exit 127). Write HTML content to a temp file; reference the path in the prompt.
- **Source code in bash heredoc** → quotes/backslashes mangle. Use `search_replace` directly; never a helper script that replaces code.
- **Orchestration chain** → 6 failure points (CLI → TTY → parser → pricing → git → log). Unexpected results: check in that order.

---

## Step 1 — Detect workdir

1. `git rev-parse --show-toplevel` in the current directory.
2. If ambiguous or no git repo → ask with `AskUserQuestion`.

---

## Step 2 — Decompose the task

**Critical rule**: Vibe is optimized for **atomic, focused tasks**.
Its system prompt literally says "Most tasks need <150 words."

| Size | Definition | Max turns | Approach |
|------|-----------|-----------|----------|
| **Trivial** | 1 file, change is obvious and located | — | **Skip delegation — edit directly** |
| **Simple** | 1 file, non-trivial logic or unknown location | 5–8 | 1 vibe call |
| **Medium** | 2–3 related files, 1 objective | 8–12 | 1 structured vibe call |
| **Complex** | >3 files OR business logic OR DB migrations | — | **Break into sub-tasks** |

**Decomposition for complex tasks:**
```
Sub-task 1: Explore / read relevant files (read-only, 5 turns)
Sub-task 2: Implement change A in file X (8 turns)
Sub-task 3: Implement change B in file Y (8 turns)
Sub-task 4: Verify / test (5 turns)
```
→ Check git diff between each sub-task before launching the next.

---

## Step 3 — Write the Vibe prompt

Vibe has no context from the parent conversation. The prompt must be **self-contained**.

**Structure of a good Vibe prompt:**
```
Stack: Python/Flask, SQLAlchemy, SQLite
Key files: app.py (routes + fetch), models.py (Entry)

TASK: [one single thing to do, stated as an imperative]

CONSTRAINTS:
- [what must not break]
- [expected format if relevant]

VERIFY: grep for "def function_name" in file.py and confirm it exists.
```

**Formulation rules:**
- One task per prompt — never "also do X and Y"
- Name the exact files to modify
- Include a grep-based verification criterion (not a file re-read)
- Language: English (better Mistral performance)

**Prompt adaptations** (auto-detected and logged per-run; `/vibe-report --adapt` shows impact):
- **C3+ tasks**: include the exact function signature (`def f(data: dict) -> tuple[bool, list[str]]:`). Recovers +14–27% pass-rate at C3–C4 by removing interface ambiguity.
- **Write/modify tasks**: append `OUTPUT FORMAT:\nModified: <file>\nDoes: <one line>\nNo other prose.` — lets Claude verify without re-reading the file.

> ⚠️ **Shell safety**: if the prompt contains UTF-8 accented chars, emojis,
> `:` in Python/YAML code, or typographic apostrophes — the vibe-delegate script
> passes them safely via a temp file (`printf %q`). Never interpolate such a prompt
> directly into a bash heredoc.

**Verification — always use grep, not file re-read:**
```
VERIFY: grep for "def extract_labels" in app.py and confirm it exists.
```
A grep is reliable. A file re-read may miss content outside the read window.

---

## Step 4 — Launch Vibe

```bash
~/tools/vibe-delegate "<workdir>" "<prompt>" [max-turns] [agent] [timeout-secs]
```

| Argument       | Default  | Notes                                           |
|----------------|----------|-------------------------------------------------|
| `workdir`      | —        | Absolute path, must exist                       |
| `prompt`       | —        | Self-contained task description                 |
| `max-turns`    | `10`     | Mistral turn limit — hard cap at 12, never more |
| `agent`        | *(none)* | See agent table below                           |
| `timeout-secs` | `180`    | Wall-clock kill timer                           |

The script allocates a pseudo-TTY via `script` (required — vibe hangs without one).

**Available agents:**

| Agent | Use |
|-------|-----|
| *(default)* | General implementation |
| `code-reviewer` | Review only, no changes |
| `planner` | Planning before implementing |
| `code-architect` | Architecture design, read-only |

**Recommended max turns:**
- Read/explore: `5`
- Simple change (1 file): `8`
- Medium change (2–3 files): `12`
- Never exceed `12` — decompose instead

**Background launch:**
```bash
~/tools/vibe-delegate "<workdir>" "<prompt>" 10 > /tmp/vibe_out.txt 2>&1 &
# Monitor with: tail -f /tmp/vibe_out.txt
```

---

## Step 5 — Supervise in real time

The script prints live:
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
Delegate tokens (run): 4,800  (last turn: 4,600+200)  |  cost ~$0.0086
Claude Sonnet 4.6 eq: same tokens would cost ~$0.0168  (ratio x2.0)
=== VIBE DONE (exit: 0) ===
=== SYNTAX OK (1 check(s)) ===

=== UNCOMMITTED CHANGES ===
 app.py | 4 ++--
[log] → ~/.local/share/delegate-runs.jsonl  (4800 tokens, exit 0, 34.2s)
```

**Vibe never commits.** All changes are left unstaged — `git checkout .` reverts everything if needed.

**Red flags to act on immediately:**

| Flag | Meaning | Action |
|------|---------|--------|
| `[WARN]` | Vibe encountered an error | Read the error, fix manually |
| `[tool]  search_replace [FAIL]` | UTF-8 match failure | Edit manually with Python `str.replace()` |
| `exit: 1` or non-zero | Vibe failed / did not complete verification | Read diff, correct prompt |
| No `[tool]  file:` lines | Vibe read but wrote nothing | Prompt was too vague or task already done |
| `=== SYNTAX ERRORS ===` | Post-run syntax check failed | **Fix before committing** |
| Same file read 5+ times | Vibe is looping — run likely lost | Abort, check diff, try again |

**Known bugs and workarounds:**

| Bug | Cause | Fix |
|-----|-------|-----|
| Variable declared twice | Same — Vibe doesn't check scope | Grep the variable before relaunching |
| Truncated prompt | Special chars in inline prompt | Script uses temp file — should be fixed |
| Wrote a Python helper just to replace code | Misdiagnosed search_replace limit — plain Python code works fine | Use search_replace directly for ASCII code; write_file only if the new content is too long for the prompt |
| Empty run — 0 files changed despite ≥3 tool calls | Multi-edit prompt: context drifts after long file read, first `search_replace` target not found byte-for-byte, run silently abandons | Split into sequential single-change runs; grep target string locally before delegating |

**If exit non-zero:** do not relaunch immediately. Read the diff, understand what was done, fix the prompt.

---

## Step 6 — Iteration

- **Max 3 attempts** per sub-task before escalating to the user.
- Between attempts, **read the git diff** to avoid doubling partial work.
- If Vibe completed ≥50% and crashed: finish the rest manually rather than relaunching.

---

## Step 7 — Report to the user

```
✓ Vibe finished — <1-line summary>

Files modified:
  - path/to/file.ext (+X / -Y lines)

[If problem]:
⚠ <description> — completing manually / relaunching?

Ready to commit?
```

---

## Orchestration rules

- **Decompose before delegating** — an oversized prompt is guaranteed to fail.
- **Streaming always** — `--output text` hides errors and blocks until the end.
- **Check diff between sub-tasks** — never launch the next one blind.
- **Don't code instead of Vibe** unless Vibe completed ≥50% and crashed.
- **Max 12 turns per call** — beyond that, Mistral context saturates.
- **Grep target before delegating** — `grep -n "exact_target" file.py` before any `search_replace` prompt. No match = empty run. Always use grep for VERIFY, not file re-read.
- **UTF-8 / emoji in the prompt** → the script handles it via temp file, but test with a short prompt first.
- **After any run that touches imports: grep the import line** — sequential runs can revert each other's import changes. Always run `grep "^from X import" file.py` before the next sub-task.
- **search_replace [OK] ≠ correct change** — Vibe may report OK even if the match was on unintended content. Always grep the specific changed line, not just check syntax.
- **Provide data structure context** — Vibe writes against what it knows. If a route accesses a DB payload, include the exact field paths (`payload['produit']['nom']`) in the prompt, not just "extract the name".
- **Reuse existing assets** — for UI tasks, tell Vibe to link existing CSS/JS files rather than generating new styles. "Use `/static/style.css` and CSS class `bar-row`" is always better than "generate a dark theme".

---

## Run Log

Every run appends one JSON entry to `~/.local/share/delegate-runs.jsonl`.
Log fields and jq queries → see `SKILL-reference.md`.

```bash
~/tools/delegate-report                  # full report
~/tools/delegate-report --since 7        # last 7 days
~/tools/delegate-report --project myapp  # filter by project
~/tools/delegate-report --fails          # failures only
~/tools/delegate-report --adapt          # failure rates by prompt adaptation
```

Or via Claude Code: `/vibe-report [args]`. Log fields and jq queries → `SKILL-reference.md`.

---

## See Also

A sister delegate using Gemini CLI exists: [gemini-skill](https://github.com/pcx-wave/gemini-skill).
Both write to the same `delegate-runs.jsonl` log, making runs comparable across delegates.
