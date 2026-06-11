---
description: Update project documentation from what was accomplished in this session
argument-hint: [name-or-number]
---

# Update Project Documentation

Update a project's CLAUDE.md based on what was accomplished in the
current conversation. This is a **scoped write** — apply edits directly.

## Scope Rules

**Update ONLY:** `projects/<name>/CLAUDE.md`

**NEVER touch during this command:**
- Memory files (`memory/MEMORY.md`, `memory/project_*.md`)
- Internal session tasks (TaskCreate / TaskUpdate)
- Repo source files under `repos/`

## Step 1: Resolve Project

Use the project already loaded in this conversation (from
`/project:resume` or any earlier project interaction). If `$ARGUMENTS`
has a token, use that as the project name instead.

If no project is in context and no argument was given, ask which project.

## Step 2: Read Current State

Read `projects/<name>/CLAUDE.md` in full.

## Step 3: Identify Updates

Review the conversation history and identify:

1. **Checklist items completed** — `- [ ]` items now done.
2. **New checklist items** — work discovered or queued.
3. **New detail files** — files created in `projects/<name>/` not yet in
   the Reference Files table.
4. **Progress entries** — milestones or outcomes to append.

If nothing to update, say so and stop.

## Step 4: Apply

Use the Edit tool to apply changes to `projects/<name>/CLAUDE.md`.
Make each edit individually — do not rewrite the entire file.

Summarize what was updated.
