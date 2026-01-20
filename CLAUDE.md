# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment Purpose

This workspace serves as a **TNF (Two Nodes with Fencing) development environment template**. TNF is an OpenShift topology that provides high availability with only two control plane nodes, using RHEL-HA (Pacemaker/Corosync) for fencing and etcd management.

**Workflow:**
1. Developers/QA clone this repo as their workspace root
2. All TNF-relevant source repositories are cloned under the `repos/` folder
3. Work with Claude from this top-level directory to get full context across all repos
4. Navigate into specific `repos/<repo-name>/` directories to implement changes

**The `repos/` folder contains all source code.** This CLAUDE.md provides a summary of each repository's relevance to TNF, so Claude understands how to navigate and use them effectively.

### Source of Truth Priority

**IMPORTANT**: When answering questions or implementing changes related to TNF:
1. **Always look at repos in this workspace FIRST** before using internal knowledge or web searches
2. If a component has a repo here, that repo is the **authoritative source of truth**
3. Code in `repos/` reflects the latest development state, which may differ from public documentation

### Fork Model

All repositories **except `two-node-toolbox`** use a fork model for contributions:
- Push changes to your personal fork first, not directly to upstream
- Create pull requests from your fork to the upstream repository
- `two-node-toolbox` is an internal tool and can be pushed to directly

### Repository Categories

Repositories are grouped by their primary purpose:

| Category | Repositories | Description |
|----------|-------------|-------------|
| **Docs** | `enhancements`, `openshift-docs` | Design specs and user-facing documentation |
| **Testing** | `origin`, `release` | E2E tests and CI/CD configuration |
| **Deployment** | `two-node-toolbox` | Primary TNF cluster deployment automation |
| **Development** | `assisted-service`, `cluster-etcd-operator`, `machine-config-operator`, `installer`, `cluster-baremetal-operator`, `resource-agents`, `dev-scripts` | Core TNF component source code |
| **Troubleshooting** | `pacemaker` | Upstream reference for debugging HA behavior |

### Typical Tasks

#### Exploration
<!-- TODO: Add guidance for codebase exploration tasks -->

#### Development
<!-- TODO: Add guidance for development workflow tasks -->

#### Troubleshooting
<!-- TODO: Add guidance for debugging and troubleshooting tasks -->

---

## Repositories

All repositories are located in the `repos/` folder.

### enhancements (`repos/enhancements/`)
**Category**: Docs

**Purpose**: OpenShift enhancement proposals repository

**TNF Relevance**: Contains the authoritative TNF enhancement document defining:
- Architecture and workflow for two-node clusters with fencing
- Component changes required (CEO, MCO, installer, BMO, etc.)
- Installation flow via Assisted Installer and Agent-Based Installer
- Failure handling scenarios and recovery procedures
- Integration between RHEL-HA stack and OpenShift

**When to use this repo**:
- Understanding design rationale and architectural decisions
- Answering "why" questions about TNF behavior
- Referencing the original design spec for component responsibilities

**Key files**:
- `enhancements/two-node-fencing/tnf.md` - Main enhancement document
- `enhancements/two-node-fencing/etcd-flowchart-both-nodes-reboot-scenarios.svg` - Reboot scenarios flowchart
- `enhancements/two-node-fencing/etcd-flowchart-gns-nogns-happy-paths.svg` - Happy path flowchart (GNS/non-GNS)

**Enhancement proposal structure**: Documents follow a standard format with sections for Summary, Motivation, Goals, Non-Goals, Proposal, Design Details, Risks, and Alternatives. Navigate using these headings to find specific information.

### assisted-service (`repos/assisted-service/`)
**Category**: Development

**Purpose**: REST/Kubernetes API service that installs OpenShift clusters with minimal infrastructure prerequisites

**TNF Relevance**: Core service orchestrating TNF cluster installation via MCE/ACM:
- Validates TNF cluster requirements (2 CP nodes, no arbiters, OCP >= 4.20)
- Collects and stores fencing credentials (BMC username/password/address) per host
- Generates install-config with fencing credentials for the installer
- Handles TNF-specific network connectivity groups (minimum 2 hosts instead of 3)

