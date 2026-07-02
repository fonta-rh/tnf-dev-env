---
description: Consolidate bloated project CLAUDE.md by archiving completed checklist items and narrative subsections
argument-hint: [name-or-number]
---

# Consolidate Project CLAUDE.md

Archive completed checklist items and completed narrative subsections
from bloated sections into a `progress-archive.md` detail file.

**Checklist archiving**: Sections with 10+ completed `- [x]` items
qualify. The last 3 completed items are kept for context. Unchecked
items are never touched.

**Narrative archiving**: `### ` subsections that are pure prose (no
checklist items) are archived when a section accumulates 10+ lines
of archivable narrative. The most recent qualifying subsection is
kept. Structural sections (Reference Files, Feature Summary, etc.)
are never touched.

## Step 0: Locate Workspace Root

The workspace root is the directory containing this `.claude/` folder.
Determine it from the path of this command file and store it as `ROOT`.
All script calls below MUST use `$ROOT/scripts/...` — never relative
paths, since the working directory may be inside a worktree.

## Step 1: Resolve Project

Extract the first token from `$ARGUMENTS`. Run
`python3 $ROOT/scripts/resume-project.py <first-token>` via Bash (omit
the token if none was provided). Parse the JSON and handle by `status`:

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
python3 $ROOT/scripts/consolidate-project.py --dry-run <project-name>
```

Parse the JSON output:

- **`status: "already_lean"`** — show the `message` and stop.
- **`status: "error"`** — show the `message` and stop.
- **`status: "needs_consolidation"`** — proceed to Step 3.

## Step 3: Confirm

Show the consolidation plan from the dry-run `sections` array:

```
Sections to consolidate in `<project>` (<claude_md_lines> lines):

| Section | Items → Archive | Subsections → Archive | Lines Freed |
|---------|----------------|-----------------------|-------------|
| <name>  | <to_archive>   | <narrative_to_archive> (<narrative_lines> lines) | ~<to_archive + narrative_lines> |
```

Omit zero-value columns when no sections have that type of archiving.

Ask: "Proceed with consolidation?"

## Step 4: Apply

Run via Bash:
```
python3 $ROOT/scripts/consolidate-project.py <project-name>
```

Parse the JSON output.

## Step 5: Report

From the result JSON, display:

```
Consolidated `<project>`:
- <section>: <archived> items archived, <kept> kept
  [if narrative] + <narrative_archived> subsections (<narrative_lines> lines) archived, <narrative_kept> kept
- ...
- CLAUDE.md: <before> → <after> lines
- Archive: progress-archive.md (<action>)
```

If `reference_table_updated` is true, note that the Reference Files
table was updated.
