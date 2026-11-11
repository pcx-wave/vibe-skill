---
name: vibe
description: >
  Delegate a coding task to Mistral Vibe and supervise the result via git diff.
  Trigger: /vibe <instruction>. Claude orchestrates, Vibe codes.
license: MIT
user-invocable: true
allowed-tools:
  - Bash
  - Read
  - Grep
---

# Vibe Orchestrator

`/vibe <instruction>`: Claude writes a prompt, `~/tools/vibe-delegate` runs Mistral
Vibe on it, Claude checks the result and reports. Details, edge cases and the
`--with-review` procedure are in `SKILL-reference.md` (same directory): read only
the section you need. Toggles, model choice and reports are separate skills
(`/vibeon`, `/vibeoff`, `/vibestatus`, `/vibe-model-pick`, `/vibe-model-clear`,
`/vibe-report`).

## 0. Delegate or not

Delegation has a fixed cost in Claude's own context (this skill plus the run
report). It pays only when Vibe does the reading and the thinking.

| Task | Action |
|---|---|
| 1 file, ≤10 lines, location known | Edit directly |
| You could do it in 1-2 turns yourself | Edit directly: a delegation costs a prompt, a run and a review, and a failed one costs double |
| You could paste the final code into the prompt | Edit directly (you already did the work) |
| Location unknown, logic to write, several files, much code to read | Delegate |

## 1. Workdir and decomposition

- Workdir = `git rev-parse --show-toplevel`; ask if ambiguous.
- One objective per run. 1 file: 5-8 turns. 2-3 files: 8-12 turns. Several
  distinct objectives or business logic: split into sequential runs and check
  `git diff` between them. Never more than 12 turns. A turn costs ~60–90 s wall
  clock under a thinking model: at 300–480 s only ~4–6 turns run, so keep one
  run to ONE new file at that budget.
- Split by objective, not by file: the same mechanical change across 10 files
  is ONE run (each run costs you a prompt, a report and extra turns; a
  10-module change split into 8 runs cost 35 % more than the same change in 4).

## 2. Write the prompt (English, self-contained)

```
Stack: <languages, frameworks>                  # optional
TASK: <one imperative>
MODIFY: a.py, b.py                             # files to change; read-only agents omit this line
CONSTRAINTS: <what must not break; exact signatures; data field paths>  # optional
VERIFY: grep for "<exact new line>" in <file>
```

- **Never write the code or the final text for Vibe**: not in the prompt, and
  not in a spec/staging file you ask it to apply "exactly". That pays for the
  work twice (21 % of past delegations did it). Describe the goal, the files,
  the constraints and the check; Vibe writes the code. An exact signature or a
  one-line anchor is fine. If you already have the code, apply it yourself.
  The script refuses prompts with 10+ lines of code (`--allow-code` overrides).
- **Keep the prompt short** (≈1,500 characters at most): you pay it at output
  price. Goal, files, constraints, check. Do not explain what Vibe can read
  in the files itself. (Past prompts: 3,000 characters median.)
- **Cap the reading**: ≤ 4 reference files in total (inline mentions in
  TASK/VERIFY count). Say: "grep -n for the anchors, read only those regions,
  never re-read". Never write "read X first" in the prompt; cap `file:line`
  comments to "the 3–5 main formulas". Reading burns the budget (one 2026-11-10
  run: 485 s, 128k tokens, 0 files, all reads).
- Name the exact files to modify. Say "the edit tool", not "search_replace".
- **Give the regions, don't make Vibe grep them**: when you already know the
  lines, `sed -n 'A,Bp' file` yourself and pass `--include file:A-B` (repeatable)
  — the harness injects the verbatim region as a REFERENCE block and Vibe uses
  it directly. The launch preflight refuses (exit 2, nothing launched) a prompt
  that misses a `TASK:`/`MODIFY:`/`VERIFY:` header (MODIFY optional for
  read-only agents), names > 4 files, or says "read … first".
- Files Vibe must read have to be **inside the workdir** (outside paths are
  denied silently).
- Never ask for one single write of a big new file: let it write in parts.
- Accented characters or emoji in the text to replace: tell Vibe to use
  `python3` with `pathlib` read/write (utf-8) for that change.
- Input data Vibe must use (HTML, a sample, a reference file you did not
  write): put it in a file inside the workdir and point to it.
- Before an edit prompt, `grep -n` the anchor yourself and pass it as `--require`.

## 3. Launch

