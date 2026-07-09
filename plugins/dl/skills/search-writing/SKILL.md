---
name: search-writing
description: "Search writing template knowledge base — plot structures, character archetypes, payoff patterns, conflict templates, and hook formulas for story creation."
allowed-tools: Bash(dl knowledge search:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 1.5
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: ce710bbc822e9754 -->

# Search Writing Templates

## Commands

This skill involves:

- `dl knowledge search` — search the writing template knowledge base for plot /
  character / payoff / conflict / hook templates

Before calling, you **must** run `dl knowledge search --help` once to confirm
current flags / filter fields / domain enums; do not write parameters from
memory or stale docs.

## Domains

| Domain | What it contains | When to use | Example query |
|--------|-----------------|-------------|---------------|
| `writing_plot` | 124 plot templates | Building a story structure from proven templates | `"重生复仇 带前世记忆 逐个击破"` |
| `writing_character` | 95 character archetypes | Designing character personality and arc | `"冷面复仇型女主 零表情最大破坏力"` |
| `writing_payoff` | 142 payoff/satisfaction templates | Designing cathartic/satisfying moments | `"绝境反杀 战力碾压 旁观者震惊"` |
| `writing_conflict` | 104 conflict structure templates | Structuring dramatic conflict and escalation | `"身份信息差 非对称博弈 降维打击"` |
| `writing_hook` | 104 hook templates | Crafting opening hooks and cliffhangers | `"权力符号入侵 位阶瞬间反转"` |
| `writing_any` | All 569 writing templates combined | Discovery when unsure which template type needed | `"女频 豪门 复仇"` |

## Filters

- `writing_*` domains: `filters.tags` (string, matches templates containing this tag, e.g. `"女频"`, `"爽"`, `"都市"`)
- `writing_any` additionally: `filters.category` (`"plot"` | `"character"` | `"payoff"` | `"conflict"` | `"hook"`)

The exact way to pass filters (`--filters-file` or otherwise) is authoritative
in `dl knowledge search --help`.

## Constraints

- Keep queries concise but descriptive (5-15 words).
- `writing_any` does not emit artifact receipts — use specific domains when you need to commit a selection.
- Writing template results include `id`, `category`, `title`, `tags`, and `description` — use the returned content as creative reference and structural guidance for story creation.
