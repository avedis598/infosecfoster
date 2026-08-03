# Playbook 5 — USB Device Detection

**File:** `playbook_05_usb_device.json`
**Sprint:** 2 (M2.6)
**Trigger type:** Webhook (USB insertion events)
**Tier availability:** A, B, C (all tiers)
**Actions:** 4
**Target SLA:** Notification within 60 seconds

---

## Purpose

Record every USB storage device inserted into any monitored endpoint, check it against an approved-devices registry, and create a permanent compliance audit trail — **without** automatically blocking anything.

## Why this playbook exists

USB drives are the highest-risk data exfiltration channel because they are invisible to network monitoring. An employee can copy 500 GB of customer data to a thumb drive and walk out with it. No firewall sees it. No email filter catches it. No SIEM detects the copy operation unless you specifically instrument for it.

USB drives are also a common initial infection vector, particularly for air-gapped or semi-isolated networks. A malicious USB dropped in a car park and plugged in by a curious employee delivers ransomware in seconds.

**But the crucial design insight: most USB usage is legitimate.** The accountant copying invoices for the external auditor. The salesperson with a licence dongle for AutoCAD. The developer with an encrypted backup drive. Auto-blocking USB devices breaks businesses and gets the SIEM blamed for lost productivity.

This playbook takes the middle path: **complete visibility, human decision on enforcement.**

## Trigger conditions

Wazuh webhook fires on USB mass storage insertion:

| Platform | Event source |
|---|---|
| Windows | Event ID 6416 (Kernel-PnP), 20001 (device installation) |
| Linux | udev events, kernel messages about new block devices |
| macOS | `system.log` entries for USB mass storage |

## Execution flow

### Step 1 — Parse USB event
Extracts:

| Field | Purpose |
|---|---|
| Device ID | Unique hardware identifier |
| Device name | Human-readable description (e.g. "Kingston DataTraveler") |
| Serial number | The specific device's serial — critical for registry matching |
| User | Who was logged in at insertion time |
| Hostname | Which endpoint |

The **serial number** is the field that makes this playbook useful. Device names are generic; serials are unique. "A Kingston USB was inserted" is noise. "Serial KGT-8842991 was inserted, which is not in your approved registry" is intelligence.

### Step 2 — Check approved device registry
Calls an internal microservice holding a per-client approved USB registry:

- Device serial numbers
- Assigned employee
- Business justification
- Approval date and approving manager

Returns approved true/false. Devices not in the registry are flagged as unknown in the notification — but again, **nothing is blocked**.

### Step 3 — Log to compliance audit trail
Writes a structured record to the dedicated OpenSearch index `usb-audit-log`:

```json
{
  "@timestamp": "2026-07-31T14:22:11+03:00",
  "hostname": "FIN-WS-04",
  "user": "ahmed.sabah",
  "device_id": "USBSTOR\\DISK&VEN_KINGSTON...",
  "device_name": "Kingston DataTraveler 3.0",
  "device_serial": "KGT-8842991",
  "approved": false,
  "client": "chemdry"
}
```

This permanent, searchable record is what regulators ask for. When a PDPL Kuwait or NCA ECC auditor asks *"how do you track data leaving your organization via removable media?"*, you point them at this index.

### Step 4 — Send notification email
Formatted email with all device details plus contextual guidance:

- **If approved:** "No action needed — logged for compliance."
- **If not approved:** "Verify with the user. Consider a DLP scan of any files transferred."

The client's IT team decides whether to intervene. Seeing an unknown USB used by the CFO the week before they travel to a competitor's office is actionable intelligence. Seeing the accountant use their known backup drive is not.

## Environment variables used

| Variable | Purpose |
|---|---|
| `CLIENT_NAME` | Client identifier |
| `CLIENT_IT_EMAIL` | Notification recipient |
| `AD_LOOKUP_TOKEN` | Approved device registry lookup |
| `OPENSEARCH_AUTH` | Audit log write |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email delivery |

## Testing procedure

**Physical test:** insert a USB drive into a Windows test agent.

**Expected within 60 seconds:**
- Email received with device name, serial, user, hostname
- Record visible in `usb-audit-log` index

Verify the audit record:

```bash
curl -X GET "https://opensearch.CLIENT.svc:9200/usb-audit-log/_search?size=5&sort=@timestamp:desc" \
  -H "Authorization: Basic $OPENSEARCH_AUTH"
```

**No cleanup needed** — the audit record is intentionally permanent.

## The device registry as a business asset

Encourage clients to actively maintain the approved device list. It converts a passive log into an active control:

1. When issuing a company USB to an employee, register it before handing it over
2. When an employee leaves, mark their devices retired
3. Quarterly audit — review the list, remove orphaned entries

Over time the registry becomes evidence in insider threat investigations: *"this device was never approved for this user, and here is the exact timestamp it was first used."*

## Why blocking is deliberately not automated

This is a design decision worth defending to clients who ask for auto-block:

| Argument for auto-block | Why we do not |
|---|---|
| "Stop exfiltration instantly" | Also stops legitimate business work with no warning |
| "Zero-trust posture" | Creates helpdesk tickets and shadow IT workarounds |
| "Other SIEMs do it" | They also generate the complaints that get SIEMs uninstalled |

The correct escalation path is: log everything → notify → let the client define policy → implement enforcement via GPO or Wazuh Active Response **as a separate, explicitly-requested project**.

## Extensions for high-security clients

For clients handling regulated data (payment processing, healthcare, government), the playbook can be extended:

- **DLP scan on transfer** — Wazuh FIM on the USB mount point detects files copied, triggers a content scan
- **Zone-based blocking** — auto-block USB storage in specific security zones via GPO, allow elsewhere
- **Just-in-time approval** — a Shuffle approval workflow that grants temporary device access

These are Tier B/C features and priced accordingly. Tier A gets logging and notification only.

## Tuning guidance

**Expect noise from:**
- USB keyboards and mice registering as devices on some Windows builds — filter by device class `DiskDrive` only
- Docking stations re-enumerating devices on every reconnect
- Virtual machine USB passthrough on developer workstations

Filter at the Wazuh rule level to mass storage class only:

```xml
<rule id="100080" level="0">
  <if_sid>USB_BASE_RULE</if_sid>
  <field name="win.eventdata.deviceClass">HIDClass</field>
  <description>Ignore: HID devices (keyboard/mouse), not storage</description>
</rule>
```

## Client-facing explanation

> "Every USB drive inserted into your systems could be legitimate business use or someone taking your data. Blocking all USBs would stop your team working. Ignoring them means you never see data walking out the door. We give you complete visibility — every device, every user, every timestamp, logged permanently for compliance and sent to you in real time. You decide what is acceptable in your business."

## MITRE ATT&CK mapping

- **T1052** — Exfiltration Over Physical Medium
- **T1052.001** — Exfiltration over USB
- **T1091** — Replication Through Removable Media
- **T1200** — Hardware Additions
- **Tactic:** Exfiltration, Initial Access

## Compliance relevance

- **PDPL Kuwait** — data movement tracking obligations
- **NCA ECC** 2-6 — Data and information protection
- **ISO 27001** A.8.3 — Media handling
- **PCI DSS** 9.7 — Media inventory control

---

*Internal — Engineering team only | amlakalarabia.com*
