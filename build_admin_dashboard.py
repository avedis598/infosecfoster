import json
import uuid

def make_uid():
    return uuid.uuid4().hex[:8]

def base_dashboard():
    return {
        "title": "IT Admin Console",
        "uid": "admin-console",
        "schemaVersion": 38,
        "timezone": "browser",
        "refresh": "30s",
        "time": {"from": "now-24h", "to": "now"},
        "graphTooltip": 1,
        "templating": {
            "list": [
                {
                    "name": "agent",
                    "type": "query",
                    "datasource": {"uid": "OpenSearch"},
                    "query": "{\"find\": \"terms\", \"field\": \"agent.name\"}",
                    "multi": True,
                    "includeAll": True,
                    "allValue": "*",
                    "refresh": 2
                },
                {
                    "name": "severity",
                    "type": "custom",
                    "options": [
                        {"text": "Critical", "value": "Critical"},
                        {"text": "High", "value": "High"},
                        {"text": "Medium", "value": "Medium"},
                        {"text": "Low", "value": "Low"}
                    ],
                    "query": "Critical,High,Medium,Low",
                    "multi": True,
                    "includeAll": True
                },
                {
                    "name": "os",
                    "type": "query",
                    "datasource": {"uid": "OpenSearch"},
                    "query": "{\"find\": \"terms\", \"field\": \"agent.os.name\"}",
                    "multi": True,
                    "includeAll": True,
                    "refresh": 2
                },
                {
                    "name": "site",
                    "type": "custom",
                    "options": [
                        {"text": "Head Office", "value": "Head Office"},
                        {"text": "Branch", "value": "Branch"},
                        {"text": "Remote", "value": "Remote"}
                    ],
                    "query": "Head Office,Branch,Remote",
                    "multi": True,
                    "includeAll": True
                }
            ]
        },
        "links": [
            {
                "title": "Quick Jump",
                "type": "link",
                "url": "#",
                "icon": "bars",
                "tags": [],
                "targetBlank": False,
                "dropdown": True,
                "asDropdown": True,
                "options": [
                    {"title": "🚨 Needs My Attention Today", "url": "/d/admin-console#row-1"},
                    {"title": "🌍 Threat Landscape", "url": "/d/admin-console#row-2"},
                    {"title": "💻 Endpoint Fleet Health", "url": "/d/admin-console#row-3"},
                    {"title": "🔐 Authentication & Access", "url": "/d/admin-console#row-4"},
                    {"title": "📁 File Integrity & Data Movement", "url": "/d/admin-console#row-5"},
                    {"title": "🛡️ Vulnerabilities & Compliance", "url": "/d/admin-console#row-6"}
                ]
            }
        ],
        "panels": []
    }

def create_row(title, grid_pos, collapsed=True):
    return {
        "id": int(make_uid()[:6], 16) % 100000,
        "type": "row",
        "title": title,
        "gridPos": grid_pos,
        "collapsed": collapsed,
        "panels": []
    }

