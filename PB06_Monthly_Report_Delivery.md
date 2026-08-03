# Playbook 6 — Monthly Report Delivery

**File:** `playbook_06_monthly_report.json`
**Sprint:** 2 (M2.6), depends on Sprint 4 (M4.1) report scripts
**Trigger type:** Scheduled — cron `0 6 1 * *` (06:00 on the 1st of each month)
**Tier availability:** A, B, C (all tiers)
**Actions:** 6
**Target SLA:** Report in inbox before start of business on day 1

---

## Purpose

On the first day of every month at 6 AM, automatically generate a comprehensive security report for the previous month, deliver it as a PDF attachment to the client's IT and executive contacts, and create a compliance record proving the report was delivered.

## Why this playbook exists

The monthly report is the single most visible deliverable in the AML-SIEM subscription. It is what the CFO sees when questioning the security spend. It is what the board reviews at quarterly meetings. It is what an auditor asks for as evidence of ongoing monitoring.

If the report does not arrive on time, or arrives incomplete, the client notices immediately. A report that fails silently is worse than no report at all — the client assumes something is monitoring when nothing is.

This playbook does three critical things:

1. **Guarantees delivery every month** — no human in the loop means no forgotten reports
2. **Creates provable delivery evidence** — the compliance log records exactly when each report was delivered and to whom
3. **Includes an AI-generated executive summary** — the client reads a human narrative, not a wall of numbers

## Trigger conditions

Scheduled cron at 06:00 Kuwait time on the 1st of every month.

The 06:00 timing is deliberate. The report lands before the workday starts, so it is the IT team's first email of the month. That first impression matters — the client opens their laptop and is immediately reminded of the value they are paying for.

## Execution flow

### Step 1 — Calculate reporting period
Python action computes the previous full month.

**Critical edge case:** on 1 January, the previous month is December **of the previous year**. Getting this wrong produces "December 2026" reports labelled 2027 — an error that undermines confidence in everything else in the document.

Output includes the human-readable label: "January 2027", not "01/27".

### Step 2 — Trigger report generator
Calls the internal `generate_report.py` Kubernetes service via HTTP POST:

```json
{
  "client": "chemdry",
  "period_start": "2027-01-01T00:00:00Z",
  "period_end": "2027-01-31T23:59:59Z",
  "report_label": "January 2027",
  "include_ai_summary": true
}
```

The generator is asynchronous — it queues the request and returns an ID immediately. Actual generation takes 30 seconds to 5 minutes depending on data volume.

### Step 3 — Poll for PDF completion
Loop checking status every 30 seconds, up to 10 minutes total. Three outcomes handled:

| Status | Action |
|---|---|
| `complete` | Capture PDF path and size, continue |
| `failed` | Log error, notify **Amlak** (not the client), stop |
| timeout | After 10 minutes, escalate to Amlak on-call |

**Why polling rather than waiting synchronously:** Shuffle actions have their own timeouts. A synchronous wait for a five-minute generation would simply fail. Short polling intervals keep the playbook responsive to failure and let it report a useful error.

### Step 4 — Download the PDF
HTTP GET on the download endpoint, saved into Shuffle's file storage for attachment.

### Step 5 — Email the report
Professionally worded email containing:

- Personalized greeting to the client team
- Summary of what the report covers
- Link to Grafana for real-time drill-down
- Contact address for questions
- Formal signature block

Sent to **both** `${CLIENT_IT_EMAIL}` and `${CLIENT_EXECUTIVE_EMAIL}`. The executive needs to see that delivery is happening; the IT team needs the document for detailed follow-up.

### Step 6 — Log delivery confirmation
Writes to the `report-delivery-log` OpenSearch index:

```json
{
  "@timestamp": "2027-02-01T06:14:22+03:00",
  "client": "chemdry",
  "report_type": "monthly",
  "report_period": "January 2027",
  "delivered_to": "it@chemdry.kw,ceo@chemdry.kw",
  "pdf_size_bytes": 425000,
  "delivery_status": "sent"
}
```

This is what proves to an auditor: *"yes, we delivered the January report on 1 February at 06:14 to these two addresses."* Twelve of these records is twelve months of demonstrable service delivery.

## Environment variables used

