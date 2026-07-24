import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from .components import C, FONT_BOLD
from ..core.config import save_client_config, load_config

class ClientDashboardTab(ttk.Frame):
    def __init__(self, parent, on_client_selected):
        super().__init__(parent)
        self.on_client_selected = on_client_selected
        self._build_ui()

    def _build_ui(self):
        self.configure(style="TFrame")
        
        # Header
        tk.Label(self, text="Fleet Dashboard", font=(FONT_BOLD, 22), bg=C["card"], fg=C["text"]).pack(pady=(30, 5))
        tk.Label(self, text="Select a client environment to manage or deploy.", font=("Inter", 12), bg=C["card"], fg=C["muted"]).pack(pady=(0, 30))
        
        # Grid container for client cards
        self.grid_frame = tk.Frame(self, bg=C["bg"])
        self.grid_frame.pack(fill="both", expand=True, padx=40, pady=10)
        
        self.refresh_clients()

    def refresh_clients(self):
        # Clear existing
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
            
        config = load_config()
        clients = config.get("clients", {})
        
        col = 0
        row = 0
        max_cols = 4
        
        # Create Add New button first
        self._create_add_card(row, col)
        col += 1
        
        # Create cards for existing clients
        for client_id, cdata in clients.items():
            if col >= max_cols:
                col = 0
                row += 1
            self._create_client_card(client_id, cdata, row, col)
            col += 1

    def _create_add_card(self, r, c):
        card = tk.Frame(self.grid_frame, bg=C["card"], highlightbackground=C["border"], highlightthickness=1, padx=20, pady=20, cursor="hand2")
        card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
        
        tk.Label(card, text="+", font=(FONT_BOLD, 36), bg=C["card"], fg=C["accent"]).pack(expand=True)
        tk.Label(card, text="Add Client", font=(FONT_BOLD, 14), bg=C["card"], fg=C["text"]).pack(pady=(10, 0))
        
        card.bind("<Button-1>", lambda e: self._show_add_modal())
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e: self._show_add_modal())

    def _create_client_card(self, client_id, cdata, r, c):
        card = tk.Frame(self.grid_frame, bg=C["card"], highlightbackground=C["border"], highlightthickness=1, padx=20, pady=20, cursor="hand2")
        card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
        
        name = cdata.get("name", client_id)
        tier = cdata.get("tier", "Unknown Tier")
        
        tk.Label(card, text="🏢", font=("", 32), bg=C["card"]).pack(pady=(0, 10))
        tk.Label(card, text=name, font=(FONT_BOLD, 14), bg=C["card"], fg=C["text"]).pack()
        tk.Label(card, text=tier, font=("Inter", 10), bg=C["card"], fg=C["muted"]).pack(pady=(5, 0))
        
        # Click handler
        handler = lambda e, cid=client_id: self.on_client_selected(cid)
        card.bind("<Button-1>", handler)
        for child in card.winfo_children():
            child.bind("<Button-1>", handler)

    def _show_add_modal(self):
        # A simple prompt for client name
        # We could use a Toplevel for more fields, but simpledialog works for quick addition
        name = simpledialog.askstring("Add Client", "Enter Client Name:")
        if not name:
            return
            
        tier = simpledialog.askstring("Add Client", "Enter Tier (e.g., Tier A, Tier B):", initialvalue="Tier A")
        if not tier:
            return
            
        # Generate ID
        client_id = name.lower().replace(" ", "_")
        
        # Save to config
        save_client_config(client_id, {"name": name, "tier": tier, "host": "", "user": "ubuntu", "key_path": ""})
        
        # Refresh UI
        self.refresh_clients()
