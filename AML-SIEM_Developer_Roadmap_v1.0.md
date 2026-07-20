# AML-SIEM Developer Roadmap — Version 1.0

**Platform:** AML-SIEM  
**Method:** 7-Sprint Engineering Build Plan — Agile Spiral Method  
**Prepared by:** Amlak Al-Arabia General Trading Co.  
**For:** Internal engineering team use only  
**Timeline:** August 2026 — August 2027  
**Classification:** Internal Confidential

---

## How to Use This Roadmap

This document is the engineering team's single source of truth for building the AML-SIEM platform. It is written for the engineers doing the work — not for clients or management. Every sprint section explains four things before giving any instructions: what already exists, what this sprint builds on top of that, what it produces that the next sprint depends on, and how to verify it is correct before moving on.

> **The fundamental rule:** No engineer starts a sprint until every gate in the previous sprint is documented as passed and signed off by the senior engineer. Gates exist because the technology enforces them — you cannot configure Shuffle if the Wazuh API is not running. Skipping gates does not save time. It creates failures you cannot diagnose.

---

## The Two-Track Deployment Model

Engineers build and iterate in Docker Compose on the lab server. Fast to start, fast to tear down, easy to debug. When a module is verified in Compose, the engineer writes the equivalent Kubernetes manifest. Client deployments always use Kubernetes (K3s). Never Docker Compose. This distinction is not optional.

| Track | Purpose and When to Use |
|---|---|
| **Docker Compose — lab only** | Rapid iteration during development. Start a service in seconds. Tear it down and rebuild when something breaks. Used exclusively on the Hetzner lab server. Never delivered to a client. |
| **Kubernetes (K3s) manifests — client delivery** | The production-grade deployment method. Every module in every sprint produces a K3s manifest. This is what the client deployment script applies. Repeatable, auditable, upgradeable. |
| **The promotion rule** | A module is not complete until both the Compose config AND the K3s manifest exist, both are tested, and both are committed to the Git repo under `/compose/` and `/k8s/` respectively. |

---

## Folder Structure — Mandatory from Day One

| Path | Contents |
|---|---|
| `/opt/aml-siem/compose/` | Docker Compose files per service — lab use only |
| `/opt/aml-siem/k8s/` | Kubernetes manifests per module — client delivery |
| `/opt/aml-siem/scripts/` | Automation scripts: deploy-client.sh, UAT suite, report generators |
| `/opt/aml-siem/clients/CLIENT_NAME/` | Per-client values.yaml and namespace config |
| `/opt/aml-siem/runbook/` | This document plus module-level step-by-step instructions |
| `/opt/aml-siem/pending-rules/` | AI-proposed suppression rules awaiting engineer approval |
| `/opt/aml-siem/ci/` | GitHub Actions workflows for CI/CD and weekly domain discovery |

---

## Sprint Overview — All 7 Sprints

| Sprint | Name | Duration | Builds On | What It Enables |
|---|---|---|---|---|
| **Sprint 0** | Environment Foundation | 2 weeks | Nothing — starting point | Everything. No other sprint is possible without this. |
| **Sprint 1** | Detection Core | 3 weeks | Sprint 0 | The entire product pipeline — every other sprint reads from or writes to this. |
| **Sprint 2** | Automation Layer | 3 weeks | Sprint 1 | Automated response, case management, 6 playbooks live. |
| **Sprint 3** | Intelligence Layer | 3 weeks | Sprint 1 + 2 | Threat intel, cold storage, Grafana, M365, Sigma rules. |
| **Sprint 4** | Reporting Layer | 2 weeks | Sprint 1 + 3 | Monthly PDF, compliance PDF, per-client config system. |
| **Sprint 5** | AI Layer | 2 weeks | Sprint 2 + 4 | Alert summaries, report narrative, false positive learning. |
| **Sprint 6** | Client Deployment Script | 2 weeks | All sprints | One command deploys a complete verified client environment. |
| **Sprint 7** | AML-Guard AI Governance | 8–10 weeks | Sprint 6 + paying clients | Employee AI tool monitoring, prompt inspection, Gulf PII detection. |

---

## Sprint 0 — Environment Foundation

> **What this sprint is:** No product is deployed here. This sprint builds the ground everything else runs on. Two weeks. Every future sprint assumes all Sprint 0 gates are passed and documented on the actual Hetzner production server. Juniors must not touch Sprint 1 until Sprint 0 sign-off is complete.

### M0.1 — Hetzner Server Provisioning

Ubuntu 22.04 LTS minimal install. Static IP assigned. SSH key-only access — password login disabled. UFW firewall enabled with only port 22 open initially. NTP sync confirmed. Hostname set to `aml-lab-01`. Timezone set to `Asia/Kuwait`.

**Connects:** Everything. Nothing runs without this server.

**✓ Gate:**
- `ssh aml-lab-01` returns shell prompt
- `ufw status` shows active with only port 22
- `timedatectl` shows NTP synced
- `date` shows Kuwait timezone

---

### M0.2 — Docker CE + Compose v2

Install Docker CE from Docker official repo — NOT Ubuntu snap version. The snap version has known networking issues that waste hours. Add engineer user to docker group. Install Compose plugin via apt. Set Docker daemon log rotation: max 10MB, max 3 files.

**Connects:** Every service in Sprints 1–7 runs inside Docker containers on this installation.

**✓ Gate:**
- `docker run hello-world` passes
- `docker compose version` returns 2.x
- Engineer runs docker without sudo
- `docker info` shows log driver with rotation configured

