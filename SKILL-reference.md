# Vibe — Reference

Not loaded at runtime. Read this file when troubleshooting, querying logs, or looking up full details for items summarised in SKILL.md.

## Known Limits — Full Details

### 1. UTF-8 / special chars cause `search_replace` failures
Vibe's `search_replace` matches byte-for-byte. Accented chars, curly quotes, or emoji in `old_string` → silent match failure, no write. Use `python3 str.replace()` for those edits, or restructure the prompt to avoid them.

### 2. Code duplication bug
Vibe sometimes re-inserts a block already written (off-by-one in its diff logic). Check for duplicate function definitions or repeated class bodies after every run.

### 3. Orchestration chain — 6 independent failure points
`vibe CLI → pseudo-TTY (script) → Python stream parser → TOML pricing lookup → git diff → JSON log`

| Link | Failure mode | Symptom |
|------|-------------|---------|
| Vibe CLI | Auth expired, update broke API | Immediate exit, no output |
| pseudo-TTY | Platform difference (GNU vs BSD flags) | Hangs silently or garbled output |
| Stream parser | Vibe changes its JSON schema | Tool calls not detected, wrong token count |
| TOML pricing | `config.toml` missing or renamed | Falls back to Mistral Medium 3.5 rates |
| git diff | Not a git repo, or Vibe committed mid-run | Wrong file count, misleading stat |
| JSON log | `~/.local/share/` not writable | Silent log skip, `/vibe-report` misses the run |

### 4. Never pass source code through a bash heredoc
Nested quotes, f-strings, or backslashes in inline bash `<< 'PYEOF'` mangle escaping. Use `search_replace` directly for ASCII code; write_file only if the new content is too long for the prompt. Never write a helper script whose sole job is `str.replace()` on another file.

### 5. HTML tags in the prompt body cause shell redirect errors (exit 127)
Tags like `<div>` are interpreted as file redirections. Write HTML/JSX content to a temp file first; reference the path in the prompt.

---

---

## Run Log Fields

Every run appends one JSON entry to `~/.local/share/delegate-runs.jsonl`.

| Field | Type | Description |
|---|---|---|
| `ts` | string | ISO 8601 UTC timestamp |
| `delegate` | string | `"vibe"` |
| `workdir` | string | Absolute project path |
| `project` | string | `basename(workdir)` |
| `prompt_words` | int | Word count of the prompt |
| `agent` | string | Agent used (`"default"`, `"code-reviewer"`, etc.) |
| `max_turns` | int | Configured `--max-turns` value |
| `timeout_secs` | int | Configured timeout in seconds |
| `exit_code` | int | 0=success · 124=timeout · other=error |
| `timed_out` | bool | `true` if `exit_code == 124` |
| `tool_calls` | int | Total tool invocations |
| `files_changed` | int | Files modified (git diff count) |
| `syntax_errors` | int | Python/JS syntax errors detected post-run |
| `duration_secs` | float | Total wall-clock duration |
| `tokens_in` | int | Prompt tokens |
| `tokens_out` | int | Completion tokens |
| `tokens_total` | int | Total tokens |
| `cost_usd` | float | Estimated delegate cost in USD |
| `cost_claude_eq` | float | Claude Sonnet 4.6 equivalent cost |
| `model` | string | Active model alias |
| `warn_count` | int | `[WARN]` events during the run |
| `search_replace_fails` | int | `search_replace [FAIL]` events |
| `wrote_nothing` | bool | `true` if ≥3 tool calls but 0 files changed (backwards compat) |
| `failure_reason` | string | `ok` \| `silent_exit` \| `near_empty` \| `wrote_nothing` \| `timeout` \| `exit_error` \| `syntax_error` \| `sr_fail` \| `warn_only` |
| `adaptations` | list | Prompt adaptations detected: `contract` \| `output_format` \| `compact` |

---

## Cost estimate methodology

Per run, `vibe-delegate` derives tokens and cost from Vibe's own session file
(`~/.vibe/logs/session/<id>/meta.json`) — these are **estimates for comparison, not billed
amounts**. How each piece is computed:

