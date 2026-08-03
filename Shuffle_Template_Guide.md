# Shuffle Template Engineering Guide

This guide explains how to build, export, and deploy reusable Shuffle SOAR playbooks across multiple clients using the AML SIEM Dynamic Template Engine.

## 1. The Core Problem
When you export a workflow from Shuffle, the JSON contains hardcoded `app_id` strings (e.g. `1deed149-099b-48db-828b-9348f205f8d2` for Wazuh). These IDs are completely unique to the database of the Shuffle instance they were exported from. If you import that JSON into a different client's Shuffle instance, the workflows will break with a `TypeError` because the apps don't match.

## 2. How The Dynamic Template Engine Solves This
The SIEM application now includes a **Dynamic ID Mapper**.
When you deploy a template, the engine parses the raw JSON, queries the target client's cluster for their unique App IDs, and seamlessly swaps them in on the fly. 

**Zero manual JSON editing is required.**

## 3. How to Create and Export Templates
To build a playbook that will seamlessly import into any client's cluster:
1. Open your master/dev Shuffle instance.
2. Build your workflow visually using the standard apps (e.g., `Wazuh`, `TheHive`, `Email`).
3. Click the **Export** button in the top right corner of the Shuffle canvas to download the JSON.
4. Rename the downloaded file to something descriptive (e.g., `PB02_Malware_Eradication.json`).
5. Drop this file directly into the `playbooks/` folder in this repository.

## 4. How to Deploy a Template
1. Open the SIEM Application.
2. In the **Connection** tab, ensure you have entered the target client's **Shuffle API Key**.
   - *(You can get this by logging into the client's Shuffle UI -> Click Admin icon in bottom left -> Profile -> Copy API Key)*
3. Click **Connect**.
4. Go to the **Shuffle SOAR** tab.
5. You will see a dropdown menu populated automatically with all `.json` files from the `playbooks/` folder.
6. Select your template and click **Deploy Selected Playbook**.

## 5. Rules for Seamless Importing
- **App Names MUST Match:** The dynamic mapper links apps by the `"app_name"` field in the JSON. Ensure your apps are named exactly `Wazuh`, `TheHive`, and `Email` in Shuffle.
- **API Keys are Required:** The deployment will instantly fail with a `401 Unauthorized` if the API key in the Connection tab is missing or invalid.
