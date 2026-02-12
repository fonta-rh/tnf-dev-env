# Dev Environment Generator

A reusable scaffolding tool for multi-repo OpenShift development environments. Define which repositories you need in a YAML config, and this tool clones, organizes, and provides AI-assisted context for your entire workspace.

Ships with a **preset system** for common development scenarios — start with a preset or build your own custom environment.

## Quick Start

```bash
# Clone this repo as your workspace
git clone <your-fork-url>
cd tnf-dev-env

# Option A: Initialize from a preset
./setup.sh init tnf          # Sets up the TNF (Two Nodes with Fencing) environment

# Option B: Start from scratch
cp dev-env.yaml.template dev-env.yaml
# Edit dev-env.yaml with your repos, then:
./setup.sh clone
```

## How It Works

1. **`dev-env.yaml`** defines which repos to clone (name, URL, branch, category, summary)
2. **`setup.sh`** manages cloning, updating, and status checking
3. **`CLAUDE.md`** gives Claude Code cross-repo context for AI-assisted development
4. **Presets** (`presets/`) provide ready-made configs with documentation and per-repo context
5. **Projects** (`projects/`) give structured workspaces for specific tasks

## Setup Script Commands

| Command | Description |
|---------|-------------|
| `./setup.sh init <preset>` | Initialize from a preset (copies config, clones repos) |
| `./setup.sh clone` | Clone all repos defined in `dev-env.yaml` |
| `./setup.sh update` | Pull latest changes for all repos |
| `./setup.sh status` | Show clone status and current branches |
| `./setup.sh list` | List configured repositories |

## Available Presets

| Preset | Description |
|--------|-------------|
| `tnf` | Two Nodes with Fencing — OpenShift HA with Pacemaker/Corosync (14 repos) |

Create your own preset by adding a directory under `presets/` with a `preset.yaml`, `dev-env.yaml`, and optional `context/` and `docs/` directories.

## Claude Code Skills

| Skill | Description |
|-------|-------------|
| `/dev-env setup` | Initialize or refresh a dev environment from a preset or custom config |
| `/project:new` | Create a structured project workspace for a specific task |
| `/project:resume` | Resume an existing project with full context reload |

## Configuration

The `dev-env.yaml` file uses a simple schema:

```yaml
repos:
  - name: my-repo
    url: https://github.com/org/my-repo.git
    directory: my-repo
    branch: main
    category: development    # docs, development, testing, deployment, troubleshooting
    summary: "Brief description of the repo's role"
```

See `dev-env.yaml.template` for the full commented schema.

## Requirements

- Git
- [Claude Code](https://claude.ai/code) (recommended for AI-assisted development)