```bash
~/tools/vibe-delegate "<workdir>" "<prompt>" [max-turns=10] [agent] [timeout-secs=300] [--require "<anchor>"]
```

- `agent`: none for edits; `plan` for read-only review/analysis (writes disabled).
- Resume: same feature / fix-up after `PARTIAL` → `--resume-last`; unrelated
  task → `--no-resume`. By default the harness **auto-resumes** the last
  same-workdir session when the previous run was limit-stopped (last run < 24 h,
  resume chain < 3) — printed as `[auto-resume] …` and logged. Resuming is cheap
  (measured 77–88 % of re-sent input is cache hits, median 87 %, n=3 runs with
  cache data); a fresh session re-reads all. On a limit stop, orphaned writes are
  saved to `.vibe-recovery/` (not applied).
- `timeout-secs` is the total budget — count `max-turns × 80 s` (a turn is
  ~60–90 s with a thinking model): 12 turns ≈ 600–960 s. The script clamps
  max-turns to `timeout/80` itself (warning printed), so the budget told to
  Vibe is always spendable. Out of turns → same session resumed up to 2 rounds.
- `--resume <id>` continues a partial run (the id is printed on failure).
- Foreground or background both work. In the foreground, set the Bash tool
  timeout to `(timeout-secs + 120) × 1000` ms (max 600000). In the background,
  **do not poll its output**: wait for the completion notification. Each poll
  is a full turn of your context (16 % of past background runs polled).

## 4. Read the result

The **last line** is the verdict; trust it over anything Vibe narrated.

| Last line | Do |
|---|---|
| `RESULT: OK — N file(s) changed` | Writes landed. Review the `DIFF` block printed just above, in this same turn: the harness checks writes, not correctness. Run an extra `git diff`, grep or Read only for what that block truncated or what looks wrong |
| `RESULT: READ-ONLY run` | Use the `VIBE FINAL ANSWER` block |
| `RESULT: PARTIAL [reason]` | Files landed despite the limit: review the DIFF, finish with the printed `--resume` — never a fresh run for the rest of this task |
| `FAILED [turn_cap]` / `[timeout]` / `[budget_limit]` | Maybe partial: FIRST `git status --short` + read the diff (a write in flight at the limit can land late), then the printed `--resume <id>` — never a fresh session for the remainder. Or split |
| `FAILED [verify_fail]` | Files landed but the `VERIFY:` command failed (exit 3): the task is not done. Read the diff and Vibe's ASSUMED line, then resume to fix |
| `FAILED [usage_error]` | Bad agent, flag or model setting: fix it, never retry verbatim |
| `FAILED [infra_error]` | Model API down: retry later or resume |
| `FAILED [wrote_nothing]`, `[write_mismatch]`, `[syntax_error]`, others | Read the `WRITE AUDIT` block, then step 5 |

Just above the verdict, `=== DELEGATION REPORT ===` is built from disk, not narration:
STATUS, FILES (vs `MODIFY:`: `declared, not written` / `written, not declared`),
VERIFY (the `VERIFY:` line run in the workdir, 60 s: PASS / FAIL / NOT RUN if prose),
RUN, VIBE (its DONE / NOT DONE / ASSUMED / BLOCKED / CHECK lines), RECOVER, NEXT.
Any `CONTRADICTION:` line overrides `RESULT: OK`: the task is not done. So write
`VERIFY:` as one shell command; Vibe sees it and may code to it, so check ASSUMED.

`VIBE FINAL ANSWER` is Vibe's own summary; quote it, not the cut `[vibe]` lines.
Vibe must not commit; if a `COMMITS CREATED` block appears, review those commits.

## 5. When a run fails

- Read the diff before relaunching, so you do not redo partial work.
- Revise the prompt (smaller scope, exact file, exact anchor) and retry. At most
  3 attempts per sub-task.
- After 3 failures, finish the task yourself and list those files as
  "ghostwritten" in the report. With `--no-ghostwrite`, stop and ask instead.
- Unusual flags (`[DENIED]`, `[ERROR]`, garbled tool names): see
  "Step 5" in `SKILL-reference.md`.

## 6. Report

```
✓ Vibe finished — <one line>
Files modified:
  - <path> (+X / -Y)
[Files ghostwritten: ...]
[⚠ problem — what you did about it]
Ready to commit?
```

With `--verbose`, quote the script's token/cost block verbatim. With
`--with-review N`, follow "Step 8" in `SKILL-reference.md`.