---

### M0.3 — K3s Kubernetes — Single Node

Install K3s lightweight Kubernetes. Configure kubeconfig for engineer access. Understand the two-track rule: Docker Compose is for lab iteration, K3s manifests are what goes to clients. Install kubectl and confirm it connects to the local cluster. Create namespaces: `aml-lab`, `aml-client-template`.

**Connects:** All Helm charts and K8s manifests in Sprints 1–7. Every client deployment uses K3s.

**✓ Gate:**
- `kubectl get nodes` shows node in Ready state
- `kubectl get namespaces` shows `aml-lab` and `aml-client-template`
- Engineer can apply and delete a test manifest independently

---

### M0.4 — Nginx Ingress + cert-manager + TLS

Deploy Nginx ingress controller in K3s. Install cert-manager for automatic Let's Encrypt certificates. Configure wildcard subdomain routing: `wazuh.CLIENT.amlsiem.com`, `shuffle.CLIENT.amlsiem.com`, `grafana.CLIENT.amlsiem.com`, `thehive.CLIENT.amlsiem.com`. All HTTP redirects to HTTPS.

**Connects:** Every web interface in the product needs TLS. Without this, nothing is client-presentable.

**✓ Gate:**
- `curl https://test.aml-lab.amlsiem.com` returns 200 or 404 with valid Let's Encrypt certificate
- `curl http://test.aml-lab.amlsiem.com` returns 301 redirect to HTTPS
- Certificate shows correct issuer

---

### M0.5 — Git Repo + Folder Structure

Create the `/opt/aml-siem/` folder structure as defined above. Initialise Git repo. Create `.gitignore` for secrets and credentials. Commit the empty structure with a README. Every engineer must understand where every file type lives before touching any sprint. This structure IS the product delivery mechanism.

**Connects:** Every sprint adds files to this structure. The client deployment script in Sprint 6 walks this tree.

**✓ Gate:**
- Senior engineer reviews and approves folder structure
- All engineers describe where each file type lives without looking
- Git repo has initial commit
- No credentials or secrets are in any committed file

---

## Sprint 1 — Detection Core

> **What this sprint is:** The entire product depends on this sprint. Wazuh receives logs. OpenSearch stores them. The dashboard shows them. Everything in Sprints 2–7 either sends data into this pipeline or reads data out of it. Think of Sprint 1 as the pipe — everything else is a valve or a tap. Three weeks. Do not rush this.

### M1.1 — OpenSearch 2.11 — 2-Node Cluster

Deploy as Kubernetes StatefulSet with persistent volume claims. Two data nodes plus one coordinator pod. Configure JVM heap at 50% of available RAM, maximum 32GB. Set index lifecycle policy to auto-delete `wazuh-alerts-*` indices older than 30 days. OpenSearch must be running and healthy before the Wazuh manager starts — it is the alerts destination.

**Connects:**
- Receives from: Wazuh manager (alerts JSON)
- Sends to: Wazuh dashboard (queries), Grafana (queries), all reporting scripts (queries)

**✓ Gate:**
- `GET /_cluster/health` returns green with all pods
- Kill one data pod — cluster goes yellow, not red
- Restart pod — returns green within 120 seconds
- `wazuh-alerts-*` index exists and accepts documents

---

### M1.2 — Wazuh Manager 4.7.x — 2-Node Cluster

Deploy master + worker as Kubernetes Deployments. Configure `ossec.conf` cluster block with node names and shared key. Both nodes must reach each other on port 1516. Wazuh API must respond on port 55000 — this is what Shuffle calls for active response. Configure email alerting via Exchange SMTP relay for level 10+ alerts. Version 4.7.x only — do not use 4.8.x until it stabilises.

**Connects:**
- Receives from: Wazuh agents (port 1514), syslog sources (port 514)
- Sends to: OpenSearch (alerts), Shuffle (webhook on high-severity alerts), Wazuh dashboard (API queries)

**✓ Gate:**
- `cluster_control -l` shows both nodes active
- `GET /api/v2/agents` returns valid JSON from the API
- Kill master node — worker continues accepting agent data within 60 seconds
- Test email arrives when a manual level 10 alert is triggered

---

### M1.3 — Wazuh Dashboard

Deploy as Kubernetes Deployment. Expose via Nginx ingress with TLS on port 443. Configure connection to OpenSearch on port 9200 and Wazuh API on port 55000. The dashboard is what you show clients in demonstrations and what their IT contact uses day to day. Ensure all modules are visible: agents, alerts, FIM, SCA, vulnerability, compliance.

**Connects:**
- Reads from: OpenSearch (alert data), Wazuh API (agent status and actions)
- Shown to: client IT contact and during sales demonstrations

**✓ Gate:**
- Login works on HTTPS with valid certificate
- Agent list shows all enrolled test agents as Active
- Alert explorer shows real-time events from test agents
- FIM module shows file change events
- Vulnerability module shows CVE scan results

---

### M1.4 — Wazuh Agent — Windows + Linux Enrollment

Test agent enrollment on: one Windows 10 endpoint, one Windows Server 2019, one Ubuntu 22.04 VM. Each must register, appear as Active in dashboard, and generate real alerts within 5 minutes. Document the enrollment command and agent group assignment process precisely — this is what engineers repeat for every client endpoint across every deployment.

**Connects:**
- Sends to: Wazuh manager on port 1514
- Enables: FIM, SCA, vulnerability detection, process monitoring on the enrolled device

