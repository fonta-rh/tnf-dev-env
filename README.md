# TNF Development Environment

A workspace template for developing and testing **Two Nodes with Fencing (TNF)** - an OpenShift topology providing high availability with two control plane nodes using RHEL-HA (Pacemaker/Corosync).

## Quick Start

```bash
# Clone this repo as your workspace
git clone https://github.com/your-org/tnf-dev-env.git
cd tnf-dev-env

# Clone all TNF-related repositories
./setup.sh
```

## How It Works

All TNF source repositories are cloned into the `repos/` folder. The `CLAUDE.md` file provides Claude Code with context about each repository's role in TNF, enabling AI-assisted development across the entire codebase.

**Workflow:**
1. Work with Claude from this top-level directory for cross-repo context
2. Navigate into `repos/<repo-name>/` to implement changes
3. Use `./setup.sh update` to pull latest changes

## Setup Script Commands

| Command | Description |
|---------|-------------|
| `./setup.sh` | Clone all repositories (first-time setup) |
| `./setup.sh update` | Pull latest changes for all repos |
| `./setup.sh status` | Show clone status and current branches |
| `./setup.sh list` | List configured repositories |

## Configuration

Edit `repos.txt` to customize which repositories to clone and which branches to use. The file is created from `repos.txt.template` on first run.

## Included Repositories

- **two-node-toolbox** - Deployment automation (AWS/external host, dev-scripts/kcli)
- **assisted-service** - Cluster installation orchestration
- **cluster-etcd-operator** - etcd management and TNF handover
- **machine-config-operator** - Pacemaker/Corosync configuration
- **resource-agents** - podman-etcd OCF agent
- **dev-scripts** - Low-level cluster deployment scripts
- **origin** - E2E test suite
- And more (see `CLAUDE.md` for details)

## Requirements

- Git
- [Claude Code](https://claude.ai/code) (recommended for AI-assisted development)
