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

## Repositories

All repositories are located in the `repos/` folder.

### enhancements (`repos/enhancements/`)
**Purpose**: OpenShift enhancement proposals repository

**TNF Relevance**: Contains the authoritative TNF enhancement document defining:
- Architecture and workflow for two-node clusters with fencing
- Component changes required (CEO, MCO, installer, BMO, etc.)
- Installation flow via Assisted Installer and Agent-Based Installer
- Failure handling scenarios and recovery procedures
- Integration between RHEL-HA stack and OpenShift

**Key files**:
- `enhancements/two-node-fencing/tnf.md` - Main enhancement document
- `enhancements/two-node-fencing/*.svg` - Architecture flowcharts for etcd scenarios

### assisted-service (`repos/assisted-service/`)
**Purpose**: REST/Kubernetes API service that installs OpenShift clusters with minimal infrastructure prerequisites

**TNF Relevance**: Core service orchestrating TNF cluster installation via MCE/ACM:
- Validates TNF cluster requirements (2 CP nodes, no arbiters, OCP >= 4.20)
- Collects and stores fencing credentials (BMC username/password/address) per host
- Generates install-config with fencing credentials for the installer
- Handles TNF-specific network connectivity groups (minimum 2 hosts instead of 3)

**Key TNF code paths**:
- `internal/common/common.go` - `IsClusterTopologyTwoNodesWithFencing()` detection logic
- `internal/cluster/validator.go` - TNF cluster validation
- `internal/cluster/transition.go` - State machine handling for TNF clusters
- `internal/installcfg/installcfg.go` - `Fencing` and `FencingCredential` structs
- `internal/installcfg/builder/builder.go` - Generates install-config with fencing data
- `internal/featuresupport/features_misc.go` - TNF feature support level checks
- `models/fencing_credentials_params.go` - BMC credential model
- `docs/enhancements/tnf-clusters.md` - Assisted-service TNF enhancement doc

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
**Purpose**: Manages etcd scaling during cluster bootstrap and operation, provisions TLS certificates

**TNF Relevance**: Contains the TNF controller code that:
- Initializes the Pacemaker cluster configuration
- Transitions etcd management from CEO to RHEL-HA
- Configures fencing using BMC credentials
- Handles the handover of etcd to the podman-etcd OCF agent

**Key paths**:
- `pkg/tnf/` - TNF-specific controllers and utilities
  - `pkg/tnf/operator/` - TNF operator starter
  - `pkg/tnf/pkg/pcs/` - Pacemaker cluster suite integration (fencing.go, etcd.go, cluster.go)
  - `pkg/tnf/setup/`, `pkg/tnf/fencing/`, `pkg/tnf/auth/` - Setup phases
- `docs/HACKING.md` - Development guide

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
**Purpose**: Manages operating system configuration and updates (systemd, cri-o/kubelet, kernel, NetworkManager, etc.)

**TNF Relevance**: Installs and configures Pacemaker/Corosync on RHCOS nodes:
- Directory structure for PCS and Corosync (`/var/lib/pcsd`, `/var/lib/corosync`, `/var/log/pcsd`, `/var/log/cluster`)
- Systemd units to enable and start PCSD service
- Fencing validator script for cluster health checking

**Key TNF paths**:
- `templates/master/00-master/two-node-with-fencing/` - TNF-specific templates
  - `units/ha-00-directories.service.yaml` - Creates directories for PCS/Corosync
  - `units/ha-01-enable-services.service.yaml` - Enables and starts PCSD
  - `files/fencing-validator.yaml` - Fencing validation script
  - `extensions/` - MCO extensions for HA packages

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
**Purpose**: OpenShift cluster installation tool supporting multiple platforms

**TNF Relevance**: Generates initial cluster configuration. The Agent-Based Installer (ABI) is one of the supported installation paths for TNF:
- Reads install-config.yaml with fencing credentials
- Generates ignition configs for the cluster
- Handles bootstrap process where one node serves as temporary bootstrap

**Key paths**:
- `pkg/asset/agent/` - Agent-Based Installer implementation
- `pkg/types/validation/installconfig.go` - Install config validation
- `pkg/types/machinepools.go` - Machine pool definitions

**Note**: TNF-specific logic is primarily in assisted-service; the installer consumes the generated configs.

**Commands**:
```bash
hack/build.sh                        # Build installer
bin/openshift-install create cluster # Create cluster
openshift-install destroy cluster    # Destroy cluster
```

### cluster-baremetal-operator (`repos/cluster-baremetal-operator/`)
**Purpose**: Deploys and manages baremetal server provisioning components (metal3.io)

**TNF Relevance**: Manages bare metal host provisioning. For TNF, BMO must avoid power-management conflicts with Pacemaker fencing on control-plane nodes (Pacemaker handles fencing, not BMO).

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

**Build**:
```bash
./autogen.sh
./configure
make
```

### openshift-docs (`repos/openshift-docs/`)
**Purpose**: Official OpenShift documentation in AsciiDoc format