**✓ Gate:**
- All three test agents show Active status
- Run `sudo useradd testuser` on Linux — alert fires in dashboard within 30 seconds
- Create new local admin on Windows — event 4720 alert fires within 60 seconds
- FIM alert fires when a file in a monitored path is modified

---

### M1.5 — Syslog Receiver — Firewall Log Ingestion

Enable Wazuh manager syslog listener on UDP and TCP port 514 in `ossec.conf` remote block. Configure and test with a real Fortinet or pfSense firewall pointed at the Wazuh manager IP. Confirm the correct decoder fires for the device type. This is required for any client with a network device — which is every client.

**Connects:**
- Receives from: firewalls, switches, routers via syslog protocol
- Feeds into: same Wazuh rules engine as agent data — no separate pipeline needed

**✓ Gate:**
- Generate a firewall event (blocked connection or failed admin login)
- Confirm alert appears in Wazuh dashboard within 60 seconds
- Rule ID matches the expected firewall decoder
- Device vendor and model identified correctly in alert metadata

---

## Sprint 2 — Automation Layer

> **What this sprint is:** Sprint 1 detects. Sprint 2 acts. Every alert at level 10+ now flows into Shuffle which decides what to do — check a hash, block an IP, create a case, send an email. TheHive is where the evidence lands. These two components together are what separates AML-SIEM from a raw Wazuh install and what justifies the price difference vs free Wazuh. Three weeks.

### M2.1 — Shuffle SOAR 1.3 — Deployment

Deploy as Kubernetes Deployment with persistent volume for workflow storage. Expose UI via Nginx ingress with TLS. Install Wazuh app from the Shuffle app marketplace. Configure Wazuh API connection with host, port 55000, and credentials stored in a Kubernetes Secret — never in plain text in any manifest.

**Connects:**
- Receives from: Wazuh manager webhook (alert JSON)
- Calls outbound: Wazuh API (active response), TheHive API (case creation), VirusTotal API (hash reputation), SMTP relay (email notifications)

**✓ Gate:**
- Shuffle UI loads on HTTPS
- Wazuh app installed and shows connected status
- Send a manual test webhook to Shuffle — execution log shows it received and processed the JSON payload within 5 seconds

---

### M2.2 — Wazuh to Shuffle Webhook Integration

Configure the `ossec.conf` integration block pointing at the Shuffle webhook URL. Set minimum alert level to 10. Test that a real Wazuh alert — not a manual webhook — arrives in Shuffle within 10 seconds. This is the wire between detection and automation. It must be proven solid before building any playbook on top of it.

**Connects:**
- From: Wazuh manager fires on every alert at level 10 or above
- To: Shuffle receives full alert JSON including rule ID, rule description, agent name, timestamp, and MITRE technique if mapped

**✓ Gate:**
- Trigger a real level 10+ alert from a test agent (five failed SSH logins)
- Shuffle execution log shows the exact alert JSON within 10 seconds
- Confirm all expected fields are present: `agent.name`, `rule.id`, `rule.description`, `rule.level`, `rule.mitre.technique`

---

### M2.3 — TheHive 5.2 — Deployment

Deploy as Kubernetes StatefulSet with bundled Elasticsearch on its own persistent volume. Expose via Nginx ingress with TLS. Create one Organisation called `AML-LAB` for testing. Create one analyst user account for lab use. Generate API key and store in Kubernetes Secret for Shuffle to use.

**Connects:**
- Receives from: Shuffle SOAR creates cases via TheHive REST API
- Read by: client IT contact via browser
- Exports to: compliance reports use case history as audit evidence

**✓ Gate:**
- TheHive UI loads on HTTPS
- Manual test case created successfully with title, description, and severity
- Shuffle calls TheHive API with test data — case appears in TheHive UI within 30 seconds with correct fields populated

---

### M2.4 — Playbook 1 — Brute Force Detection and Block

**Trigger:** Wazuh rule IDs 5710 to 5763 (multiple authentication failures)

**Actions in sequence:**
1. Extract source IP from alert JSON
2. Call Wazuh API active-response to block IP at host firewall
3. Send formatted email to client IT contact
4. Create TheHive case with IP, alert count, agent name, and timestamp as evidence

Every step must handle failure gracefully — a failed VirusTotal call must not prevent the TheHive case from being created.

**✓ Gate:**
- Run 5 failed SSH logins in 60 seconds on test agent
- Within 90 seconds: source IP is blocked, email received at test inbox, TheHive case exists with correct evidence
- Full end-to-end time under 90 seconds

---

### M2.5 — Playbook 2 — Malicious File Hash Detection

**Trigger:** Wazuh FIM alert on new executable with extension `.exe`, `.dll`, or `.ps1` in monitored paths

**Actions:**
1. Extract SHA256 file hash from FIM alert
2. Call VirusTotal API v3
3. If detection count exceeds 3 antivirus engines, escalate TheHive case to critical severity and include the full VirusTotal report link in case notes

> Uses free tier VirusTotal API key — rate limit: 4 requests per minute.

**✓ Gate:**
- Copy EICAR test file to a monitored path on the Windows test agent
- FIM alert fires → Shuffle extracts hash → VirusTotal returns detection count greater than zero
- TheHive case created with VirusTotal detection count and report URL in case notes
- Total time under 60 seconds

---

### M2.6 — Playbooks 3 to 6 — Remaining Automation Set

