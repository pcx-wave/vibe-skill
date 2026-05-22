# Vibe — Reference

Not loaded at runtime. Use when querying or debugging `delegate-runs.jsonl`.

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
| `wrote_nothing` | bool | `true` if ≥3 tool calls but 0 files changed |

---

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
