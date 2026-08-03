# Playbook 4 — SSL Certificate Expiry Warnings

**File:** `playbook_04_ssl_expiry.json`
**Sprint:** 2 (M2.6)
**Trigger type:** Scheduled — cron `0 8 * * *` (daily 08:00 Kuwait time)
**Tier availability:** A, B, C (all tiers)
**Actions:** 3
**Target SLA:** Report delivered before start of business

---

## Purpose

Once a day, check every SSL/TLS certificate on every monitored system, categorize them by how soon they expire, and send one consolidated email — but only when action is actually needed.

## Why this playbook exists

Expired SSL certificates cause silent business damage. The website works fine, then suddenly customers see browser warnings and abandon their purchase. The mail server works fine, then Outlook shows "cannot verify server identity" and users cannot send. The API works fine, then partner integrations start failing at 3 AM.

The cost of an expired cert is measured in hours of downtime, panicked calls to IT, and for e-commerce, direct lost revenue. The cost of a renewal is a few minutes. This playbook makes sure the renewal always happens in time.

**Why Let's Encrypt and cert-manager do not fully solve this.** Automatic renewal works well when everything is configured correctly. But renewal fails silently in a dozen ways: DNS-01 challenge misconfiguration, ACME rate limits hit, domains missing from the config, expired ACME accounts, crashed cert-manager pods. This playbook catches those failures while there is still time to fix them manually.

## Trigger conditions

Scheduled cron at 08:00 Kuwait time daily. No webhook.

The playbook does not discover certificates itself — that is done by Wazuh's certificate monitoring (which requires a custom decoder for cert expiry events). This playbook consumes the alerts that monitoring generates.

## Execution flow

### Step 1 — Query OpenSearch for cert expiry alerts
Searches for all alerts in the last 24 hours in the `ssl_certificate_expiry` rule group. Returns up to 100 results, which covers even large clients with many certificates.

### Step 2 — Categorize by expiry window
Python action buckets each certificate:

| Bucket | Days remaining | Meaning |
|---|---|---|
| 🚨 Expired | < 0 | Immediate action — service may already be broken |
| 🔴 Critical | 0–7 | Renew this week without fail |
| 🟠 Warning | 8–14 | Renew this week or next |
| 🟡 Notice | 15–30 | Plan renewal in your normal maintenance window |

The categorization matters because it tells the reader what to do without requiring them to do date arithmetic. An expired cert needs someone at a keyboard now; a 30-day notice is a calendar item.

### Step 3 — Send consolidated email (conditional)
This is where the playbook differs from naive alerting. A conditional branch checks whether **any** certificates fall into **any** action-needed bucket:

- **Total = 0** → no email sent at all
- **Total > 0** → one email with all four categories

**Why one consolidated email rather than one per certificate:** a client with 50 servers might have 200 certificates. Sending 200 emails a day is worse than useless — they all end up filtered to a spam folder within a week, along with the one that actually mattered. One email per day, only when action is needed, stays scannable and stays trusted.

## Environment variables used

| Variable | Purpose |
|---|---|
| `CLIENT_NAME` | Client identifier in subject line |
| `CLIENT_IT_EMAIL` | Report recipient |
| `OPENSEARCH_AUTH` | Base64 credentials for the alert query |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email delivery |

## Testing procedure

**Manual trigger:** Shuffle UI → Workflow 4 → Run. If no certificates need attention, the run completes in seconds and sends nothing (correct behaviour).

**To force a test**, insert a synthetic cert expiry alert into OpenSearch:

```bash
curl -X POST "https://opensearch.CLIENT.svc:9200/wazuh-alerts-test/_doc" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic $OPENSEARCH_AUTH" \
  -d '{
    "@timestamp": "2026-07-31T08:00:00Z",
    "rule": {"groups": ["ssl_certificate_expiry"], "level": 10},
    "data": {"cert_name": "test.example.com", "days_until_expiry": 5},
    "agent": {"name": "test-agent"}
  }'
```

Re-run the playbook. Expected: email arrives showing `test.example.com` under the 🔴 Critical bucket.

**Cleanup:** delete the test index.

```bash
curl -X DELETE "https://opensearch.CLIENT.svc:9200/wazuh-alerts-test" \
  -H "Authorization: Basic $OPENSEARCH_AUTH"
```

## Special handling for Let's Encrypt certificates

If a Let's Encrypt-issued certificate appears in the report, the email explicitly states: *"This should have auto-renewed — check cert-manager logs before renewing manually."*

This distinction matters operationally. Let's Encrypt certificates in the AML-SIEM platform are **Amlak's responsibility** to auto-renew via cert-manager in K3s — not the client's manual task. If one appears in the client's report, something is broken on your side.

Recommended extension: add a second notification branch that alerts Amlak on-call (Slack or PagerDuty) whenever the certificate issuer contains "Let's Encrypt". The client sees the warning; your team sees the actual work item.

Check cert-manager health with:

```bash
kubectl get certificates -A
kubectl describe certificate CERT_NAME -n NAMESPACE
kubectl logs -n cert-manager deploy/cert-manager --tail=100
```

## Tuning guidance

**Common false positives:**

- Development and staging certificates that intentionally use short-lived self-signed certs
- Certificates from an internal Certificate Authority that does not follow public CA conventions
- Legacy systems using long-expired but internally-trusted certificates

Add per-certificate exceptions in the Wazuh rule rather than lowering the general threshold:

```xml
<rule id="100070" level="0">
  <if_sid>SSL_EXPIRY_BASE_RULE</if_sid>
  <field name="cert_name">dev.internal.local</field>
  <description>Ignore: dev environment self-signed cert</description>
</rule>
```

**Adjusting the schedule:** to run twice daily (morning and evening), change the cron to `0 8,17 * * *`. For clients with very large certificate estates, weekly may be sufficient — `0 8 * * 1` for Monday mornings only.

## Client-facing explanation

> "Every SSL certificate on your network has an expiration date. Miss one and your customers see warnings that make them distrust your site — or your systems simply stop working. We check every certificate every morning and send you a single summary of anything needing attention in the next 30 days. On days when everything is fine, we do not email you at all. When something needs action, you get one clear list."

## Compliance relevance

Certificate lifecycle management appears in:
- **ISO 27001** A.10.1 — Cryptographic controls
- **NCA ECC** 2-8 — Cryptography
- **PCI DSS** 4.1 — Strong cryptography for transmission

The daily report plus the delivery record constitutes evidence of an active certificate management process.

---

*Internal — Engineering team only | amlakalarabia.com*