| Playbook | Trigger | Actions |
|---|---|---|
| **Playbook 3** | New admin account — Windows event 4720 or 4732 | Immediate email to IT manager and a high-priority TheHive case with username and domain |
| **Playbook 4** | SSL certificate expiry — Wazuh monitors certificate expiry | Formatted warning emails at 30, 14, and 7 days before expiry |
| **Playbook 5** | USB device insertion — Wazuh detects USB mount event | Logs device ID, hostname, and logged-in user; sends notification email |
| **Playbook 6** | Monthly report trigger — scheduled 06:00 on the 1st of each month | Calls `generate_report.py`, emails the resulting PDF to the client IT manager |

> Playbook 6 depends on Sprint 4 reporting scripts being deployed.

**✓ Gate:** Each of the four playbooks has a written test scenario executed and a PASS or FAIL result documented. All 6 playbooks total are signed off by the senior engineer before Sprint 3 begins.

---

## Sprint 3 — Intelligence Layer

> **What this sprint is:** Sprint 1 sees threats. Sprint 2 responds to them. Sprint 3 knows more about them before they arrive and stores the history long-term. This sprint adds three capabilities: knowing known-bad IPs and hashes before an alert fires, keeping 12 months of logs cheaply, and showing executives a dashboard they can understand. Three weeks.

### M3.1 — OSINT Threat Intelligence CDB Integration

Deploy `update_threat_intel.py` as a Kubernetes CronJob running daily at 02:00. Script pulls from 5 OSINT feeds: AbuseCH Feodo Tracker, ThreatFox, Emerging Threats, MalwareBazaar, URLhaus. Writes three CDB list files to a Kubernetes PersistentVolume shared with the Wazuh manager pod. Wazuh manager reloads CDB lists without restart.

**Custom rules in `local_rules.xml`:**
- Rule 100200 — malicious IP
- Rule 100201 — malicious hash
- Rule 100202 — malicious domain

**✓ Gate:**
- Run CronJob manually without waiting for 02:00
- CDB files written with correct Wazuh format (`value:` per line)
- Trigger an alert from a known bad IP in the Feodo list — rule 100200 fires correctly in the Wazuh dashboard

---

### M3.2 — ClickHouse 23.8 LTS — Cold Storage Tier

Deploy as Kubernetes StatefulSet with a large persistent volume. Use LTS version only — not non-LTS ClickHouse releases. Create `wazuh_cold` database and `events` table partitioned by date. Deploy a daily Kubernetes CronJob that queries OpenSearch for the previous day's alerts and inserts them into ClickHouse. This gives 12-month retention at a fraction of OpenSearch storage cost.

> Completely independent of the live alert pipeline — ClickHouse failure does not affect real-time detection.

**Connects:**
- Receives from: daily sync CronJob reading OpenSearch via REST API
- Sends to: Grafana (30+ day trend queries), compliance report scripts (historical event counts)

**✓ Gate:**
- Insert 10,000 test rows via `clickhouse-client`
- `SELECT count(*)` returns 10,000
- Grafana data source configured and test query returns results for a date range
- Daily sync CronJob runs and moves one day of data from OpenSearch to ClickHouse successfully

---

### M3.3 — Grafana OSS 10.3 — Executive Dashboard

Deploy as Kubernetes Deployment. Configure two data sources: OpenSearch plugin for 0–30 day data and ClickHouse plugin for 30–365 day data.

**Standard client dashboard template panels:**
- Alert count over time
- Top 10 rules bar chart
- Severity breakdown pie chart
- Agent status table
- Threat intel hit counter

Export dashboard JSON and commit to Git — this template is cloned per client.

> Grafana is the executive view. Wazuh dashboard is the analyst view. Do not confuse their purposes.

**✓ Gate:**
- Both data sources connected and show green status
- Dashboard loads with real data
- Year-over-year trend panel queries ClickHouse and shows historical data
- Dashboard JSON exported and committed to Git repo
- Senior engineer approves layout as client-presentable

---

### M3.4 — M365 and Azure AD Log Integration

Configure Wazuh Office 365 module in `ossec.conf`. Register Azure AD application with `AuditLog.Read.All` and `ActivityFeed.Read` permissions — minimum permissions only. Set polling interval to 5 minutes. Verify that Azure AD sign-in logs, Exchange audit logs, and Teams activity all flow into OpenSearch.

> **Tier B feature only** — deployed for Standard plan clients. Do not deploy to Tier A clients.

**✓ Gate:**
- Perform a test Azure AD sign-in with a test account — log appears in Wazuh dashboard within one 5-minute polling cycle
- Simulate a failed MFA attempt — a Wazuh alert fires for the authentication failure
- Azure AD admin activity event confirms correct decoder is applied

---

### M3.5 — Sigma Rules — Curated 50-Rule Set

Install `sigma-cli` on the lab server. Clone the SigmaHQ/sigma community repository. Select 50 rules from these categories:
- Windows process creation attacks (Mimikatz, PsExec, living-off-the-land binaries)
- Lateral movement techniques
- Scheduled task abuse
- Credential dumping

Convert to Wazuh XML format using `sigma convert`. Import to Wazuh manager rules directory and restart. Verify at least 5 rules trigger correctly on simulated attack scenarios.

**✓ Gate:**
- Wazuh manager restarts with zero rule parse errors in the log
- Five simulated attack scenarios (using Atomic Red Team or equivalent manual commands) each trigger the expected converted Sigma rule in the dashboard
- Rule IDs and MITRE technique mappings visible in alert metadata

