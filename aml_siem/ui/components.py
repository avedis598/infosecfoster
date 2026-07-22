import tkinter as tk

C = {
    "bg":       "#313131",
    "card":     "#2B2B2B",
    "surface":  "#414141",
    "border":   "#4D4D4D",
    "text":     "#ffffff",
    "muted":    "#a3a3a3",
    "mono":     "#7ee787",
    "accent":   "#2fa572",  # Forest theme green
    "success":  "#2fa572",
    "warn":     "#d29922",
    "danger":   "#f85149",
    "fail":     "#f85149",
    "wazuh":    "#00aed6",
    "thehive":  "#f0a500",
    "shuffle":  "#00d4b1",
}

FONT_BOLD  = ("Segoe UI", 10, "bold")
FONT_STEP  = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_MONO  = ("Consolas", 10)


class FlatBtn(tk.Label):
    """Dark-themed button using tk.Label to avoid macOS native button styling limitations."""

    @staticmethod
    def _lighten(hex_color):
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            return f"#{min(255,r+30):02x}{min(255,g+30):02x}{min(255,b+30):02x}"
        except Exception:
            return hex_color

    def __init__(self, parent, text="", command=None,
                 bg=None, fg=None, font=None,
                 padx=14, pady=8, **kw):
        self._bg = bg or C["surface"]
        self._fg = fg or C["text"]
        self._hover_bg = self._lighten(self._bg)
        _font = font or FONT_STEP
        
        self.command = command or (lambda: None)
        self.state = kw.pop("state", "normal")
        
        # Remove tk.Button specific keys
        for _k in ("activebackground", "activeforeground", "disabledforeground", 
                   "highlightthickness", "highlightbackground", "highlightcolor", 
                   "relief", "bd", "borderwidth"):
            kw.pop(_k, None)
            
        super().__init__(
            parent,
            text=text,
            bg=self._bg, fg=self._fg, font=_font,
            padx=padx, pady=pady,
            cursor="hand2",
            **kw
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _on_enter(self, _):
        if self.state != "disabled":
            self.configure(bg=self._hover_bg)

    def _on_leave(self, _):
        if self.state != "disabled":
            self.configure(bg=self._bg)
            
    def _on_click(self, _):
        if self.state != "disabled":
            self.command()

    def configure(self, **kw):
        if "command" in kw:
            self.command = kw.pop("command") or (lambda: None)
            
        if "state" in kw:
            self.state = kw.pop("state")
            if self.state == "disabled":
                kw["fg"] = C["muted"]
            else:
                kw["fg"] = self._fg
                
        if "bg" in kw or "background" in kw:
            self._bg = kw.get("bg") or kw.get("background") or self._bg
            self._hover_bg = self._lighten(self._bg)
            kw["bg"] = self._bg
            
        if kw:
            super().configure(**kw)

    config = configure

class CollapsibleFrame(tk.Frame):
    def __init__(self, parent, title, bg=C["surface"], fg=C["accent"], font=FONT_BOLD, collapsed=False, **kwargs):
        self.show_chk = kwargs.pop("show_chk", False)
        self.chk_var = kwargs.pop("chk_var", None)
        self.chk_command = kwargs.pop("chk_command", None)
        
        super().__init__(parent, bg=bg, **kwargs)
        self.collapsed = collapsed
        
        self.header_frame = tk.Frame(self, bg=bg)
        self.header_frame.pack(side="top", fill="x")
        
        self.toggle_btn = tk.Label(
            self.header_frame, text="[+]" if self.collapsed else "[-]", 
            bg=bg, fg=fg, font=FONT_MONO, cursor="hand2"
        )
        self.toggle_btn.bind("<Button-1>", lambda e: self.toggle())
        self.toggle_btn.pack(side="left", anchor="w")
        
        if self.show_chk:
            if self.chk_var is None:
                self.chk_var = tk.BooleanVar(value=True)
            self.chk_btn = tk.Checkbutton(
                self.header_frame, variable=self.chk_var, bg=bg, fg=fg, 
                selectcolor="#2a7b8e", activebackground=bg, font=("Segoe UI", 9)
            )
            if self.chk_command:
                self.chk_btn.config(command=self.chk_command)
            self.chk_btn.pack(side="left", padx=(5,0))
        
        self.title_lbl = tk.Label(self.header_frame, text=title, bg=bg, fg=fg, font=font, cursor="hand2")
        self.title_lbl.bind("<Button-1>", lambda e: self.toggle())
        self.title_lbl.pack(side="left", padx=(5,0))
        
        self.sub_frame = tk.Frame(self, bg=bg)
        if not self.collapsed:
            self.sub_frame.pack(side="top", fill="x", padx=(20, 0))

    def toggle(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.sub_frame.pack_forget()
            self.toggle_btn.config(text="[+]")
        else:
            self.sub_frame.pack(side="top", fill="x", padx=(20, 0))
            self.toggle_btn.config(text="[-]")
            self.sub_frame.pack(side="top", fill="x", padx=(20, 0))