**TNF Relevance**: Contains user-facing documentation for TNF installation and operation

**Key paths**:
- `installing/installing_two_node_cluster/` - Two-node cluster installation guides
- `installing/installing_two_node_cluster/installing_tnf/` - TNF-specific installation docs
- `modules/installation-two-node-*` - Modular content about TNF

**Note**: Documentation is in AsciiDoc (`.adoc`) format with includes/snippets pattern.

### dev-scripts (`repos/dev-scripts/`)
**Purpose**: Development and testing environment scripts for deploying OpenShift on libvirt VMs with virtualbmc

**TNF Relevance**: Primary tool for creating TNF development and testing clusters locally or in CI:
- Configures libvirt VMs with virtualbmc to simulate baremetal nodes
- Enables full TNF deployment including Redfish-based fencing

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
**Purpose**: Deployment automation framework for two-node OpenShift clusters in development and testing environments

**TNF Relevance**: Primary tool for TNF developers/QA to quickly deploy and manage TNF clusters:
- Automates AWS EC2 hypervisor provisioning via CloudFormation
- Supports "Bring Your Own Server" workflow for existing RHEL 9 hosts
- Wraps dev-scripts and kcli for simplified cluster deployment
- Provides cluster lifecycle management (deploy, clean, shutdown, startup)
- Automated Redfish stonith configuration for fencing topology
- Includes utilities for patching resource-agents on live clusters

**Deployment options**:
- **AWS Hypervisor**: Automated EC2 instance creation and cluster deployment
- **External Host**: Use existing RHEL 9 server with Ansible playbooks
- **dev-scripts method**: Traditional deployment (arbiter and fencing topologies)
- **kcli method**: Modern deployment with simplified VM management (fencing only)

**Key paths**:
- `deploy/` - Main deployment automation directory
  - `deploy/aws-hypervisor/` - AWS CloudFormation and instance lifecycle scripts
  - `deploy/openshift-clusters/` - Ansible playbooks for cluster deployment
  - `deploy/openshift-clusters/roles/` - Ansible roles (dev-scripts, kcli, redfish, proxy)
- `docs/fencing/` - TNF-specific documentation
- `helpers/` - Utility scripts

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
- `test/extended/two_node/utils/` - Test utilities

**Test execution**:
```bash
openshift-tests run openshift/two-node              # Run TNF test suite
openshift-tests run openshift/two-node --run "name" # Run specific test
```

### release (`repos/release/`)
**Purpose**: OpenShift CI/CD configuration repository for Prow jobs and test workflows

**TNF Relevance**: Central orchestration point for TNF CI testing:
- Prow job configurations for TNF tests
- Step registry workflows for TNF scenarios
- Cluster profiles for TNF testing environments

**Key TNF paths**:
- `ci-operator/config/` - CI operator configurations for TNF-related repos
- `ci-operator/step-registry/` - Reusable test steps and workflows
  - `baremetalds-two-node-fencing-workflow.yaml` - Main TNF workflow

---

## TNF Architecture Overview

```
                    +---------------------------------------------+
                    |         Assisted Installer / MCE            |
                    |  (orchestrates initial cluster setup)       |
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
                               |   (Redfish/IPMI)      |
                               +-----------------------+
```

## TNF Installation Flow (via Assisted Installer)

1. **User creates cluster via ACM/MCE** with 2 control-plane nodes
2. **assisted-service validates** the configuration:
   - Exactly 2 CP nodes, no arbiters, no workers initially
   - OCP version >= 4.20
   - Both hosts have fencing credentials (BMC address/username/password)
   - Platform is `baremetal` or `none`
3. **assisted-service generates install-config** with fencing credentials
4. **Bootstrap phase**: One node serves as bootstrap, etcd runs as 2-member cluster
5. **Bootstrap teardown**: Bootstrap node removed from etcd, reboots as control-plane
6. **MCO applies TNF MachineConfigs**:
   - Creates directories for PCS/Corosync
   - Enables and starts PCSD service
7. **CEO TNF controller initializes RHEL-HA**:
   - Initializes Pacemaker cluster
   - Configures fencing with BMC credentials
   - Transitions etcd management to podman-etcd OCF agent
8. **Pacemaker takes over**: Now manages etcd, cri-o, kubelet with fencing protection

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
- **Fencing credentials required**: BMC address, username, password for both nodes
- **Platform support**: `baremetal` or `none` only

---

## Debugging Commands

**On TNF cluster nodes**:
```bash
# Check Pacemaker status
sudo pcs status

# Check etcd pod/container status
sudo crictl ps -a | grep etcd
sudo podman ps -a | grep etcd

# Check Pacemaker logs
sudo journalctl -u pacemaker
sudo journalctl -u corosync

# Check etcd resource agent logs
sudo cat /var/log/cluster/corosync.log
sudo crm_mon -1
```

**Via oc (from a machine with kubeconfig)**:
```bash
oc get nodes
oc get pods -n openshift-etcd
oc get etcd -o yaml
oc describe clusteroperator/etcd
oc describe clusteroperator/machine-config
```