---

## Sprint 4 — Reporting Layer

> **What this sprint is:** This is what the client sees at the end of every month. Not dashboards — a PDF in their inbox that a non-technical manager can read and show to their board or regulator. This sprint deploys the three Python scripts already built and wires them into the Kubernetes schedule and Shuffle playbook pipeline. Two weeks.

### M4.1 — Monthly SIEM Report — Kubernetes CronJob

Deploy `generate_report.py` as a Kubernetes CronJob scheduled for 06:00 on the 1st of each month. Mount environment variables from a Kubernetes Secret: OpenSearch credentials, client name, SMTP credentials. Output PDF written to a persistent volume. Shuffle Playbook 6 picks up the file path and emails it to the client IT manager.

> This is the most visible monthly deliverable — if this breaks, the client notices immediately.

**✓ Gate:**
- Run CronJob manually against real OpenSearch data
- PDF generated with correct client name, correct month label, real alert numbers matching OpenSearch query results
- Email arrives at test inbox with PDF attached
- File size under 1MB
- All 4 pages render without layout errors

---

### M4.2 — Compliance Report — Quarterly Schedule and On-Demand

Deploy `generate_compliance.py` as a Kubernetes CronJob scheduled quarterly on the 1st of January, April, July, and October. Also configured as a manual Shuffle trigger for on-demand generation. Maps 12 NCA ECC and ISO 27001 controls to live Wazuh OpenSearch data. Produces PASS, PARTIAL, or FAIL status per control with evidence counts. Includes a signature block for regulator submission.

> This document is what clients present to auditors.

**✓ Gate:**
- Run with real OpenSearch data — all 12 controls display PASS or PARTIAL with correct evidence counts
- PDF renders with signature block on the final page
- Senior engineer reviews compliance mapping against NCA ECC framework and approves accuracy

---

### M4.3 — Per-Client Configuration System — values.yaml

Design and implement the `/clients/CLIENT_NAME/values.yaml` structure. Each client file contains:

```yaml
client_name: ""
primary_it_contact_email: ""
escalation_email: ""
tier: "A"  # or B
supported_log_sources: []
wazuh_agent_group: ""
kubernetes_namespace: ""
include_m365: false
include_aigovernance: false
```

Adding a new client is: create one folder, create one YAML file, run one command.

**✓ Gate:**
- Create a values.yaml for a fictional test client
- Deploy using only that file and the deployment script
- Verify: reports show correct client name, alert emails go to correct address, correct Tier features are active, wrong-tier features are absent

---

## Sprint 5 — AI Layer

> **Critical engineering rule for this entire sprint: every AI call is asynchronous and non-blocking with a 10-second timeout. If the API call fails for any reason, the system continues normally. The AI layer enhances — it never blocks. Every engineer must understand and verify this before writing a single integration. Two weeks.**

### M5.1 — AI Integration Point 1 — Alert Triage Summarisation

Add one HTTP action to each of the 6 Shuffle playbooks, positioned after the TheHive case creation step. Call the Anthropic API (`model: claude-sonnet-4-6`) with the alert JSON fields: rule description, rule level, agent name, MITRE technique.

> **Do NOT send:** raw log content, usernames, file contents, or internal IP addresses.

Append the returned plain-English summary as a case note via TheHive API. Timeout: 10 seconds. On failure: log the error and continue.

**✓ Gate:**
- Trigger a real alert — TheHive case note contains a readable plain-English summary of the threat
- Disable the API key in the Kubernetes Secret — trigger another alert — TheHive case is still created and the playbook completes successfully
- AI note is absent but no failure is recorded
- Re-enable key — AI notes return on next alert

---

### M5.2 — AI Integration Point 2 — Monthly Report Executive Narrative

Update `generate_report.py` to call the Anthropic API before rendering the PDF. Pass the assembled monthly stats JSON as input. The returned paragraph is inserted into the Jinja2 template as the `executive_summary` variable on page 1.

**Fallback:** if the API call fails or times out, a static template paragraph is built from the stats data and inserted instead. The PDF is always generated on schedule regardless of API availability.

> Prompt text is stored in the runbook under version control — not hardcoded in the script.

**✓ Gate:**
- Run monthly report with real OpenSearch data — page 1 contains an AI-generated paragraph that specifically mentions the actual alert numbers from that month
- Simulate API failure by setting a wrong API key — PDF still generates on schedule with a readable fallback paragraph
- Output reviewed by senior engineer for quality before deploying to first client

---

### M5.3 — AI Integration Point 3 — False Positive Pattern Analysis

Build a monthly Python script that:
1. Queries TheHive API for cases resolved as false positive in the last 30 days
2. Sends the rule IDs, descriptions, and agent names to the Anthropic API requesting candidate Wazuh suppression rules in `local_rules.xml` XML format
3. Outputs draft XML snippets plus plain-English justification for each proposed rule to `/opt/aml-siem/pending-rules/`

> **AI proposes — engineer decides — engineer deploys manually.** No suppression rule is ever deployed automatically.

**✓ Gate:**
- Mark 5 test cases as false positive in TheHive
- Run the script — output file contains readable candidate suppression rules in correct Wazuh XML format with justifications
- Senior engineer reviews output for accuracy
- At least 3 of the 5 proposed rules are syntactically correct Wazuh XML that could be used directly

---

## Sprint 6 — Client Deployment Script

