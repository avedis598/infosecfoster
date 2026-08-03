# Playbook 7B — Weekly AI Governance Summary

**File:** `playbook_07b_aig_weekly.json`
**Sprint:** 7 (M7.4)
**Trigger type:** Scheduled — cron `0 8 * * 1` (Mondays 08:00 Kuwait time)
**Tier availability:** Tier C only (AI Governance module)
**Actions:** 3
**Target SLA:** Delivered before start of business Monday

---

## Purpose

Every Monday morning, aggregate all AI Governance violations from the previous seven days across the organization and send an executive summary showing which employees, departments, and AI tools generated the most policy events.

## Why this playbook exists

Individual violations from Playbook 7A are tactical — they concern specific incidents. Leadership needs strategic visibility: are violations trending up or down? Which departments have the biggest problem? Which AI tools are employees actually using?

Without a weekly roll-up, the IT manager sees dozens of individual case emails and loses the pattern entirely. With it, they see one email: *"47 violations this week, 22 from Sales, mostly targeting ChatGPT."*

That single view enables four things:

1. **Targeted training** — if Sales has the most violations, run a Sales-specific session rather than a company-wide one nobody attends
2. **Tool sanctioning** — if 80% of usage goes to ChatGPT, either license ChatGPT Enterprise officially or block it entirely; the middle ground is where leaks happen
3. **Trend detection** — violations trending up means the current training is not working
4. **Executive reporting** — the client can show their board real numbers proving AI risk is actively managed

## Trigger conditions

Scheduled cron at 08:00 Kuwait time every Monday.

The Monday timing is deliberate. It sets the security tone for the week. The IT manager reads it over morning coffee before other issues consume the day. If the summary shows problems, they can raise them in the Monday stand-up.

## Execution flow

### Step 1 — Query aggregated events
A single OpenSearch aggregation query over the last 7 days for the `AI_GOVERNANCE` rule group returns:

| Aggregation | Output |
|---|---|
| `total` | Count of all AI Governance events |
| `by_entity_type` | Top 20 rule IDs — which data categories |
| `by_user` | Top 10 users by violation count |
| `by_ai_tool` | Top 10 destinations targeted |
| `by_action` | Blocked / redacted / allowed-and-logged breakdown |

Aggregations are dramatically more efficient than fetching individual documents. Even at 500 violations per week the query returns in milliseconds because OpenSearch never materializes the underlying documents.

### Step 2 — Format executive summary
Python action converts raw aggregation buckets into readable text, mapping rule IDs to human labels:

```
AI GOVERNANCE WEEKLY SUMMARY
Reporting period: last 7 days
═══════════════════════════════════════

TOTAL EVENTS: 47

BY SENSITIVE DATA TYPE:
  - Personal Info (Name/Email/Phone): 18
  - Credit Card: 12
  - Kuwait Civil ID: 7
  - Source Code: 5
  - API Key or Secret: 3
  - Internal IP Range: 2

TOP USERS BY VIOLATIONS:
  - ahmed.sabah: 8
  - fatima.alrasheed: 5
  - mohammed.khaled: 4

AI TOOLS ACCESSED:
  - chatgpt.com: 28
  - claude.ai: 12
  - gemini.google.com: 5
  - copilot.microsoft.com: 2

POLICY ACTIONS TAKEN:
  - Blocked: 32
  - Redacted: 12
  - Allowed and logged: 3
═══════════════════════════════════════
```

**Plain text, no tables.** Executives read this on phones, and HTML tables render badly across mobile mail clients. Monospaced plain text is reliable everywhere.

### Step 3 — Send summary email
Recipients:

- `${CLIENT_IT_EMAIL}` — tactical view, informs day-to-day management
- `${CLIENT_COMPLIANCE_EMAIL}` — regulatory view, informs compliance reporting

Body includes the formatted summary, interpretation guidance on what different trends mean, Grafana links for drill-down and 12-month historical view, and suggested actions based on the numbers.

### Zero-violation weeks still send

