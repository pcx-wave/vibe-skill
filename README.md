<!-- Suggested GitHub topics: claude-code, llm-tools, mistral, gemini-cli, ai-coding, shell, developer-tools, vibe-coding -->

# vibe-skill

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg) ![Shell](https://img.shields.io/badge/language-Shell-green.svg) ![GitHub stars](https://img.shields.io/github/stars/pcx-wave/vibe-skill?style=social) ![Claude Code skill](https://img.shields.io/badge/-Claude%20Code%20skill-CC785C)

**Claude orchestrates. Vibe does the heavy lifting. You review the diff, save tokens, costs and avoid hitting limits!**

Claude only reads the script's summary: ≈700–1,100 tokens of output per run in the 2026-11-09 benchmark, plus the prompt it writes, however many files Vibe reads internally (a median Vibe 3 run processes ≈215k tokens).

Note that Vibe works natively with Mistral models which are capable and significantly cheaper than Claude, but Vibe can also be configured to use any other provider/model instead. Eg you can use a deepseek model with vibe tooling. 

Summary:
1. User types `/vibe <instruction>` in Claude Code
2. Claude decomposes the task and writes a prompt
3. `vibe-delegate` runs Mistral Vibe in a pseudo-TTY, within a turn and time budget
4. If Vibe runs out of turns, the same session is resumed automatically (it keeps its context)
5. The delegate checks every write against Vibe's session journal and prints one verdict line: `RESULT: OK` or `RESULT: FAILED [reason]`
6. Claude reviews the diff and summarizes the result

---

## Why

**Cost savings** — Vibe's file reads and edits consume delegate tokens (or whatever model you configure), not Claude tokens. Most of a run's input is the conversation re-sent on every model call, and about 92 % of it is served from the provider's cache. Measured on 4 benchmark tasks with `glm-5-3` (2026-11-09; cost as billed by Vibe's own run export):

| Per run | Range over 4 tasks |
|---|---|
| Tokens processed by Vibe | 59k – 108k (90 – 94 % of input cached) |
| Delegate cost (cache-aware) | $0.028 – $0.041 |
| Same tokens and cache share at Claude Sonnet 4.6 rates ($3 in, $0.30 cached, $15 out per M) | $0.055 – $0.072 (≈1.9× more) |
| Wall time | 52 – 60 s |

> Production runs are larger: the median Vibe 3 run (28 runs, 2026-10-29 → 2026-11-09) processed 215k tokens. Their cost was logged before the harness read the cache split, at list price with no cache discount ($0.35 median; Claude equivalent $0.88). On the benchmark runs that method overstated the delegate cost 3.1 – 3.8× and the Claude equivalent 3.5 – 4.8×. Since 2026-11-09 each run logs `cost_usd` from Vibe's export (`cost_source: vibe_export`) and a cache-aware `cost_claude_eq`. The "same tokens" comparison is only indicative: Claude doing the task itself would make a different number of calls. On a Mistral Pro subscription, usage inside the plan's limits costs no API fee. List prices checked on 2026-11-09: Mistral Medium 3.5 $1.50/$7.50, DeepSeek V4 Flash $0.14/$0.28 per M tokens.

> **Delegation does cost Claude tokens** — writing the prompt and reading the result back. But the real lever is context: when Claude does the work directly, every file read accumulates in its context and is re-read on every subsequent turn. When Vibe does it, none of that enters Claude's context at all. Modelled breakeven (prompt and result sizes measured, file sizes modelled): **≈4 source files touched per task**. Below that, direct is cheaper. Above it, delegation wins by a growing margin (+66% at 10 files, +89% at 30 files). See [handoff-probe/ECONOMICS.md](https://github.com/pcx-wave/handoff-probe/blob/main/ECONOMICS.md) for the full analysis.

> **Pro plan users:** Mistral Vibe (CLI included) is part of Mistral's [Pro plan](https://mistral.ai/pricing), $14.99/mo excluding tax as of 2026-11-09. Mistral does not publish the exact usage limits; beyond them, usage continues pay-as-you-go at API rates. Inside the limits, delegations cost no API fee.

### Delegation synthesis — as of 2026-06-08 (Vibe 2.x, historical)

