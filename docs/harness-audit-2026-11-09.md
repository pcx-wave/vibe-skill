# Harness audit — 2026-11-09 (Vibe 3.0.3, glm-5-3)

Trigger: since the Vibe 3.0.3 upgrade (2026-10-29), delegations failed almost
every day: "Vibe did nothing", "Vibe crashed", "out of turns", "timeout".
Method:
- Read the run log and the session store turn by turn.
- Run the harness on real Vibe against a benchmark repo with hidden
  acceptance tests: 4 tasks × glm-5-3 `high`/`low` × 3 = 24 runs, plus 10
  edge-case runs and 4 final regression runs.
- Do not trust the script's own `RESULT` line: hidden tests decide.

Commits: `3c9edbf`, `253ed35`, `f5cbcf5`, `76f658d`.

## Baseline (31 runs since the Vibe 3 upgrade)

12 runs failed (39 %):

| Count | What the user saw | Verified cause |
|---|---|---|
| 7 | "crash" (exit 3) | **Out of turns** (12 model calls out of 12). Vibe 3 exit 3 = stopped on a limit, but the harness logged it as `exit_error`. |
| 4 | timeout | Not general slowness; see below. |
| 1 | exit 2 | Model API stream broke mid-run. |
| — | read-only runs died at once | `plan`, `default` and `lean` agents no longer exist in Vibe 3 (`Agent 'plan' not found`). |

What happened in each of the 4 timeouts, from the session journal:
- **280 s budget:** after reading 1 file, Vibe was generating a whole new
  module in one call.
- **590 s, exit 2:** 3 turns reading 10 files, then a big single-call write. The
  prompt had asked for "one single write call". The stream broke mid-generation.
- **592 s:** 6 turns of reading; one turn spent **47,000 characters** on hidden
  reasoning.
- **447 s:** the work was done (3 files). Vibe then ran a project-wide `tsc`
  with a 300 s timeout, and the budget expired during it.

An earlier note in this session blamed "re-read loops". That was wrong: it
came from miscounting journal records.

Reasoning volume over 318 model calls since the upgrade:
- 72 % of everything the model generated was hidden reasoning (`thinking = "high"`).
- Median reasoning per turn: 230 chars. 90th percentile: 8,810. Maximum: 128,494.
- Output rate is about 80 to 200 tokens/s, so a run's duration mostly tracks
  how much the model reasons.

## Fixes

| # | Bug | Fix | Verified by |
|---|-----|-----|-------------|
| 1 | Outcome guessed from heuristics | Every round runs with `--output-dir`. The verdict comes from Vibe's `export.json` (outcome, session id, exact tokens). | All runs |
| 2 | Out of turns = failure | **Auto-continue:** on `turn_limit`, the script resumes the *same* session (`--resume`), up to 2 more rounds. On a mid-run API failure, it resumes once. | A turn-limited task finished; 6 files over 3 rounds |
| 3 | External `timeout` killed the pty wrapper, so no export and no diagnosis | Vibe's own `--time-limit` stops the run cleanly and still writes the export. The outer `timeout` is now only a backstop. | 60 s budget: clean stop at 64 s, resume command printed |
| 4 | Timeout floor of turns × 90 s applied **per round** (worst case 54 min) | `timeout-secs` is one **total** budget, auto-continue rounds included. It is never raised; default 300 s. | 120 s budget with one continuation: 54 s. 60 s budget: no continuation |
| 5 | `plan`/`explore` agents dead | They map to `auto-approve` with the write tools disabled, plus a READ-ONLY note in the prompt. | Review run: 0 files written |
| 6 | **The write audit was blind:** it parsed a pre-Vibe-3 journal shape (`toolName`/`input`) and found 0 writes on every run since 2026-10-29 | It now reads `action_intent`/`action_result` records (`edit`, `search_replace`, `write_file`) with each call's own outcome. | Every benchmark run |
| 7 | Vibe prunes the live journal on every resume, so earlier rounds' writes vanished from the audit | The audit also reads each round's journal copy (`round-*/session/journal`), deduplicated by `action_id`. `--resume` skips earlier records by journal sequence. | 3-round run, 6/6 writes listed |
| 8 | Changed-file count included caches (2 real edits reported as 6) | `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache` and `node_modules` are pruned. | T1 runs |
| 9 | A 4xx from the model API was resumed like a transient failure | A 4xx (other than 429) → `usage_error`, never resumed. | `thinking=off`: 20 s and a clear verdict, instead of 75 s and `infra_error` |
| 10 | A deadline interrupt was shown as `[DENIED]` with a "path outside workdir" hint | Shown as `[STOPPED] … (run ended mid-call)`. | Deadline run |
| 11 | A `--resume` of an already-finished task → `FAILED [wrote_nothing]` | New verdict `ok_resumed_nothing_left` (OK). | Resume run |
| 12 | Editing or redeploying the script mid-run corrupted running delegations (`syntax error near done`) | The whole script is wrapped in `{ … }`, so bash parses it all before it runs. | File edited during a run: run finished OK |
| 13 | Dead `messages.jsonl` "recovery scan" could overwrite a whole file with an edit's `new_string` | Removed. | — |
| 14 | Vibe ran full builds or test suites inside the budget | The prompt gets a `CHECKS:` line: only quick, targeted checks; the caller verifies. | — |
| 15 | Prompts asked for "one single write call" of a big module, or listed 8-10 files to read | New prompt rules in SKILL.md, Step 3. | — |
| 16 | Tests polluted the real run log | Env overrides: `DELEGATE_RUN_LOG` for the log path, `DELEGATE_MODEL` for a one-run model alias. | Real log unchanged (3552 lines) |

