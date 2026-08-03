import tkinter as tk
from tkinter import ttk
from .components import C, FONT_BOLD

class OverviewTab(ttk.Frame):
    def __init__(self, parent, refresh_callback=None):
        super().__init__(parent)
        self.refresh_callback = refresh_callback
        
        # Main layout
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Header
        header_frame = tk.Frame(self, bg=C["bg"])
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        title = tk.Label(header_frame, text="Cluster Overview", font=(FONT_BOLD, 18), bg=C["bg"], fg=C["text"])
        title.pack(side="left")
        
        self.refresh_btn = tk.Button(header_frame, text="Refresh", command=self._on_refresh, 
                                     bg=C["accent"], fg=C["bg"], font=(FONT_BOLD, 12), borderwidth=0, padx=15, pady=5)
        self.refresh_btn.pack(side="right")
        
        # Content frame (split into Pods and Tools vertically)
        content_frame = tk.Frame(self, bg=C["bg"])
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        content_frame.columnconfigure(0, weight=1)
        content_frame.rowconfigure(0, weight=2) # Pods on top
        content_frame.rowconfigure(1, weight=1) # Versions on bottom
        
        # Top: Pod Cards
        pod_frame = tk.Frame(content_frame, bg=C["card"], padx=10, pady=10)
        pod_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        tk.Label(pod_frame, text="Pod Status", font=(FONT_BOLD, 14), bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 10))
        
        # Scrollable canvas for pods
        self.canvas = tk.Canvas(pod_frame, bg=C["card"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(pod_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=C["card"])
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bottom: Tool Versions Table
        tools_frame = tk.Frame(content_frame, bg=C["card"], padx=10, pady=10)
        tools_frame.grid(row=1, column=0, sticky="nsew")
        
        tk.Label(tools_frame, text="Tool Versions", font=(FONT_BOLD, 14), bg=C["card"], fg=C["text"]).pack(anchor="w", pady=(0, 10))
        
        columns = ("Tool", "Version")
        self.tree = ttk.Treeview(tools_frame, columns=columns, show="headings", height=15)
        self.tree.heading("Tool", text="Image / Component")
        self.tree.heading("Version", text="Version Tag")
        
        self.tree.column("Tool", width=200)
        self.tree.column("Version", width=100)
        self.tree.pack(fill="both", expand=True)
        
        # Status Label
        self.status_lbl = tk.Label(self, text="Waiting for data...", bg=C["bg"], fg=C["muted"])
        self.status_lbl.grid(row=2, column=0, sticky="w", padx=20, pady=5)

    def _on_refresh(self):
        if self.refresh_callback:
            self.refresh_btn.config(state="disabled")
            self.status_lbl.config(text="Fetching cluster data...")
            self.refresh_callback()

    def set_data(self, pod_data, version_data, error=None):
        self.refresh_btn.config(state="normal")
        
        if error:
            self.status_lbl.config(text=f"Error: {error}", fg=C["danger"])
            return
            
        self.status_lbl.config(text="Data updated successfully.", fg=C["success"])
        
        # Update Pods Matrix
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
            
        num_cols = 4
        for i in range(num_cols):
            self.scrollable_frame.columnconfigure(i, weight=1, uniform="card")
            
        row_idx, col_idx = 0, 0
            
        for pod in pod_data:
            pod_name = pod.get("name", "Unknown")
            status = pod.get("status", "Unknown")
            
            # Determine color
            if status in ("Running", "Succeeded"):
                bg_col = C["success"] if status == "Running" else C["mono"]
                fg_col = C["bg"]
            elif status in ("Pending", "ContainerCreating"):
                bg_col = C["warn"]
                fg_col = C["bg"]
            else:
                bg_col = C["danger"]
                fg_col = C["text"]
                
            card = tk.Frame(self.scrollable_frame, bg=C["bg"], highlightbackground=bg_col, highlightthickness=2, padx=10, pady=10)
            card.grid(row=row_idx, column=col_idx, padx=5, pady=5, sticky="nsew")
            
            col_idx += 1
            if col_idx >= num_cols:
                col_idx = 0
                row_idx += 1
            
            tk.Label(card, text=pod_name, font=(FONT_BOLD, 12), bg=C["bg"], fg=C["text"]).pack(anchor="w")
            tk.Label(card, text=f"Status: {status}", bg=bg_col, fg=fg_col).pack(anchor="w", pady=(5, 0))
            
            # Containers
            containers = pod.get("containers", [])
            if containers:
                c_text = "Containers: " + ", ".join(containers)
                tk.Label(card, text=c_text, bg=C["bg"], fg=C["muted"], font=("TkDefaultFont", 9)).pack(anchor="w")
                
        # Update Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for tool in version_data:
            self.tree.insert("", "end", values=(tool["name"], tool["version"]))
