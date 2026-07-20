import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import queue

from ..core.config import load_config, save_config
from ..core.ssh_runner import SSHRunner
from ..core.orchestrator import Orchestrator

from .components import C, FONT_BOLD
from .tabs_connection import ConnectionTab
from .tabs_setup import SetupTab
from .tabs_dashboards import WazuhTab, TheHiveTab, ShuffleTab

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
        
        self.tab_conn = ConnectionTab(
            self.notebook, 
            self._on_connect, 
            self._on_browse_key,
            self._on_save_config,
            self._on_load_config
        )
        self.notebook.add(self.tab_conn, text=" Connection ")
        
        self.tab_setup = SetupTab(self.notebook, self.steps_def, self._on_run_setup)
        self.notebook.add(self.tab_setup, text=" Setup ")
        
        self.tab_wazuh = WazuhTab(self.notebook, refresh_callback=self._fetch_wazuh_agents)
        self.tab_thehive = TheHiveTab(self.notebook)
        self.tab_shuffle = ShuffleTab(self.notebook)
        
        # Load saved config
        self._populate_config(self.config)

    def _fetch_wazuh_agents(self):
        import threading
        def worker():
            if not self.ssh or not self.ssh.is_connected():
                self.after(0, lambda: self.tab_wazuh.set_agent_count("Error: Not connected"))
                return
                
            cmd = "KUBECONFIG=~/.kube/config kubectl exec -n aml-lab $(KUBECONFIG=~/.kube/config kubectl get pods -n aml-lab -l node-role=master -o jsonpath='{.items[0].metadata.name}') -c wazuh-manager -- /var/ossec/bin/agent_control -l"
            ok, out = self.ssh.run(cmd)
            
            if not ok:
                self.after(0, lambda: self.tab_wazuh.set_agent_count("Error: Command failed"))
                return
                
            # Parse output to find active external agents
            lines = out.split("\n")
            active_count = 0
            for line in lines:
                if "Active" in line and "(server)" not in line:
                    active_count += 1
            
            self.after(0, lambda: self.tab_wazuh.set_agent_count(str(active_count)))
            
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
            self.notebook.select(self.tab_setup)
            
            # Show integration tabs
            self.notebook.add(self.tab_wazuh, text=" Wazuh ")
            self.notebook.add(self.tab_thehive, text=" TheHive ")
            self.notebook.add(self.tab_shuffle, text=" Shuffle ")
            
            domain = self.config.get("cf_domain", "amlsiem.com")
            
            self.tab_wazuh.set_url(f"https://wazuh.aml-lab.{domain}")
            self.tab_thehive.set_url(f"https://thehive.aml-lab.{domain}")
            self.tab_shuffle.set_url(f"https://shuffle.aml-lab.{domain}")
            
            # Trigger initial fetch
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
        
        # Hide integration tabs on disconnect
        try:
            self.notebook.forget(self.tab_wazuh)
            self.notebook.forget(self.tab_thehive)
            self.notebook.forget(self.tab_shuffle)
        except tk.TclError:
            pass

    def _on_run_setup(self):
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
        
        def on_complete():
            self.orchestrator._put_ui(lambda: self.tab_setup.run_btn.config(state="normal"))
            self.orchestrator._put_ui(lambda: self.tab_setup.append_log(f"\n{'═'*52}\n  Run Complete\n{'═'*52}", "head"))
            
        self.orchestrator.run_steps(
            steps=steps_to_run,
            on_log=lambda m, t="": self.orchestrator._put_ui(lambda: self.tab_setup.append_log(m, t)),
            on_log_output=lambda o: self.orchestrator._put_ui(lambda: self.tab_setup.append_log_output(o)),
            on_badge_update=lambda sid, txt, col: self.orchestrator._put_ui(lambda: self.tab_setup.set_badge(sid, txt, col)),
            on_sub_update=lambda sid, idx, st: self.orchestrator._put_ui(lambda: self.tab_setup.set_sub(sid, idx, st)),
            on_progress=lambda d, t, l="": self.orchestrator._put_ui(lambda: self.tab_setup.set_progress(d, t, l)),
            on_complete=on_complete
        )

    def destroy(self):
        self._disconnect()
        super().destroy()