> **What this sprint is:** Everything built in Sprints 0 to 5 is now assembled into a single repeatable deployment script. An engineer runs one command with a client name and tier. The script reads the client values.yaml, applies all Kubernetes manifests in the correct dependency order, configures all integrations, runs the full UAT test suite automatically, and produces a signed deployment report. This script is the product. Every client deployment improves it. Two weeks.

### M6.1 — deploy-client.sh — Master Deployment Script

**Arguments:** client name, tier (A or B), environment (lab or production)

**Execution sequence:**
1. Validate that values.yaml exists and all required fields are populated
2. Create Kubernetes namespace from client name
3. Apply manifests in strict dependency order: OpenSearch → Wazuh manager → Dashboard → Shuffle → TheHive → CronJobs → Ingress rules
4. Wait for each pod to reach Running state before proceeding to the next
5. Configure all integrations using values.yaml values
6. Run the automated UAT suite
7. Output a timestamped deployment report

**✓ Gate:**
- Delete all resources for a test client
- Run `deploy-client.sh` from a completely blank K8s namespace
- Entire Tier A stack deployed, all pods running, UAT passing, deployment report produced — in under 4 hours with no manual steps required during execution

---

### M6.2 — Automated UAT Test Suite — 6 Scenarios

| # | Scenario | Checks |
|---|---|---|
| T01 | Brute force detection and IP block | Alert in Wazuh, execution in Shuffle, case in TheHive, email received |
| T02 | Malicious file hash detection and VirusTotal check | FIM alert, Shuffle hash lookup, TheHive case with VT report |
| T03 | New admin account alert and TheHive case | Event 4720, email to IT manager, high-priority case |
| T04 | SSL certificate expiry warning email | Email at 30/14/7 day thresholds |
| T05 | USB device detection notification | Device ID, hostname, username logged and emailed |
| T06 | Monthly report PDF generation | PDF generated and emailed with correct data |

Each test produces PASS or FAIL with a timestamped evidence log. Any FAIL halts the deployment and alerts the engineer by email. The signed deployment report cannot be generated until all 6 pass.

**✓ Gate:**
- All 6 UAT scenarios pass on a fresh deployment
- Deliberately break one component (set wrong webhook URL in Shuffle) — relevant scenario FAILS and deployment report is not generated
- Fix the component — re-run UAT — PASS — deployment report generated

---

### M6.3 — Runbook v1.0 — Engineer Reference Document

Every module from M0.1 through M6.2 documented with:
- Purpose of the module
- Exact commands run during build
- Expected output at each step
- How to verify it is correct
- How to troubleshoot the 3 most common failure modes
- What other modules depend on it

> The runbook is a living document. Updated after every client deployment with lessons learned — this is mandatory, not optional.

**✓ Gate:**
- A mid-level engineer who was not involved in any sprint reads the runbook and independently executes M1.1 through M1.4 on a blank server in under 5 hours
- Zero questions asked during execution
- Senior engineer observes and signs off

---

## Sprint 7 — AML-Guard AI Governance Module

> **Pre-condition — read before starting:** Sprint 7 begins ONLY after Sprint 6 is complete AND at least one paying client is live on the production AML-SIEM core stack. This module adds new infrastructure alongside the existing product — it does not replace anything. If the core product is not stable with a paying client, do not start Sprint 7.
>
> **Estimated duration:** 8–10 weeks  
> **Owner:** Mid-level Engineer 2, supervised by senior engineer

### What AML-Guard Does and Why It Matters

An employee opens ChatGPT and pastes in a customer contract with 50 Kuwait Civil ID numbers. That data leaves the corporate network, enters OpenAI's training pipeline, and may be surfaced to competitors. No one inside the company knows it happened. AML-Guard intercepts this before it reaches ChatGPT, detects the Civil IDs using Microsoft Presidio, blocks or redacts the content, and creates a TheHive case with the employee's identity, the AI tool used, and the exact entity types detected.

> **Market context:** 83% of organisations currently have no technical control over employee AI tool usage (IBM 2025). No major SIEM product — Splunk, QRadar, or Elastic — currently offers prompt-level content inspection. AML-Guard is the first SMB-accessible product to do this. The first-mover window in the Gulf market is approximately 12–18 months.

### The AML-Guard Stack — Three Open-Source Components

| Component | Role, Licence, and Why This One |
|---|---|
| **LiteLLM Proxy** (MIT) | AI traffic gateway. Sits in front of every AI provider (OpenAI, Anthropic, Google, Microsoft). Intercepts the full API request including prompt text. Exposes it to AISG for inspection before forwarding. 47,000+ GitHub stars. Weekly releases — new AI providers added automatically within hours of launch. |
| **Microsoft Presidio** (MIT) | PII and sensitive data detection engine. Runs as a Kubernetes microservice. Uses spaCy NLP, regex, and named entity recognition. Detects names, emails, phone numbers, credit cards, API keys, IP ranges, and custom patterns. You add Gulf-specific recognisers for Kuwait Civil ID, UAE Emirates ID, Saudi Iqama, GCC IBAN. Returns confidence-scored entity list in milliseconds per request. |
| **AI Security Gateway** (Apache 2.0) | Orchestration layer. Receives request from LiteLLM, calls Presidio, evaluates policy (block / redact / allow-and-log), forwards clean content or rejects. Blocks prompt injection attacks. Logs every decision with full context. Fails closed — if Presidio is unreachable, all requests are blocked, not passed through. |
| **Squid proxy + AD auth** (free) | Network-layer identity for browser traffic. Employees using a browser route through Squid. Squid authenticates via Kerberos against Active Directory — every connection is tagged with `domain\username`. Squid access log feeds Wazuh via syslog. |

