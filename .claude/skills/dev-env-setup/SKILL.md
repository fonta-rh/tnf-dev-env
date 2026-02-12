---
name: dev-env-setup
description: Initialize or refresh a dev environment from a preset or custom config
argument-hint: [setup|setup custom]
user-invocable: true
---

# Dev Environment Setup Skill

You are helping a developer set up or refresh their multi-repo development
environment. This skill handles cloning repos, distributing context files,
and generating the root CLAUDE.md repo table.

## Subcommand Routing

Parse `$ARGUMENTS` to determine the mode:

- **`$ARGUMENTS` is empty, "setup", or starts with "setup "** (but NOT
  "setup custom"): Follow [Mode A: From Preset](#mode-a-from-preset)
- **`$ARGUMENTS` is "setup custom" or starts with "setup custom "**:
  Follow [Mode B: From Scratch](#mode-b-from-scratch)

---

## Mode A: From Preset

### Step 1: Select Preset

List available presets by scanning the `presets/` directory. For each
subdirectory, read `preset.yaml` to get name and description.

Present the presets to the user via AskUserQuestion. If only one preset
exists, suggest it as the default but still confirm.

### Step 2: Initialize

Run `./setup.sh init <preset-name>` via Bash to copy the preset's
`dev-env.yaml` to the root. This also copies `settings.local.json.tpl`
if `.claude/settings.local.json` doesn't exist yet.

### Step 3: Clone Repos

Run `./setup.sh clone` via Bash to clone all repos defined in
`dev-env.yaml`. This may take a while for large repos — let the user
know.

### Step 4: Distribute Context Files

For each repo defined in the preset's `dev-env.yaml`:

1. Check if `repos/<repo-name>/CLAUDE.md` already exists (native
   CLAUDE.md from the repo itself)
2. If **no native CLAUDE.md exists** and
   `presets/<preset>/context/<repo-name>.md` exists:
   - Copy the context file to `repos/<repo-name>/CLAUDE.md`
   - This gives Claude repo-specific context when working in that directory
3. If a **native CLAUDE.md already exists**:
   - Do NOT overwrite it — the repo's own CLAUDE.md takes priority
   - The preset's context file remains in `presets/<preset>/context/`
     and can be loaded on demand by the `/project` skill

Log which repos got supplemental CLAUDE.md files and which were skipped.

### Step 5: Generate Root CLAUDE.md Repo Table

Read the `dev-env.yaml` to build a markdown table of all repos. Then
read the current root `CLAUDE.md` and replace the content between the
`<!-- AUTO-GENERATED` comment markers with the freshly generated table.

The table format:
```markdown
| Name | Category | Summary |
|------|----------|---------|
| `<name>` | <category> | <summary> |
```

### Step 6: Summary

Present a summary to the user:
- Number of repos cloned
- Which repos got supplemental CLAUDE.md files
- Which repos already had native CLAUDE.md files (skipped)
- Pointer to preset docs (`presets/<preset>/docs/`)
- Suggest next steps: `/project new` to start a task

---

## Mode B: From Scratch

### Step 1: Gather Requirements

Ask the user to describe their project or focus area:
> "What project or component are you working on? This helps me suggest
> relevant repositories."

### Step 2: Add Repos

Help the user build their repo list. Options:
- Paste Git URLs directly
- Search by org/repo name
- Browse suggestions based on their description

For each repo, collect: name, URL, directory, branch, category, summary.

### Step 3: Generate dev-env.yaml

Write the `dev-env.yaml` file at the repo root using the Write tool,
following the schema from `dev-env.yaml.template`.

### Step 4: Clone Repos

Run `./setup.sh clone` via Bash.

### Step 5: Explore and Generate Context

For each cloned repo that does NOT have a native CLAUDE.md, use the
Task tool with `subagent_type=Explore` to scan the repo and generate
a supplemental CLAUDE.md. The explore agent should extract:

- **Purpose** (from README first line or repo description)
- **Key paths** (entry points, main packages, src directories)
- **Build/test commands** (from Makefile, package.json, etc.)
- **Test directory locations**
- **Language/framework** (from go.mod, package.json, Cargo.toml, etc.)

Write the generated context as `repos/<repo-name>/CLAUDE.md` with the
header:
```
<!-- Auto-generated supplemental context. Edit as needed. -->
```

For repos WITH a native CLAUDE.md, skip generation.

### Step 6: Generate Root CLAUDE.md

Same as Mode A Step 5 — update the repo table in root CLAUDE.md.

### Step 7: Review

Show the user what was generated:
- List all repos and their status
- Show which repos got auto-generated CLAUDE.md files
- Offer to let them review and edit any generated files

---

## Important Notes

- Always use the Write tool to create/modify files, not Bash echo/cat
- Use Bash tool only for `./setup.sh` commands and `mkdir -p`
- The `dev-env.yaml` file is gitignored (user-specific config)
- Preset context files in `presets/<preset>/context/` are committed to
  the repo and shared across the team
- When copying context files to `repos/<name>/CLAUDE.md`, those copies
  are gitignored via the `repos/` entry in `.gitignore`
