import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import queue

from ..core.config import load_config, save_config
from ..core.ssh_runner import SSHRunner
from ..core.orchestrator import Orchestrator

from .components import C, FONT_BOLD
from .tabs_connection import ConnectionTab
from .tabs_setup import SetupTab
from .tabs_dashboards import WazuhTab, TheHiveTab, ShuffleTab, GrafanaTab
from .tabs_reports import ReportsTab
from .tabs_clients import ClientDashboardTab
from .tabs_overview import OverviewTab
class AMLSiemApp(tk.Tk):
    def __init__(self, steps_def):
        super().__init__()
        self.steps_def = steps_def
        
        # Core engines
        self.ssh = None
        self.orchestrator = None
        
        # State
        self.config = load_config()
        
        self._build_window()
        self._build_tabs()
        
        # Queue draining for thread-safe UI updates
        self.after(40, self._drain_queue)

    def _build_window(self):
        self.title("AML-SIEM Build Orchestrator")
        self.geometry("1200x820")
        self.minsize(1000, 700)
        self.configure(bg=C["bg"])
        
        # Theme for Notebook
        style = ttk.Style()
        style.theme_use('default')
        style.configure("TNotebook", background=C["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=C["card"], foreground=C["muted"], padding=[20, 5], borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", C["accent"])], foreground=[("selected", C["bg"])])

    def _build_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(expand=True, fill="both")
        
        self.tab_clients = ClientDashboardTab(self.notebook, self._on_client_selected)
        self.notebook.add(self.tab_clients, text=" Clients ")
        
        self.tab_conn = ConnectionTab(
            self.notebook, 
            self._on_connect, 
            self._on_browse_key,
            self._on_save_config,
            self._on_load_config
        )
        # Connection tab is hidden initially until a client is selected
        
        self.tab_setup = SetupTab(self.notebook, self.steps_def, self._on_run_setup)
        # Setup tab is hidden initially
        
        self.tab_overview = OverviewTab(self.notebook, refresh_callback=self._fetch_overview)
        self.tab_wazuh = WazuhTab(self.notebook, refresh_callback=self._fetch_wazuh_agents)
        self.tab_thehive = TheHiveTab(self.notebook)
        self.tab_shuffle = ShuffleTab(self.notebook, install_callback=self._install_pb01)
        self.tab_grafana = GrafanaTab(self.notebook)
        self.tab_reports = ReportsTab(self.notebook, self.ssh)
        
        # Load saved config (will load active_client by default)
        from ..core.config import get_active_client_config
        self._populate_config(get_active_client_config())

    def _install_pb01(self):
        if not self.ssh or not self.ssh.is_connected():
            messagebox.showerror("Error", "Connect to the cluster first via the Connection tab.")
            return

        messagebox.showinfo("Installing PB01", "Starting PB01 playbook installation in the background. Please wait.")
        import threading
        def worker():
            script = """
import urllib.request, json, ssl, sys, uuid

def get_uuid(): return str(uuid.uuid4())
shuffle_url = "http://shuffle-backend.aml-lab.svc.cluster.local:5001"

try:
    req = urllib.request.Request(f"{shuffle_url}/api/v1/users/login", data=json.dumps({"username": "admin", "password": "Admin1234!"}).encode(), headers={"Content-Type": "application/json"})
    res = urllib.request.urlopen(req, timeout=10)
    data = json.loads(res.read())
    token = data.get("apikey", "")
    if not token:
        token = data.get("session_token", "")
    if not token:
        try:
            token = data.get("cookies", [{}])[0].get("value", "")
        except:
            token = ""
    if not token:
        print(f"Login succeeded but no token found. Response: {data}")
        sys.exit(1)
except Exception as e:
    print(f"Login failed: {e}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}", "Cookie": f"session_token={token}", "Content-Type": "application/json"}

try:
    req = urllib.request.Request(f"{shuffle_url}/api/v1/apps", headers=headers)
    res = urllib.request.urlopen(req, timeout=10)
    apps = json.loads(res.read())
except Exception as e:
    print(f"Failed to fetch apps: {e}")
    sys.exit(1)

wazuh_app = next((a for a in apps if a.get("name") == "Wazuh"), None)
thehive_app = next((a for a in apps if a.get("name") == "TheHive"), None)
email_app = next((a for a in apps if a.get("name") == "Email"), None)

trigger_id = get_uuid()
wazuh_id = get_uuid()
thehive_id = get_uuid()
email_id = get_uuid()

wazuh_block = {"id": wazuh_id, "name": "Wazuh Active Response", "app_name": "Wazuh", "position": {"x": 300, "y": 150}, "parameters": [{"name": "command", "value": "firewall-drop"}, {"name": "arguments", "value": "[\\\"$exec.text.data.srcip\\\"]"}, {"name": "agent_id", "value": "$exec.text.agent.id"}]}
if wazuh_app:
    wazuh_block["app_id"] = wazuh_app["id"]
    wazuh_block["app_version"] = wazuh_app["app_version"]

thehive_block = {"id": thehive_id, "name": "Create TheHive Case", "app_name": "TheHive", "position": {"x": 300, "y": 300}, "parameters": [{"name": "title", "value": "Brute Force Attack Detected: Blocked Source IP ($exec.text.data.srcip)"}, {"name": "description", "value": "Attacker IP: $exec.text.data.srcip\\nAgent Host: $exec.text.agent.name\\nRule ID: $exec.text.rule.id"}, {"name": "severity", "value": "3"}, {"name": "tags", "value": "[\\\"brute-force\\\", \\\"active-response\\\", \\\"sshd\\\"]"}]}
if thehive_app:
    thehive_block["app_id"] = thehive_app["id"]
    thehive_block["app_version"] = thehive_app["app_version"]

email_block = {"id": email_id, "name": "Send Alert Email", "app_name": "Email", "position": {"x": 300, "y": 450}, "parameters": [{"name": "recipient", "value": "admin@amlsiem.com"}, {"name": "subject", "value": "CRITICAL: Brute Force Blocked on $exec.text.agent.name"}, {"name": "body", "value": "Attacker IP: $exec.text.data.srcip\\nTarget Agent: $exec.text.agent.name\\n\\nPlease review TheHive for case details."}]}
if email_app:
    email_block["app_id"] = email_app["id"]
    email_block["app_version"] = email_app["app_version"]

workflow = {
  "name": "PB01 - Brute Force Detection and Block",
  "description": "Playbook 1: Automatically blocks SSH brute force attackers.",
  "id": get_uuid(),
  "actions": [wazuh_block, thehive_block, email_block],
  "triggers": [{"id": trigger_id, "name": "Wazuh Webhook", "app_name": "Webhook", "type": "webhook", "position": {"x": 50, "y": 300}, "parameters": []}],
  "branches": [
    {"id": get_uuid(), "source_id": trigger_id, "destination_id": wazuh_id, "conditions": [{"condition": "matches regex", "source": "$exec.text.rule.id", "destination": "^(5710|5711|5712|5715|5716|5720|5758|5760|5763)$"}]},
    {"id": get_uuid(), "source_id": trigger_id, "destination_id": thehive_id, "conditions": [{"condition": "matches regex", "source": "$exec.text.rule.id", "destination": "^(5710|5711|5712|5715|5716|5720|5758|5760|5763)$"}]},
    {"id": get_uuid(), "source_id": trigger_id, "destination_id": email_id, "conditions": [{"condition": "matches regex", "source": "$exec.text.rule.id", "destination": "^(5710|5711|5712|5715|5716|5720|5758|5760|5763)$"}]}
  ]
}

try:
    req = urllib.request.Request(f"{shuffle_url}/api/v1/workflows", data=json.dumps(workflow).encode(), headers=headers, method="POST")
    res = urllib.request.urlopen(req, timeout=10)
    print("SUCCESS")
except urllib.error.HTTPError as e:
    print(f"Failed to create workflow: {e.read().decode()}")
"""
            import base64
            script_b64 = base64.b64encode(script.encode()).decode()
            cmd = f"KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{{.items[0].metadata.name}}') -c wazuh-manager -- sh -c 'echo {script_b64} | base64 -d | python3'"
            ok, out = self.ssh.run(cmd)
            
            if ok and "SUCCESS" in out:
                self.after(0, lambda: messagebox.showinfo("Success", "PB01 Playbook successfully installed into Shuffle SOAR!"))
            else:
                self.after(0, lambda: messagebox.showerror("Installation Failed", f"Failed to install playbook:\\n{out}"))
                
        threading.Thread(target=worker, daemon=True).start()


    def _on_client_selected(self, client_id):
        from ..core.config import set_active_client, get_active_client_config
        set_active_client(client_id)
        client_conf = get_active_client_config()
        self._populate_config(client_conf)
        
        # Switch tabs - insert before forgetting to prevent TclError empty notebook on Windows
        self.notebook.insert(0, self.tab_conn, text=f" Connection: {client_conf.get('name', client_id)} ")
        self.notebook.forget(self.tab_clients)
        self.notebook.select(self.tab_conn)

    def _fetch_overview(self):
        import threading
        def worker():
            if not self.ssh or not self.ssh.is_connected():
                self.after(0, lambda: self.tab_overview.set_data([], [], error="Not connected"))
                return
            
            script = """
import subprocess, json
try:
    res = subprocess.run(["/usr/local/bin/kubectl", "get", "pods", "-n", "aml-lab", "-o", "json"], capture_output=True, text=True, env={"KUBECONFIG": "/home/amlak-siem-admin/.kube/config"})
    if res.returncode != 0:
        print(json.dumps({"error": res.stderr}))
        exit(0)
    data = json.loads(res.stdout)
    pods = []
    tools = set()
    for item in data.get("items", []):
        p_name = item.get("metadata", {}).get("name", "Unknown")
        status = item.get("status", {}).get("phase", "Unknown")
        
        c_names = []
        for c in item.get("spec", {}).get("containers", []):
            c_names.append(c.get("name", ""))
            img = c.get("image", "")
            if img:
                if ":" in img:
                    name, tag = img.rsplit(":", 1)
                else:
                    name, tag = img, "latest"
                tools.add((name, tag))
                
        pods.append({"name": p_name, "status": status, "containers": c_names})
        
    versions = [{"name": n, "version": t} for n, t in sorted(list(tools))]
    print(json.dumps({"pods": pods, "versions": versions}))
except Exception as e:
    print(json.dumps({"error": str(e)}))
"""
            import base64
            script_b64 = base64.b64encode(script.encode()).decode()
            cmd = f"echo {script_b64} | base64 -d | python3"
            ok, out = self.ssh.run(cmd)
            
            if not ok:
                self.after(0, lambda: self.tab_overview.set_data([], [], error="SSH command failed"))
                return
                
            try:
                import json
                data = json.loads(out)
                if "error" in data:
                    self.after(0, lambda: self.tab_overview.set_data([], [], error=data["error"]))
                else:
                    self.after(0, lambda: self.tab_overview.set_data(data.get("pods", []), data.get("versions", [])))
            except Exception as e:
                self.after(0, lambda: self.tab_overview.set_data([], [], error=f"Parse error: {e}"))
                
        threading.Thread(target=worker, daemon=True).start()

    def _fetch_wazuh_agents(self):
        import threading
        def worker():
            if not self.ssh or not self.ssh.is_connected():
                err = {"Total": "Err", "Active": "Err", "Disconnected": "Err", "Pending": "Err", "Never connected": "Err"}
                self.after(0, lambda: self.tab_wazuh.set_agent_stats(err))
                self.after(0, lambda: self.tab_wazuh.set_alert_stats({"Total": "Err", "Level 12+": "Err", "Auth Failure": "Err", "Auth Success": "Err"}))
                return
                
            script = """
import subprocess, urllib.request, json, ssl

stats = {"agents": {"Total": "0", "Active": "0", "Disconnected": "0", "Pending": "0", "Never connected": "0"},
         "alerts": {"Total": "0", "Level 12+": "0", "Auth Failure": "0", "Auth Success": "0"}}

# 1. Agent Stats
try:
    res = subprocess.run(["/var/ossec/bin/agent_control", "-j", "-l"], capture_output=True, text=True)
    if res.returncode == 0:
        agent_data = json.loads(res.stdout).get("data", [])
        valid_agents = [a for a in agent_data if a.get("id") != "000"]
        
        stats["agents"]["Total"] = str(len(valid_agents))
        active, disc, pend, never = 0, 0, 0, 0
        for agent in valid_agents:
            st = agent.get("status", "")
            if st == "Active": active += 1
            elif st == "Disconnected": disc += 1
            elif st == "Pending": pend += 1
            elif st == "Never connected": never += 1
        
        stats["agents"]["Active"] = str(active)
        stats["agents"]["Disconnected"] = str(disc)
        stats["agents"]["Pending"] = str(pend)
        stats["agents"]["Never connected"] = str(never)
except Exception:
    stats["agents"]["Total"] = "Err1"

# 2. Alert Stats (Last 24h) from OpenSearch
import datetime
now = datetime.datetime.utcnow()
past = now - datetime.timedelta(days=1)
time_filter = {"range": {"@timestamp": {"gte": past.strftime("%Y-%m-%dT%H:%M:%SZ"), "lte": now.strftime("%Y-%m-%dT%H:%M:%SZ")}}}

os_url = "http://opensearch-proxy.aml-lab.svc.cluster.local:9200/wazuh-alerts-*/_count"

def get_count(query):
    try:
        req = urllib.request.Request(os_url, data=json.dumps(query).encode(), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as res:
            return str(json.loads(res.read()).get("count", 0))
    except Exception:
        return "Err2"

stats["alerts"]["Total"] = get_count({"query": {"bool": {"filter": [time_filter]}}})
stats["alerts"]["Level 12+"] = get_count({"query": {"bool": {"filter": [time_filter, {"range": {"rule.level": {"gte": 12}}}]}}})
stats["alerts"]["Auth Failure"] = get_count({"query": {"bool": {"filter": [time_filter, {"match": {"rule.groups": "authentication_failed"}}]}}})
stats["alerts"]["Auth Success"] = get_count({"query": {"bool": {"filter": [time_filter, {"match": {"rule.groups": "authentication_success"}}]}}})

print(json.dumps(stats))
"""
            import base64
            script_b64 = base64.b64encode(script.encode()).decode()
            cmd = f"KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{{.items[0].metadata.name}}') -c wazuh-manager -- sh -c 'echo {script_b64} | base64 -d | python3'"
            ok, out = self.ssh.run(cmd)

            
            if not ok:
                err = {"Total": "Err", "Active": "Err", "Disconnected": "Err", "Pending": "Err", "Never connected": "Err"}
                self.after(0, lambda: self.tab_wazuh.set_agent_stats(err))
                self.after(0, lambda: self.tab_wazuh.set_alert_stats({"Total": "Err", "Level 12+": "Err", "Auth Failure": "Err", "Auth Success": "Err"}))
                return
                
            try:
                import json
                data = json.loads(out)
                self.after(0, lambda: self.tab_wazuh.set_agent_stats(data.get("agents", {})))
                self.after(0, lambda: self.tab_wazuh.set_alert_stats(data.get("alerts", {})))
            except Exception:
                err = {"Total": "Parse", "Active": "Parse", "Disconnected": "Parse", "Pending": "Parse", "Never connected": "Parse"}
                self.after(0, lambda: self.tab_wazuh.set_agent_stats(err))
                self.after(0, lambda: self.tab_wazuh.set_alert_stats({"Total": "Parse", "Level 12+": "Parse", "Auth Failure": "Parse", "Auth Success": "Parse"}))
                
        threading.Thread(target=worker, daemon=True).start()

    def _populate_config(self, config_data):
        if "host" in config_data: self.tab_conn.host_var.set(config_data["host"])
        if "user" in config_data: self.tab_conn.user_var.set(config_data["user"])
        if "key_path" in config_data: self.tab_conn.key_var.set(config_data["key_path"])
        if "cf_token" in config_data: self.tab_conn.cf_token_var.set(config_data["cf_token"])
        if "cf_zone" in config_data: self.tab_conn.cf_zone_var.set(config_data["cf_zone"])
        if "alert_email" in config_data: self.tab_conn.alert_email_var.set(config_data["alert_email"])

    def _drain_queue(self):
        """Safely apply UI updates coming from the background orchestrator."""
        if self.orchestrator:
            try:
                while True:
                    fn = self.orchestrator.ui_queue.get_nowait()
                    fn()
            except queue.Empty:
                pass
        self.after(40, self._drain_queue)

    def _on_browse_key(self):
        path = filedialog.askopenfilename(title="Select SSH Private Key")
        if path:
            self.tab_conn.key_var.set(path)

    def _on_save_config(self):
        import os
        config_path = "config.json"
        if os.path.exists(config_path):
            if not messagebox.askyesno("Confirm Overwrite", f"{config_path} already exists.\nDo you want to overwrite it?"):
                return
        
        save_config({
            "host": self.tab_conn.host_var.get(),
            "user": self.tab_conn.user_var.get(),
            "key_path": self.tab_conn.key_var.get(),
            "cf_token": self.tab_conn.cf_token_var.get(),
            "cf_zone": self.tab_conn.cf_zone_var.get(),
            "alert_email": self.tab_conn.alert_email_var.get()
        })
        messagebox.showinfo("Success", f"Configuration saved to {config_path}")

    def _on_load_config(self):
        import json
        path = filedialog.askopenfilename(title="Select Config File", filetypes=[("JSON Files", "*.json")])
        if path:
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                self._populate_config(data)
                self.config.update(data)
                messagebox.showinfo("Success", f"Configuration loaded from {path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load config: {e}")

    def _on_connect(self):
        if self.ssh and self.ssh.is_connected():
            self._disconnect()
            return
            
        host = self.tab_conn.host_var.get()
        user = self.tab_conn.user_var.get()
        key = self.tab_conn.key_var.get()
        
        # Save config
        save_config({
            "host": host,
            "user": user,
            "key_path": key,
            "cf_token": self.tab_conn.cf_token_var.get(),
            "cf_zone": self.tab_conn.cf_zone_var.get(),
            "alert_email": self.tab_conn.alert_email_var.get()
        })
        
        # Reload config to ensure we have cf_domain
        self.config = load_config()
        
        self.tab_conn.set_status(f"Connecting to {host}...", C["warn"])
        
        self.ssh = SSHRunner(host, "22", user, key)
        ok, msg = self.ssh.connect()
        
        if ok:
            self.tab_conn.set_status(f"Connected to {host}", C["success"])
            self.tab_conn.set_button("Disconnect", C["danger"], self._disconnect)
            self.orchestrator = Orchestrator(self.ssh)
            
            # Show Setup tab right after Connection
            self.notebook.insert(1, self.tab_setup, text=" Setup ")
            self.notebook.select(self.tab_setup)
            
            # Show integration tabs
            self.notebook.add(self.tab_overview, text=" Overview ")
            self.notebook.add(self.tab_wazuh, text=" Wazuh ")
            self.notebook.add(self.tab_thehive, text=" TheHive ")
            self.notebook.add(self.tab_shuffle, text=" Shuffle ")
            self.notebook.add(self.tab_grafana, text=" Grafana ")
            self.notebook.add(self.tab_reports, text=" Reports ")
            self.tab_reports.ssh = self.ssh
            
            from ..core.config import get_active_client_config
            client_conf = get_active_client_config()
            domain = client_conf.get("cf_domain", "amlsiem.com")
            
            self.tab_wazuh.set_url(f"https://wazuh.aml-lab.{domain}")
            self.tab_thehive.set_url(f"https://thehive.aml-lab.{domain}")
            self.tab_shuffle.set_url(f"https://shuffle.aml-lab.{domain}")
            self.tab_grafana.set_urls(
                url=f"https://grafana.aml-lab.{domain}/d/unified/unified-siem-dashboard"
            )
            
            # Trigger initial fetches
            self._fetch_overview()
            self._fetch_wazuh_agents()
        else:
            self.tab_conn.set_status("Connection Failed", C["danger"])
            messagebox.showerror("SSH Error", msg)
            self.ssh = None

    def _disconnect(self):
        if self.ssh:
            self.ssh.close()
            self.ssh = None
        if self.orchestrator:
            self.orchestrator.stop()
            self.orchestrator = None
            
        self.tab_conn.set_status("Not Connected", C["muted"])
        self.tab_conn.set_button("Connect", C["accent"], self._on_connect)
        
        # Back to clients - insert before forgetting to prevent TclError empty notebook on Windows
        self.notebook.insert(0, self.tab_clients, text=" Clients ")
        self.tab_clients.refresh_clients()
        self.notebook.select(self.tab_clients)

        # Hide integration tabs and connection tab on disconnect
        try:
            self.notebook.forget(self.tab_conn)
            self.notebook.forget(self.tab_setup)
            self.notebook.forget(self.tab_overview)
            self.notebook.forget(self.tab_wazuh)
            self.notebook.forget(self.tab_thehive)
            self.notebook.forget(self.tab_shuffle)
            self.notebook.forget(self.tab_grafana)
            self.notebook.forget(self.tab_reports)
        except Exception:
            pass
        self.notebook.select(self.tab_clients)

    def _on_run_setup(self, force=False):
        if not self.orchestrator or not self.ssh or not self.ssh.is_connected():
            messagebox.showerror("Error", "Please connect to the server first.")
            self.notebook.select(self.tab_conn)
            return
            
        selected_ids = self.tab_setup.get_selected_ids()
        if not selected_ids:
            return
            
        steps_to_run = [s for s in self.steps_def if s["id"] in selected_ids]
        
        self.tab_setup.run_btn.config(state="disabled")
        self.tab_setup.clear_log()
        
        def safe_ui(fn):
            if self.orchestrator:
                self.orchestrator._put_ui(fn)

        def on_complete():
            safe_ui(lambda: self.tab_setup.run_btn.config(state="normal"))
            safe_ui(lambda: self.tab_setup.append_log(f"\n{'═'*52}\n  Run Complete\n{'═'*52}", "head"))
            
        self.orchestrator.run_steps(
            steps=steps_to_run,
            force=force,
            on_log=lambda m, t="": safe_ui(lambda: self.tab_setup.append_log(m, t)),
            on_log_output=lambda o: safe_ui(lambda: self.tab_setup.append_log_output(o)),
            on_badge_update=lambda sid, txt, col: safe_ui(lambda: self.tab_setup.set_badge(sid, txt, col)),
            on_sub_update=lambda sid, idx, st: safe_ui(lambda: self.tab_setup.set_sub(sid, idx, st)),
            on_progress=lambda d, t, l="": safe_ui(lambda: self.tab_setup.set_progress(d, t, l)),
            on_complete=on_complete
        )

    def destroy(self):
        self._disconnect()
        super().destroy()