---

### M7.1 — LiteLLM + Presidio + AISG Deployment

Deploy all three as Kubernetes pods in the client tenant namespace alongside the existing AML-SIEM stack.

**Start order:** Presidio must be Ready before AISG starts. AISG must be Ready before LiteLLM starts.

- **LiteLLM:** Kubernetes Deployment with persistent config volume
- **Presidio:** Kubernetes Deployment exposing REST API on port 5002 — internal only, not exposed via Nginx
- **AISG:** Kubernetes Deployment calling Presidio internally

No existing pods are modified.

**✓ Gate:**
- All three pods Running in the client namespace
- AISG calls Presidio with a test string containing a fake email address — Presidio returns `EMAIL_ADDRESS` entity
- LiteLLM sends a clean test prompt through the full chain and receives a valid AI response
- AISG blocks a test prompt containing a fake credit card number — prompt never reaches the AI provider

---

### M7.2 — Gulf-Specific Presidio Custom Recognisers

Build four custom Presidio recogniser classes in Python:

| Recogniser | Format |
|---|---|
| `KuwaitCivilIDRecogniser` | 12-digit format with checksum validation |
| `UAEEmiratesIDRecogniser` | 784-YYYY-XXXXXXX-X format |
| `SaudiIqamaRecogniser` | 10-digit starting with 1 or 2 |
| `GCCIBANRecogniser` | Prefixes KW, SA, AE, BH, QA, OM with length validation |

Store all four in `/opt/aml-siem/aiGuard/recognisers/`. Load into Presidio at startup via Kubernetes ConfigMap.

**Test criteria:** 100 genuine-format test strings and 100 random strings per recogniser — false positive rate must be under 5%.

**✓ Gate:**
- Kuwait Civil ID recogniser detects a correctly formatted 12-digit test ID with confidence above 0.85
- 100 random 12-digit numbers — fewer than 5 false positives
- Same test run for UAE Emirates ID, Saudi Iqama, and GCC IBAN
- All four recognisers load at Presidio startup with zero errors in logs

---

### M7.3 — Wazuh Custom Decoder and Rules for AML-Guard

Write a custom Wazuh decoder in `/var/ossec/etc/decoders/aml-guard.xml` to parse AISG syslog output format.

Write 10 custom rules in `/var/ossec/etc/rules/aml-guard-rules.xml`:

| Rule ID | Entity | Severity |
|---|---|---|
| 100300 | Kuwait Civil ID detected | Critical |
| 100301 | UAE Emirates ID | Critical |
| 100302 | Saudi Iqama | Critical |
| 100303 | GCC IBAN | High |
| 100304 | Credit card | High |
| 100305 | API key or secret | High |
| 100306 | Internal IP range | Medium |
| 100307 | Name, email, or phone | Medium |
| 100308 | Source code pattern | Medium |
| 100309 | Custom sensitive phrase | High |

All rules include MITRE ATT&CK technique **T1048** (Exfiltration Over Alternative Protocol).

**✓ Gate:**
- Paste a test AISG syslog line into `wazuh-logtest` — the correct rule fires based on entity type
- Alert appears in the Wazuh dashboard within 30 seconds
- Rule group shows `AI_GOVERNANCE`
- MITRE technique T1048 is mapped
- All 10 rules tested with corresponding syslog samples

---

### M7.4 — AML-Guard Shuffle Playbooks

**Playbook 7A — AI Governance Violation Alert**

Triggers on any Wazuh rule 100300–100309 match.

Actions:
1. Extract username from AD lookup using the machine name from the Wazuh alert
2. Create TheHive case with entity type, AI tool, username, department, device, timestamp, and action taken
3. Send email to IT manager in English with Arabic courtesy line
4. For rules 100300–100302 (critical entities): also email the department head

**Playbook 7B — Weekly AI Governance Summary**

Scheduled every Monday 08:00. Queries Wazuh alerts from the previous 7 days for rule group `AI_GOVERNANCE`. Sends a formatted summary email to IT manager showing top users, violation counts, and entity types.

**✓ Gate:**
- Trigger a real Kuwait Civil ID detection via a test prompt
- Within 60 seconds: TheHive case exists with correct entity type and username; email received at IT manager inbox with Arabic courtesy line; department head email received for critical entities
- Run Playbook 7B manually — weekly summary email delivered with correct violation counts

---

### M7.5 — Monthly Report — AI Governance Section

Update `generate_report.py` to add an AI Governance section when `include_aigovernance: true` is set in the client `values.yaml`.

**New section content:**
- Total AI tool requests this month
- Violation count by entity type (table)
- Top 5 users by AI tool usage
- Top 3 AI tools accessed
- Actions taken breakdown (blocked vs redacted vs allowed-and-logged)
- Trend compared to prior month

**✓ Gate:**
- Run `generate_report.py --include-aigovernance` for a client with real AML-Guard data
- PDF contains AI Governance section with real numbers
- Section renders correctly without breaking existing page layout
- Senior engineer approves content and layout

---

### M7.6 — CI/CD Pipeline — Dynamic AI Domain List and Recogniser Updates

**GitHub Actions Workflow 1 — Weekly Domain Discovery** (every Sunday at 23:00):
- Calls LLM API requesting all known public AI service domains
- Diffs output against current domain list in Git
- Opens a pull request with new domains for engineer review — never auto-merges
- After approval: AISG policy reloads without downtime

