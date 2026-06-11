---
description: Update project documentation from what was accomplished in this session
argument-hint: [name-or-number]
---

# Update Project Documentation

You are updating a project's documentation based on what was accomplished
in the current conversation. This is a **scoped write** — only the project
CLAUDE.md gets updated.

## Scope Rules

**Update ONLY:** `projects/<name>/CLAUDE.md`

**NEVER touch during this command:**
- Memory files (`memory/MEMORY.md`, `memory/project_*.md`)
- Internal session tasks (TaskCreate / TaskUpdate)
- Repo source files under `repos/`

Memory may be stale or summarized differently. The project CLAUDE.md is
the source of truth for project state.

## Step 1: Resolve Project

Extract the first token from `$ARGUMENTS`. Run
`scripts/resume-project.py <first-token>` via Bash (omit the token if
none was provided). Parse the JSON and handle by `status`:

- **`ok`** — use `project.name`. Proceed.
- **`no_argument`** — check if a project was loaded earlier in this
  conversation (e.g., via `/project:resume`). If so, use that project
  name. Otherwise, present the first 3 `alternatives` as AskUserQuestion
  options. Re-run with the chosen name.
- **`not_found`** / **`out_of_range`** — show `error_message`, present
  `alternatives` as a picker, re-run.
- **`no_projects`** — show `error_message` and stop.

## Step 2: Read Current State

Read `projects/<name>/CLAUDE.md` in full.

## Step 3: Diff Against Session

Review the conversation history for this session and identify:

1. **Checklist items completed** — items in the CLAUDE.md checklists
   (`- [ ]`) that are now done based on work in this session.
2. **New checklist items** — work discovered or queued during the session
   that should be tracked (append to the appropriate section).
3. **New detail files** — files created in `projects/<name>/` during this
   session that aren't in the Reference Files table yet.
4. **Progress entries** — significant milestones or outcomes to append to
   the Progress section.

## Step 4: Present Changes

Before editing, show the user a numbered list of proposed changes:

```
Proposed updates to <name>/CLAUDE.md:

1. ✓ Check off: "<checklist item text>"
2. ✓ Check off: "<checklist item text>"
3. + Add to Progress: "<new entry>"
4. + Add to Reference Files: `<filename>` — <description>
5. + Add checklist item: "<new item>"
```

If nothing to update, say so and stop.

Ask: "Apply these updates? You can drop items by number."

## Step 5: Apply

Use the Edit tool to apply the approved changes to
`projects/<name>/CLAUDE.md`. Make each edit individually — do not
rewrite the entire file.

Confirm what was updated.
