---
description: Consolidate bloated project CLAUDE.md by archiving completed checklist items
argument-hint: [name-or-number]
---

# Consolidate Project CLAUDE.md

Archive completed checklist items from bloated sections into a
`progress-archive.md` detail file. Keeps the last 3 completed items
and a pointer line in each section for recent context.

Sections with 10+ completed `- [x]` items qualify. Unchecked items,
strikethroughs, and non-checklist content are never touched.

## Step 1: Resolve Project

Extract the first token from `$ARGUMENTS`. Run
`scripts/resume-project.py <first-token>` via Bash (omit the token if
none was provided). Parse the JSON and handle by `status`:

- **`ok`** — use `project.name` as the target. Proceed to Step 2.
- **`no_argument`** — check if a project was loaded earlier in this
  conversation. If so, re-run the script with that name. Otherwise,
  present the first 3 `alternatives` as AskUserQuestion options plus
  "See all projects". Re-run with the chosen name.
- **`not_found`** / **`out_of_range`** — show `error_message`, present
  `alternatives` as a picker, re-run with chosen name.
- **`no_projects`** — show `error_message` and stop.

## Step 2: Dry Run

Run via Bash:
```
python3 scripts/consolidate-project.py --dry-run <project-name>
```

Parse the JSON output:

- **`status: "already_lean"`** — show the `message` and stop.
- **`status: "error"`** — show the `message` and stop.
- **`status: "needs_consolidation"`** — proceed to Step 3.

## Step 3: Confirm

Show the consolidation plan from the dry-run `sections` array:

```
Sections to consolidate in `<project>`:

| Section | Checked | To Archive | Keep | Unchecked | Strikethrough |
|---------|---------|------------|------|-----------|---------------|
| <name>  | <N>     | <N>        | <N>  | <N>       | <N>           |
```

Ask: "Proceed with consolidation?"

## Step 4: Apply

Run via Bash:
```
python3 scripts/consolidate-project.py <project-name>
```

Parse the JSON output.

## Step 5: Report

From the result JSON, display:

```
Consolidated `<project>`:
- <section>: <archived> items archived, <kept> kept
- ...
- CLAUDE.md: <before> → <after> lines
- Archive: progress-archive.md (<action>)
```

If `reference_table_updated` is true, note that the Reference Files
table was updated.