**GitHub Actions Workflow 2 — Presidio Update Test** (on every new Presidio release):
- Pulls new image, runs the Gulf recogniser test suite (100 strings per recogniser)
- Posts results as a PR comment
- Engineer approves upgrade only if test pass rate stays above 95%

**✓ Gate:**
- Weekly workflow runs and creates a PR with at least one new AI tool domain (or shows zero new domains with a clear log)
- Presidio update workflow runs against a new test image and posts test results as a PR comment
- Engineer approves and domain list or image update deploys to lab within 10 minutes of approval

---

### Sprint 7 UAT Test Scenarios

| # | Test Scenario | How to Trigger | Expected Result | Pass? |
|---|---|---|---|---|
| **T07** | Kuwait Civil ID — block | Submit a test prompt via LiteLLM containing a correctly formatted 12-digit Kuwait Civil ID | AISG blocks request. Presidio detected KW_CIVIL_ID with confidence above 0.85. Wazuh rule 100300 fires. Shuffle creates a critical TheHive case with entity type and username. IT manager email sent. Prompt never reached the AI provider. End to end under 5 seconds. | ☐ |
| **T08** | PII redaction mode | Submit a prompt with a real email address and phone number, client policy set to redact mode | AISG forwards redacted version with [REDACTED] replacing sensitive values. AI response returned to user. Wazuh logs the redaction event. TheHive informational case created. User workflow uninterrupted. | ☐ |
| **T09** | API key detection | Submit a prompt containing a string matching AWS AKIA key format | AISG blocks. Wazuh rule 100305 fires. TheHive case with entity type API_KEY. IT manager email sent. Prompt never reached AI provider. | ☐ |
| **T10** | Fail-safe — Presidio unreachable | Stop the Presidio Kubernetes pod. Submit any test prompt. | AISG blocks ALL requests while Presidio is down — fails closed. No prompt reaches any AI provider. Wazuh alert fires: AML-Guard inspection service unavailable. On-call engineer email triggered. | ☐ |
| **T11** | New AI domain blocked | Add a new test domain to the AISG blocklist via the CI/CD PR process. Submit a request to that domain. | Domain blocked at AISG. Wazuh logs the blocked attempt as an informational event. No TheHive case (informational only). CI/CD PR process documented and confirmed working. | ☐ |
| **T12** | Monthly report with AI Governance section | Run `generate_report.py` with `include_aigovernance` enabled after T07–T09 | PDF renders with AI Governance section showing 3 violations, correct entity types, username, and actions taken. No layout breaks on any existing page. PDF under 1.5MB. | ☐ |

---

## Appendix — Complete Port and Connection Reference

> Every port listed here must be open in the Kubernetes network policy for its respective service. No port should be open to the internet unless it is explicitly listed as externally accessible below.

| Service | Port | Protocol | Direction | Accessible From |
|---|---|---|---|---|
| OpenSearch data nodes | 9200 | TCP | Inbound | Wazuh manager, Grafana, report scripts — internal only |
| OpenSearch cluster transport | 9300 | TCP | Inbound | Between OpenSearch pods only |
| Wazuh agent comms | 1514 | UDP+TCP | Inbound | All agent endpoints (external) |
| Wazuh agent registration | 1515 | TCP | Inbound | All agent endpoints at enrollment (external) |
| Wazuh cluster comms | 1516 | TCP | Inbound | Between Wazuh manager pods only |
| Wazuh API | 55000 | TCP | Inbound | Shuffle, Wazuh dashboard — internal only |
| Wazuh syslog receiver | 514 | UDP+TCP | Inbound | Firewalls, switches, routers (external) |
| Wazuh dashboard | 443 | TCP | Inbound | via Nginx — external (client browser) |
| Shuffle SOAR UI | 443 | TCP | Inbound | via Nginx — external (engineer and admin only) |
| TheHive UI and API | 443 | TCP | Inbound | via Nginx — external (client IT contact) |
| Grafana | 443 | TCP | Inbound | via Nginx — external (client management) |
| ClickHouse HTTP | 8123 | TCP | Inbound | Grafana, sync CronJob — internal only |
| Nginx ingress | 80 + 443 | TCP | Inbound | Internet (80 redirects to 443) |
| LiteLLM proxy (Sprint 7) | 4000 | TCP | Inbound | Corporate endpoints via Squid — internal |
| Presidio API (Sprint 7) | 5002 | TCP | Inbound | AISG only — internal, not exposed |
| AISG (Sprint 7) | 8080 | TCP | Inbound | LiteLLM only — internal, not exposed |
| Squid proxy (Sprint 7) | 3128 | TCP | Inbound | Corporate browser endpoints — internal |
| Outbound — AI providers (Sprint 7) | 443 | TCP | Outbound | AISG to OpenAI, Anthropic, Google, Microsoft APIs |
| Outbound — VirusTotal | 443 | TCP | Outbound | Shuffle to api.virustotal.com |
| Outbound — OSINT feeds | 443 | TCP | Outbound | Threat intel CronJob to AbuseCH, Emerging Threats, etc. |
| Outbound — Anthropic API | 443 | TCP | Outbound | Shuffle and report scripts to api.anthropic.com |
| Outbound — Microsoft Graph | 443 | TCP | Outbound | Wazuh Office 365 module to graph.microsoft.com |

---

*Internal — Engineering team only | amlakalarabia.com*
