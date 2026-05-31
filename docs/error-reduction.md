# Error reduction — analysis & plan (2026-05-31)

Point-in-time analysis over **2,103 vibe delegations** (2026-05-12 → 2026-05-30),
real-project runs only (1,964; synthetic test scaffolds excluded). Numbers are a
dated snapshot — do not edit in place; append a new dated analysis if they change.

## Observed errors → fixes → gaps

| Error | Rate | Root cause | Implemented today | Effect | Missing lever |
|---|---|---|---|---|---|
| `exit_error` | 18.7% | Engages (~7 tool calls) then exits non-zero, 95% wrote nothing — multi-edit context drift or first `search_replace` target not byte-exact → abandons | SKILL.md: decompose, one change/run, grep-target-first | Advisory only — nothing enforces it | Pre-flight **target-presence gate** in `vibe-delegate` |
| `wrote_nothing` | 7.1% | Tool calls, 0 files, exit 0 — same drift/no-op, or already done | `failure_reason` taxonomy; `output_format` adaptation | Measures + perceives, doesn't prevent | Same target-gate; distinguish "already done" |
| `sr_fail` | 2.4% | `search_replace` byte miss — accents, backticks, indent drift | Prompt-via-tempfile; guidance: `python str.replace` | Reduces prompt-side only; vibe-internal match still fails | Auto-fallback to `str.replace` for non-ASCII targets |
| `warn_only` | 2.5% | Non-fatal tool errors | `[WARN]` surfacing | Perceives — usually harmless | Low priority |
| `near_empty` | 1.6% | <50 tokens out, nothing written — prompt too thin | `compact`/`contract` tracking | Measures | Min-prompt-quality gate |
| `syntax_error` | 0.4% | Wrote invalid code | Post-run syntax gate | Catches, doesn't prevent | Optional `--revert-on-syntax-error` |
| `timeout` | 0.3% | Task too large | `max-turns` cap, decompose | Reduces — already low | Adequate |
| model mismatch | — | `devstral-small` 63% ok — agent-mode model for inline edits | Synthesis note; `/vibe-model-pick` | Documents | Codify routing in SKILL.md |

## The consolidation that matters

`exit_error` + `wrote_nothing` ≈ **26%** are one bug: *vibe engaged but never landed
an edit.* Everything else is ≤2.5%. One lever covers the dominant share — stop the
run before it starts when the edit anchor can't be matched.

## Prioritized plan

| # | Action | Attacks | Type | Status |
|---|---|---|---|---|
| 1 | **Target-presence gate** — `--require "<string>"` (repeatable) on `vibe-delegate`; grep in workdir before launch, abort + log `precheck_abort` if absent | `exit_error`, `wrote_nothing`, `sr_fail` (~28%) | Prevention + enforcement | **implemented 2026-05-31** |
| 2 | Accent/backtick auto-fallback to `python str.replace` | `sr_fail` | Prevention | todo |
| 3 | Model-routing guidance: inline-edit → mistral-medium/deepseek; agent-mode (devstral) → read/explore only | model-mismatch `exit_error` | Guidance | todo |
| 4 | Make `contract`/`output_format` adaptations default, then read `/vibe-report --adapt` after ~100 adapted runs | correctness + perceived failures | Measurement → proof | todo (0 adapted runs so far) |

Only #1–#2 are true error *reducers*. #3 is routing. #4 is the feedback loop that
proves whether the adaptation work moved the rate — without it we are guessing.
