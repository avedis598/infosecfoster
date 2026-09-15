# SIEM Deployment Steps Summary

This document outlines all the automated steps orchestrated by the backend.

## M0_FOUNDATION
- **M0.1 — Verify Ubuntu 22.04 & Static IP**: Verify the base server is Ubuntu 22.04 LTS and has a static IP assigned
- **Step 2 — SSH Config & Key Setup**: Runs on your Mac — generate SSH key pair and write ~/.ssh/config
- **M0.1 — Step 3 — System Update**: Update package lists and upgrade all packages
- **M0.1 — Step 4 — Set Hostname**: Set hostname to aml-lab-01 and update /etc/hosts
- **M0.1 — Step 5 — Set Timezone**: Set timezone to Asia/Kuwait and confirm NTP sync
- **M0.1 — Step 6 — Disable Password SSH Login**: Enforce SSH key-only access and restart sshd
- **M0.1 — Step 7 — Configure UFW Firewall**: Install UFW, default deny incoming, allow only port 22
- **M0.1 — Step 8 — Enable Auto Security Updates**: Install and configure unattended-upgrades
- **M0.1 — Step 9 — Create amlsiem Admin User**: Create dedicated amlsiem user with sudo and SSH key access
- **M0.1 — Step 10 — Verify System Resources**: Check CPU, RAM, and disk meet Sprint 1 minimum requirements
- **Gate Verification — M0.1**: Run all gate checks and confirm PASS/FAIL for Sprint 0 sign-off
- **D01 — Remove Existing Docker Installations**: Remove any old or snap-based Docker before installing from official repo
- **D02 — Install Prerequisites**: Install packages required to add Docker's official apt repository
- **D03 — Add Docker GPG Key**: Add Docker's official GPG signing key so apt can verify packages
- **D04 — Add Docker apt Repository**: Point apt at Docker's official servers instead of Ubuntu mirrors
- **D05 — Install Docker CE + Compose Plugin**: Install Docker CE, CLI, containerd, buildx, and Compose v2 plugin
- **D06 — Start & Enable Docker Service**: Start Docker daemon and enable it to start automatically on boot
- **D07 — Add User to Docker Group**: Allow engineer to run docker without sudo
- **D07B — Reconnect SSH**: Disconnect and reconnect SSH so docker group membership takes effect
- **D08 — Configure Log Rotation**: Set Docker daemon log rotation: max 10MB per file, max 3 files
- **D09 — Run hello-world Test**: Pull and run Docker hello-world to confirm installation works end-to-end
- **Gate Verification — M0.2 Docker CE**: Run all M0.2 gate checks and confirm PASS/FAIL for sign-off
- **K01 — Pre-install Checks**: Verify resources and port availability before K3s install
- **K02 — Install K3s**: Download and install K3s via official install script
- **K03 — Configure kubeconfig**: Copy kubeconfig to home directory and set permissions
- **K04 — Verify kubectl**: Confirm kubectl is accessible and connects to the cluster
- **K05 — Check System Pods**: Verify all K3s internal pods are running
- **K06 — Create Namespaces**: Create aml-lab and aml-client-template namespaces
- **K07 — Set Default Namespace**: Set aml-lab as default so -n flag is not needed every command
- **K08 — Re-enable UFW with K3s Rules**: Open required K3s ports and re-enable firewall
- **K09 — Apply and Delete Test Manifest**: Engineer applies, verifies, then deletes a test ConfigMap
- **Gate Verification — M0.3 K3s**: Run all M0.3 gate checks — PASS/FAIL for sign-off
- **N01 — Disable K3s Built-in Traefik**: Remove Traefik so it does not conflict with Nginx on ports 80/443
- **N02 — Install Helm**: Install Helm package manager — required for Nginx and cert-manager
- **N03 — Install Nginx Ingress Controller**: Deploy Nginx ingress via Helm with production timeout and body size settings
- **N04 — Open Ports 80 and 443 in UFW**: Allow HTTP and HTTPS traffic through the OS firewall
- **N04B — Cloudflare DNS Records**: Create Cloudflare DNS A records for amlsiem.com subdomains (runs on Mac)
- **N04C — GCP VPC Firewall Rules**: Open ports 80 and 443 in GCP VPC firewall — shows exact fix if permission denied
- **N05 — Install cert-manager**: Deploy cert-manager for automatic Let Encrypt TLS certificates
- **N06 — Create Let Encrypt ClusterIssuer**: Configure cert-manager to use Let Encrypt production CA via HTTP-01 challenge
- **N07 — Deploy Test App and Ingress**: Deploy a test nginx pod and Ingress to verify routing works end-to-end
- **N08 — Verify Nginx Routing**: Confirm Nginx is responding on ports 80 and 443
- **N09 — Save Ingress Template to Repo**: Write the standard client Ingress template to /opt/aml-siem/k8s/templates
- **Gate Verification — M0.4 Nginx + TLS**: Run all M0.4 gate checks — PASS/FAIL for sign-off
- **G01 — Create Root Folder**: Create root folder /opt/aml-siem and set ownership to current user
- **G02 — Create Folder Tree**: Create the full directory structure for configurations, helm, scripts, and logs
- **G03 — Initialize Git Repository**: Initialize a local git repository in /opt/aml-siem and configure commit user details
- **G04 — Create gitignore File**: Create .gitignore in /opt/aml-siem to prevent committing credentials and sensitive info
- **G05 — Create README.md File**: Create baseline documentation README.md in the root directory
- **G06 — Create gitkeep Files**: Add .gitkeep to empty directories so git tracks the folder structure
- **G07 — Upload Sprint Documentation**: Upload markdown documents from local workspace to VM docs directory
- **G08 — Security Audit check**: Ensure no raw credentials or keys are found in plain text documentation
- **G09 — Test gitignore Functionality**: Verify that git correctly ignores files matching the blacklist
- **G10 — Perform First Commit**: Stage and commit folder structure as the baseline in git
- **Gate Verification — M0.5 Git & Folders**: Validate that all M0.5 folders exist, git is configured, gitignore is active, and first commit is done
## M1_DETECTION
- **M1.1 — OpenSearch 2.11 Cluster**: Deploy OpenSearch 2.11 2-node cluster with coordinator pod and 30-day index lifecycle retention policy
- **Gate Verification — M1.1 OpenSearch**: Validate cluster status green, node failover, recovery, and alerts index ingestion capabilities
- **M1.2 — Wazuh Manager 4.7.x Cluster**: Deploy Wazuh Manager 4.7.x Master + Worker nodes with Filebeat sidecars and Exchange email alerting
- **Gate Verification — M1.2 Wazuh Manager**: Validate cluster entries, query REST API, test master failover, and high-severity log alert email triggers
- **M1.3 — Wazuh Dashboard**: Deploy Wazuh Dashboard 4.7.x linked to OpenSearch and Wazuh Manager, exposed via Nginx Ingress with TLS
- **Gate Verification — M1.3 Wazuh Dashboard**: Validate ingress endpoint HTTP routing, certificate issue, and API connection status
- **M1.4 — Wazuh Agent — Windows + Linux Enrollment**: Expose agent enrollment/connection services via LoadBalancer and configure centralized telemetry profile (FIM/SCA/Logs) on the manager
- **Gate Verification — M1.4 Wazuh Agent Enrollment**: Verify that at least one test agent is active and real system events (e.g. user creation) generate alerts in the dashboard logs within 5 minutes
- **M1.5 — Syslog Receiver — Firewall Log Ingestion**: Configure host firewall, cloud security rules, and redeploy Wazuh manager with active syslog UDP/TCP receiver on port 514
- **Gate Verification — M1.5 Syslog Ingestion**: Simulate firewall syslog traffic over UDP and verify decoder trigger and alert mapping inside OpenSearch SIEM dashboard
## M2_AUTOMATION
- **M2.1 — Shuffle SOAR 1.3 — Deployment**: Deploy Shuffle SOAR (backend, frontend, orborus) and Mailpit mock mail catcher on Kubernetes with persistent volumes and HTTPS Ingress.
- **Gate Verification — M2.1 Shuffle SOAR**: Verify Shuffle UI loads over HTTPS and internal components are reachable.
- **M2.2 — Wazuh to Shuffle Webhook Integration**: Configure custom-webhook integration in Wazuh master ossec.conf and restart master service.
- **Gate Verification — M2.2 Alert Webhook Integration**: Trigger failed SSH login brute force and verify alert webhook is received in Shuffle logs.
- **M2.3 — TheHive 5.2 — Deployment**: Deploy TheHive 5.2 (StatefulSet) and its storage backends (Cassandra, Elasticsearch) on Kubernetes with persistent volumes.
- **Gate Verification — M2.3 TheHive 5.2**: Verify TheHive UI loads over HTTPS and internal APIs are accessible.
- **M2.4 — Playbook 1 — Brute Force Detection and Block**: Register SSH failed login playbook rules inside Shuffle and setup active response DROP commands.
- **Gate Verification — M2.4 SSH Brute Force Automation**: Simulate SSH brute force attack, verify IP drop block, email dispatch via SMTP, and case log in TheHive.
- **M2.5 — Playbook 2 — Malicious File Hash Detection**: Register FIM threat integration workflow inside Shuffle SOAR to verify VirusTotal v3 API scanning.
- **Gate Verification — M2.5 FIM Malicious Hash Automation**: Inject file addition events, trigger VirusTotal lookup simulation, and check for high-severity case in TheHive.
- **M2.6 — Playbooks 3 to 6 — Remaining Automation Set**: Import Playbooks 3-6 workflow templates for administrators auditing, certs validation, USB mounts logging, and compliance scheduling.
- **Gate Verification — M2.6 Playbooks 3-6 Automation Path**: Simulate administrator creation, certificate expiry, and USB mounts; verify notifications dispatched to external SMTP.
- **M2.7 — TheHive Org & Analyst Setup**: Create the AML-SOC organization, generate an Analyst user, and extract an API key for Shuffle integrations.
## M3_INTELLIGENCE
- **M3.1 — OSINT Threat Intelligence CDB Integration**- **Gate Verification — M3.1 OSINT**: Verify that Wazuh successfully loads the OSINT CDB list without errors
- **M3.2 — ClickHouse 23.8 LTS — Cold Storage Tier**- **Gate Verification — M3.2 ClickHouse**: Verify ClickHouse pod is running and responding to queries
- **M3.3 — Grafana OSS 10.3 — Executive Dashboard**- **Gate Verification — M3.3 Grafana**: Verify Grafana pod is running and responding
- **M3.4 — M365 and Azure AD Log Integration**- **Gate Verification — M3.4 Azure AD Integration**: Verify Office365 configuration is present in ossec.conf
- **M3.5 — Sigma Rules — Curated 50-Rule Set**- **Gate Verification — M3.5 Sigma Rules**: Verify Sigma rules XML file is loaded in Wazuh
## M4_REPORTING
- **M4.1 — Monthly SIEM Report — Kubernetes CronJob**- **Gate Verification — M4.1 Monthly Report**: Run CronJob manually and verify PDF generation
- **M4.2 — Compliance Report — Quarterly Schedule**- **Gate Verification — M4.2 Compliance Report**: Verify compliance report generates PASS/PARTIAL statuses
- **M4.3 — Per-Client Configuration System**- **Gate Verification — M4.3 Per-Client Config**: Verify values.yaml parser correctly extracts configuration
## M5_AI
- **M5.1 — AI Alert Triage Summarisation**- **Gate Verification — M5.1 Alert Triage**: Verify Shuffle API patch executed successfully
- **M5.2 — AI Executive Narrative for Reports**- **Gate Verification — M5.2 Executive Narrative**: Verify AI report fallback mechanism works securely
- **M5.3 — AI False Positive Pattern Analysis**- **Gate Verification — M5.3 False Positive Analysis**: Verify AI generated proper Wazuh XML snippets
