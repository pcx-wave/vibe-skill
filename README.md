<!-- Suggested GitHub topics: claude-code, llm-tools, mistral, gemini-cli, ai-coding, shell, developer-tools, vibe-coding -->

# vibe-skill

![MIT License](https://img.shields.io/badge/license-MIT-blue.svg) ![Shell](https://img.shields.io/badge/language-Shell-green.svg) ![GitHub stars](https://img.shields.io/github/stars/pcx-wave/vibe-skill?style=social) ![Claude Code skill](https://img.shields.io/badge/-Claude%20Code%20skill-CC785C)

**Claude orchestrates. Vibe does the heavy lifting. You review the diff, save tokens, costs and avoid hitting limits!**

Claude sees only ~500–1500 tokens per run regardless of how many file reads Vibe performs internally — massive savings on exploratory and implementation tasks.

Note that Vibe works natively with Mistral models which are capable and significantly cheaper than Claude, but Vibe can also be configured to use any other provider/model instead. Eg you can use a deepseek model with vibe tooling. 

Summary:
1. User types `/vibe <instruction>` in Claude Code
2. Claude decomposes the task and writes a prompt
3. `vibe-delegate` runs Mistral Vibe in a pseudo-TTY
4. The delegate reports tool calls, token counts, and `git diff --stat`
5. Claude reviews the diff and summarizes the result

---

## Why

**Cost savings** — Vibe's file reads and edits consume cheap delegate tokens (or whatever model you configure), not Claude tokens:

| Scenario | Claude Sonnet 4.6 | Mistral Medium 3.5 | DeepSeek V4 Flash |
|----------|-------------------|--------------------|-------------------|
| Simple 1-file tweak (800 tokens) | ~$0.004 | ~$0.002 | ~$0.0001 |
| 6-read implementation task (4,800 tokens) | ~$0.023 | ~$0.012 | ~$0.0008 |
| Complex multi-file refactor (12,000 tokens) | ~$0.058 | ~$0.029 | ~$0.002 |

> Costs based on official pricing (May 2026): Claude $3/$15 per M tokens, Mistral Medium 3.5 $1.50/$7.50, DeepSeek V4 Flash $0.14/$0.28. Assumes ~85% input / 15% output, typical for coding tasks. Claude orchestration overhead: ~500 tokens per run (negligible).

> **Le Chat Pro users:** Mistral Vibe is included in the [Le Chat Pro](https://mistral.ai/pricing) subscription (~$18/mo). Mistral does not publicly document the exact usage limits, but community reports suggest ~1–1.5B tokens/month are included. Within that allowance every delegation costs $0 in API fees — cheaper than any paid model.

### Subscribe to Mistral Pro, or just use DeepSeek?

DeepSeek's headline input rate is $0.14/M — but that is the cache-**miss** rate. With
prompt caching on iterative coding (the same file context resent across turns), real
billed cost is far lower. Measured over this period: **$5.07 for 227M tokens ≈ $0.022/M
blended**, because 90% of input was served from cache at $0.0028/M. At that rate
DeepSeek-only stays cheaper than the Mistral Pro subscription (~$18/mo) until **~800M
tokens/month**:

```
tokens/month  │ DeepSeek only* │ Mistral Pro sub │ Verdict
──────────────┼────────────────┼─────────────────┼──────────────────────────
  50M         │  $1.12         │  $18.36         │ DeepSeek cheaper
 221M (now)   │  $4.93         │  $18.36         │ DeepSeek cheaper
 500M         │  $11.15        │  $18.36         │ DeepSeek cheaper
 820M         │  $18.30        │  $18.36         │ ← break-even
   1B         │  $22.30        │  $18.36         │ Mistral Pro worth it
```

\* Assumes the ~90% cache-hit rate observed on iterative coding. One-off, diverse tasks
cache less and trend toward the $0.14/M miss rate — at which break-even drops back to
~130M/month. So the honest range is **break-even somewhere between ~130M (cache-light)
and ~800M (cache-heavy) tokens/month.**

At the current ~221M/month on cache-heavy coding, DeepSeek-only (~$5) is well under the
Mistral Pro sub — the *opposite* of what a cache-blind $0.14/M estimate would suggest.
Subscribe to Mistral Pro only once you are reliably above your break-even band, and use
it until the quota (~1B–1.5B tokens) is exhausted. Never let Mistral roll into
pay-as-you-go ($1.52/M blended).

### Delegation synthesis — as of 2026-05-30

Snapshot over **2,103 vibe delegations**, 2026-05-12 → 2026-05-30 (19 days). Pulled from the shared run log via `delegate-report` (vibe scope).

**Performance & savings**

| Metric | Value |
|---|---|
| Delegations | 2,103 |
| Tokens delegated | 139.8M |
| Exit-success rate | 81% |
| Clean rate (no soft failure) | 67% |
| Avg run duration | 33s |
| **Actually paid** | **$5.07 DeepSeek (billed) + Le Chat Pro sub (~$18/mo)** |
| Same workload on Claude Sonnet 4.6 | $456.94 |
| **Effective saving** | **≈ 20× cheaper than Claude** |
| Pay-as-you-go API equivalent | $174.28 *(reference only — not what was paid)* |

> The 81% vs 67% gap is *soft* failures — runs that exit 0 but write nothing or miss a `search_replace`. Exit code alone overstates real success; see the error table below.
>
> **What this actually cost:** 104M of the 139.8M tokens ran on `mistral-medium-3.5` under a flat **Le Chat Pro subscription** (~$18/mo, ~1B-token quota — $0 marginal); the DeepSeek runs cost **$5.07**, verified from provider billing. The `$174.28` figure and the per-model "API-rate cost" column below are what the same volume *would* cost at pay-as-you-go rates — a model-comparison reference, **not money spent**. Against Claude's $456.94, real out-of-pocket (~$23 for the period) is roughly **20× cheaper**.
>
> **Why the log over-counts DeepSeek:** of DeepSeek's 221M input tokens, **90% were cache hits** at $0.0028/M (50× cheaper than the $0.14/M miss rate), so real cost was $5.07 — not the ~$35 the run log estimates. The log prices every input token at the full miss rate (no cache awareness), and runs logged before DeepSeek pricing was added used the Mistral fallback. Cache alone is a ~6× overstatement here. See [cost methodology](SKILL-reference.md#cost-estimate-methodology).

**By model**

| Model | Runs | Exit-ok | Avg dur | Tokens | API-rate cost¹ | vs Claude |
|---|---|---|---|---|---|---|
| mistral-medium-3.5 | 1,718 | 79% | 31s | 104.2M | $137.09 | $206.24 |
| deepseek-flash | 269 | 93% | 41s | 32.1M | $35.43 | $67.12 |
| devstral-small | 68 | 63% | 19s | 2.6M | $0.26 | $7.81 |
| mistral (Le Chat) | 48 | 95% | 43s | 0.9M | $1.49 | $1.49 |

¹ Pay-as-you-go reference, not actual spend — mistral-medium ran on the Le Chat Pro sub; DeepSeek's real billed cost was **$5.07** (90% cache hits), not the cache-blind $35.43 shown here.

`deepseek-flash` is the value pick (93% exit-ok at ~$0.13/run). `devstral-small` underperforms (63%) — it is an agent-mode model and fits the inline-edit delegation pattern poorly; prefer it only for read/explore.

**Error rate** (real projects, 1,964 runs — synthetic test scaffolds excluded)

| Class | Rate | What it is |
|---|---|---|
| clean ok | 67.1% | completed and wrote files |
| `exit_error` | 18.7% | engaged (~7 tool calls) then exited non-zero, **95% wrote nothing** |
| `wrote_nothing` | 7.1% | tool calls but 0 files, exit 0 |
| `warn_only` | 2.5% | non-fatal warnings, usually fine |
| `sr_fail` | 2.4% | `search_replace` byte-match miss (accents, backticks) |
| `near_empty` | 1.6% | <50 tokens out, nothing written |
| `syntax_error` | 0.4% | wrote invalid code (caught by post-run gate) |
| `timeout` | 0.3% | task too large / context saturated |

**`exit_error` + `wrote_nothing` (≈26%) share one root cause:** vibe engages but lands no edit — multi-edit context drift, or the first `search_replace` target isn't found byte-for-byte and the run abandons. This is the single biggest reliability lever.

**Fixes shipped after this snapshot (2026-05-31)** to attack the above — impact to be measured in the next snapshot:

- **`--require` target-presence gate** → the `exit_error` + `wrote_nothing` cluster (~26%): aborts before launch when the `search_replace` anchor isn't in the file, so a doomed run never runs (logged as cheap `precheck_abort` instead of a wasted `exit_error`).
- **Model routing** → model-mismatch `exit_error`: agent-mode `devstral-small` is kept to read/explore; inline edits go to `deepseek-flash` / `mistral-medium-3.5`.
- **`failure_reason` taxonomy** → visibility: surfaces the silent `silent_exit` / `near_empty` failures the old flag missed.
- **`contract` / `output_format` adaptations** → correctness and the "vibe wrote nothing, I'll redo it" loop; left off-by-default until `/vibe-report --adapt` has enough runs to prove they help.

Effect is read straight from `/vibe-report` — `precheck_abort` displacing `exit_error`, and the `--adapt` cohort once it fills. See [`docs/error-reduction.md`](docs/error-reduction.md) for the full plan.

**Versus the other delegate (`opencode`)**

| | vibe | opencode |
|---|---|---|
| Runs | 2,103 | 254 |
| Tokens | 139.8M | 8.5M |
| Exit-ok | 81% | 81% |
| API-rate cost (reference) | $174.28 | $0 (free tiers) |
| Models | mistral-medium, deepseek-flash (paid, capable) | free deepseek / mimo / nemotron tiers |

Same headline exit-rate, very different profile: `opencode` runs free model tiers at zero cost but with high `silent_exit` (model returns nothing) and timeout rates (e.g. nemotron timed out on 31 of 50 runs). It's economical for cheap bulk exploration; vibe's paid models are the choice when the edit has to actually land. Both write to the same log, so `/vibe-report --all` compares them directly.

---

**Context window protection** — On long coding sessions, every file read, function body, and debug loop burns Claude's context. Delegating to Vibe keeps that budget free. Claude enters the task, hands off, and comes back only to review the result — no context bleed from Vibe's internal turns.

**Built-in quality gate** — Claude doesn't just fire and forget. After each Vibe run, Claude reads the `git diff`, checks for syntax errors, and summarizes what changed before reporting back to you. You get a second pair of eyes on every delegation without lifting a finger.

---

## Prerequisites

- [Mistral Vibe](https://vibe.mistral.ai/) CLI installed and authenticated (`vibe --version`)
- [Claude Code](https://claude.ai/code) with skills enabled
- `script` command available (GNU/Linux or BSD/macOS variant)
- `timeout` command available; on macOS install GNU coreutils for `gtimeout` (or ensure your chosen `timeout` fallback is set up)
- `python3` and optionally `node` for syntax checks
- A git repository to work in

---

## Installation

```bash
git clone https://github.com/pcx-wave/vibe-skill.git && cd vibe-skill && mkdir -p ~/tools ~/.claude/skills/vibe ~/.claude/skills/vibeon ~/.claude/skills/vibeoff ~/.claude/skills/vibestatus ~/.claude/skills/vibe-model-pick ~/.claude/skills/vibe-model-clear ~/.claude/skills/vibe-report && ln -sf "$(pwd)/tools/vibe-delegate" ~/tools/vibe-delegate && ln -sf "$(pwd)/tools/delegate-report" ~/tools/delegate-report && chmod +x ~/tools/vibe-delegate ~/tools/delegate-report && ln -sf "$(pwd)/SKILL.md" ~/.claude/skills/vibe/SKILL.md && ln -sf "$(pwd)/VIBEON.md" ~/.claude/skills/vibeon/SKILL.md && ln -sf "$(pwd)/VIBEOFF.md" ~/.claude/skills/vibeoff/SKILL.md && ln -sf "$(pwd)/VIBESTATUS.md" ~/.claude/skills/vibestatus/SKILL.md && ln -sf "$(pwd)/VIBE-MODEL-PICK.md" ~/.claude/skills/vibe-model-pick/SKILL.md && ln -sf "$(pwd)/VIBE-MODEL-CLEAR.md" ~/.claude/skills/vibe-model-clear/SKILL.md && ln -sf "$(pwd)/VIBE-REPORT.md" ~/.claude/skills/vibe-report/SKILL.md
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

Verify with `~/tools/vibe-delegate /tmp "Say hello in one sentence." 3`

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

### Model selection

By default, Vibe uses whatever `active_model` is set in `~/.vibe/config.toml`. You can override it per-session without touching that file:

```
/vibe-model-pick              — interactive menu built from your config.toml models
/vibe-model-pick devstral-small  — switch directly by alias
/vibe-model-clear             — remove the override, return to config default
/vibestatus                   — shows both auto-mode state and active model override
```

The override is stored in `~/.local/share/vibe-model.flag` and is picked up by `vibe-delegate` on every run. It persists across sessions until you clear it.

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
| Everything else | Delegated to Vibe |

Pure questions and conversations always go directly to Claude.

---

## Terminal output

Sample output from a real run:

```
=== VIBE START ===
Workdir : /path/to/project
Agent   : default
Model   : (config default)
Turns   : 10
Timeout : 180s
Prompt  : Stack: Python/Flask. File: app.py ...
===================
  [read]  app.py
  [tool]  file: app.py
  [tool]  search_replace [OK] ...
  [vibe]  Done. Converted date to datetime.date in fetch_data().
Tool calls: 5  |  warns: 0  |  sr_fails: 0
Model               : deepseek-flash
Delegate tokens (run): 4,800  (last turn: 4,600+200)  |  cost ~$0.0007
Claude Sonnet 4.6 eq: same tokens would cost ~$0.0168  (ratio x24.0)
=== VIBE DONE (exit: 0) ===
=== SYNTAX OK (1 file(s) checked) ===

=== UNCOMMITTED CHANGES ===
 app.py | 4 ++--
[log] → ~/.local/share/delegate-runs.jsonl  (4800 tokens, exit 0, 34.2s, saved ~$0.0161 vs Claude)
```

---

## How vibe-delegate works

```
Claude Code
  └─ /vibe <instruction>
       └─ SKILL.md logic
            └─ ~/tools/vibe-delegate <workdir> <prompt> [turns] [agent] [timeout]
                 ├─ writes prompt to temp file (avoids shell injection with UTF-8/emoji)
                 ├─ generates a temp shell script for the vibe command
                 ├─ runs: python3 -c 'pty.spawn(<vibe-script>)'
                 │         └─ allocates pseudo-TTY (required — vibe hangs without one)
                 ├─ pipes JSON streaming output through Python parser
                 │         └─ prints [read] / [write] / [WARN] / [vibe] lines
                 ├─ reads real token counts from Mistral session log
                 ├─ runs syntax checks on modified .py and .js files
                 ├─ prints git diff --stat
                 └─ appends JSON entry to ~/.local/share/delegate-runs.jsonl
```

Python's `pty.spawn` allocates a pseudo-TTY — portable across Linux and macOS, and it works even when the parent process has no controlling TTY (unlike the `script` command, which the delegate originally used); prompt via temp file avoids shell injection with UTF-8/emoji.

**Shell vs Python split** — `vibe-delegate` started as pure shell. Python is now embedded in four places where shell falls short:

| What | Why Python |
|------|-----------|
| JSON stream parser (live output) | Vibe emits a JSON stream; shell can't reliably parse it line by line without race conditions |
| Token count + cost calculation | Reads `~/.vibe/config.toml` (TOML parsing), looks up per-model pricing, handles float arithmetic |
| Syntax check (`py_compile`) | stdlib module — one line, no dependencies |
| Run log writer | Builds a structured JSON entry with multiple computed fields; shell heredoc+`jq` would be fragile |

`delegate-report` is fully Python: it aggregates, sorts, and formats tabular data across hundreds of log entries — the kind of work where shell pipelines become unmaintainable.

> Cost figures are **estimates**, not billed amounts. Total tokens are Vibe's real count, but the input/output split is *approximated* from the last turn's ratio, cache reads are not accounted for, and prices come from `config.toml`. See [`SKILL-reference.md` → Cost estimate methodology](SKILL-reference.md#cost-estimate-methodology) for exactly how it is derived and its limits.

---

## Examples

- `examples/good-prompts.md` — prompt patterns that reliably work
- `examples/anti-patterns.md` — what fails and why, with fixes

---

## Sister project

A parallel delegate using **Gemini CLI** is available at [pcx-wave/gemini-skill](https://github.com/pcx-wave/gemini-skill). Same orchestration pattern, same run log format — different model and trade-offs.

## Reporting

Every run is logged to `~/.local/share/delegate-runs.jsonl` with tokens, cost, model, and failure details. Query it with `~/tools/delegate-report [--since N] [--project NAME] [--fails]` or from Claude Code: `/vibe-report [args]`.

The log is shared with sister delegates (e.g. gemini-skill), so the report defaults to **vibe runs only**. Use `--all` for the cross-delegate comparison, or `--delegate NAME` to scope to another tool.

---

## Feedback

See [`docs/feedback-claude-sonnet.md`](docs/feedback-claude-sonnet.md) for original feedback from Claude after hours of practice that drove the iterations on `vibe-delegate` — real bugs hit, root causes, and the fixes applied.

---

## License

MIT
