import tkinter as tk
import webbrowser
from .components import C, FONT_BOLD, FlatBtn

class BaseDashboardTab(tk.Frame):
    def __init__(self, parent, title, bg_color):
        super().__init__(parent, bg=C["bg"])
        self.bg_color = bg_color
        
        self.container = tk.Frame(self, bg=C["bg"])
        self.container.pack(expand=True)
        
        self.title_lbl = tk.Label(self.container, text=title, font=("Helvetica", 24, "bold"), 
                                  bg=C["bg"], fg=self.bg_color)
        self.title_lbl.pack(pady=20)
        
        self.url_lbl = tk.Label(self.container, text="Not available", font=("Helvetica", 14), 
                                bg=C["bg"], fg=C["text"])
        self.url_lbl.pack(pady=10)
        
        self.btn = FlatBtn(self.container, text="Open in Browser", bg=self.bg_color, fg=C["bg"], 
                           command=self._open_url)
        self.btn.pack(pady=20)
        
        self.creds_frame = tk.Frame(self.container, bg=C["bg"])
        self.creds_frame.pack(pady=20)
        
        self.url = ""

    def set_url(self, url):
        self.url = url
        self.url_lbl.config(text=url)
        
    def _open_url(self):
        if self.url:
            webbrowser.open(self.url)

class WazuhTab(BaseDashboardTab):
    def __init__(self, parent, refresh_callback=None):
        super().__init__(parent, "Wazuh Dashboard", C["wazuh"])
        self.refresh_callback = refresh_callback
        
        tk.Label(self.creds_frame, text="Username: admin", bg=C["bg"], fg=C["text"], font=FONT_BOLD).pack(pady=2)
        tk.Label(self.creds_frame, text="Password: admin", bg=C["bg"], fg=C["text"], font=FONT_BOLD).pack(pady=2)
        
        # Stats container
        self.stats_container = tk.Frame(self.container, bg=C["bg"])
        self.stats_container.pack(pady=20, fill="x", padx=40)
        
        # Agent Stats Frame
        tk.Label(self.stats_container, text="Agent Status", font=("Helvetica", 16, "bold"), bg=C["bg"], fg=C["text"]).pack(anchor="w", pady=(0, 10))
        self.agents_frame = tk.Frame(self.stats_container, bg=C["bg"])
        self.agents_frame.pack(fill="x", pady=(0, 20))
        
        self.agent_vars = {}
        for metric in ["Total", "Active", "Disconnected", "Pending", "Never connected"]:
            card = tk.Frame(self.agents_frame, bg=C["card"], highlightbackground=C["border"], highlightthickness=1, padx=15, pady=10)
            card.pack(side="left", padx=5, fill="x", expand=True)
            tk.Label(card, text=metric, font=("Inter", 10), bg=C["card"], fg=C["muted"]).pack()
            var = tk.StringVar(value="-")
            tk.Label(card, textvariable=var, font=("Helvetica", 20, "bold"), bg=C["card"], fg=C["wazuh"]).pack(pady=(5,0))
            self.agent_vars[metric] = var

        # Alert Stats Frame
        tk.Label(self.stats_container, text="OpenSearch Alerts (Last 24h)", font=("Helvetica", 16, "bold"), bg=C["bg"], fg=C["text"]).pack(anchor="w", pady=(0, 10))
        self.alerts_frame = tk.Frame(self.stats_container, bg=C["bg"])
        self.alerts_frame.pack(fill="x", pady=(0, 20))
        
        self.alert_vars = {}
        for metric in ["Total", "Level 12+", "Auth Failure", "Auth Success"]:
            card = tk.Frame(self.alerts_frame, bg=C["card"], highlightbackground=C["border"], highlightthickness=1, padx=15, pady=10)
            card.pack(side="left", padx=5, fill="x", expand=True)
            tk.Label(card, text=metric, font=("Inter", 10), bg=C["card"], fg=C["muted"]).pack()
            var = tk.StringVar(value="-")
            tk.Label(card, textvariable=var, font=("Helvetica", 20, "bold"), bg=C["card"], fg=C["warn"]).pack(pady=(5,0))
            self.alert_vars[metric] = var
            
        self.refresh_btn = FlatBtn(self.stats_container, text="Refresh Data", bg=C["muted"], fg=C["bg"], command=self._on_refresh)
        self.refresh_btn.pack(pady=10)
        
    def _on_refresh(self):
        if self.refresh_callback:
            for v in self.agent_vars.values(): v.set("...")
            for v in self.alert_vars.values(): v.set("...")
            self.after(100, self.refresh_callback)
            
    def set_agent_stats(self, stats):
        for k, v in stats.items():
            if k in self.agent_vars:
                self.agent_vars[k].set(str(v))
                
    def set_alert_stats(self, stats):
        for k, v in stats.items():
            if k in self.alert_vars:
                self.alert_vars[k].set(str(v))

class TheHiveTab(BaseDashboardTab):
    def __init__(self, parent):
        super().__init__(parent, "TheHive", C["thehive"])
        
        tk.Label(self.creds_frame, text="Username: admin@thehive.local", bg=C["bg"], fg=C["text"], font=FONT_BOLD).pack(pady=2)
        tk.Label(self.creds_frame, text="Password: secret", bg=C["bg"], fg=C["text"], font=FONT_BOLD).pack(pady=2)

class ShuffleTab(BaseDashboardTab):
    def __init__(self, parent):
        super().__init__(parent, "Shuffle SOAR", C["shuffle"])
        
        tk.Label(self.creds_frame, text="Username: admin", bg=C["bg"], fg=C["text"], font=FONT_BOLD).pack(pady=2)
        tk.Label(self.creds_frame, text="Password: Admin1234!", bg=C["bg"], fg=C["text"], font=FONT_BOLD).pack(pady=2)

from tkinter import ttk

class GrafanaTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=C["bg"])
        
        self.title = tk.Label(self, text="Unified SIEM Dashboard", font=("Helvetica", 24, "bold"), bg=C["bg"], fg=C["warn"])
        self.title.pack(pady=40)
        
        self.url_lbl = tk.Label(self, text="Not available", font=("Helvetica", 14), bg=C["bg"], fg=C["text"])
        self.url_lbl.pack(pady=10)
        
        self.btn = FlatBtn(self, text="Open in Browser", bg=C["warn"], fg=C["bg"], command=lambda: self._open_url(self.url))
        self.btn.pack(pady=20)
        
        tk.Label(self, text="Consolidated Executive & Operational Views", bg=C["bg"], fg=C["text"], font=FONT_BOLD).pack(pady=2)

    def set_urls(self, url):
        self.url = url
        self.url_lbl.config(text=f"URL: {url}")

    def _open_url(self, url):
        import webbrowser
        if url:
            webbrowser.open(url)
