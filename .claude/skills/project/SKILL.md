---
name: project
description: Create and manage project workspaces for development tasks
argument-hint: <new|resume> [description]
user-invocable: true
---

# Project Workspace Manager

You are helping a developer manage project workspaces. Projects live
under the `projects/` directory and provide structured working environments
for specific tasks (bug investigations, feature development, CI work, etc.).

## Subcommand Routing

Parse `$ARGUMENTS` to determine the subcommand (case-insensitive):

- **`$ARGUMENTS` is exactly "new" or starts with "new "**: Follow the
  [New Project](#new-project) flow below. Everything after "new " is an
  optional initial description of the task.
- **`$ARGUMENTS` is exactly "resume" or starts with "resume "**: Follow
  the [Resume Project](#resume-project) flow below. Everything after
  "resume " is an optional project name to resume directly.
- **`$ARGUMENTS` is empty or doesn't start with a recognized
  subcommand**: Ask the user which subcommand they want using
  AskUserQuestion with options "new" and "resume".

---

## New Project

### Step 1: Gather Task Information

Ask the user questions to understand what they're working on. Use the
AskUserQuestion tool for structured questions and encourage free-text
descriptions.

**1a. Task Description**

If the user provided a description after "new" in the arguments, use that.
Otherwise, ask:

> "What task are you working on? Please describe it in a sentence or two."

**1b. Task Type**

Based on the description, suggest a task type and confirm with the user.
Use AskUserQuestion with these options:

| Type | When to suggest |
|------|-----------------|
| Bug investigation | Description mentions a bug, issue, OCPBUGS, regression, failure, broken behavior |
| Feature development | Description mentions adding, implementing, creating new functionality |
| CI/testing | Description mentions CI, Prow, test failures, promotion, job configuration |
| Documentation | Description mentions docs, writing, documenting, guide |
| Analysis/review | Description mentions reviewing, analyzing, investigating (without a specific bug), understanding |

**1c. JIRA Ticket (optional)**

Ask: "Do you have a JIRA ticket for this task? If so, paste the URL
(e.g., https://issues.redhat.com/browse/OCPBUGS-12345). Otherwise, just
say 'no'."

**1d. Related Repositories**

Ask which repos from this workspace are relevant. **Dynamically load
the repo list** from `dev-env.yaml` at the workspace root:

1. Read `dev-env.yaml` and extract each repo's `name` and `summary`
   fields from the `repos:` array.
2. Build AskUserQuestion options with multiSelect=true, using
   `name` as the label and `summary` as the description.
3. If `dev-env.yaml` does not exist or has no repos, skip this step
   and note that no repos are configured (the user can add them
   later by editing the project's CLAUDE.md frontmatter).

**1e. Additional Context (optional)**

Ask: "Any additional context? (PR URLs, Prow job URLs, related projects,
etc.) Say 'no' to skip."

### Step 2: Generate Folder Name

Based on the gathered information:

1. If a JIRA ticket was provided, extract the ticket ID (e.g.,
   `OCPBUGS-74679`) and use it as the suggested folder name.
2. Otherwise, generate a kebab-case slug from the task description
   (e.g., "Fix kubelet start timeout after fencing" becomes
   `fix-kubelet-start-timeout`). Keep it under 40 characters.
3. **Check if `projects/<suggestion>/` already exists** using ls. If it
   does, inform the user and ask:
   - Use a different name (suggest appending `-2`, `-3`, etc.)
   - Resume the existing project instead (point them to `/project resume`)
4. Once you have a name that doesn't conflict, present the suggestion
   and ask the user to confirm or provide an alternative:

> "I suggest naming the project folder: `<suggestion>`. Is that OK, or
> would you prefer a different name?"

### Step 3: Create Project Scaffold

Create the project directory and generate files based on the task type.

**3a. Create directory structure**

Use the Bash tool to create directories. The base is always
`projects/<folder-name>/`.

Additional subdirectories by type:

| Type | Directories |
|------|-------------|
| Bug investigation | `logs/`, `docs/` |
| Feature development | `docs/`, `patches/` |
| CI/testing | `results/`, `scripts/` |
| Documentation | `drafts/` |
| Analysis/review | `docs/` |

**3b. Generate CLAUDE.md**

Write the CLAUDE.md file at `projects/<folder-name>/CLAUDE.md` using the
Write tool. The content MUST follow the template for the detected type
(see [CLAUDE.md Templates](#claudemd-templates) below).

**3c. Generate .gitignore**

Write a `.gitignore` at `projects/<folder-name>/.gitignore` with:

```
# Large files that shouldn't be committed
*.log
*.txt.gz
*.tar.gz
```

### Step 4: Suggest Skills and Next Steps

After creating the project, provide a summary:

1. List the files and directories created
2. Suggest relevant skills based on the task type (see
   [Skill Suggestions](#skill-suggestions))
3. Suggest concrete next steps for starting the work
4. Remind the user they can resume this project later with
   `/project resume`

---

## Resume Project

### Step 1: Select Project

**1a. Determine project name**

If the user provided a name after "resume" in the arguments (e.g.,
`/project resume OCPBUGS-74679`), use that as the target project name.

If no name was provided (`/project resume` with no arguments), scan the
`projects/` directory using the Bash tool (`ls projects/`) and present
all directories as options via AskUserQuestion so the user can pick one.

**1b. Validate project exists**

Check that `projects/<name>/` exists. If it does not:
- Show an error: "Project `<name>` not found."
- List all available projects from `projects/`
- Ask the user to pick from the list or provide a corrected name

### Step 2: Load Project Context

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

### Step 3: Present Project Summary

Display a structured summary using this format:

```
## 📂 Project: <name>

| Field | Value |
|-------|-------|
| **Type** | <type from frontmatter, or inferred, or "Unknown"> |
| **Created** | <date from frontmatter, or "Unknown"> |
| **Status** | <status from frontmatter, or "Unknown"> |
| **JIRA** | <URL from frontmatter, or "None"> |
| **Repos** | <comma-separated list, or "None specified"> |

### Files
<list all files found in Step 2d>

### Progress
<If the context file contains checklist items (`- [x]` and `- [ ]`),
show a summary line like: "3/6 items completed" and list the checklist
items. If no checklist items found, say "No progress checklist found.">
```

After the summary table, confirm that the full CLAUDE.md or README.md
content has been read into context (it was read in Step 2 — just note
this to the user so they know the context is loaded).

### Step 4: Suggest Next Steps

Based on the project state, provide actionable suggestions:

**4a. Next checklist item**

If the context file has a Progress section with checklist items, find
the first unchecked item (`- [ ]`) and suggest it as the immediate next
action. For example:
> "Based on your progress checklist, the next step is: **Logs collected
> and analyzed**. Would you like to start on that?"

**4b. Skill suggestions**

Suggest relevant skills based on the project type, using the same
mapping as in [Skill Suggestions](#skill-suggestions):

| Type | Skills to suggest |
|------|-------------------|
| bug | `/prow-job:analyze-test-failure`, `/prow-job:analyze-install-failure`, `/prow-job:extract-must-gather`, `/feature-dev:feature-dev` |
| feature | `/feature-dev:feature-dev`, `/pr-review-toolkit:review-pr` |
| ci-testing | `/prow-job:analyze-test-failure`, `/prow-job:analyze-install-failure`, `/prow-job:analyze-resource`, `/prow-job:extract-must-gather` |
| docs | `/feature-dev:feature-dev` |
| analysis | `/pr-review-toolkit:review-pr`, `/prow-job:analyze-test-failure`, `/feature-dev:feature-dev` |

If the type is unknown, suggest `/feature-dev:feature-dev` as a general
starting point.

**4c. Ask what to work on**

End by asking the user what they'd like to work on. Use AskUserQuestion
with contextually relevant options based on the project state. Always
include a "Something else" option. For example, for a bug investigation
with unchecked items:
- "Work on next checklist item: <item>"
- "Review/update project notes"
- "Something else"

---

## CLAUDE.md Templates

All generated CLAUDE.md files start with YAML frontmatter for machine
readability, followed by type-specific sections.

### Common Frontmatter

```yaml
---
project: <folder-name>
type: <bug|feature|ci-testing|docs|analysis>
created: <YYYY-MM-DD>
status: active
jira: <URL or "none">
repos:
  - <repo1>
  - <repo2>
related_links:
  - <any URLs provided>
# If user provided no URLs, use: related_links: []
---
```

### Bug Investigation Template

```markdown
# <Title from JIRA or description>

## Bug Summary

**<One-line summary>**

<Expanded description from user input>

- **Jira**: <URL>
- **Priority**: TBD
- **Component**: <Component if known>
- **Affected Version**: TBD
- **Assignee**: TBD

## Attachments

| File | Description |
|------|-------------|
| *(add log files, screenshots, etc. here)* | |

## Timeline

```
(Reconstruct key events from logs here)
```

## Investigation Findings

*(Document findings as investigation progresses)*

## Root Cause

*(To be determined)*

## Fix Plan

- [ ] Identify root cause
- [ ] Determine fix approach
- [ ] Implement fix
- [ ] Test on cluster
- [ ] Submit PR

## Progress

- [x] Project created
- [ ] Bug details captured
- [ ] Logs collected and analyzed
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] PR submitted

## Related Source Code

| Repo | Key Path | Purpose |
|------|----------|---------|
| *(fill in relevant code paths)* | | |

## Suggested Skills

<Insert from skill suggestions table>
```

### Feature Development Template

```markdown
# <Feature Title>

## Feature Summary

<Description from user input>

- **Jira**: <URL>
- **Target Version**: TBD
- **Enhancement**: *(link to enhancement doc if applicable)*

## Design Notes

*(Document design decisions, alternatives considered, etc.)*

### Architecture

*(Describe how this feature fits into the project architecture)*

### API Changes

*(Any new or modified APIs, CRDs, FeatureGates)*

## Implementation Plan

- [ ] Review enhancement doc (if exists)
- [ ] Design approach
- [ ] Implement changes
- [ ] Write tests
- [ ] Submit PR(s)

## Related PRs

| PR | Repo | Status | Description |
|----|------|--------|-------------|
| *(track PRs here)* | | | |

## Progress

- [x] Project created
- [ ] Design documented
- [ ] Implementation started
- [ ] Tests written
- [ ] PR(s) submitted
- [ ] PR(s) merged

## Related Source Code

| Repo | Key Path | Purpose |
|------|----------|---------|
| *(fill in relevant code paths)* | | |

## Suggested Skills

<Insert from skill suggestions table>
```

### CI/Testing Template

```markdown
# <Test/CI Task Title>

## Test Summary

<Description from user input>

- **Jira**: <URL>
- **CI Job(s)**: *(link to relevant Prow jobs)*
- **Test Suite**: *(e.g., e2e, integration)*

## CI Job Links

| Job | Status | Link |
|-----|--------|------|
| *(track CI jobs here)* | | |

## Test Failures

*(Document test failures, patterns, and fixes)*

### Failure Analysis

| Test | Error | Root Cause | Fix |
|------|-------|------------|-----|
| | | | |

## Scripts

*(Document any helper scripts in the scripts/ directory)*

## Progress

- [x] Project created
- [ ] CI jobs identified
- [ ] Failures analyzed
- [ ] Fixes implemented
- [ ] CI passing

## Related Source Code

| Repo | Key Path | Purpose |
|------|----------|---------|
| *(fill in relevant code paths)* | | |

## Suggested Skills

<Insert from skill suggestions table>
```

### Documentation Template

```markdown
# <Documentation Task Title>

## Doc Summary

<Description from user input>

- **Jira**: <URL>
- **Target**: *(which docs are being created/updated)*

## Target Documents

| Document | Repo Path | Status |
|----------|-----------|--------|
| *(list docs to create or modify)* | | |

## Review Notes

*(Capture review feedback, technical accuracy notes, etc.)*

## Progress

- [x] Project created
- [ ] Draft written
- [ ] Technical review
- [ ] Editorial review
- [ ] PR submitted

## Related Source Code

| Repo | Key Path | Purpose |
|------|----------|---------|
| *(fill in relevant code paths)* | | |

## Suggested Skills

<Insert from skill suggestions table>
```

### Analysis/Review Template

```markdown
# <Analysis Title>

## Analysis Summary

<Description from user input>

- **Jira**: <URL>
- **Scope**: *(what is being analyzed/reviewed)*

## Findings

*(Document analysis results here)*

## Recommendations

*(Based on findings, what actions should be taken)*

## Progress

- [x] Project created
- [ ] Analysis started
- [ ] Findings documented
- [ ] Recommendations made
- [ ] Actions taken

## Related Source Code

| Repo | Key Path | Purpose |
|------|----------|---------|
| *(fill in relevant code paths)* | | |

## Suggested Skills

<Insert from skill suggestions table>
```

---

## Skill Suggestions

Based on the project type, include these suggestions in the generated
CLAUDE.md "Suggested Skills" section:

### Bug Investigation
```
- `/prow-job:analyze-test-failure` — Analyze test failures from Prow CI jobs
- `/prow-job:analyze-install-failure` — Analyze OpenShift installation failures
- `/prow-job:extract-must-gather` — Extract must-gather archives from CI artifacts
- `/feature-dev:feature-dev` — When the fix requires significant code changes
```

### Feature Development
```
- `/feature-dev:feature-dev` — Guided feature development with codebase analysis
- `/pr-review-toolkit:review-pr` — Review PRs before submitting
```

### CI/Testing
```
- `/prow-job:analyze-test-failure` — Analyze test failures from Prow CI jobs
- `/prow-job:analyze-install-failure` — Analyze installation failures
- `/prow-job:analyze-resource` — Analyze Kubernetes resource lifecycle in CI artifacts
- `/prow-job:extract-must-gather` — Extract must-gather from CI artifacts
```

### Documentation
```
- `/feature-dev:feature-dev` — Understand codebase to write accurate docs
```

### Analysis/Review
```
- `/pr-review-toolkit:review-pr` — Comprehensive PR review
- `/prow-job:analyze-test-failure` — Analyze CI test data
- `/feature-dev:feature-dev` — Deep codebase exploration
```

---

## Important Notes

- Always use the Write tool to create files, never echo/cat via Bash
- Use Bash tool only for `mkdir -p` to create directories
- After creating the project, briefly list what was created and what
  the user should do next
- If the user provides enough context in the initial `/project new`
  arguments, minimize questions — only ask what's truly missing
- The YAML frontmatter `status` field should always start as `active`
- Use today's date for the `created` field
- When populating the "Related Source Code" table:
  - For each selected repo, check `repos/<repo>/CLAUDE.md` or
    `presets/*/context/<repo>.md` for "Key paths", "Key files",
    or similar sections
  - If found, add 1-3 most relevant paths to the table
  - If not found, add the repo name with an empty path and a TODO
    comment like "TODO: fill in relevant paths"