def main():
    dash = base_dashboard()
    panels = dash["panels"]

    # -------------------------------------------------------------------------
    # ROW 0 - STATUS BAR 
    # -------------------------------------------------------------------------
    panels.append({
        "type": "gauge",
        "title": "Security Posture Score",
        "gridPos": {"h": 5, "w": 4, "x": 0, "y": 0},
        "datasource": {"uid": "SIEM-Telemetry"},
        "targets": [{
            "refId": "A", "query": "", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "avg", "field": "posture_score"}],
            "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "auto"}}]
        }],
        "fieldConfig": {
            "defaults": {
                "min": 0, "max": 100,
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "orange", "value": 70},
                        {"color": "green", "value": 85}
                    ]
                }
            }
        }
    })

    panels.append({
        "type": "stat",
        "title": "Open Critical Cases",
        "gridPos": {"h": 5, "w": 4, "x": 4, "y": 0},
        "datasource": {"uid": "TheHive"},
        "targets": [{
            "type": "json",
            "url": "/query?range=all",
            "refId": "A",
            "format": "table",
            "source": "url",
            "url_options": {
                "method": "POST",
                "data": "{\"query\": [{\"_name\": \"listCase\"}, {\"_name\": \"filter\", \"_field\": \"status\", \"_value\": \"Open\"}, {\"_name\": \"filter\", \"_field\": \"severity\", \"_value\": 3}]}"
            }
        }],
        "transformations": [{"id": "reduce", "options": {"reducers": ["count"]}}],
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "background"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}, {"color": "red", "value": 1}]
                }
            }
        },
        "options": {"colorMode": "background"}
    })

    panels.append({
        "type": "stat",
        "title": "Agents Online",
        "gridPos": {"h": 5, "w": 4, "x": 8, "y": 0},
        "datasource": {"uid": "SIEM-Telemetry"},
        "targets": [
            {
                "refId": "A", "query": "", "timeField": "timestamp",
                "metrics": [{"id": "1", "type": "max", "field": "wazuh_active"}],
                "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "auto"}}]
            }
        ],
        "options": {"graphMode": "area", "colorMode": "value"},
        "fieldConfig": {
            "defaults": {
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "red", "value": None}, {"color": "green", "value": 1}]
                }
            }
        }
    })

    panels.append({
        "type": "stat",
        "title": "Events Processed",
        "gridPos": {"h": 5, "w": 4, "x": 12, "y": 0},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "auto"}}]
        }],
        "options": {"graphMode": "area", "colorMode": "none"}
    })

    panels.append({
        "type": "stat",
        "title": "Unpatched Critical CVEs",
        "gridPos": {"h": 5, "w": 4, "x": 16, "y": 0},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.groups:vulnerability-detector AND data.vulnerability.severity:Critical AND agent.name:$agent",
            "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": []
        }],
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "value"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}, {"color": "orange", "value": 1}, {"color": "red", "value": 5}]
                }
            }
        }
    })

    panels.append({
        "type": "stat",
        "title": "Critical Alerts (24h)",
        "gridPos": {"h": 5, "w": 4, "x": 20, "y": 0},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.level:>=12 AND agent.name:$agent",
            "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": []
        }],
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "background"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}, {"color": "red", "value": 1}]
                }
            }
        },
        "options": {"colorMode": "background"}
    })

    # -------------------------------------------------------------------------
    # ROW 1 - 🚨 Needs My Attention Today
    # -------------------------------------------------------------------------
    r1 = create_row("🚨 Needs My Attention Today", {"h": 1, "w": 24, "x": 0, "y": 5}, collapsed=False)
    
    r1["panels"].append({
        "type": "logs",
        "title": "Recent Critical Alerts (rule.level >= 10)",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 6},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.level:>=10 AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"type": "logs", "id": "1"}],
            "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "auto", "min_doc_count": 0}}]
        }],
        "options": {"showLabels": False, "showTime": True, "wrapLogMessage": True, "sortOrder": "Descending"}
    })

    r1["panels"].append({
        "type": "table",
        "title": "Open Cases (TheHive)",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 6},
        "datasource": {"uid": "TheHive"},
        "targets": [{
            "type": "json",
            "url": "/query?range=all",
            "refId": "A",
            "format": "table",
            "source": "url",
            "url_options": {
                "method": "POST",
                "data": "{\"query\": [{\"_name\": \"listCase\"}, {\"_name\": \"filter\", \"_field\": \"status\", \"_value\": \"Open\"}, {\"_name\": \"sort\", \"_fields\": [{\"_createdAt\": \"desc\"}]}, {\"_name\": \"page\", \"from\": 0, \"to\": 20}]}"
            },
            "columns": [
                {"selector": "caseId", "text": "ID", "type": "number"},
                {"selector": "title", "text": "Title", "type": "string"},
                {"selector": "severity", "text": "Severity", "type": "number"},
                {"selector": "assignee", "text": "Assignee", "type": "string"}
            ]
        }]
    })
    panels.append(r1)

    # -------------------------------------------------------------------------
    # ROW 2 - 🌍 Threat Landscape
    # -------------------------------------------------------------------------
    r2 = create_row("🌍 Threat Landscape", {"h": 1, "w": 24, "x": 0, "y": 14}, collapsed=True)
    
    r2["panels"].append({
        "type": "geomap",
        "title": "Attack Origin Geomap",
        "gridPos": {"h": 10, "w": 12, "x": 0, "y": 15},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "data.srcip:* AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [
                {"id": "2", "type": "terms", "field": "GeoLocation.location", "settings": {"min_doc_count": 1, "size": 100}}
            ]
        }],
        "options": {
            "view": {"id": "zero", "lat": 29.37, "lon": 47.97, "zoom": 2},
            "layers": [{"type": "markers", "name": "Layer 1", "config": {"showLegend": True}}]
        }
    })

    r2["panels"].append({
        "type": "timeseries",
        "title": "Alert Severity Over Time",
        "gridPos": {"h": 10, "w": 12, "x": 12, "y": 15},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [
                {"id": "3", "type": "terms", "field": "rule.level", "settings": {"min_doc_count": 1, "size": 10}},
                {"id": "2", "type": "date_histogram", "settings": {"interval": "auto"}}
            ]
        }],
        "options": {
            "legend": {"displayMode": "table", "placement": "bottom"},
            "tooltip": {"mode": "multi"}
        },
        "fieldConfig": {
            "defaults": {
                "custom": {"stacking": {"mode": "normal", "group": "A"}, "fillOpacity": 80}
            }
        }
    })

    r2["panels"].append({
        "type": "bargauge",
        "title": "Top Attack Techniques (MITRE)",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 25},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.mitre.technique:* AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [{"id": "2", "type": "terms", "field": "rule.mitre.technique", "settings": {"min_doc_count": 1, "size": 10}}]
        }],
        "options": {"displayMode": "lcd", "orientation": "horizontal"}
    })

    r2["panels"].append({
        "type": "heatmap",
        "title": "Attack Volume Heatmap",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 25},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "1h"}}]
        }],
        "options": {"calculate": True}
    })
    panels.append(r2)

    # -------------------------------------------------------------------------
    # ROW 3 - 💻 Endpoint Fleet Health
    # -------------------------------------------------------------------------
    r3 = create_row("💻 Endpoint Fleet Health", {"h": 1, "w": 24, "x": 0, "y": 33}, collapsed=True)
    
    r3["panels"].append({
        "type": "state-timeline",
        "title": "Agent Status Timeline (Connect/Disconnect)",
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 34},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "(rule.id:501 OR rule.id:504) AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "max", "field": "rule.id"}],
            "bucketAggs": [
                {"id": "3", "type": "terms", "field": "agent.name", "settings": {"min_doc_count": 1, "size": 20}},
                {"id": "2", "type": "date_histogram", "settings": {"interval": "auto", "min_doc_count": 0}}
            ]
        }],
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "red", "value": None},
                        {"color": "green", "value": 501},
                        {"color": "red", "value": 504}
                    ]
                }
            }
        }
    })

    r3["panels"].append({
        "type": "table",
        "title": "Agent Inventory",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 42},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [
                {"id": "2", "type": "terms", "field": "agent.name", "settings": {"min_doc_count": 1, "size": 100}},
                {"id": "3", "type": "terms", "field": "agent.os.name", "settings": {"min_doc_count": 1, "size": 1}},
                {"id": "4", "type": "terms", "field": "agent.version", "settings": {"min_doc_count": 1, "size": 1}},
                {"id": "5", "type": "terms", "field": "agent.ip", "settings": {"min_doc_count": 1, "size": 1}}
            ]
        }]
    })

    r3["panels"].append({
        "type": "piechart",
        "title": "OS Distribution",
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 42},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [{"id": "2", "type": "terms", "field": "agent.os.name", "settings": {"min_doc_count": 1, "size": 10}}]
        }],
        "options": {"pieType": "donut"}
    })

    r3["panels"].append({
        "type": "barchart",
        "title": "Agent Version Drift",
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 42},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [{"id": "2", "type": "terms", "field": "agent.version", "settings": {"min_doc_count": 1, "size": 10}}]
        }],
        "options": {"orientation": "horizontal"}
    })
    panels.append(r3)

    # -------------------------------------------------------------------------
    # ROW 4 - 🔐 Authentication & Access
    # -------------------------------------------------------------------------
    r4 = create_row("🔐 Authentication & Access", {"h": 1, "w": 24, "x": 0, "y": 50}, collapsed=True)
    
    r4["panels"].append({
        "type": "timeseries",
        "title": "Login Success vs Failure",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 51},
        "datasource": {"uid": "OpenSearch"},
        "targets": [
            {
                "refId": "Success", "query": "rule.groups:authentication_success AND agent.name:$agent", "timeField": "timestamp",
                "metrics": [{"id": "1", "type": "count"}],
                "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "auto"}}]
            },
            {
                "refId": "Failure", "query": "rule.groups:authentication_failed AND agent.name:$agent", "timeField": "timestamp",
                "metrics": [{"id": "1", "type": "count"}],
                "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "auto"}}]
            }
        ],
        "fieldConfig": {
            "defaults": {
                "custom": {"lineInterpolation": "smooth", "fillOpacity": 15}
            },
            "overrides": [
                {"matcher": {"id": "byName", "options": "Count"}, "properties": [{"id": "color", "value": {"fixedColor": "green", "mode": "fixed"}}]},
                {"matcher": {"id": "byName", "options": "Count"}, "properties": [{"id": "color", "value": {"fixedColor": "red", "mode": "fixed"}}]}
            ]
        }
    })

    r4["panels"].append({
        "type": "bargauge",
        "title": "Failed Logins by User",
        "gridPos": {"h": 8, "w": 6, "x": 12, "y": 51},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.groups:authentication_failed AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [{"id": "2", "type": "terms", "field": "data.srcuser", "settings": {"min_doc_count": 1, "size": 10}}]
        }],
        "options": {"orientation": "horizontal", "displayMode": "gradient"}
    })

    r4["panels"].append({
        "type": "logs",
        "title": "Privileged Actions Log (sudo/admin)",
        "gridPos": {"h": 8, "w": 6, "x": 18, "y": 51},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "(rule.groups:sudo OR rule.groups:syslog) AND rule.level:>=5 AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"type": "logs", "id": "1"}],
            "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "auto", "min_doc_count": 0}}]
        }],
        "options": {"showLabels": False, "showTime": True, "wrapLogMessage": True}
    })
    panels.append(r4)

    # -------------------------------------------------------------------------
    # ROW 5 - 📁 File Integrity & Data Movement
    # -------------------------------------------------------------------------
    r5 = create_row("📁 File Integrity & Data Movement", {"h": 1, "w": 24, "x": 0, "y": 59}, collapsed=True)
    
    r5["panels"].append({
        "type": "timeseries",
        "title": "FIM Events Over Time",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 60},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.groups:syscheck AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [
                {"id": "3", "type": "terms", "field": "syscheck.event", "settings": {"min_doc_count": 1, "size": 5}},
                {"id": "2", "type": "date_histogram", "settings": {"interval": "auto"}}
            ]
        }],
        "fieldConfig": {
            "defaults": {
                "custom": {"drawStyle": "bars", "fillOpacity": 80}
            }
        }
    })

    r5["panels"].append({
        "type": "table",
        "title": "Most-Changed Files",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 60},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.groups:syscheck AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [{"id": "2", "type": "terms", "field": "syscheck.path", "settings": {"min_doc_count": 1, "size": 10}}]
        }]
    })
    panels.append(r5)

    # -------------------------------------------------------------------------
    # ROW 6 - 🛡️ Vulnerabilities & Compliance
    # -------------------------------------------------------------------------
    r6 = create_row("🛡️ Vulnerabilities & Compliance", {"h": 1, "w": 24, "x": 0, "y": 68}, collapsed=True)
    
    r6["panels"].append({
        "type": "bargauge",
        "title": "CVE Severity Breakdown",
        "gridPos": {"h": 8, "w": 6, "x": 0, "y": 69},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.groups:vulnerability-detector AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [{"id": "2", "type": "terms", "field": "data.vulnerability.severity", "settings": {"min_doc_count": 1, "size": 5}}]
        }],
        "options": {"displayMode": "lcd"}
    })

    r6["panels"].append({
        "type": "histogram",
        "title": "Patch Aging (Days since CVE published)",
        "gridPos": {"h": 8, "w": 10, "x": 6, "y": 69},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.groups:vulnerability-detector AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "max", "field": "data.vulnerability.cvss.cvss3.base_score"}],
            "bucketAggs": [{"id": "2", "type": "date_histogram", "settings": {"interval": "auto"}}]
        }]
    })

    r6["panels"].append({
        "type": "table",
        "title": "Top Vulnerable Hosts",
        "gridPos": {"h": 8, "w": 8, "x": 16, "y": 69},
        "datasource": {"uid": "OpenSearch"},
        "targets": [{
            "refId": "A", "query": "rule.groups:vulnerability-detector AND agent.name:$agent", "timeField": "timestamp",
            "metrics": [{"id": "1", "type": "count"}],
            "bucketAggs": [
                {"id": "2", "type": "terms", "field": "agent.name", "settings": {"min_doc_count": 1, "size": 10}},
                {"id": "3", "type": "terms", "field": "data.vulnerability.severity", "settings": {"min_doc_count": 1, "size": 5}}
            ]
        }]
    })
    panels.append(r6)

    with open("admin_dashboard.json", "w") as f:
        json.dump(dash, f, indent=2)
    print("admin_dashboard.json created.")

if __name__ == "__main__":
    main()
