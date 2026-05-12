---
name: vibe
description: >
  Delegate a coding task to Mistral Vibe and supervise the result via git diff.
  Trigger: /vibe <instruction>. Claude orchestrates, Vibe codes.
license: MIT
user-invocable: true
allowed-tools:
  - bash
  - read_file
  - grep
---

# Vibe Orchestrator

When the user invokes `/vibe <instruction>`, Claude delegates the implementation
to Mistral Vibe via its programmatic mode, supervises in real time, and reports.

---

## Known Limits

Hard constraints of Mistral Vibe CLI — not config options.

### 1. Requires a pseudo-TTY
Vibe checks for a TTY on startup. Without one (plain pipe), it hangs silently —
0 tool calls, no output, silent timeout. The `vibe-delegate` script allocates a
pseudo-TTY via `script` (Linux: `script -q -c "..." /dev/null`, macOS: `script -q /dev/null "..."`). **Never call vibe directly in a pipe.**

### 2. UTF-8 / special chars cause `search_replace` failures
Vibe's `search_replace` tool matches byte-for-byte. Accented chars, curly quotes,
or emoji in `old_string` → silent match failure, no write. Workaround: use
`python3 str.replace()` for those edits, or restructure the prompt to avoid them.

### 3. Context saturation above ~12 turns
Mistral's context fills with repeated file reads. Beyond 12 turns the model starts
looping — re-reading files it already read, not making progress. Hard cap: `--max-turns 12`.

### 4. `--output text` hides errors
`--output text` buffers everything until the run ends and suppresses intermediate
errors. Always use `--output streaming` (done automatically by `vibe-delegate`).

### 5. Code duplication bug
Vibe sometimes re-inserts a block it has already written (off-by-one in its diff
logic). Check for duplicate function definitions or repeated class bodies after
every run.

---

## Known projects

<!-- Customize this table for your own projects -->
| Name | Path |
|------|------|
| my-project | /path/to/my-project |

---

## Step 1 — Detect workdir

1. If the instruction mentions a known project → use its path.
2. Otherwise: `git rev-parse --show-toplevel` in the current directory.
3. If ambiguous → ask with `AskUserQuestion`.

---

## Step 2 — Decompose the task

**Critical rule**: Vibe is optimized for **atomic, focused tasks**.
Its system prompt literally says "Most tasks need <150 words."

**Evaluate complexity before launching:**

| Size | Definition | Max turns | Approach |
|------|-----------|-----------|----------|
| **Simple** | 1 file, 1 clear change | 5–8 | 1 vibe call |
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

> ⚠️ **Shell safety**: if the prompt contains UTF-8 accented chars, emojis,
> `:` in Python/YAML code, or typographic apostrophes — the vibe-delegate script
> passes them safely via a temp file (`printf %q`). Never interpolate such a prompt
> directly into a bash heredoc.

**Verification — always use grep, not file re-read:**
```
VERIFY: grep for "def extract_labels" in app.py and confirm it exists.
```
A grep is reliable. A file re-read may miss content outside the read window.

**Examples:**

❌ Bad (too vague, too large):
```
Fix the API, add a signal classifier, update the UI with colored badges
```

✅ Good (atomic, verifiable):
```
Stack: Python/Flask. File: app.py

TASK: In fetch_data(), convert the date string (format "YYYY-MM-DD")
to datetime.date before returning, and convert id to str.

VERIFY: grep for "datetime.date" in app.py and confirm it appears in fetch_data.
```

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
- Never exceed `15` — decompose instead

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
Mistral tokens (real): 4,800  (4,600 prompt + 200 completion)  |  cost ~$0.0086
Claude Sonnet 4.6 eq: same tokens would cost ~$0.0168  (ratio x2.0)
=== VIBE DONE (exit: 0) ===
=== SYNTAX OK (1 file(s) checked) ===

=== UNCOMMITTED CHANGES ===
 app.py | 4 ++--
[log] → ~/.local/share/delegate-runs.jsonl  (4800 tokens, exit 0, 34.2s)
```

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
| `search_replace failed` | UTF-8/emoji chars in `old_string` | Edit with `python3 str.replace()` |
| Duplicated code at end of file | Vibe re-inserts an already-present block | Read diff, delete duplicate manually |
| Variable declared twice | Same — Vibe doesn't check scope | Grep the variable before relaunching |
| Truncated prompt | Special chars in inline prompt | Script uses temp file — should be fixed |

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
- **VERIFY with grep, not file re-read** — `grep -n "def foo" file.py` is reliable.
- **UTF-8 / emoji in the prompt** → the script handles it via temp file, but test with a short prompt first.

---

## Token economics

Vibe's internal turns (repeated file reads, etc.) consume **Mistral tokens**,
not Claude tokens. Claude only receives the compressed final output (~500–1500 tokens/run).

For a task with 6 reads of an 800-line file: ~4800 tokens on Mistral's side, 0 on Claude's.
**Real advantage** on exploratory tasks. Neutral or slightly negative if Vibe fails and
generates long error output that comes back into Claude's context.

**Approximate pricing (Mistral Codestral):**
- ~$1.5/M input tokens, ~$7.5/M output tokens
- Claude Sonnet 4.6: ~$3/M input, ~$15/M output
- Typical ratio: ~2x cheaper per token than Claude, plus 0 Claude tokens on orchestration overhead

Real token counts and cost are printed after every run and appended to the run log.

---

## Run Log

Every run appends one JSON entry to `~/.local/share/delegate-runs.jsonl`.

**Fields logged:**

| Field           | Type    | Description                                          |
|-----------------|---------|------------------------------------------------------|
| `ts`            | string  | ISO 8601 UTC timestamp                               |
| `delegate`      | string  | `"vibe"`                                             |
| `workdir`       | string  | Absolute project path                                |
| `project`       | string  | `basename(workdir)`                                  |
| `prompt_words`  | int     | Word count of the prompt (complexity proxy)          |
| `agent`         | string  | Agent used (`"default"`, `"code-reviewer"`, etc.)   |
| `max_turns`     | int     | Configured `--max-turns` value                       |
| `timeout_secs`  | int     | Configured timeout in seconds                        |
| `exit_code`     | int     | 0=success · 124=timeout · other=error                |
| `timed_out`     | bool    | `true` if `exit_code == 124`                         |
| `tool_calls`    | int     | Total tool invocations made by Vibe                  |
| `files_changed` | int     | Files modified (git diff count)                      |
| `syntax_errors` | int     | Python/JS syntax errors detected post-run            |
| `duration_secs` | float   | Total wall-clock duration                            |
| `tokens_in`     | int     | Prompt tokens (from Mistral session log)             |
| `tokens_out`    | int     | Completion tokens                                    |
| `tokens_total`  | int     | Total tokens                                         |
| `cost_usd`      | float   | Estimated cost in USD                                |
| `model`         | string  | `"mistral"`                                          |

**Useful queries:**
```bash
# All recent runs
cat ~/.local/share/delegate-runs.jsonl | python3 -m json.tool | less

# Success rate
jq -r '[.exit_code] | @tsv' ~/.local/share/delegate-runs.jsonl | sort | uniq -c

# Timed-out runs
jq 'select(.timed_out == true)' ~/.local/share/delegate-runs.jsonl

# Total cost
jq -r '.cost_usd' ~/.local/share/delegate-runs.jsonl \
  | awk '{sum+=$1} END {printf "Total: $%.4f\n", sum}'
```

---

## See Also

A sister delegate using Gemini CLI exists: [gemini-skill](https://github.com/pcx-wave/gemini-skill).
Both write to the same `delegate-runs.jsonl` log, making runs comparable across delegates.