> **These numbers predate Vibe 3** (released 2026-10-29), which changed the CLI's exit codes, agents and session format. Right after the upgrade, 12 of 31 delegations failed (39 %) and the harness misread most of them. The 2026-11-09 audit ([`docs/harness-audit-2026-11-09.md`](docs/harness-audit-2026-11-09.md)) has the causes, the fixes and a 24-run benchmark with hidden acceptance tests: the verdict was correct on 23 of 24 runs. Fresh Vibe 3 production numbers will replace this section once enough runs exist.

Snapshot over **2,450 vibe delegations**, 2026-05-12 → 2026-06-08 (28 days). Pulled from the shared run log via `delegate-report` (vibe scope).

**Performance & savings**

| Metric | Value |
|---|---|
| Delegations | 2,450 |
| Tokens delegated | 155.2M |
| Exit-success rate | 79% |
| Avg run duration | 32s |
| **Real cost (with sub)** | **$0 Mistral (inside the Pro subscription) + $0.67 DeepSeek** |
| Mistral at API rate (no sub) | ~$37 cache-aware estimate ($151 at list price without cache, as logged) |
| Same workload on Claude Sonnet 4.6 | ~$139 (cache-aware, 90.5% hit rate) |

**By model**

| Model | Runs | Exit-ok | Tokens | With sub | API ref (no sub) | vs Claude |
|---|---|---|---|---|---|---|
| mistral (Le Chat Pro) | 1,911 | 78% | 111.9M | $0 | ~$37 | ~$101 |
| deepseek-flash | 369 | 88% | 35.5M | $0.67 | $0.67 | ~$32 |

> Real cost methodology: All Mistral runs (mistral-medium-3.5 + Le Chat interface) covered by Le Chat Pro subscription — $0 marginal cost. DeepSeek $0.67 is actual spend (from logs). Hit rate of 90.5% back-calculated from that spend. Claude equivalent applies the same hit rate with Claude's cache pricing ($0.30/M hits, $3/M misses, $15/M output), assuming 97.6% input / 2.4% output split.

`deepseek-flash` was the value pick (88% exit-ok at ≈$0.002/run: $0.67 over 369 runs).

**Error rate** (earlier snapshot of 2026-05-30: real projects, 1,964 runs, synthetic test scaffolds excluded)

| Class | Rate | What it is |
|---|---|---|
| clean ok | 67.1% | completed and wrote files |
| `exit_error` | 18.7% | engaged (≈7 tool calls) then exited non-zero, **95% wrote nothing** |
| `wrote_nothing` | 7.1% | tool calls but 0 files, exit 0 |
| `warn_only` | 2.5% | non-fatal warnings, usually fine |
| `sr_fail` | 2.4% | `search_replace` byte-match miss (accents, backticks) |
| `near_empty` | 1.6% | <50 tokens out, nothing written |
| `syntax_error` | 0.4% | wrote invalid code (caught by post-run gate) |
| `timeout` | 0.3% | task too large / context saturated |

At the time, the ≈26 % `exit_error` + `wrote_nothing` was attributed to Vibe engaging but landing no edit: multi-edit context drift, or a first `search_replace` anchor not found byte-for-byte. That diagnosis was not re-verified per run. The `--require` gate added then aborts the anchor-not-found case before launch.

**Versus the other delegate (`opencode`)**

| | vibe | opencode |
|---|---|---|
| Runs | 2,450 | 254 |
| Tokens | 155.2M | 8.5M |
| Exit-ok | 79% | 81% |
| Real cost | $0.67 + Pro subscription | $0 (free tiers) |
| Models | mistral-medium, deepseek-flash (paid, capable) | free deepseek / mimo / nemotron tiers |

Same headline exit-rate, very different profile: `opencode` runs free tiers at zero cost, but 25 % of its runs produced nothing and 19 % timed out over the same period (vibe: 5 % and 0.2 %). Use it for cheap exploration; vibe's paid models are the choice when the edit has to land. Both write to the same log — `/vibe-report --all` compares them.

---

## Prerequisites

