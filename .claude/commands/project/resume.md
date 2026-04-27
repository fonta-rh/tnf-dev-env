---
description: Resume an existing project workspace
argument-hint: [name-or-number]
---

# Resume Project Workspace

You are helping a developer resume work on an existing project workspace.
Projects live under the `projects/` directory. Your job is to reload
context and get the developer back up to speed quickly.

Everything after "resume" in `$ARGUMENTS` is an optional project name
to resume directly.

## Step 1: Select Project

**1a. Determine project name**

Handle the argument in `$ARGUMENTS` using these cases:

**Case A — Numeric shorthand** (e.g., `/project:resume 1`):
If the argument is a plain integer N, look in your conversation context
for the numbered "📂 Recent projects" table produced by the SessionStart
hook. Pick the project name on row N from that table. This avoids an
unnecessary shell call since the hook output is already in context.
If the table is not in context (e.g., session was cleared), fall back to
running `scripts/recent-projects.py --names` and pick the Nth line.
If N is out of range, show an error like "Only M projects exist." and
fall through to Case C (interactive picker).

**Case B — Project name** (e.g., `/project:resume OCPBUGS-74679`):
If the argument is a non-numeric string, use it directly as the target
project name (current behavior).

**Case C — No argument** (`/project:resume`):
Look in your conversation context for the "📂 Recent projects" table.
If present, extract the project names from it (up to 3) and present
them as AskUserQuestion options, plus a "See all projects" option.
If the table is not in context, run
`scripts/recent-projects.sh --names | head -3` to get the names instead.
If the user picks "See all projects", run `ls projects/` and present
the full list as a second AskUserQuestion.

**1b. Validate project exists**

Check that `projects/<name>/` exists. If it does not:
- Show an error: "Project `<name>` not found."
- List all available projects from `projects/`
- Ask the user to pick from the list or provide a corrected name

## Step 2: Load Project Context

Read whatever context file the project has, in priority order:

**2a. Try `projects/<name>/CLAUDE.md`**

If the file exists, read it in full. Then check if it starts with YAML
frontmatter (a line that is exactly `---` followed by YAML content and
closed by another `---`):
- **Has frontmatter**: Parse the YAML to extract `project`, `type`,
  `created`, `status`, `jira`, `repos`, and `related_links` fields.
