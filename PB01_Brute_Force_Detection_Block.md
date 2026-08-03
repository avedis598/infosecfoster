# Playbook 1 — Brute Force Detection & Block

**File:** `playbook_01_brute_force.json`
**Sprint:** 2 (M2.4)
**Trigger type:** Webhook
**Tier availability:** A, B, C (all tiers)
**Actions:** 9
**Target SLA:** End-to-end under 90 seconds

---

## Purpose

Detects password-guessing attacks in real time, blocks the attacker's IP address at the endpoint firewall, and creates a documented incident case — all within 90 seconds of the threshold being crossed.

## Why this playbook exists

Brute force attacks run 24/7 against any exposed SSH, RDP, or web login. A determined attacker tries thousands of passwords per minute. Without automation you have two options: respond fast enough manually (not realistic for an SME IT team), or eventually get breached.

This playbook removes human latency entirely. By the time the IT contact reads their morning email about an overnight attack, the source IP has already been blocked for eight hours.

## Trigger conditions

Wazuh sends a webhook when any `authentication_failures` rule fires at level 10 or above — typically 3–5 failed logins from the same source IP within a 2-minute window.

| Rule ID | Description |
|---|---|
| 5710 | sshd authentication failed |
| 5712 | sshd brute force trying to get access |
| 5716 | sshd insecure connection attempt |
| 5720 | Multiple SSHD authentication failures |
| 5551 | pam_unix authentication failures |
| 60122 | Windows failed logon (event 4625) |
| 18107 | Windows repeated failed logon attempts |

## Execution flow

### Step 1 — Parse Wazuh alert
Shuffle receives the JSON payload from the Wazuh webhook. Extracts the alert into named variables so later steps can reference rule description, agent name, and source IP.

### Step 2 — Extract source IP
Reads `data.srcip`. This becomes the input for every enrichment step. If the field is missing (rare edge case), the playbook logs the error and stops — you cannot block an IP you do not know.

### Step 3 — GeoIP lookup
Calls `ip-api.com` (free, no API key). Returns city, country, ISP, coordinates.

This context is what makes an alert humanly useful. "Failed login from 45.156.128.10" is anonymous. "Failed login from Moscow, Russia (ISP: DigitalOcean)" tells you it is automated attack traffic, not your CFO who forgot their password while travelling.

### Step 4 — VirusTotal reputation
Queries VirusTotal IP intelligence. Returns how many of roughly 85 security vendors flag this IP as malicious. A clean IP shows 0/85; a known botnet node might show 30/85.

### Step 5 — AbuseIPDB check
Queries AbuseIPDB for a crowdsourced confidence score (0–100) plus reported abuse categories (SSH bruteforce, web spam, phishing).

### Step 6 — Block IP via Wazuh Active Response
Calls the Wazuh manager API with `!firewall-drop`. The target agent adds an iptables (Linux) or Windows Firewall rule blocking the source IP.

The block happens **at the endpoint firewall**, not the network perimeter. This is deliberate — it works even when the client has no central firewall you can automate against, and it contains the attack without disrupting other systems.

### Step 7 — Compose email body
Builds a formatted plaintext email with attack summary, source location, VirusTotal detections, AbuseIPDB confidence, agent affected, and action taken.

### Step 8 — Send email
Delivers via SMTP relay to `${CLIENT_IT_EMAIL}`. Subject line uses 🚨 so it stands out in a crowded inbox.

### Step 9 — Create TheHive case
Creates a formal case with the full evidence chain: raw alert JSON, all enrichment results, action taken. Severity 3 (High). Tagged `brute-force`, client name, `automated`, and origin country.

This case is what the IT team reviews during investigation, and what appears in monthly reports as "threats blocked."

## Environment variables used

| Variable | Purpose |
|---|---|
| `CLIENT_NAME` | Client identifier in subject lines and tags |
| `CLIENT_IT_EMAIL` | Notification recipient |
| `WAZUH_API_KEY` | Active Response authentication |
| `THEHIVE_API_KEY` | Case creation |
| `VT_API_KEY` | VirusTotal reputation |
| `ABUSEIPDB_API_KEY` | AbuseIPDB reputation |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email delivery |

## Testing procedure

From an external test host (not on the client network):

```bash
for i in {1..10}; do
  ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no \
      wronguser@AGENT_IP
done
```

**Expected within 90 seconds:**
- Source IP blocked — verify with `sudo iptables -L INPUT -n | grep TEST_IP`
- Email received at the IT contact address
- TheHive case created with full enrichment evidence

**Cleanup:**
```bash
sudo iptables -D INPUT -s TEST_IP -j DROP
```

## Tuning guidance

**False positives to expect:**
- Password managers testing multiple accounts
- Users on VPN whose IP appears from unusual geographies
- Automated backup systems authenticating frequently
- CI/CD pipelines doing mass SSH operations

**Suppression example** for a known-good source:

```xml
<rule id="100051" level="0">
  <if_sid>5710</if_sid>
  <srcip>10.5.10.100</srcip>
  <description>Ignore: auth failures from monitoring server</description>
</rule>
```

**High-traffic clients:** If a client has hundreds of legitimate users authenticating worldwide, the geographic anomaly signal weakens. Weight VirusTotal and AbuseIPDB scores more heavily than geography in your triage.

**Adjusting the threshold** — to fire at 3 failures instead of 5:

```xml
<rule id="100050" level="10" overwrite="yes">
  <if_matched_sid>5710</if_matched_sid>
  <same_source_ip/>
  <frequency>3</frequency>
  <timeframe>120</timeframe>
  <description>Adjusted: 3 SSH failures in 120s</description>
</rule>
```

## Rate limit considerations

VirusTotal free tier allows 4 requests per minute. If more than 4 distinct brute force sources fire per minute, calls will return HTTP 429. Options:

1. Add a Shuffle rate limiter node before the VT call
2. Upgrade to VirusTotal paid tier
3. Cache VT results for repeat IPs (recommended — attackers reuse IPs)

The playbook continues to TheHive case creation even if VT returns 429, so the audit trail is never lost.

## Client-facing explanation

> "Password-guessing attacks run constantly against your internet-facing systems. Without automation we would need your team to check email every five minutes, decide if an alert is real, and manually block the source — which is not realistic. This playbook does that reasoning in 90 seconds using threat intelligence from VirusTotal and AbuseIPDB, before the attacker gets far enough to succeed. You will see the blocks in your monthly report."

## MITRE ATT&CK mapping

- **T1110** — Brute Force
- **T1110.001** — Password Guessing
- **T1110.003** — Password Spraying
- **Tactic:** Credential Access

---

*Internal — Engineering team only | amlakalarabia.com*