## Benchmark

Fixture: a small Python package (`shop/`: money, catalog, orders, report),
with hidden pytest files copied in only after each run.

| Task | Shape |
|---|---|
| T1 | Small edit in 2 files |
| T2 | New module after reading 3 files, exact text format required (the shape of the real failures) |
| T3 | Rename across 3 files, keeping a deprecated alias |
| T4 | Root-cause bug fix, plus a regression test |

| Model alias | Hidden tests passed | Mean wall | Max wall | Cost (12 runs) |
|---|---|---|---|---|
| `glm-5-3` (`thinking = "high"`) | 11/12 | 93 s | 145 s | $1.33 |
| `glm-5-3-low` | 12/12 | 79 s | 118 s | $1.24 |
| `thinking = "off"` | — | — | — | API 400: `reasoning_effort 'none' is not supported` |

- **Harness verdict accuracy: 23 of 24 correct.** The one miss is a model
  formatting error (`Discount (10%)` missing its colon) that only project
  tests can catch. Always read the diff.
- **`high` vs `low`:** the difference is within noise on tasks this size, so
  the default is unchanged. The `glm-5-3-low` alias is defined in
  `~/.vibe/config.toml`. To settle it, replay 3 or 4 of the hard real-project tasks
  under each level.
- **Final regression** (script after all fixes): 4 out of 4 OK, hidden tests
  pass.

## Expected effect (estimate, not yet measured)

- **Failure rate:** 8 to 10 of the 12 baseline failures have a cause addressed
  above. Expected rate is about **10-15 %**, down from 39 %.
  - Still exposed: a large single-call generation under a 300 s budget, and a
    task too big for 3 rounds (ends `turn_cap`: split it, or resume).
- **Verdicts:** now verified against the journal. Their accuracy before the fix
  was not measured.
- **Unchanged:**
  - The quality of Vibe's code.
  - The duration of a successful run (median about 95 s).
  - Auto-continued tasks cost more (up to 3 rounds of turns), but they finish
    instead of failing.

**How to check:** after 20 to 30 real delegations, run
`/vibe-report --since 2026-11-09` and compare with 39 %. Above **20 %**, the
estimate was wrong: analyse the new failures turn by turn, as above.

## Benchmark reproduction

The fixture, tasks, hidden tests and runner (`run_one.sh TASK MODEL REP`) were
built in the session scratchpad and are not kept in the repo. Rebuild them
from the descriptions above. Always run with `DELEGATE_RUN_LOG` set.