**Note**: This repo is also used as part of the **Agent Based Installation (ABI)** flow when installing via MCE/ACM. For standalone ABI without MCE/ACM, see the `installer` repository.

**Key TNF code paths**:
- `internal/common/common.go` - `IsClusterTopologyTwoNodesWithFencing()` detection logic
- `internal/cluster/validator.go` - TNF cluster validation
- `internal/cluster/transition.go` - State machine handling for TNF clusters
- `internal/installcfg/installcfg.go` - `Fencing` and `FencingCredential` structs
- `internal/installcfg/builder/builder.go` - Generates install-config with fencing data
- `internal/featuresupport/features_misc.go` - TNF feature support level checks
- `models/fencing_credentials_params.go` - BMC credential model
- `docs/enhancements/tnf-clusters.md` - Assisted-service TNF enhancement doc

**TNF-related test files**:
- `internal/common/common_test.go`
- `internal/cluster/validator_test.go`
- `internal/cluster/transition_test.go`
- `internal/installcfg/builder/builder_test.go`
- `internal/host/host_test.go`
- `internal/bminventory/inventory_test.go`
- `internal/provider/baremetal/installConfig_test.go`
- `internal/controller/controllers/agent_controller_test.go`
- `internal/controller/controllers/bmh_agent_controller_test.go`
- `cmd/agentbasedinstaller/host_config_test.go`
- `subsystem/kubeapi/kubeapi_test.go`

**Key constants** (from `internal/common/common.go`):
- `MinimumVersionForTwoNodesWithFencing = "4.20"`
- `AllowedNumberOfMasterHostsInTwoNodesWithFencing = 2`

**Commands**:
```bash
skipper make all                    # Build everything
skipper make build-minimal          # Build binary only
skipper make generate-from-swagger  # Regenerate after API changes
skipper make unit-test              # Run unit tests (requires Docker/Podman)
skipper make subsystem-test         # Run subsystem tests
```

### cluster-etcd-operator (`repos/cluster-etcd-operator/`)
**Category**: Development

**Purpose**: Manages etcd scaling during cluster bootstrap and operation, provisions TLS certificates

**TNF Relevance**: **This is the heart of TNF**. Contains the TNF controller code that runs on the cluster after installation and orchestrates the transition to Pacemaker-managed etcd:
- Initializes the Pacemaker cluster configuration
- Transitions etcd management from CEO to RHEL-HA
- Configures fencing using BMC credentials
- Handles the handover of etcd to the podman-etcd OCF agent

**Key paths**:
- `pkg/tnf/` - TNF-specific controllers and utilities
  - `pkg/tnf/operator/starter.go` - TNF operator entry point
  - `pkg/tnf/auth/runner.go` - Authentication phase
  - `pkg/tnf/setup/runner.go` - Setup phase
  - `pkg/tnf/fencing/runner.go` - Fencing configuration phase
  - `pkg/tnf/after-setup/runner.go` - Post-setup phase
  - `pkg/tnf/pkg/pcs/` - Pacemaker integration
    - `cluster.go` - Cluster initialization
    - `etcd.go` - etcd resource configuration
    - `fencing.go` - STONITH/fencing setup
    - `types.go` - Type definitions
  - `pkg/tnf/pkg/config/` - Cluster configuration
  - `pkg/tnf/pkg/etcd/` - etcd management
  - `pkg/tnf/pkg/jobs/` - Job controller
  - `pkg/tnf/pkg/tools/` - Utilities (conditions, secrets, redact, etc.)
- `docs/HACKING.md` - Development guide

**TNF controller phases** (executed in order):
1. **auth** - Handles Pacemaker authentication between nodes (pcsd tokens)
2. **setup** - Initializes Pacemaker cluster, configures resources
3. **fencing** - Configures STONITH with BMC credentials
4. **after-setup** - Post-setup tasks, hands etcd management to Pacemaker

**TNF-related test files**:
- `pkg/tnf/operator/starter_test.go`
- `pkg/tnf/pkg/pcs/fencing_test.go`
- `pkg/tnf/pkg/pcs/types_test.go`
- `pkg/tnf/pkg/config/cluster_test.go`
- `pkg/tnf/pkg/etcd/etcd_test.go`
- `pkg/tnf/pkg/jobs/jobcontroller_test.go`
- `pkg/tnf/pkg/tools/redact_test.go`