If `total_events` is 0, the email still goes out with different content:

> "No AI Governance violations this week — your team is using AI tools responsibly. Continued monitoring is active."

**Why this matters:** silence is ambiguous. If the client receives no email, they may reasonably assume the service failed. A "zero violations" email is a positive signal and a heartbeat proving the pipeline works. Never skip the send.

## Environment variables used

| Variable | Purpose |
|---|---|
| `CLIENT_NAME` | Client identifier in subject |
| `CLIENT_IT_EMAIL` | Tactical recipient |
| `CLIENT_COMPLIANCE_EMAIL` | Compliance recipient |
| `OPENSEARCH_AUTH` | Aggregation query authentication |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email delivery |

## Testing procedure

**Prerequisite:** run five or more Playbook 7A tests first so there is data to aggregate.

**Manual trigger:** Shuffle UI → Workflow 7B → Run.

**Expected:**
- Aggregation query returns within a few seconds
- Summary email arrives at both recipients
- Counts match the number of test violations generated
- Entity type labels are human-readable, not raw rule IDs
- Grafana links resolve correctly

**Zero-data test:** run against a fresh client namespace with no violations. Confirm the "no violations this week" variant sends rather than an empty or malformed email.

Verify the underlying data directly:

```bash
curl -X POST "https://opensearch.CLIENT.svc:9200/wazuh-alerts-*/_search" \
  -H "Authorization: Basic $OPENSEARCH_AUTH" \
  -H "Content-Type: application/json" \
  -d '{
    "size": 0,
    "query": {"bool": {"must": [
      {"range": {"@timestamp": {"gte": "now-7d"}}},
      {"match": {"rule.groups": "AI_GOVERNANCE"}}
    ]}},
    "aggs": {"total": {"value_count": {"field": "rule.id.keyword"}}}
  }'
```

## Interpreting trends

The 12-month Grafana view linked in the email is where longer patterns become visible:

| Trend | Interpretation | Recommended action |
|---|---|---|
| Rising | Training is not landing, or a new AI tool emerged | Refresh training; check the AI domain blocklist for new destinations |
| Falling | Training is working, awareness is up | Reinforce with positive messaging |
| Steady | Baseline established | Unlikely to change without intervention; consider policy change |
| Sudden spike | New tool launched, or a project involving sensitive data | Investigate the specific department and time window |

Over time these summaries become the client's documentary evidence that AI Governance is a managed program rather than an ignored risk.

## Adapting for larger organizations

For clients with 500+ employees, the "top 10 users" list may show no meaningful concentration — usage spreads evenly. In that case extend the aggregation to report:

- **Top departments** instead of top individual users
- **Percentage of workforce** engaging with AI tools at all
- **First-time violators this week** — the onboarding cohort who need training

These are per-client customizations driven by size and reporting preference, not baseline behaviour.

## Integration with the monthly report

Playbook 7B produces weekly data. Sprint 4's `generate_report.py` (with `include_aigovernance: true`) aggregates four to five weekly periods into the AI Governance section of the monthly PDF.

The three views serve three audiences:

| View | Cadence | Audience |
|---|---|---|
| Grafana AI Governance dashboard | Real-time | IT manager, drill-down investigation |
| Playbook 7B weekly email | Weekly | IT manager + compliance officer |
| Monthly report AI section | Monthly | Executive, board, auditor |

Same underlying data, three levels of abstraction.

## Client-facing explanation

> "Every Monday, before you start your week, you will know how your team used AI tools last week. How many times they tried to send sensitive data. Which departments had the most incidents. Which AI tools are being used most. This is the visibility that lets you run training sessions before problems become policy violations. When your board asks how you are managing AI risk, you show them a year of these weekly summaries."

## Compliance relevance

- **PDPL Kuwait** — demonstrable ongoing monitoring of personal data handling
- **ISO 27001** 9.1 — Monitoring, measurement, analysis and evaluation
- **NCA ECC** 1-6 — Cybersecurity review and audit

---

*Internal — Engineering team only | amlakalarabia.com*
