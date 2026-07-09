# Skill: audience_analysis

Current runtime role: audience signal synthesis and writeback.

## Status

- Canonical instructions now live in [SKILL.md](/Users/tangkaixin/Dev/agent_platform/skills/audience-analysis/SKILL.md).
- Audience analysis now writes durable findings through `context_write` and `session_commit`.
- It is no longer described as a pure legacy memory-only skill.

## Runtime dependencies

- Analytics/context: `get_content_metrics`, `context_find`
- Writeback/projection: `context_write`, `session_commit`