**Commands**:
```bash
make build                    # Build binaries
hack/generate.sh              # Regenerate alerts from jsonnet
make test                     # Run tests

# OTE (OpenShift Tests Extension) framework
./cluster-etcd-operator-tests-ext run-suite openshift/cluster-etcd-operator/all
./cluster-etcd-operator-tests-ext run-test "test-name"
./cluster-etcd-operator-tests-ext list suites
```

### machine-config-operator (`repos/machine-config-operator/`)
**Category**: Development

**Purpose**: Manages operating system configuration and updates (systemd, cri-o/kubelet, kernel, NetworkManager, etc.)

**TNF Relevance**: Prepares nodes for Pacemaker **BEFORE** CEO TNF controller runs (Day 1 setup):
- Directory structure for PCS and Corosync (`/var/lib/pcsd`, `/var/lib/corosync`, `/var/log/pcsd`, `/var/log/cluster`)
- Systemd units to enable and start PCSD service
- Fencing validator script for cluster health checking
- Installs HA packages via rpm-ostree extensions

**Key TNF paths**:
- `templates/master/00-master/two-node-with-fencing/` - TNF-specific templates
  - `units/ha-00-directories.service.yaml` - Creates directories for PCS/Corosync
  - `units/ha-01-enable-services.service.yaml` - Enables and starts PCSD
  - `files/fencing-validator.yaml` - Fencing validation script
  - `extensions/two-node-ha` - MCO extension trigger file

