# start

Run the workflow from `@.cursor/skills/subagent-development-loop/SKILL.md`.

Execution rules:
1. First hand the task to `@.cursor/agents/ivan.md` for decomposition and planning.
2. Then hand the plan to `@.cursor/agents/boris.md` for implementation.
3. After implementation, run review via `@.cursor/agents/emelya.md`.
4. If `emelya` finds issues — send them back to `boris` for fixes, then run `emelya` again.
5. Repeat until `emelya` reports **No issues found** (or the user stops the iteration).

In your reply to the user, always include:
- what was implemented,
- what issues were found and fixed,
- final review status,
- any remaining risks or next steps.
