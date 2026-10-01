# Harness audit — 2026-10-01 (Vibe 2.25.7; tests run with GLM-5.3, findings are model-independent)

Trigger: recurring supervisor misreads — "Vibe can't read files over 50 KB",
"Vibe did nothing", runs reported FAILED that had worked, and the reverse.
Method: interview Vibe directly (read-only, then write mode) on a 149 KB test
file, then check **every** claim against the session store
(`~/.vibe/logs/session/unified/<uuid>/generations/<CURRENT>/{runtime-state,checkpoint,projection-state}.json`).
Vibe's own narrative was wrong twice (H11), so the session store is the only
source treated as truth below.

Status legend: FIXED and FIX both shipped in this release, DOC (behaviour documented, no code).

| ID | Symptom | Root cause (verified) | Status |
|----|---------|----------------------|--------|
| H1 | `model: unknown`, 0 tokens on every run after the unified-harness rollout | Unified `meta.json` has no stats | FIXED |
| H2 | Capped runs logged `ok` / `RESULT: OK` | `--max-turns` exhaustion exits 0, turn status `completed` | FIXED |
| H3 | Direct `vibe -p` hangs until timeout, no session created | Reads stdin to EOF when stdin is not a TTY | DOC + FIX |
| H4 | Vibe burns turns on `search_tool_functions` | Model-facing tool is `edit`; prompts say `search_replace` | FIX |
| H5 | `RESULT: FAILED [sr_fail]`, exit 3, on a run that succeeded | Any failed search_replace = FAILED, even if a later edit on the same file succeeded | FIX |
| H6 | Supervisor never sees Vibe's final answer | Stream parser cuts each message at 400 chars | FIX |
| H7 | `[read] file_system.read_file` with no path; write_file targets skipped by syntax check | Parser reads `file_path`/`filePath`; read_file and write_file use `path` | FIX |
| H8 | "Vibe can't read files > 50 KB" | Myth — see detail. One call returns 50 KiB; paging works | DOC + FIX (preflight note) |
| H9 | WRITE AUDIT lists a failed edit as `CHANGED` | Audit is per-file (disk), not per-call; ignores call outcome | FIX |
| H10 | Vibe cannot pace itself | Turn budget is never shown to the model | FIX |
| H11 | Vibe's self-description is wrong | It answers from its model-side view, not the runtime | DOC |

## Detail and evidence

### H3 — `vibe -p` blocks on stdin
Reproduced 2026-10-01, same prompt, 60 s timeout:

| Invocation | Result |
|---|---|
| `vibe -p "Reply PONG" --output text` (stdin inherited from a non-TTY shell) | rc 124 after 60 s, no output, **no session created** |
| same with `--agent plan` | rc 124, identical |
| same with `< /dev/null` | rc 0 in 16 s, `PONG` |

`vibe-delegate` is not affected (it runs vibe under `pty.spawn`). Any *direct*
call must use `< /dev/null`. This is why the first interview call of this
audit timed out at 400 s; it was not the plan agent and not the prompt.

