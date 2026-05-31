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
| 2 | Accent/backtick auto-fallback to `python str.replace` | `sr_fail` | Prevention | **deferred** (see below) |
| 3 | Model-routing guidance: inline-edit → mistral-medium/deepseek; agent-mode (devstral) → read/explore only | model-mismatch `exit_error` | Guidance | **implemented 2026-05-31** |
| 4 | Apply `contract`/`output_format` adaptations on a *fraction* of eligible runs, then read `/vibe-report --adapt` after ~100 adapted runs; default only if the rate drops | correctness + perceived failures | Measurement → proof | **deferred** (see below) |

## Why #2 and #4 are deferred — and when to revisit

**#2 (accent/backtick auto-fallback) — deferred as overengineering.**
To actually perform a fallback edit, `vibe-delegate` would need both the *old* and
the *new* string. It only has the freeform prompt. The `--require` gate works because
it only needs the old anchor (to grep); a real fallback edit would mean building a
structured `--replace "old" "new" file` mini-editor into the delegate, bypassing vibe
entirely. That is disproportionate machinery for a **2.4%** failure class, and the
non-overengineered form is just guidance that already half-exists in Known Limits.
- **Revisit when:** `sr_fail` climbs and stays above ~5% of runs, **or** a structured
  edit interface gets added to the delegate for some other reason (then the fallback
  is nearly free to bolt on).

**#4 (default the adaptations) — deferred because it must follow evidence, not precede it.**
Defaulting `contract`/`output_format` means appending a signature + receipt block to
*every* prompt before we have a single adapted run to judge them by (currently **0**).
It is also self-defeating: if every run is adapted, `/vibe-report --adapt` has no
non-adapted baseline to compare against — defaulting destroys the very A/B signal that
would justify it. So the correct sequence is measure → then default.
- **Revisit when:** ~100 eligible runs have been delegated *with* adaptations applied
  (Claude passing typed signatures / receipt blocks on a fraction of edit tasks). At
  that point `/vibe-report --adapt` shows whether the adapted cohort has a lower
  failure rate than the unadapted one. Default the winning adaptation only if it does.

Only #1–#2 are true error *reducers*; #1 is shipped, #2 is parked. #3 is routing
(shipped). #4 is the feedback loop that proves whether the adaptation work moved the
rate — it stays open until enough adapted runs exist to read.