| Piece | Source / method | Caveat |
|---|---|---|
| Total tokens | `session_total_llm_tokens` from meta.json | Real — Vibe's measured count |
| Input vs output split | Exact cumulative `session_prompt_tokens` / `session_completion_tokens` from meta.json | Falls back to the last-turn ratio only if those fields are absent (older Vibe) |
| Cache tokens | **Not accounted for** — meta.json exposes no cache hit/miss split | All input is priced at the full input rate; if the provider caches prompt prefixes (cheaper), the estimate is an upper bound. **Measured example:** vibe's 269 DeepSeek runs (32.1M tokens) — the log estimates ~$4.6, but real billing was **~$0.67** because ~90% of input was cache hits at $0.0028/M (50× cheaper than the $0.14/M miss rate). Cache-blindness ≈ 7× overstatement. Provider billing (DeepSeek, OpenAI, Anthropic, Gemini all expose hit/miss) is the only source of true cost |
| Price | `(in × input_price + out × output_price) / 1e6`, per-model prices from `~/.vibe/config.toml` | Fallback is 1.5 / 7.5 (Mistral Medium). Runs logged *before* a model's pricing was added used that fallback — e.g. early DeepSeek runs show Mistral-rate cost, inflated ~7× |
| Claude equivalent | Same in/out tokens priced at $3 / $15 per M | Fixed Sonnet 4.6 reference rate |

Vibe's own `session_cost` is present in meta.json but **not used** — the script recomputes
from the config price table so every model is compared on one consistent basis.

**Known improvement (not yet done):** switch the in/out split from the last-turn ratio to the
exact `session_prompt_tokens` / `session_completion_tokens`. Affects future runs only.

## jq Queries

```bash
# Success rate
jq -r '.exit_code' ~/.local/share/delegate-runs.jsonl | sort | uniq -c

# Total cost vs Claude equivalent
jq -r '[.cost_usd, .cost_claude_eq] | @tsv' ~/.local/share/delegate-runs.jsonl \
  | awk '{c+=$1; e+=$2} END {printf "Spent: $%.4f  Claude eq: $%.4f  Saved: $%.4f\n", c, e, e-c}'

# Runs with search_replace failures
jq 'select(.search_replace_fails > 0)' ~/.local/share/delegate-runs.jsonl

# Empty runs (wrote nothing despite tool calls)
jq 'select(.wrote_nothing == true)' ~/.local/share/delegate-runs.jsonl
```

---

## Manual Completion Logging

Run after finishing a task manually (after Vibe failures):

```bash
python3 tools/log-manual.py
```

Run from the project root. Estimates: output tokens = lines_added × 10, input tokens = lines_added × 40. Flagged `cost_estimated: true` in the log.

### Script source

```python
import json, datetime, subprocess, os

workdir = subprocess.run(['git','rev-parse','--show-toplevel'], capture_output=True, text=True).stdout.strip() or os.getcwd()
project = os.path.basename(workdir.rstrip('/'))

stat = subprocess.run(['git','-C',workdir,'diff','--stat'], capture_output=True, text=True).stdout
lines_added = sum(
    int(l.split('+')[1].split()[0])
    for l in stat.splitlines()
    if '|' in l and '+' in l
) if stat else 0
files_changed = len([l for l in stat.splitlines() if '|' in l])

tokens_out = lines_added * 10
tokens_in  = lines_added * 40
cost = (tokens_in * 3.0 + tokens_out * 15.0) / 1_000_000

entry = {
    'ts': datetime.datetime.utcnow().isoformat() + 'Z',
    'delegate': 'claude-manual',
    'workdir': workdir, 'project': project,
    'exit_code': 0, 'files_changed': files_changed,
    'tokens_in': tokens_in, 'tokens_out': tokens_out,
    'tokens_total': tokens_in + tokens_out,
    'cost_usd': round(cost, 6), 'cost_estimated': True,
    'lines_added': lines_added,
}
log = os.path.expanduser('~/.local/share/delegate-runs.jsonl')
with open(log, 'a') as f:
    f.write(json.dumps(entry) + '\n')
print(f'[log] claude-manual -> {project}  ~{lines_added} lines added  est. cost ${cost:.4f}')
```
