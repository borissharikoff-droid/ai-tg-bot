---
name: subagent-development-loop
description: Orchestrates a fixed multi-agent development workflow: planning with ivan, implementation with boris, and review with emelya, then loops back to boris if review finds issues. Use when the user asks to build, implement, refactor, or fix code and wants a structured subagent handoff. Trigger on requests mentioning subagents, workflow, pipeline, ivan, boris, emelya, or "process raboty subagentov".
---

# Subagent Development Loop

## Purpose

Use this skill to run development tasks through a strict quality loop with three agents:

1. `@.cursor/agents/ivan.md` - planning and task decomposition
2. `@.cursor/agents/boris.md` - implementation
3. `@.cursor/agents/emelya.md` - review and issue detection

If review finds issues, return to `@.cursor/agents/boris.md` for fixes, then run `@.cursor/agents/emelya.md` again.

## When To Apply

Apply this skill when:
- The task is software development (new feature, bug fix, refactor, integration).
- The user asks for a structured subagent process.
- The user mentions `ivan`, `boris`, `emelya`, or asks for a multi-step quality workflow.

## Required Workflow

Follow this sequence exactly.

### Step 1 - Plan with Ivan

- Invoke `@.cursor/agents/ivan.md` first.
- Ask Ivan to:
  - Restate the goal
  - Capture assumptions and constraints
  - Produce an ordered task breakdown
  - Highlight risks and blockers
  - Provide the immediate next action
- Keep Ivan output concise and execution-ready.

### Step 2 - Build with Boris

- Pass Ivan's plan to `@.cursor/agents/boris.md`.
- Ask Boris to:
  - Implement the requested change
  - Run relevant validation (tests/lint/type checks if available)
  - Summarize changes and assumptions
- Prefer minimal, focused changes that solve the root cause.

### Step 3 - Review with Emelya

- Send Boris changes/diff to `@.cursor/agents/emelya.md`.
- Ask Emelya for prioritized findings with severity and actionable fixes.
- Emelya must explicitly state either:
  - `No issues found`, or
  - A concrete issue list.

### Step 4 - Fix Loop (If Needed)

- If Emelya reports issues:
  1. Send findings to `@.cursor/agents/boris.md`.
  2. Ask Boris to fix all reported issues.
  3. Re-run `@.cursor/agents/emelya.md` review.
  4. Repeat until Emelya reports `No issues found` or user stops iteration.

## Loop Exit Conditions

Exit the loop when one of the following is true:
- Emelya reports `No issues found`.
- The user approves remaining risks.
- A blocker requires user decision.

## Handoff Template

Use this short template between agents:

```markdown
Task:
[user goal]

Current phase:
[Ivan planning | Boris implementation | Emelya review | Boris fixes]

Inputs:
- Constraints:
- Relevant files:
- Prior findings/decisions:

Expected output:
[clear, phase-specific output]
```

## Final Response To User

When the loop is done, report:
1. What was implemented
2. What issues were found and fixed (if any)
3. Final validation/review status
4. Any remaining risks or follow-up tasks
