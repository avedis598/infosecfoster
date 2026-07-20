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
        
        self.agent_frame = tk.Frame(self.container, bg=C["bg"])
        self.agent_frame.pack(pady=20)
        
        self.agent_lbl = tk.Label(self.agent_frame, text="Live Agents: Unknown", bg=C["bg"], fg=C["text"], font=("Helvetica", 14))
        self.agent_lbl.pack(side="left", padx=10)
        
        self.refresh_btn = FlatBtn(self.agent_frame, text="Refresh", bg=C["muted"], fg=C["bg"], command=self._on_refresh)
        self.refresh_btn.pack(side="left")
        
    def _on_refresh(self):
        if self.refresh_callback:
            self.agent_lbl.config(text="Live Agents: Loading...")
            # Schedule the callback (which might be blocking or async)
            self.after(100, self.refresh_callback)
            
    def set_agent_count(self, count_str):
        self.agent_lbl.config(text=f"Live Agents: {count_str}")

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