### H4 — two names for one tool
- Model view (Vibe's own answer, twice): tool `edit`, args `file_path, old_string, new_string, replace_all`.
- Runtime view (runtime-state `actions`, 100 sessions): `file_system.search_replace`, args `{file_path, content:[{old_str,new_str,replace_all}]}`. `edit` never appears.
- Asked to "call search_replace", Vibe spent 2 calls on `search_tool_functions` before editing (round 2 stream).

Rule: prompts say **"the edit tool"**; parsers/audits match `search_replace`
(runtime name). Other runtime names: `file_system.read_file {path, offset, limit}`,
`file_system.write_file {path, content}`, `file_system.bash {command}`.

### H5 — recovered failure reported as FAILED
Round 2: Vibe ran a deliberately failing edit and the real edit (in parallel).
Runtime: one `failed` (`tool_failed: block 0: old_str not found`), one
`succeeded` (`lines_changed: 1`). Disk: correct one-line diff. Harness:
`RESULT: FAILED [sr_fail]`, exit 3. A supervisor reading that line reports a
failure that did not happen. New rule: `sr_fail` only when a file with a failed
edit has **no** successful edit/write in the same run.

### H6 — final answer truncated
Stream line: `2. \`edit\` (arguments: file_path, old_string, new_string, r` (cut at 400).
Same answer in `checkpoint.json → turn.outcome.output`: ~2 KB, complete.
Fix: print the full final answer from the checkpoint in a dedicated block.

### H7 — paths missing in parser
Unified stream effects carry `detail.input.path` for read_file/write_file.
Parser looked only at `filePath`/`file_path` → empty path in `[read]` lines, and
write_file targets never reached the syntax-check list.

### H8 — the 50 KB "limit", measured
`read_file big.py` (149,020 bytes, no offset/limit):
- **succeeds** (not an error), `returned_bytes: 51200`, `was_truncated: true`,
  `file_size_bytes: 149020`, `lines_read: 1882` — the model is told the file is bigger;
- results over 40,000 chars are offloaded to `<session>/tool-results/*.json`;
  the model sees an inline excerpt plus that path;
- `offset`/`limit` page through the rest; `grep -n` locates anchors;
- `~/.vibe/config.toml [tools.read_file] max_read_bytes = 64000` is **not** what
  the unified harness applied (51,200 observed).

So: Vibe *can* work on large files. The failure mode is reasoning on the first
50 KiB without paging. The old preflight note ("do NOT read them whole … ONE
search_replace") also fought Vibe's system rule *"Never edit a file you have not
read in this session"*. New note: grep -n → read_file with offset/limit around
the line → edit.

### H9 — write audit per-call
Round 2 audit printed both edits as `on disk: CHANGED`, including the one that
failed. Fix: audit from runtime-state `actions` (`state: succeeded|failed`,
error message), still cross-checked against disk.

### H10 — turn budget
Vibe (round 1): "Nothing in my context states the value or shows a turn counter."
Combined with H2, a capped run just stops. Fix: harness appends
`You have N turns in total; keep the last one for a short final summary.`

### H11 — do not trust Vibe's self-report
Wrong claims in this audit: "no tool named search_replace" (runtime name),
"read_file has no size limit" (51,200 per call), "harness note said error".
Ask Vibe for *experiments*, then read the session store.

## Unified harness — what it changes for delegation

Vibe moves installs to the "unified harness" through a GrowthBook rollout
(`--legacy-harness` opts out). Claimed features vs what an enrolled install
exposes, checked in the session store:

| Claimed | Observed (enrolled test install) | Consequence for the skill |
|---|---|---|
| `run_typescript` sandbox batching many tool calls | **present** when the internal `mistralai_vibe_local_harness` package is installed (not on PyPI; `tools.file_system.{edit,read_file,bash}` callable inside). A first check wrongly said "absent" — it only searched `runtime-state.json`; the catalog lives in `chunks/`. First request was ignored because the harness's own `RUN BUDGET` line said "use the edit tool"; with that line fixed, Vibe did 6 edits in one `run_typescript` loop (4 turns, 35k tokens vs 5 turns, 43k). Edits made in the sandbox are still journaled as `file_system.search_replace` actions | Ask for it on repetitive multi-file edits; never contradict it in the same prompt |
| On-demand tool discovery (`search_tool_functions`) | present; triggered whenever a prompt names a tool the model doesn't see by that name | Say "edit tool", not "search_replace" (H4) |
| Several tool calls per model turn | yes: 6 reads + 6 edits in **5** turns | `--max-turns` counts model calls; ask for parallel independent edits |
| New session store | `unified/<uuid>/generations/...` | H1, H2, H6, H9 read from it |
| Connectors enabled by default | user-configured MCP servers (`mcp_*`) plus `connector_github_app`, `connector_web_search` loaded in every session (exposure `programmatic`, i.e. reachable only through `run_typescript`) | Extra context per run; `enable_connectors = false` in config.toml (or `disabled = true` per `[[connectors]]`) if token cost matters — per Vibe, not yet measured |

Cross-check with Vibe's own review of this audit (2026-10-01): it said
`VIBE_HARNESS` "does not exist" — true for Vibe, but it is a `vibe-delegate`
variable translated to `--legacy-harness`/`--experimental-harness`; the session
layouts prove the benchmark ran on both backends (2 `unified/<uuid>`, 2
`session_*`). It also said the local-harness package was absent from the test
install — false: it was installed, and Vibe's own interactive session there ran
`run_typescript`. Same lesson as H11.

Benchmark, same prompts, `VIBE_HARNESS=unified|legacy`, GLM-5.3, one run each:

| Task | Harness | Correct | Tool calls | Tokens | Time |
|---|---|---|---|---|---|
| 1 edit in 149 KB file | unified | yes | 4 | 39,304 | 19.1 s |
| 1 edit in 149 KB file | legacy | yes | 3 | 27,764 | 29.2 s |
| 6 one-line edits, 6 files | unified | 6/6 | 12 | 26,037 | 21.2 s |
| 6 one-line edits, 6 files | legacy | 6/6 | 12 | 22,164 | 24.4 s |

No reliability difference; unified faster, legacy cheaper in tokens. Kept the
default (unified). One sample per cell — re-measure before switching.

Controls for the fixes (all on the patched harness):
- deliberate failed edit + successful edit → `RESULT: OK`, audit `recovered` (was FAILED);
- single unrecovered failed edit → `RESULT: FAILED [sr_fail]`, exit 3 (unchanged);
- 6-file task at max-turns 2 → `FAILED [turn_cap]`, exit 3; 2-file task at 12 → `OK`.

## Why "Vibe did nothing" kept coming back
It was rarely Vibe. In order of measured impact: H2 (capped runs logged ok —
about a quarter of a month's runs in the logs examined), H5 (successful runs reported FAILED), H6 (supervisor never saw the
answer), H7 (writes invisible to the parser), H1 (no tokens/model — runs looked
empty). The harness now surfaces the session store's ground truth instead.

## Supervisor checklist (post-fix)
1. Read the last line `=== RESULT: ... ===` and the exit code (3 = failed).
2. Read `=== VIBE FINAL ANSWER ===` (full text, from checkpoint).
3. Read `=== WRITE AUDIT ===` (per call: ok/FAILED + disk state).
4. Confirm with `git diff`. Never conclude from `[vibe]`/`[tool]` stream lines alone.
