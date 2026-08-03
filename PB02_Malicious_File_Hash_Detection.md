# Playbook 2 — Malicious File Hash Detection

**File:** `playbook_02_malicious_hash.json`
**Sprint:** 2 (M2.5)
**Trigger type:** Webhook (Wazuh FIM)
**Tier availability:** A, B, C (all tiers)
**Actions:** 6
**Target SLA:** End-to-end under 60 seconds

---

## Purpose

Every time a new executable file appears on a monitored endpoint, check its cryptographic signature against a global malware database and — if confirmed malicious — create a case whose severity matches the actual threat level detected.

## Why this playbook exists

Ransomware, banking trojans, and info-stealers arrive as files. A user downloads what looks like an invoice PDF but is actually an `.exe`. A macro in an email attachment writes a payload to `%TEMP%`. A compromised software installer drops a DLL that appears to belong to the application.

Traditional antivirus catches known malware but misses variants and zero-days. VirusTotal aggregates 85+ antivirus engines plus behavioural analysis — if any one of them has ever seen this file anywhere in the world, VirusTotal knows. This playbook wires that intelligence directly into your file monitoring pipeline.

## Trigger conditions

Wazuh File Integrity Monitoring (FIM) generates an alert when a new file is added to a monitored path with an executable extension: `.exe`, `.dll`, `.ps1`, `.bat`, `.vbs`, `.js`, `.jar`, `.scr`, `.msi`.

**Typical monitored paths:**

| Platform | Paths |
|---|---|
| Windows | `C:\Users\*\Downloads`, `C:\Users\*\AppData\Local\Temp`, `C:\ProgramData\`, browser download folders |
| Linux | `/tmp`, `/var/tmp`, `/opt/`, user home directories |
| Web servers | Web root paths (webshell detection) |

FIM computes a SHA256 hash of every new file and includes it in the alert payload as `syscheck.sha256_after`.

## Execution flow

### Step 1 — Extract file hash
Reads `syscheck.sha256_after`. This cryptographic fingerprint is what VirusTotal will look up. A single byte change produces a completely different hash — this is what makes hash-based detection precise but also brittle against polymorphic malware.

### Step 2 — Validate hash format
Regex confirms a valid 64-character hex string. FIM sometimes fires on directory changes with no file and no hash — this step skips those cleanly instead of wasting a VirusTotal API call on an empty query.

### Step 3 — VirusTotal hash lookup
Sends the hash to VirusTotal's file report API. Returns:

- Count of engines detecting it as malicious
- Count detecting it as suspicious
- Specific detection names (e.g. `Trojan.GenericKD.12345`)
- File type, size, first-seen date
- Whether it is a known-good Microsoft-signed binary

### Step 4 — Evaluate threat level dynamically
Python action calculates severity from the VT result:

| VT malicious + suspicious | Severity | Label | Meaning |
|---|---|---|---|
| ≥10 detections | 4 | **CRITICAL** | Confirmed malware — isolate immediately |
| 3–9 detections | 3 | **HIGH** | Very likely malicious — quarantine and investigate |
| 1–2 detections | 2 | **MEDIUM** | Possibly malicious — may be a niche-engine false positive |
| 0 detections | 1 | **LOW** | Unknown file — logged for record, no action required |

This dynamic scaling is the core insight of the playbook. A file with 40 detections needs immediate response. A file with 1 detection might be a legitimate but obscure utility. Same playbook, different urgency, no human triage required.

### Step 5 — Create TheHive case with dynamic severity
Case title includes the severity label so the client sees "CRITICAL Malicious File" or "MEDIUM Malicious File" at a glance.

Description contains:
- File path and SHA256 hash
- Full VirusTotal detection breakdown
- Popular threat classification names
- Direct link to the VT report for deeper investigation
- Recommended response steps scaled to severity

### Step 6 — Email IT contact
Notification with the same severity-scaled content. Critical files get a 🦠 subject line that stands out; low-severity uses a calmer subject.

## Environment variables used

| Variable | Purpose |
|---|---|
| `CLIENT_NAME` | Client identifier |
| `CLIENT_IT_EMAIL` | Notification recipient |
| `THEHIVE_API_KEY` | Case creation |
| `VT_API_KEY` | VirusTotal file report |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email delivery |

## Testing procedure

On a Windows test agent, download the EICAR test file to a monitored path:

```powershell
Invoke-WebRequest -Uri "https://secure.eicar.org/eicar.com.txt" `
                  -OutFile "C:\Users\test\Downloads\eicar.exe"
```

**Expected within 60 seconds:**
- FIM alert fires
- Hash extracted and sent to VirusTotal
- VT returns high detection count
- Critical-severity TheHive case created with VT report URL
- Email received

> **Note:** EICAR is a harmless test string that every antivirus engine detects as malicious by convention. It is not real malware. Windows Defender may delete it before FIM sees it — temporarily exclude the test folder from Defender during testing.

**Cleanup:** delete the test file and close the resulting TheHive case as a test.

## Known limitations and caveats

**Windows Update noise.** Every Windows Update touches hundreds of legitimate files. Tune FIM monitored paths to exclude `C:\Windows\System32\` and `C:\Windows\WinSxS\` or you will generate massive noise.

**New installers show low detection.** Newly released software often has 0 VT detections simply because it is new. Do not treat "0 detections" as definitively safe — a genuine zero-day also shows 0. This is why 0-detection files are still logged at severity 1 rather than discarded.

**Encrypted archives are opaque.** If a `.zip` is password-protected, VirusTotal cannot scan its contents. The playbook only sees the archive hash, not the malware inside. Layer with endpoint EDR for defence in depth.

**Polymorphic malware evades hashing.** Malware that changes its own bytes on each infection produces a new hash every time, so VT has never seen it. Hash lookup is one layer, not the whole defence — the Sigma rules from Sprint 3 M3.5 catch behavioural indicators that hashing misses.

**Rate limits.** VirusTotal free tier is 4 requests per minute. On a busy endpoint doing a software install, FIM may generate dozens of hashes in seconds. Add a rate limiter or cache repeat hashes.

## Tuning guidance

To raise the critical threshold from 10 to 5 detections, edit the Python action in Step 4:

```python
if total_bad >= 5:      # was 10
    severity = 4
    severity_label = 'CRITICAL'
```

To restrict monitoring to fewer paths, edit the client's Wazuh `ossec.conf`:

```xml
<syscheck>
  <directories check_all="yes" realtime="yes">C:\Users\*\Downloads</directories>
  <directories check_all="yes" realtime="yes">C:\ProgramData</directories>
  <ignore type="sregex">^C:\\Windows\\WinSxS</ignore>
  <ignore type="sregex">\.log$|\.tmp$</ignore>
</syscheck>
```

## Client-facing explanation

> "When new files land on your endpoints, we compare them against a global database of every malware sample seen by 85 different antivirus engines. If the file has ever been reported as malicious anywhere in the world, we know within 30 seconds. The case we create tells your IT team exactly how serious it is — a file with 40 detections gets a 'stop everything' case; a file with 1 detection gets a 'look at this when you can' case. Your team does not have to guess which files matter."

## MITRE ATT&CK mapping

- **T1204** — User Execution
- **T1105** — Ingress Tool Transfer
- **T1027** — Obfuscated Files or Information
- **Tactic:** Execution, Defense Evasion

---

*Internal — Engineering team only | amlakalarabia.com*
