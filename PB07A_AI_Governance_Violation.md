# Playbook 7A — AI Governance Violation

**File:** `playbook_07a_ai_governance.json`
**Sprint:** 7 (M7.4)
**Trigger type:** Webhook (Wazuh rules 100300–100309)
**Tier availability:** Tier C only (AI Governance module)
**Actions:** 5
**Target SLA:** End-to-end under 60 seconds

---

## Purpose

Detect the moment an employee attempts to send sensitive data — Kuwait Civil IDs, credit cards, API keys, or company source code — into a consumer AI tool, confirm the block, and create a documented policy violation case with the employee's identity and department context.

## Why this playbook exists

The rise of ChatGPT, Claude, Gemini, and Copilot created a data leakage vector that no existing security tool addresses. Employees paste customer records into ChatGPT to draft a personalized email. Finance staff paste statements for quick analysis. Developers paste proprietary code to debug.

The data leaves the corporate network the moment they hit send. For regulated data — Kuwait Civil IDs, health records, financial account numbers — this constitutes a data breach under PDPL Kuwait, GDPR, and NCA regulations.

Roughly 83% of organizations have no technical control over employee AI tool usage (IBM 2025). No major SIEM — Splunk, QRadar, Elastic — currently offers prompt-level content inspection. AML-Guard is the first SMB-accessible product that stops this data before it leaves.

## Trigger conditions

Wazuh webhook fires when the AI Security Gateway (AISG) reports a detection via syslog. Custom rules 100300–100309 match specific entity types.

| Rule ID | Entity detected | Wazuh level | Case severity |
|---|---|---|---|
| 100300 | Kuwait Civil ID (12-digit) | 14 | **Critical (4)** |
| 100301 | UAE Emirates ID (784-YYYY-XXXXXXX-X) | 14 | **Critical (4)** |
| 100302 | Saudi Iqama (10-digit) | 14 | **Critical (4)** |
| 100303 | GCC IBAN (KW/SA/AE/BH/QA/OM) | 10 | High (3) |
| 100304 | Credit card number | 10 | High (3) |
| 100305 | API key or secret | 10 | High (3) |
| 100306 | Internal IP range | 7 | High (3) |
| 100307 | Personal info (name/email/phone) | 7 | High (3) |
| 100308 | Source code pattern | 7 | High (3) |
| 100309 | Custom sensitive phrase | 10 | High (3) |

Rules **100300–100302** are the *critical entity* set — regulated national identity numbers under GCC law. These trigger the additional department head escalation in Step 5.

## Execution flow

### Step 1 — Parse AISG event
Extracts:

| Field | Purpose |
|---|---|
| Hostname | Where the request originated |
| AI destination | Which tool was targeted (ChatGPT, Claude, Gemini, Copilot) |
| Detected entity types | Categories found by Presidio |
| Policy action | What AISG did — blocked / redacted / allowed-and-logged |
| Prompt length | Context only, never content |

Also computes `is_critical` — whether the rule ID falls in the 100300–100302 range.

> ### ⚠️ Prompt content is NEVER logged
>
> This is the defining policy decision of the entire AI Governance module. The playbook knows *"a Kuwait Civil ID was detected in a prompt heading to ChatGPT"* — never which Civil ID, never the surrounding text.
>
> See the dedicated section below for why this matters.

### Step 2 — AD user lookup
Calls the internal microservice mapping hostname → currently-logged-in user → full AD profile:

- Full name and username
- Department
- Manager
- Department head email (needed for critical escalation)

Without this step the alert reads *"someone on WKS-042 tried to leak data"* — useless. With it: *"Ahmed Al-Sabah (Finance, reports to Mohammed Al-Rasheed) attempted to send a Kuwait Civil ID to ChatGPT"* — actionable.

### Step 3 — Create TheHive case
Severity 4 (Critical) for rules 100300–100302, otherwise 3 (High).

**TLP and PAP both set to 3 (Amber — restricted distribution).** AI Governance cases contain HR-sensitive information about employee behaviour and must not circulate as widely as a normal security case.

Description includes:
- Complete user context from AD
- AI tool targeted
- Entity type detected (never the entity value)
- Policy action taken by AISG
- Applicable compliance frameworks (PDPL Kuwait, GDPR)
- Recommended follow-up
- MITRE T1048 mapping
- Explicit note that prompt content was not stored

### Step 4 — Email IT manager (always)
Every violation notifies `${CLIENT_IT_EMAIL}` with:

- User identification
- Nature of the violation (entity type only)
- Action AML-Guard took
- Recommended follow-up: policy refresher, documentation
- **Bilingual Arabic courtesy line:**
  `شكراً لك على مساعدتك في الحفاظ على أمن بيانات الشركة`