- **No frontmatter**: Treat the entire file as free-form context. Infer
  the project type from headings or content if possible (e.g., "Bug
  Summary" → bug, "Feature Summary" → feature).

**2a-ii. Parse Reference Files table**

Check if the CLAUDE.md contains a `## Reference Files` section with a
markdown table (columns: `File`, `Content`). If found, parse it into a
detail file manifest — a list of (filename, description) pairs. These
are the project's detail files.

**Do NOT read detail files yet.** The CLAUDE.md index is small; detail
files are loaded on demand in Step 4 based on what the user wants to
work on.

If no Reference Files table exists, this is an older monolithic project.
All content is already in context from reading the full CLAUDE.md. Note
this internally and skip detail-file logic in Steps 3-4.

**2b. Fall back to `projects/<name>/README.md`**

If no CLAUDE.md exists but README.md does, read it in full. Infer the
project type from headings or content if possible.

**2c. No context file**

If neither CLAUDE.md nor README.md exists:
- List all files in the project directory (see Step 2d)
- Ask the user: "This project has no CLAUDE.md or README.md. Can you
  briefly describe what this project is about so I can help you
  continue?"

**2d. List project files**

In all cases, list all files in the project directory (recursively) using
the Bash tool (`find projects/<name>/ -type f | sort`). This gives both
you and the user a picture of what's in the project.

If a Reference Files manifest was parsed in Step 2a-ii, cross-reference
the file listing against it. Note any files that exist on disk but are
NOT in the manifest — these may be organically created files that should
be registered. Mention them in the summary (Step 3) so the user can
decide whether to add them to the Reference Files table.

**2e. Auto-load repo context**

If the project's frontmatter contains a `repos` list (non-empty), load
context for each repo to prime your understanding of the codebase:

1. For each repo name in the `repos` list:
   a. First, check if `repos/<repo>/CLAUDE.md` exists. If so, read it.
   b. Otherwise, search for `presets/*/context/<repo>.md`. If found,
      read the first match.
   c. If neither exists, skip silently (the repo may not have context
      files yet).
2. After loading, briefly note to the user which repo context files
   were loaded (e.g., "Loaded context for: cluster-etcd-operator,
   installer").
3. Do NOT load context for repos not listed in the project's
   frontmatter — only load what's relevant to this project.

## Step 3: Present Project Summary

Display a structured summary using this format:

```
## Project: <name>

| Field | Value |
|-------|-------|
| **Type** | <type from frontmatter, or inferred, or "Unknown"> |
| **Created** | <date from frontmatter, or "Unknown"> |
| **Status** | <status from frontmatter, or "Unknown"> |
| **JIRA** | <URL from frontmatter, or "None"> |
| **Repos** | <comma-separated list, or "None specified"> |
```

**If the project has a Reference Files table** (new index format):

```
### Reference Files
<show the Reference Files table from CLAUDE.md>

<if any files on disk are NOT in the manifest, note:
"Unregistered files: <list>. Consider adding these to Reference Files.">

### Progress
<checklist summary + items>
```

Add: "Project index loaded. Detail files will be loaded based on what
you choose to work on."

**If the project has NO Reference Files table** (older monolithic format):

```
### Files
<list all files found in Step 2d>

### Progress
<checklist summary + items>
```

Add: "Full project context loaded from CLAUDE.md."

## Step 4: Suggest Next Steps and Load Context

This step serves two purposes: help the user pick what to work on, AND
load the right detail files for that task.

**4a. Build task menu from checklists**

Scan unchecked items (`- [ ]`) in the Progress section and any plan
section (Fix Plan, Implementation Plan, etc.). These represent
available tasks.

For each unchecked item, determine which detail files are relevant by
matching the item's text against the Reference Files descriptions.
Use the description text to make the match — for example, an item like
"Build custom payload" maps to a file described as "custom-payload.sh
pipeline docs", and "Analyze CI run" maps to "CI run analysis,
timelines."

**4b. Present choices with file annotations**

Use AskUserQuestion with options that show which detail files will be
loaded. Examples for a bug project:

- "Next: Build custom payload with fix (loads: ci-testing-custom-payload.md, ci-runs.md)"
- "Continue investigation (loads: investigation.md, source-code-map.md)"
- "Review all project notes (loads: all detail files)"
- "Something else"

The user thinks in tasks and sees filenames as metadata. If the project
has no Reference Files table (monolithic format), skip the "loads:"
annotations since all content is already in context.

**4c. Load detail files based on choice**

After the user picks a task:
1. Read the mapped detail files using the Read tool.
2. Confirm what was loaded: "Loaded: investigation.md, source-code-map.md"
3. If the user picks "Review all project notes", read ALL files from the
   Reference Files manifest.
4. If the user picks "Something else", ask what they want to do and
   load relevant files based on their response.
5. If a mapped file does not exist on disk, skip it silently.

**4d. Skill suggestions**

Suggest relevant skills based on the project type:

| Type | Skills to suggest |
|------|-------------------|
| bug | `/prow-job:analyze-test-failure`, `/prow-job:analyze-install-failure`, `/prow-job:extract-must-gather`, `/feature-dev:feature-dev` |
| feature | `/feature-dev:feature-dev`, `/pr-review-toolkit:review-pr` |
| ci-testing | `/prow-job:analyze-test-failure`, `/prow-job:analyze-install-failure`, `/prow-job:analyze-resource`, `/prow-job:extract-must-gather` |
| docs | `/feature-dev:feature-dev` |
| analysis | `/pr-review-toolkit:review-pr`, `/prow-job:analyze-test-failure`, `/feature-dev:feature-dev` |

If the type is unknown, suggest `/feature-dev:feature-dev` as a general
starting point.

**4e. Reference Files convention reminder**

End with a brief note: "If you create new detail files during this
session, add them to the Reference Files table in CLAUDE.md so future
sessions can discover them."

---

## Important Notes

- Always use the Write tool to read/create files, never echo/cat via Bash
- Use Bash tool for `ls`, `find`, and `mkdir -p` operations
- If the project has no context file, don't try to fabricate one — ask
  the user for context instead
