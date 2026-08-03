import json
import re

with open("aml_siem/steps/grafana_assets.py", "r") as f:
    content = f.read()

# Extract the JSON string from grafana_assets.py
match = re.search(r'UNIFIED_DASHBOARD_JSON = "(.*?)"\n', content)
if not match:
    match = re.search(r'UNIFIED_DASHBOARD_JSON = (.*?)\n', content)
    json_str = match.group(1)
    # decode the python string literal
    dashboard_json_str = eval(json_str)
    dashboard = json.loads(dashboard_json_str)
else:
    dashboard_json_str = match.group(1).encode('utf-8').decode('unicode_escape')
    dashboard = json.loads(dashboard_json_str)

# TheHive Row and Panels
thehive_panels = [
    {
      "type": "row",
      "title": "Incident Response - TheHive",
      "gridPos": {"h": 1, "w": 24, "x": 0, "y": 15}
    },
    {
      "type": "stat",
      "title": "Open Cases",
      "gridPos": {"h": 6, "w": 4, "x": 0, "y": 16},
      "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "TheHive"},
      "targets": [
        {
          "type": "json",
          "url": "/query?range=all",
          "global_query_id": "",
          "refId": "A",
          "format": "table",
          "source": "url",
          "url_options": {
            "method": "POST",
            "data": "{\n  \"query\": [\n    {\"_name\": \"listCase\"},\n    {\"_name\": \"filter\", \"_field\": \"status\", \"_value\": \"Open\"}\n  ]\n}"
          },
          "root_selector": "",
          "columns": []
        }
      ],
      "transformations": [
        {
          "id": "reduce",
          "options": {
            "reducers": ["count"]
          }
        }
      ]
    },
    {
      "type": "piechart",
      "title": "Open Cases by Severity",
      "gridPos": {"h": 6, "w": 6, "x": 4, "y": 16},
      "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "TheHive"},
      "targets": [
        {
          "type": "json",
          "url": "/query?range=all",
          "refId": "A",
          "format": "table",
          "source": "url",
          "url_options": {
            "method": "POST",
            "data": "{\n  \"query\": [\n    {\"_name\": \"listCase\"},\n    {\"_name\": \"filter\", \"_field\": \"status\", \"_value\": \"Open\"}\n  ]\n}"
          },
          "root_selector": "",
          "columns": [
            {"selector": "severity", "text": "severity", "type": "number"}
          ]
        }
      ],
      "transformations": [
        {
          "id": "groupingToMatrix",
          "options": {
            "columnField": "severity",
            "rowField": "severity",
            "valueField": "severity"
          }
        }
      ]
    },
    {
      "type": "table",
      "title": "Recent Cases",
      "gridPos": {"h": 6, "w": 14, "x": 10, "y": 16},
      "datasource": {"type": "yesoreyeram-infinity-datasource", "uid": "TheHive"},
      "targets": [
        {
          "type": "json",
          "url": "/query?range=all",
          "refId": "A",
          "format": "table",
          "source": "url",
          "url_options": {
            "method": "POST",
            "data": "{\n  \"query\": [\n    {\"_name\": \"listCase\"},\n    {\"_name\": \"sort\", \"_fields\": [{\"_createdAt\": \"desc\"}]},\n    {\"_name\": \"page\", \"from\": 0, \"to\": 20}\n  ]\n}"
          },
          "root_selector": "",
          "columns": [
            {"selector": "caseId", "text": "ID", "type": "number"},
            {"selector": "title", "text": "Title", "type": "string"},
            {"selector": "severity", "text": "Severity", "type": "number"},
            {"selector": "status", "text": "Status", "type": "string"},
            {"selector": "assignee", "text": "Assignee", "type": "string"},
            {"selector": "_createdAt", "text": "Created", "type": "timestamp"}
          ]
        }
      ]
    }
]

dashboard["panels"].extend(thehive_panels)

updated_json_str = json.dumps(json.dumps(dashboard))

content = re.sub(
    r'UNIFIED_DASHBOARD_JSON = .*?\n',
    f'UNIFIED_DASHBOARD_JSON = {updated_json_str}\n',
    content
)

with open("aml_siem/steps/grafana_assets.py", "w") as f:
    f.write(content)