The Arabic line is not decoration. In Kuwait, English-only enterprise notifications read as foreign product. The bilingual touch signals a locally-built product built for this market, and it consistently lands well in client feedback.

### Step 5 — Conditional email to department head
Only fires when `is_critical == True` (rules 100300–100302).

Content is executive-focused rather than technical:
- Employee name
- What was attempted
- What was prevented
- Recommendation to hold a policy conversation
- Reference to the TheHive case for the IT trail

**Reasoning:** Kuwait Civil ID, UAE Emirates ID, and Saudi Iqama are regulated PII under GCC law. Mishandling them carries legal consequence beyond IT policy — that is the department head's responsibility, not IT's alone.

## Environment variables used

| Variable | Purpose |
|---|---|
| `CLIENT_NAME` | Client identifier |
| `CLIENT_IT_EMAIL` | Always notified |
| `AD_LOOKUP_TOKEN` | User context resolution |
| `THEHIVE_API_KEY` | Case creation |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email delivery |

Department head email comes from the AD lookup response, not a static variable.

## The prompt content decision — why it matters

Storing prompt content would create a larger problem than the one being solved.

The prompts sent to AI tools **contain the sensitive data that AML-Guard exists to protect**. Logging those prompts means building a searchable database of employee-submitted Civil IDs, credit cards, and confidential business information — a substantial PDPL liability sitting inside your own platform.

What the playbook stores:

| Stored | Not stored |
|---|---|
| Fact that a violation occurred | The prompt text |
| Category of data (entity type) | The entity value itself |
| User identity | Surrounding conversation |
| Timestamp and destination | AI response |

If a client needs proof of what specifically was blocked, AISG retains temporary in-memory logs for 15 minutes only. Nothing is persisted.

Be prepared to explain this to clients who ask *"but can I see what they actually typed?"* The answer is no, deliberately, and that is a feature you should sell rather than apologize for.

## Escalation to HR

Neither this playbook nor any part of AML-SIEM automatically involves HR. That is a client policy decision. The playbook provides the audit trail; HR involvement is triggered by the client's internal escalation policy.

Typical patterns clients adopt:

| Occurrence | Typical response |
|---|---|
| First violation | Informal reminder from IT |
| Second within 30 days | Written policy refresher, signed by employee |
| Third | HR conversation with department head present |
| Sustained pattern | Formal disciplinary process |

None of this is automated. The playbook only supplies evidence.

## Testing procedure

Submit a test prompt through LiteLLM containing a fake Kuwait Civil ID:

```bash
curl -X POST "https://litellm.CLIENT.svc:4000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $LITELLM_KEY" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "Help me contact customer 285010112345 about their account"}
    ]
  }'
```

> **`285010112345` is a fabricated 12-digit number for testing — not a real Kuwait Civil ID.**

**Expected within 60 seconds:**
- AISG blocks the request — prompt never reaches the AI provider
- Presidio detected `KW_CIVIL_ID` with confidence above 0.85
- Wazuh rule 100300 fires
- Critical TheHive case created with correct entity type and username
- Email received at IT manager
- Email received at department head (because 100300 is a critical entity)
- **Verify: no prompt text appears anywhere in the case or logs**

That last check is the important one. Run it every time you modify this playbook.

## Tuning guidance

**False positive sources:**

| Source | Mitigation |
|---|---|
| Random 12-digit numbers matching Civil ID format | Presidio checksum validation (M7.2 requirement: <5% FP rate) |
| Test data in developer prompts | Exclude developer workstations, or use a separate policy zone |
| Public IP addresses misread as internal | Tighten the internal range definition in the recognizer |

Adjust Presidio confidence thresholds in the recognizer config rather than in this playbook — the playbook responds to what Presidio reports.

## Client-facing explanation

> "Every time one of your employees tries to send customer data, financial information, or company secrets to ChatGPT or similar AI tools, we intercept it before it leaves your network. The employee sees a message explaining the block. We document it. Your IT manager gets an email. For the most serious violations — attempting to send GCC national IDs — we also notify the department head. This gives you the audit trail for PDPL compliance and the visibility to run internal training when patterns emerge. We never store what they actually typed — only that a category of sensitive data was detected."

## MITRE ATT&CK mapping

- **T1048** — Exfiltration Over Alternative Protocol
- **T1048.002** — Exfiltration Over Asymmetric Encrypted Non-C2 Protocol
- **Tactic:** Exfiltration

## Compliance relevance

- **PDPL Kuwait** — personal data processing and cross-border transfer
- **GDPR** Art. 32 — security of processing (if EU data subjects involved)
- **NCA ECC** 2-6 — Data and information protection
- **ISO 27001** A.8.12 — Data leakage prevention

---

*Internal — Engineering team only | amlakalarabia.com*