**MCO Extensions concept**: Extensions install RPM packages on RHCOS via rpm-ostree:
- The `two-node-ha` extension installs pacemaker, corosync, pcs, fence-agents, and related packages
- Extensions are triggered by filename presence (the file content doesn't matter, just the file existing)
- This happens during node configuration, before CEO runs

**TNF-related test files**:
- `test/e2e-2of2/extension_test.go`
- `pkg/daemon/update_test.go`
- `pkg/controller/common/helpers_test.go`

**Commands**:
```bash
make build        # Build binaries
make test-unit    # Run unit tests
make verify       # Run verification checks
```

**Inspecting MCO in a cluster**:
```bash
oc describe clusteroperator/machine-config
oc describe machineconfigpool
```

### installer (`repos/installer/`)
**Category**: Development

**Purpose**: OpenShift cluster installation tool supporting multiple platforms

**TNF Relevance**: Main repo for **standalone Agent-Based Installation (ABI)** without MCE/ACM:
- Reads install-config.yaml with fencing credentials
- Generates ignition configs for the cluster
- Handles bootstrap process where one node serves as temporary bootstrap
- Contains its own fencing credentials handling for ABI flow

**Key paths**:
- `pkg/asset/agent/` - Agent-Based Installer implementation
- `pkg/asset/agent/manifests/fencingcredentials.go` - Fencing credentials handling for ABI
- `pkg/types/validation/installconfig.go` - Install config validation
- `pkg/types/machinepools.go` - Machine pool definitions

**Note**: Two installation paths exist for TNF:
1. **Standalone ABI** (this repo) - Direct installation without MCE/ACM, uses `openshift-install` directly
2. **MCE/ACM with assisted-service** - Uses assisted-service to orchestrate installation

Both paths require fencing credentials in install-config.yaml.

**TNF-related test files**:
- `pkg/asset/agent/manifests/fencingcredentials_test.go`
- `pkg/asset/agent/installconfig_test.go`
- `pkg/types/validation/installconfig_test.go`
- `pkg/asset/machines/master_test.go`

**Commands**:
```bash
hack/build.sh                        # Build installer
bin/openshift-install create cluster # Create cluster
openshift-install destroy cluster    # Destroy cluster
```

### cluster-baremetal-operator (`repos/cluster-baremetal-operator/`)
**Category**: Development

**Purpose**: Deploys and manages baremetal server provisioning components (metal3.io)

**TNF Relevance**: Manages bare metal host provisioning. For TNF, BMO must avoid power-management conflicts with Pacemaker fencing on control-plane nodes (Pacemaker handles fencing, not BMO).

**Note**: No TNF-specific code exists in this repo. The TNF relationship is purely about awareness - CBO/BMO should not attempt to power-manage control-plane nodes that are under Pacemaker's control.

**Key paths**:
- `api/v1alpha1/provisioning_types.go` - Provisioning CR definitions
- `config/crd/bases/metal3.io_provisionings.yaml` - CRD definition

**Commands**:
```bash
make build      # Build operator
make test       # Run tests
make generate   # Generate manifests
make deploy     # Deploy to cluster
```

### resource-agents (`repos/resource-agents/`)
**Category**: Development

**Purpose**: OCF-compliant resource agents for Pacemaker and rgmanager

**TNF Relevance**: Contains the `podman-etcd` resource agent that Pacemaker uses to control etcd after CEO hands it over:
- Creates and manages etcd containers via Podman
- Handles etcd cluster membership (adding/removing members)
- Manages learner nodes and standalone scenarios
- Implements force-new-cluster for recovery after fencing
- Monitors certificate changes and restarts etcd accordingly
- Prevents split-brain via careful peer detection

**Key files**:
- `heartbeat/podman-etcd` - The main OCF resource agent script (~75KB, ~2000 lines)
- `heartbeat/podman` - Base podman resource agent

**Key functions in podman-etcd**:
- `podman_start()` - Container startup with cluster state detection
- `leave_etcd_member_list()` - Safe node removal from etcd cluster
- `reconcile_member_state()` - Promotes learners, reconciles cluster
- `container_health_check()` - Advanced health monitoring

**Testing**: **IMPORTANT** - No unit tests exist for podman-etcd. Testing must be done on a live TNF cluster:
- Use `make patch-nodes` in `two-node-toolbox` (from `deploy/` directory)
- This builds the modified resource-agents RPM and deploys it to cluster nodes
- See `two-node-toolbox/helpers/build-and-patch-resource-agents.yml` for the patching playbook

**Build**:
```bash
./autogen.sh
./configure
make
```

### pacemaker (`repos/pacemaker/`)
**Category**: Troubleshooting

**Purpose**: High-availability cluster resource manager from ClusterLabs (upstream)

**TNF Relevance**: Core component of the RHEL-HA stack that provides:
- Cluster resource management and orchestration
- STONITH/fencing daemon for BMC power operations
- Quorum enforcement and split-brain prevention
- Integration with Corosync for membership and messaging
- Execution of OCF resource agents (like podman-etcd)

**Note**: This is **upstream Pacemaker** included for reference only:
- TNF uses Pacemaker but will **NOT modify it** - changes go to RHEL packages
- Useful for understanding HA internals when troubleshooting
- Also helpful for resource-agents development (understanding how Pacemaker invokes OCF agents)
- In production, Pacemaker comes from RHEL-HA packages, not built from this source

**Key paths** (for troubleshooting/understanding):
- `daemons/fenced/` - STONITH/fencing daemon (executes BMC power operations)
- `daemons/controld/` - CRM controller (handles fencing requests, Corosync events)
- `daemons/controld/controld_fencing.c` - Fencing request handling
- `lib/fencing/` - Fencing API library

**Note**: Pacemaker configuration options (stonith-enabled, no-quorum-policy, etc.) are set automatically by CEO's TNF controller - see `cluster-etcd-operator/pkg/tnf/pkg/pcs/`.

**Commands** (for reference):
```bash
./autogen.sh && ./configure && make   # Build
make check                            # Run tests
```

**Documentation**: https://clusterlabs.org/pacemaker/doc/

### openshift-docs (`repos/openshift-docs/`)
**Category**: Docs

**Purpose**: Official OpenShift documentation in AsciiDoc format (becomes docs.openshift.com)

**TNF Relevance**: Contains user-facing documentation for TNF installation and operation

**Key paths**:
- `installing/installing_two_node_cluster/` - Two-node cluster installation guides
- `installing/installing_two_node_cluster/installing_tnf/` - TNF-specific docs:
  - `install-tnf.adoc` - Installation guide
  - `install-post-tnf.adoc` - Post-installation tasks
  - `installing-two-node-fencing.adoc` - Fencing setup
- `modules/installation-two-node-*` - Modular content about TNF

**Documentation structure**:
- Uses AsciiDoc (`.adoc`) format
- **Assemblies** (topic directories) include content from **modules** (reusable snippets)
- Modules in `modules/` are included via `include::` directives
- This repo is the source for https://docs.openshift.com

### dev-scripts (`repos/dev-scripts/`)
**Category**: Development

**Purpose**: Development and testing environment scripts for deploying OpenShift on libvirt VMs with virtualbmc

**TNF Relevance**: Primary tool for creating TNF development and testing clusters locally or in CI:
- Configures libvirt VMs with virtualbmc to simulate baremetal nodes
- Enables full TNF deployment including Redfish-based fencing

**Relationship to two-node-toolbox**:
- `two-node-toolbox` (TNT) **wraps dev-scripts** for simplified deployment
- This repo is for development/modification of the deployment scripts themselves
- When TNT deployments fail, often need to look here to understand what went wrong
- Also useful for troubleshooting TNT installation issues (since TNT uses dev-scripts under the hood)

**TNF-specific configuration**:

The `AGENT_E2E_TEST_SCENARIO` variable supports TNF scenarios:
- `TNF_IPV4` - TNF cluster with IPv4 networking
- `TNF_IPV6` - TNF cluster with IPv6 networking
- `TNF_IPV4_DHCP` - TNF cluster with IPv4 DHCP
- `TNF_IPV6_DHCP` - TNF cluster with IPv6 DHCP

**Key TNF variables**:
```bash
# Automatically set when NUM_MASTERS=2 and NUM_ARBITERS=0
export ENABLE_TWO_NODE_FENCING="true"

# TNF requires redfish BMC driver (only supported driver for TNF)
export BMC_DRIVER=redfish
```

**TNF scenario VM specs**:
```bash
export NUM_MASTERS=2
export MASTER_VCPU=8
export MASTER_DISK=100
export MASTER_MEMORY=32768
export NUM_WORKERS=0
export ENABLE_TWO_NODE_FENCING="true"
```

**Key TNF code paths**:
- `common.sh` - Auto-detection of TNF topology, TNF scenario settings
- `utils.sh` - `node_map_to_install_config_fencing_credentials()` function generates fencing credentials
- `agent/roles/manifests/templates/install-config_baremetal_yaml.j2` - Jinja2 template for fencing credentials
- `ocp_install_env.sh` - Injects fencing block into install-config

**Commands**:
```bash
# Full agent-based installation (TNF)
make agent

# Individual agent steps
make agent_requirements     # Install software dependencies
make agent_build_installer  # Build/extract openshift-install
make agent_configure        # Configure network, create manifests
make agent_create_cluster   # Generate ISO and boot VMs

# Cleanup
make agent_cleanup          # Remove agent artifacts
make clean                  # Full cleanup (VMs, network, artifacts)
make realclean              # Deep cleanup including cache

# Debugging
make agent_gather           # Collect logs from agent install
```

**MCE deployment for TNF testing**:
```bash
export AGENT_DEPLOY_MCE=true
make agent
```

**Prerequisites**:
- CentOS/RHEL 8+ host with at least 64GB RAM (32GB minimum)
- Libvirt and virtualbmc for VM management
- `CI_TOKEN` from console-openshift-console.apps.ci.l2s4.p1.openshiftapps.com
- Pull secret from cloud.redhat.com

### two-node-toolbox (`repos/two-node-toolbox/`)
**Category**: Deployment

**Purpose**: Deployment automation framework for two-node OpenShift clusters in development and testing environments

**TNF Relevance**: **THE go-to tool** for TNF developers/QA. One-stop-shop for cluster lifecycle:
- Automates AWS EC2 hypervisor provisioning via CloudFormation
- Supports "Bring Your Own Server" workflow for existing RHEL 9 hosts
- Wraps dev-scripts and kcli for simplified cluster deployment
- Provides cluster lifecycle management (deploy, clean, shutdown, startup)
- Automated Redfish stonith configuration for fencing topology
- Includes utilities for patching resource-agents on live clusters

**Deployment options**:
- **AWS Hypervisor**: Automated EC2 instance creation and cluster deployment
- **External Host**: Use existing RHEL 9 server with Ansible playbooks
- **dev-scripts method**: Traditional deployment (fencing topology)
- **kcli method**: Modern deployment with simplified VM management (fencing only)

**Key paths**:
- `deploy/` - Main deployment automation directory
  - `deploy/aws-hypervisor/` - AWS CloudFormation and instance lifecycle scripts
  - `deploy/openshift-clusters/` - Ansible playbooks (setup.yml, clean.yml, redeploy.yml)
  - `deploy/openshift-clusters/roles/` - Ansible roles (dev-scripts, kcli, redfish, proxy)
- `helpers/` - Utility scripts:
  - `build-and-patch-resource-agents.yml` - For patching resource-agents on live clusters
  - `collect-tnf-logs.yml` - Log collection playbook
  - `fencing_validator.sh` - Fencing validation script
- `docs/fencing/` - TNF-specific documentation

**Cross-references**:
- **dev-scripts**: TNT wraps dev-scripts; look there for underlying deployment logic
- **resource-agents**: Use `make patch-nodes` to test podman-etcd changes on live clusters

**Troubleshooting note**: For cluster troubleshooting, there is an etcd-troubleshooting Claude skill with helpers. Check the `helpers/` directory for troubleshooting utilities.

**Commands** (from `deploy/` directory):
```bash
# One-command deployment (AWS)
make deploy fencing-ipi    # Deploy TNF cluster with IPI
make deploy arbiter-ipi    # Deploy TNA cluster with IPI

# Instance lifecycle
make create                # Create EC2 instance
make init                  # Initialize instance
make ssh                   # SSH into hypervisor
make start / make stop     # Start/stop instance
make destroy               # Destroy instance

# Cluster operations
make redeploy-cluster      # Redeploy cluster
make clean                 # Clean cluster
make patch-nodes           # Build and patch resource-agents RPM
make get-tnf-logs          # Collect cluster logs
```

**External host workflow**:
```bash
cd deploy/openshift-clusters/
cp inventory.ini.sample inventory.ini
# Edit inventory.ini with server details
ansible-playbook init-host.yml -i inventory.ini  # One-time setup
ansible-playbook setup.yml -i inventory.ini      # Deploy cluster
```

**Prerequisites**:
- AWS CLI configured (for AWS hypervisor option)
- Ansible, make, jq, rsync, golang
- Pull secret from cloud.redhat.com
- CI_TOKEN for CI builds

### origin (`repos/origin/`)
**Category**: Testing

**Purpose**: OpenShift extended test suite and E2E testing framework

**TNF Relevance**: Contains the comprehensive TNF E2E test suite:
- TNF topology validation
- Recovery scenarios after node failures
- Node replacement procedures
- Degraded mode behavior
- Pacemaker/etcd integration testing

**Key TNF paths**:
- `test/extended/two_node/` - Main TNF test directory
  - `tnf_topology.go` - General TNF topology tests
  - `tnf_recovery.go` - Recovery scenario testing
  - `tnf_node_replacement.go` - Node replacement tests
  - `tnf_degraded.go` - Degraded mode testing
- `test/extended/two_node/utils/common.go` - Test utilities

**Running tests**:
- Tests require a **running TNF cluster** - they are E2E tests that interact with real cluster
- Tests are typically run via CI (see `release` repo for job configurations)
- For local execution, need `KUBECONFIG` pointing to a TNF cluster

**Test execution**:
```bash
openshift-tests run openshift/two-node              # Run TNF test suite
openshift-tests run openshift/two-node --run "name" # Run specific test
```

### release (`repos/release/`)
**Category**: Testing

**Purpose**: OpenShift CI/CD configuration repository for Prow jobs and test workflows

**TNF Relevance**: Central orchestration point for TNF CI testing:
- Prow job configurations for TNF tests
- Step registry workflows for TNF scenarios
- Cluster profiles for TNF testing environments

**How OpenShift CI works**:
- **Prow**: Kubernetes-based CI system that runs jobs
- **ci-operator**: OpenShift-specific test orchestrator
- **Step registry**: Reusable test steps, chains, and workflows
- Workflows compose steps for full test scenarios

**Key TNF paths**:
- `ci-operator/step-registry/baremetalds/two-node/fencing/` - TNF step registry workflows:
  - `baremetalds-two-node-fencing-workflow.yaml` - Main TNF workflow
  - `extended/` - Extended test workflow
  - `techpreview/` - Tech preview workflow
  - `upgrade/` - Upgrade workflow
  - `post-install/` - Post-install validation and node degradation tests
- `ci-operator/jobs/openshift/` - Presubmit/periodic job configurations:
  - `cluster-etcd-operator/` - CEO presubmit jobs
  - `machine-config-operator/` - MCO presubmit jobs
  - `installer/` - Installer presubmit jobs
  - `origin/` - Origin presubmit jobs

---

## TNF Architecture Overview

```
                         INSTALLATION PATHS
    +------------------+  +------------------+  +------------------+
    | Assisted Inst.   |  | Agent-Based Inst.|  |   IPI Installer  |
    |   (MCE/ACM)      |  | (openshift-inst) |  |                  |
    +--------+---------+  +--------+---------+  +--------+---------+
             |                     |                     |
             +---------------------+---------------------+
                                   |
                                   v
                    +---------------------------------------------+
                    |     machine-config-operator (MCO)           |
                    |   - Installs HA packages (pacemaker, pcs)   |
                    |   - Creates directories, enables PCSD       |
                    |   - Prepares nodes BEFORE CEO runs          |
                    +----------------------+----------------------+
                                           |
                    +----------------------v----------------------+
                    |       cluster-etcd-operator (CEO)           |
                    |   - Manages etcd during bootstrap           |
                    |   - TNF controller initializes RHEL-HA      |
                    |   - Hands over etcd to Pacemaker            |
                    +----------------------+----------------------+
                                           |
          +--------------------------------+--------------------------------+
          |                                |                                |
+---------v---------+          +-----------v-----------+          +---------v---------+
|     Corosync      |          |      Pacemaker        |          |    podman-etcd    |
| (cluster member-  |<-------->|  (fault tolerance     |<-------->|   (OCF agent      |
|  ship & quorum)   |          |   & failover)         |          |    for etcd)      |
+-------------------+          +-----------+-----------+          +-------------------+
                                           |
                               +-----------v-----------+
                               |     BMC Fencing       |
                               |     (Redfish)         |
                               +-----------------------+
```

## Key TNF Concepts

- **C-quorum**: Quorum as determined by Corosync membership
- **E-quorum**: Quorum as determined by etcd membership
- **Fencing**: Powering off unresponsive nodes via BMC to prevent split-brain
- **force-new-cluster**: etcd flag to restart as cluster-of-one after peer failure
- **Learner node**: etcd node waiting to become a full voting member
- **STONITH**: "Shoot The Other Node In The Head" - fencing mechanism

## TNF Failure Scenarios

1. **Network failure**: Pacemaker fences one node, survivor restarts etcd as cluster-of-one
2. **Node failure**: Survivor fences peer, continues operating
3. **etcd failure**: OCF agent detects and restarts etcd
4. **Kubelet failure**: Pacemaker manages kubelet restart

## Key Version Requirements

- **OCP minimum version for TNF**: 4.20
- **BMC protocol**: Redfish required (only supported BMC protocol for TNF fencing)
- **Fencing credentials required**: BMC address, username, password for both nodes
- **Platform support**: `baremetal` or `none` only

---

## Debugging Commands

**On TNF cluster nodes**:
```bash
# Pacemaker status
sudo pcs status
sudo crm_mon -1              # One-time cluster status

# Fencing/STONITH
sudo stonith_admin -l        # List STONITH devices
sudo stonith_admin -H        # Show fence history

# Cluster configuration
sudo cibadmin -Q             # Query CIB configuration
sudo crm_resource -l         # List resources

# etcd container status
sudo crictl ps -a | grep etcd
sudo podman ps -a | grep etcd

# Logs
sudo journalctl -u pacemaker
sudo journalctl -u corosync
sudo cat /var/log/cluster/corosync.log
```

**Via oc (from a machine with kubeconfig)**:
```bash
oc get nodes
oc get pods -n openshift-etcd
oc get etcd -o yaml
oc describe clusteroperator/etcd
oc describe clusteroperator/machine-config
```
