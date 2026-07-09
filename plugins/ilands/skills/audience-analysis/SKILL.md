---
name: audience-analysis
description: "Turn recent content metrics into reusable audience understanding and durable strategy signals without collapsing into vanity-metric chasing."
allowed-tools: Bash(ilands:*)
metadata:
  ilands:
    applicable-to: [full]
    priority: 2.1
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


# Audience Analysis

## Methodology

1. Use `ilands get-content-metrics --content-id=<content_id>` to inspect recent content performance.
2. Use `ilands context-find --query="..."` to compare the newest audience behavior with previous baselines, recurring questions, and prior content hypotheses.
3. Identify audience signals that are actionable for future decisions: topic appetite, pacing tolerance, completion behavior, follow-on curiosity, or interaction style.
4. Persist the strongest audience findings via `ilands context-write --key="..." --value='...'` so topic selection and workflow routing can query them later.
5. When a durable audience shift is detected, record the evidence via additional `ilands context-write` entries so Dream can evaluate a SELF delta during its Evolve phase.

## Output Format
```json
{
  "time_window": "string",
  "audience_patterns": [
    {
      "pattern": "string",
      "evidence": "string",
      "implication": "string"
    }
  ],
  "source_context_refs": ["context://..."],
  "self_delta_recommended": false
}
```

## Constraints
- Focus on patterns, not leaderboard vanity.
- Baseline comparison matters more than absolute metrics without context.
- Audience analysis should inform future creation, not instantly rewrite identity from noisy data.

For full parameter reference: `ilands --help`