- [Mistral Vibe](https://vibe.mistral.ai/) CLI **3.x**, installed and authenticated (`vibe --version`; tested with 3.0.3). Vibe 2.x is no longer supported: the harness reads Vibe 3's run export and session journal.
- [Claude Code](https://claude.ai/code) with skills enabled
- `python3` (pseudo-TTY via `pty.spawn`, stream parsing, audits) and optionally `node` for JS syntax checks
- `timeout` on your `PATH` (GNU coreutils; on macOS, `brew install coreutils` installs it as `gtimeout`, so add coreutils' `gnubin` directory to `PATH`). It is only a backstop: Vibe's own `--time-limit` stops the run first
- A git repository to work in

---

## Installation

```bash
git clone https://github.com/pcx-wave/vibe-skill.git && cd vibe-skill && mkdir -p ~/tools ~/.claude/skills/vibe ~/.claude/skills/vibeon ~/.claude/skills/vibeoff ~/.claude/skills/vibestatus ~/.claude/skills/vibe-model-pick ~/.claude/skills/vibe-model-clear ~/.claude/skills/vibe-report && ln -sf "$(pwd)/tools/vibe-delegate" ~/tools/vibe-delegate && ln -sf "$(pwd)/tools/delegate-report" ~/tools/delegate-report && chmod +x ~/tools/vibe-delegate ~/tools/delegate-report && ln -sf "$(pwd)/SKILL.md" ~/.claude/skills/vibe/SKILL.md && ln -sf "$(pwd)/SKILL-reference.md" ~/.claude/skills/vibe/SKILL-reference.md && ln -sf "$(pwd)/VIBEON.md" ~/.claude/skills/vibeon/SKILL.md && ln -sf "$(pwd)/VIBEOFF.md" ~/.claude/skills/vibeoff/SKILL.md && ln -sf "$(pwd)/VIBESTATUS.md" ~/.claude/skills/vibestatus/SKILL.md && ln -sf "$(pwd)/VIBE-MODEL-PICK.md" ~/.claude/skills/vibe-model-pick/SKILL.md && ln -sf "$(pwd)/VIBE-MODEL-CLEAR.md" ~/.claude/skills/vibe-model-clear/SKILL.md && ln -sf "$(pwd)/VIBE-REPORT.md" ~/.claude/skills/vibe-report/SKILL.md
```

### Step-by-step

```bash
# 1. Clone this repo
git clone https://github.com/pcx-wave/vibe-skill.git
cd vibe-skill

# 2. Install the scripts (symlinks — stay in sync with git pull)
mkdir -p ~/tools
ln -sf "$(pwd)/tools/vibe-delegate" ~/tools/vibe-delegate
ln -sf "$(pwd)/tools/delegate-report" ~/tools/delegate-report
chmod +x ~/tools/vibe-delegate ~/tools/delegate-report

# 3. Install the skills for Claude Code
mkdir -p ~/.claude/skills/vibe ~/.claude/skills/vibeon ~/.claude/skills/vibeoff ~/.claude/skills/vibestatus \
         ~/.claude/skills/vibe-model-pick ~/.claude/skills/vibe-model-clear ~/.claude/skills/vibe-report
ln -sf "$(pwd)/SKILL.md" ~/.claude/skills/vibe/SKILL.md
ln -sf "$(pwd)/SKILL-reference.md" ~/.claude/skills/vibe/SKILL-reference.md
ln -sf "$(pwd)/VIBEON.md" ~/.claude/skills/vibeon/SKILL.md
ln -sf "$(pwd)/VIBEOFF.md" ~/.claude/skills/vibeoff/SKILL.md
ln -sf "$(pwd)/VIBESTATUS.md" ~/.claude/skills/vibestatus/SKILL.md
ln -sf "$(pwd)/VIBE-MODEL-PICK.md" ~/.claude/skills/vibe-model-pick/SKILL.md
ln -sf "$(pwd)/VIBE-MODEL-CLEAR.md" ~/.claude/skills/vibe-model-clear/SKILL.md
ln -sf "$(pwd)/VIBE-REPORT.md" ~/.claude/skills/vibe-report/SKILL.md

# 4. (Optional) Enable auto-mode — Claude delegates all code tasks automatically
#    without requiring /vibe each time. Toggle with /vibeon and /vibeoff.
grep -q "vibe auto-mode" ~/.claude/CLAUDE.md 2>/dev/null || cat >> ~/.claude/CLAUDE.md << 'EOF'

# vibe auto-mode
At the start of every user request that involves writing, editing, or fixing code:
1. Run `test -f ~/.local/share/vibe-auto.flag` (silent, no output to user).
2. If the flag exists → automatically invoke the `vibe` skill exactly as if the user had typed `/vibe <their full instruction>`. Do NOT ask first, do NOT explain — just delegate.
3. If the flag is absent → proceed normally.

The flag is toggled by `/vibeon` and `/vibeoff`.
EOF

```

Verify with a read-only run (it must not write anything):

```bash
mkdir -p /tmp/vibe-check && ~/tools/vibe-delegate /tmp/vibe-check "Say hello in one sentence." 3 plan
# last line: === RESULT: READ-ONLY run (no writes expected) ===
```

### Updating

Because both installs use symlinks, a `git pull` is all you need:

```bash
cd ~/vibe-skill && git pull
```

`~/tools/vibe-delegate` and `~/.claude/skills/vibe/SKILL.md` are automatically up to date — no re-copy needed.

> **Migrating from a previous `cp`-based install?** Replace the copies with symlinks:
> ```bash
> cd ~/vibe-skill
> ln -sf "$(pwd)/tools/vibe-delegate" ~/tools/vibe-delegate
> ln -sf "$(pwd)/SKILL.md" ~/.claude/skills/vibe/SKILL.md
> ```

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

### Flags

All optional — the no-flag path stays the default and lightest:

```
/vibe --with-review N <instruction>      — Claude reviews Vibe's diff and re-delegates fixes up to N times
/vibe --verbose <instruction>            — print per-model token/cost breakdown when done
/vibe --no-ghostwrite <instruction>      — halt on repeated Vibe write failures instead of finishing
```

- **`--with-review N`** — after Vibe finishes, Claude takes a reviewer pass over the changes and re-delegates a fix for each fundamental issue (logic/crash/contract/scope/security only — not style), up to N iterations. Trades Claude tokens for less manual review.
- **`--verbose`** — prints the token/cost block per model: I/O with the coder model (e.g. Mistral), the total, and the projected Claude-token cost it spared.
- **`--no-ghostwrite`** — by default, if Vibe writes nothing after 3 retries, Claude finishes the task itself (ghostwrite fallback) so the run never strands — ghostwritten files are reported separately. `--no-ghostwrite` disables that fallback: after 3 failed attempts Claude halts and asks you (retry / abort) instead.

### Calling the script directly

Claude calls this for you, but it works on its own:

```bash
~/tools/vibe-delegate <workdir> "<prompt>" [max-turns] [agent] [timeout-secs] [options]
```

| Argument / option | Default | What it does |
|---|---|---|
| `max-turns` | `10` | Model calls per round, hard cap 12. Decompose rather than raise it |
| `agent` | `auto-approve` | `plan` (also `explore`, `code-reviewer`, …) = **read-only**: write tools disabled. `default`/`lean` map to `auto-approve` (Vibe 3 removed them) |
| `timeout-secs` | `300` | **Total** wall-clock budget, auto-continue rounds included. Never raised by the script |
| `--continue-rounds N` / `--no-continue` | `2` | Extra rounds on the **same session** when Vibe stops on its turn limit |
| `--resume <session-id>` | — | Continue an earlier session; the id is printed on every partial run |
| `--require "<string>"` | — | Repeatable. Abort before launching if the string is not in the workdir (pass your edit anchor) |
| env `DELEGATE_MODEL=<alias>` | flag file | Model alias for this run only |
| env `DELEGATE_RUN_LOG=<path>` | `~/.local/share/delegate-runs.jsonl` | Write the run log elsewhere: use it for tests so they never pollute your real log |

### Model selection

By default, Vibe uses whatever `active_model` is set in `~/.vibe/config.toml`. You can override it per-session without touching that file:

```
/vibe-model-pick              — interactive menu built from your config.toml models
/vibe-model-pick devstral-small  — switch directly by alias
/vibe-model-clear             — remove the override, return to config default
/vibestatus                   — shows both auto-mode state and active model override
```

`/vibe-model-pick` only lists models that already exist in `~/.vibe/config.toml`. To use a model that isn't there yet, you have to add it first — e.g. to add DeepSeek:

1. Add a `[[providers]]` block with the API endpoint and the env var holding the key (never put the key itself in the file):

   ```toml
   [[providers]]
   name = "deepseek"
   api_key_env_var = "DEEPSEEK_API_KEY"
   api_base = "https://api.deepseek.com"
   api_style = "openai"
   backend = "generic"
   ```

2. Add a `[[models]]` block pointing at that provider, with an `alias` you'll use to select it:

   ```toml
   [[models]]
   name = "deepseek-v4-flash"
   provider = "deepseek"
   alias = "deepseek-flash"
   temperature = 0.7
   input_price = 0.14
   output_price = 0.28
   ```

3. Export the key in your shell env: `export DEEPSEEK_API_KEY=sk-...`

4. Either set `active_model = "deepseek-flash"` at the top of `config.toml` to make it the permanent default, or run `/vibe-model-pick deepseek-flash` to use it for the current session only.

`input_price`/`output_price` are only used for Vibe's own cost-tracking display — they're optional and don't affect functionality.

The override is stored in `~/.local/share/vibe-model.flag` and is picked up by `vibe-delegate` on every run. It persists across sessions until you clear it.

**Reasoning effort.** A model's `thinking` level in `config.toml` drives most of a run's duration: in the Vibe 3 sessions of 2026-10-29 → 2026-11-09 (mostly `glm-5-3` at `high`), 72 % of everything the model generated was hidden reasoning. You can define a second alias of the same model with a lower level and pick it with `/vibe-model-pick`. In the 2026-11-09 benchmark, `low` vs `high` on `glm-5-3` gave 12/12 vs 11/12 tasks passed and 79 s vs 93 s mean, which is within noise on small tasks. Not every level is accepted: `glm-5-3` rejects `off` with an API 400, which the script reports as `FAILED [usage_error]`.

### Vibe-auto mode

For frictionless delegation, enable auto-mode once in your Claude Code session:

```
/vibeon      — every code request is automatically delegated to Vibe, no /vibe prefix needed
/vibeoff     — return to normal Claude behaviour
/vibestatus  — auto-mode state + active model override
```

With `vibeon` active, just talk to Claude normally:

```
add pagination to the /posts route
fix the broken email validation
refactor the auth middleware into its own module
```

Claude intercepts code requests and applies a pre-filter before delegating:

| Task | Action |
|---|---|
| 1 file, ≤10 lines, exact location known | Claude edits directly — no delegation overhead |
| The code to insert is already written out | Claude edits directly — delegating would pay for it twice |
| Everything else | Delegated to Vibe |

Pure questions and conversations always go directly to Claude.

---

## Terminal output

Sample output from a real run (benchmark task; abridged, path shortened):

```
=== VIBE START ===
Workdir : /path/to/project
Agent   : auto-approve
Model   : glm-5-3
Turns   : 10
Timeout : 300s total (all rounds)
Prompt  : Bug: an Order with discount_percent=10 ... gives total() == 3868 cents, but the...
===================
  [vibe] The bug is in `discount_amount`: it rounds per unit instead of once on the subtotal. Fixing it now.
  [tool]  file: /path/to/project/shop/orders.py
  [vibe] Now adding the regression test:
  [tool]  file_system.bash: cat >> tests/test_basic.py ...
Tool calls: 5  |  warns: 0  |  sr_fails: 0
Model               : glm-5-3
Delegate tokens (run): 69,531  |  cost ~$0.1007

=== VIBE FINAL ANSWER (full, last model message from the session journal) ===
All 3 tests pass. Changes: shop/orders.py discount_amount now applies the
discount once to the subtotal ... tests/test_basic.py adds a regression test ...

=== VIBE DONE (exit: 0, outcome: finished, rounds: finished) ===
=== SYNTAX OK (2 check(s)) ===

=== WRITE AUDIT (journal vs disk) ===
  edit           shop/orders.py  call: ok  disk: CHANGED
  [note] tests/test_basic.py changed on disk without a write call (bash/run_typescript, or a generated file)

=== UNCOMMITTED CHANGES ===
 shop/orders.py      |  6 +-----
 tests/test_basic.py | 13 ++++++++++++-
[log] → ~/.local/share/delegate-runs.jsonl  (69531 tokens, exit 0, 95.7s)
=== RESULT: OK — 2 file(s) changed, verified against the session journal ===
```

### Reading the verdict

The **last line** is the verdict. Read it before anything Vibe narrated:

| Last line | Meaning | What to do |
|---|---|---|
| `RESULT: OK — N file(s) changed` | Every write call Vibe journaled landed on disk | Review `git diff`: the harness checks writes, not correctness |
| `RESULT: OK (UNVERIFIED)` | Files changed but no session journal was found to check them against | Review `git diff` |
| `RESULT: OK — resumed session finished with nothing left to write` | A `--resume` whose earlier run had already done the work | Read the final answer |
| `RESULT: READ-ONLY run` | `plan`-type run, nothing written by design | Read the final answer |
| `RESULT: FAILED [turn_cap]` | Still out of turns after the auto-continue rounds | Split the task, or run the printed `--resume <id>` command |
| `RESULT: FAILED [timeout]` | Total time budget used up; Vibe stopped cleanly | Same: resume or split |
| `RESULT: FAILED [infra_error]` | Model API failed again after one automatic resume | Retry later, or resume |
| `RESULT: FAILED [usage_error]` | Vibe or the provider rejected the request (bad agent, flag, model setting) | Fix it; never retry verbatim |
| `RESULT: FAILED [wrote_nothing]` and others | Vibe explored but wrote nothing, a write did not land, syntax error, … | Inspect the WRITE AUDIT block |

The script's exit code is non-zero on every `FAILED`, so `vibe-delegate ... && next-step` stops there. Vibe must not commit: the prompt tells it to leave every change uncommitted, so `git checkout .` reverts a run. In the 520 delegated sessions on record it never committed in the project (once, in a throwaway test repo under `/tmp`). If it ever does, the script prints a `COMMITS CREATED` block.

---

## How vibe-delegate works

```
Claude Code
  └─ /vibe <instruction>
       └─ SKILL.md logic
            └─ ~/tools/vibe-delegate <workdir> <prompt> [turns] [agent] [timeout]
                 ├─ writes prompt to temp file (avoids shell injection with UTF-8/emoji)
                 │    + appends the turn budget and a "quick checks only" rule
                 ├─ runs: python3 -c 'pty.spawn(<vibe-script>)'   (vibe hangs without a TTY)
                 │    vibe -p ... --max-turns N --time-limit T --output-dir <round dir>
                 ├─ streams JSON output through a parser → [read] / [tool] / [WARN] / [vibe] lines
                 ├─ reads Vibe's export.json: outcome, session id, exact token usage
                 │    └─ turn limit hit? resume the same session (up to 2 more rounds,
                 │       within the remaining time budget)
                 ├─ prints Vibe's final answer, from the session journal
                 ├─ runs syntax checks on modified .py and .js files
                 ├─ WRITE AUDIT: every edit/write call in the journal vs files changed on disk
                 ├─ prints git diff --stat
                 ├─ appends JSON entry to ~/.local/share/delegate-runs.jsonl
                 └─ prints the RESULT verdict line
```

> Cost figures are estimates. See [`SKILL-reference.md`](SKILL-reference.md#cost-estimate-methodology) for methodology.

---

## Examples

- `examples/good-prompts.md` — prompt patterns that reliably work
- `examples/anti-patterns.md` — what fails and why, with fixes

---

## Sister projects

Parallel delegates using the same orchestration pattern and run log format — different models and trade-offs:

- [pcx-wave/gemini-skill](https://github.com/pcx-wave/gemini-skill) — delegate to **Gemini CLI**
- [pcx-wave/opencode-skill](https://github.com/pcx-wave/opencode-skill) — delegate to **OpenCode CLI**

## Reporting

Every run is logged to `~/.local/share/delegate-runs.jsonl` with tokens, cost, model, and failure details. Query it with `~/tools/delegate-report [--since N] [--project NAME] [--fails]` or from Claude Code: `/vibe-report [args]`.

The log is shared with sister delegates (gemini-skill, opencode-skill), so the report defaults to **vibe runs only**. Use `--all` for the cross-delegate comparison, or `--delegate NAME` to scope to another tool.

---

## Feedback

See [`docs/feedback-claude-sonnet.md`](docs/feedback-claude-sonnet.md) for original feedback from Claude after hours of practice that drove the iterations on `vibe-delegate` — real bugs hit, root causes, and the fixes applied. Harness audits: [`docs/harness-audit-2026-10-01.md`](docs/harness-audit-2026-10-01.md) (Vibe 2.x) and [`docs/harness-audit-2026-11-09.md`](docs/harness-audit-2026-11-09.md) (Vibe 3).

---

## License

MIT
