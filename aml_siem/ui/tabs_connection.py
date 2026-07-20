import tkinter as tk
from tkinter import filedialog
from .components import C, FONT_BOLD, FONT_STEP, FlatBtn

class ConnectionTab(tk.Frame):
    def __init__(self, parent, on_connect, on_browse_key, on_save_config, on_load_config):
        super().__init__(parent, bg=C["bg"])
        self.on_connect = on_connect
        self.on_browse_key = on_browse_key
        self.on_save_config = on_save_config
        self.on_load_config = on_load_config

        # Variables
        self.host_var = tk.StringVar(value="192.168.1.100")
        self.user_var = tk.StringVar(value="ubuntu")
        self.key_var = tk.StringVar(value="~/.ssh/id_rsa")
        self.cf_token_var = tk.StringVar()
        self.cf_zone_var = tk.StringVar()
        
        self.conn_status_var = tk.StringVar(value="Not Connected")
        self.conn_status_lbl = None

        self._build_ui()

    def _build_ui(self):
        # Outer container to center the form
        outer_container = tk.Frame(self, bg=C["bg"])
        outer_container.place(relx=0.5, rely=0.5, anchor="center")
        
        container = tk.Frame(outer_container, bg=C["card"], padx=40, pady=40)
        container.pack()
        
        # Header
        tk.Label(container, text="Target Server", bg=C["card"], fg=C["text"], 
                 font=("Segoe UI", 16, "bold")).pack(anchor="center", pady=(0,20))

        # Form Grid
        grid = tk.Frame(container, bg=C["card"])
        grid.pack(fill="x")
        grid.columnconfigure(1, weight=1)

        fields = [
            ("IP Address / Host:", self.host_var),
            ("SSH Username:", self.user_var),
            ("Private Key Path:", self.key_var),
        ]
        
        for i, (label_text, var) in enumerate(fields):
            tk.Label(grid, text=label_text, bg=C["card"], fg=C["muted"], font=FONT_STEP).grid(
                row=i, column=0, sticky="e", pady=10, padx=(0,15))
            
            f_frame = tk.Frame(grid, bg=C["card"])
            f_frame.grid(row=i, column=1, sticky="we", pady=10)
            
            entry = tk.Entry(f_frame, textvariable=var, bg=C["surface"], fg=C["text"], 
                             insertbackground=C["text"], font=FONT_STEP, relief="flat", bd=5, width=30)
            entry.pack(side="left", fill="x", expand=True)
            
            if i == 2: # Key path gets browse button
                FlatBtn(f_frame, text="Browse", bg=C["border"], fg=C["text"], command=self.on_browse_key, 
                        padx=10, pady=2, font=FONT_STEP).pack(side="left", padx=(10,0))

        # Optional config
        tk.Label(container, text="Cloudflare API (Optional)", bg=C["card"], fg=C["text"], 
                 font=("Segoe UI", 12, "bold")).pack(anchor="center", pady=(30,10))
                 
        cf_grid = tk.Frame(container, bg=C["card"])
        cf_grid.pack(fill="x")
        cf_grid.columnconfigure(1, weight=1)
        
        cf_fields = [
            ("API Token:", self.cf_token_var),
            ("Zone ID:", self.cf_zone_var)
        ]
        
        for i, (label_text, var) in enumerate(cf_fields):
            tk.Label(cf_grid, text=label_text, bg=C["card"], fg=C["muted"], font=FONT_STEP).grid(
                row=i, column=0, sticky="e", pady=10, padx=(0,15))
            tk.Entry(cf_grid, textvariable=var, bg=C["surface"], fg=C["text"], 
                     insertbackground=C["text"], font=FONT_STEP, relief="flat", bd=5, width=30).grid(
                row=i, column=1, sticky="we", pady=10)

        # Config Action Row
        config_frame = tk.Frame(container, bg=C["card"])
        config_frame.pack(fill="x", pady=(20,0))
        FlatBtn(config_frame, text="Load Config", bg=C["border"], fg=C["text"], command=self.on_load_config).pack(side="left", padx=(0,10))
        FlatBtn(config_frame, text="Save Config", bg=C["border"], fg=C["text"], command=self.on_save_config).pack(side="left")

        # Status and Action Row
        action_frame = tk.Frame(container, bg=C["card"])
        action_frame.pack(fill="x", pady=(40,0))
        
        self.conn_status_lbl = tk.Label(action_frame, textvariable=self.conn_status_var, 
                                        bg=C["card"], fg=C["muted"], font=FONT_BOLD)
        self.conn_status_lbl.pack(side="left")
        
        # Connect button in Green, Terminal button in White/Gray
        self.btn_connect = FlatBtn(action_frame, text="Connect", bg=C["accent"], fg="white", command=self.on_connect)
        self.btn_connect.pack(side="right")
        self.btn_term = FlatBtn(action_frame, text="Terminal", bg=C["border"], fg="white", command=lambda: print("Terminal logic pending"))
        self.btn_term.pack(side="right", padx=(0, 10))
        
    def set_status(self, text, color):
        self.conn_status_var.set(text)
        self.conn_status_lbl.config(fg=color)
        
    def set_button(self, text, bg, command):
        self.btn_connect.config(text=text, bg=bg, command=command)