| Variable | Purpose |
|---|---|
| `CLIENT_NAME` | Client identifier |
| `CLIENT_IT_EMAIL` | Primary recipient |
| `CLIENT_EXECUTIVE_EMAIL` | Executive recipient |
| `REPORT_API_TOKEN` | Report generator authentication |
| `OPENSEARCH_AUTH` | Delivery log write |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email delivery |

## The AI executive summary

The `include_ai_summary: true` flag activates Sprint 5 M5.2 behaviour. The Claude API generates a plain-English narrative from the month's statistics.

Instead of "342 alerts, 47 threats blocked", page 1 opens with something like:

> "January 2027 was a moderate activity month for Chemdry Kuwait. Total alert volume increased 12% over December, driven primarily by three brute force campaigns targeting your public-facing SSH bastion — all blocked before achieving access. Notable events include a compromised laptop quarantined within 8 minutes of showing malware indicators. Compliance-relevant activity: 4 admin account changes (all verified as authorized), 12 new endpoints protected, and 100% agent uptime for the month."

This is what the CEO reads. This paragraph is what justifies the subscription renewal.

**Fallback behaviour:** if the Claude API call fails or times out (10-second limit), the report generator inserts a static template paragraph built from the same statistics. The PDF is always produced on schedule regardless of AI availability. This is the non-negotiable rule from Sprint 5 — the AI layer enhances, it never blocks.

## Testing procedure

**Manual trigger:** Shuffle UI → Workflow 6 → Run.

Prerequisites: the report generator service must be running.

```bash
kubectl get pods -n CLIENT | grep report-generator
```

**Expected:**
- Report generation starts, poll loop reports progress
- PDF downloaded within 10 minutes
- Email arrives at both recipients with PDF attached
- PDF under 1 MB, all pages render without layout errors
- Delivery record written to `report-delivery-log`

Verify the delivery log:

```bash
curl -X GET "https://opensearch.CLIENT.svc:9200/report-delivery-log/_search?size=5&sort=@timestamp:desc" \
  -H "Authorization: Basic $OPENSEARCH_AUTH"
```

## Failure scenarios and handling

| Scenario | Detection | Response |
|---|---|---|
| Report generator crashed | Status returns `failed` | Alert Amlak on-call, not the client. Fix and re-run manually. |
| Generation timeout (>10 min) | Poll loop exhausts | Escalate to Amlak on-call. Usually indicates an OpenSearch query problem. |
| Empty report (no data for period) | PDF generated but minimal | Still send — "no security events during this period" is itself meaningful information for the client. |
| SMTP relay down | Email action fails | Log as `failed`, notify Amlak. Contact the client by phone or Slack while email is restored. |
| Client email bounced | SMTP bounce webhook | Separate playbook alerts Amlak to update the contact record. |

**Design principle:** infrastructure failures notify Amlak; only successful deliveries reach the client. The client should never receive an error message from your platform about your platform.

## Tuning guidance

**Schedule adjustment.** Some clients prefer reports on the 3rd or 5th to allow for month-end reconciliation in their own systems. Change the cron:

```
0 6 3 * *    # 06:00 on the 3rd
```

**Additional recipients.** For clients with a compliance officer or external auditor on the distribution list, add to the recipients parameter. Keep the list short — a report emailed to 15 people gets read by none of them.

**Quarterly compliance report.** The related `generate_compliance.py` (Sprint 4 M4.2) runs on a separate quarterly schedule: `0 6 1 1,4,7,10 *`. Consider a sibling playbook rather than extending this one — different document, different audience, different cadence.

## Client-facing explanation

> "On the first of every month, before your team arrives, your monthly security report is in your inbox. Your CFO gets it. Your board can review it. When your auditor asks whether you receive regular reports on your security posture, you show them twelve months of reports and the delivery log proving they arrived. You never have to remember to ask us for a report — we send it, every month."

## Compliance relevance

- **NCA ECC** 1-6 — Cybersecurity review and audit
- **ISO 27001** 9.1 — Monitoring, measurement, analysis and evaluation
- **ISO 27001** 9.3 — Management review

The delivery log is the evidence artifact for all three.

---

*Internal — Engineering team only | amlakalarabia.com*
