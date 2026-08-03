# Playbook 3 — New Admin Account Alert

**File:** `playbook_03_new_admin.json`
**Sprint:** 2 (M2.6)
**Trigger type:** Webhook (Windows Security events)
**Tier availability:** A, B, C (all tiers)
**Actions:** 4
**Target SLA:** Notification within 60 seconds

---

## Purpose

Detects when a new user account is created on Windows systems or any user is added to a privileged administrative group, then alerts the client through two independent notification paths simultaneously.

## Why this playbook exists

Privileged account changes are the strongest single signal of a successful compromise. Attackers who breach a network need persistence — they either abuse existing admin credentials repeatedly (noisy, detectable) or create their own account (quieter, more durable). Creating a new admin account is the preferred move.

Every major ransomware attack, insider threat, and APT campaign of the past five years involved privilege escalation events like these. The pattern is consistent: gain initial access, then create your own admin account to maintain control independent of the credentials you stole.

Beyond attacks, unauthorized admin account creation is a compliance red flag. Auditors specifically probe this in ISO 27001 and NCA ECC reviews. Being able to answer "who created that account, when, and under what authorization" is the difference between a clean audit and a finding.

## Trigger conditions

Wazuh webhook fires on these Windows Security Event IDs:

| Event ID | Meaning |
|---|---|
| 4720 | A user account was created |
| 4732 | A member was added to a security-enabled **local** group |
| 4728 | A member was added to a security-enabled **global** group |
| 4756 | A member was added to a security-enabled **universal** group |

The playbook activates when the target group is privileged (Administrators, Domain Admins, Enterprise Admins, Schema Admins, Backup Operators) or when any new account is created.

## Execution flow

### Step 1 — Parse admin event
Extracts from the Windows event data:

| Field | Meaning |
|---|---|
| Target user | The account being created or added |
| Target domain | Where the account lives |
| Actor | The account that performed the change |
| Agent | The machine where the change happened |
| Group | Which privileged group is affected (4732 events) |

Also translates the raw event ID into plain English — "User Created" or "Added to Privileged Group" — so the notification is readable by non-security IT staff.

### Step 2 — Check actor authorization
Calls the internal Active Directory lookup microservice (`ad-lookup.internal`) to verify:

- Is the actor a real, current employee?
- Do they hold Delegated Administrator rights?
- Is this action within their normal responsibilities?

For clients without an AD lookup service deployed, this step logs "authorization check unavailable" and the playbook continues. The case is still created; the responder does the verification manually.

### Step 3 — Create high-priority TheHive case
Severity 3 (High) by default. You cannot automatically determine whether a change was authorized, but you must respond quickly if it was not.

Case description includes:
- The event that occurred
- Target account and group details
- Actor identity and their AD profile
- A verification checklist for the responder
- MITRE ATT&CK mapping (T1078 or T1098)
- Full raw alert as evidence

### Step 4 — Dual notification email
This is the distinctive design decision of this playbook. The email goes to **both**:

- `${CLIENT_IT_EMAIL}` — the primary IT contact
- `${CLIENT_ESCALATION_EMAIL}` — an independent escalation contact

**Reasoning:** in a real breach, the attacker may already control the primary IT contact's mailbox and could delete alerts before anyone sees them. Emailing an independent second recipient ensures the alert reaches uncompromised eyes. This is cheap insurance against the exact scenario the playbook is designed to catch.

The email includes a concrete rollback command the responder can run immediately:

```
net user TARGET_USER /active:no
```

This gives non-security IT staff a defensive action they can take without needing to understand the full context first.

## Environment variables used

| Variable | Purpose |
|---|---|
| `CLIENT_NAME` | Client identifier |
| `CLIENT_IT_EMAIL` | Primary notification |
| `CLIENT_ESCALATION_EMAIL` | Independent second notification |
| `AD_LOOKUP_TOKEN` | Actor authorization check |
| `THEHIVE_API_KEY` | Case creation |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email delivery |

## Testing procedure

On a Windows test agent, running as administrator:

```powershell
net user testuser Test123! /add
net localgroup Administrators testuser /add
```

**Expected:**
- Event 4720 fires → playbook executes → email + case
- Event 4732 fires → playbook executes → email + case
- Both emails arrive at IT contact **and** escalation contact
- Two TheHive cases created (or one, if you have rule chaining configured)

**Cleanup:**
```powershell
net localgroup Administrators testuser /delete
net user testuser /delete
```

Close the resulting TheHive cases as test artifacts.

## Response workflow for the client

When the IT team receives this email:

1. Check immediately whether a change ticket exists for this account
2. **If yes:** mark the TheHive case as authorized with the ticket reference, close it
3. **If no:** contact the actor directly to verify — a real employee confirms; an attacker does not respond
4. **If the actor cannot be reached within 15 minutes:** disable the new account and escalate to Amlak
5. Document the outcome in the TheHive case regardless — this is the audit trail

## Tuning guidance

**Common false positives:**

| Source | Pattern |
|---|---|
| Windows Update | Creates scheduled task accounts — event 4720 with no group addition |
| IT onboarding | Legitimate new admin staff |
| MSP activity | Your own or a third-party MSP making authorized changes |
| Software installers | Service account creation during install |

Suppress specific known-legitimate actors rather than disabling detection:

```xml
<rule id="100060" level="3">
  <if_sid>60106</if_sid>
  <field name="win.eventdata.subjectUserName">msp_admin</field>
  <description>Downgraded: authorized MSP admin account creation</description>
</rule>
```

**Never disable the base detection.** If this playbook is too noisy, tune the actor exclusions — do not raise the threshold or turn the rule off. This is the highest-signal detection in the entire platform.

## Client-facing explanation

> "When someone creates a new admin account on your systems, it either means you are being attacked or one of your team made a change without a ticket. Both need immediate verification. We alert both your IT lead and a backup contact simultaneously — because in a real breach, the attacker will try to hide alerts from whichever account they have already compromised. Sending to two people means the alert always reaches someone."

## MITRE ATT&CK mapping

- **T1136** — Create Account
- **T1136.001** — Local Account
- **T1136.002** — Domain Account
- **T1098** — Account Manipulation
- **T1078** — Valid Accounts
- **Tactic:** Persistence, Privilege Escalation

---

*Internal — Engineering team only | amlakalarabia.com*
