---
name: vibe-report
description: Show Vibe usage report — token/cost/failure stats. Usage: /vibe-report [--since N] [--project NAME] [--fails]
license: MIT
user-invocable: true
allowed-tools:
  - bash
---

# /vibe-report

Run `~/tools/delegate-report` with any flags extracted from the arguments and display output verbatim.

| User says | Flag |
|-----------|------|
| "last 7 days", "7d" | `--since 7` |
| "last 30 days", "30d" | `--since 30` |
| "project foo" | `--project foo` |
| "only failures", "fails", "bugs" | `--fails` |
| (nothing) | (no flags — full report) |
