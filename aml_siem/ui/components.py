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


class FlatBtn(tk.Button):
    """Dark-themed button. Uses tk.Button internally — no custom Canvas drawing.
    This avoids macOS layout-cascade deadlocks that occurred with the Canvas version."""

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
        # Remove any canvas-only keys that tk.Button doesn't know
        for _k in ("highlightthickness", "highlightbackground",
                   "highlightcolor", "relief", "bd", "borderwidth"):
            kw.pop(_k, None)
        super().__init__(
            parent,
            text=text, command=command or (lambda: None),
            bg=self._bg, fg=self._fg, font=_font,
            relief="flat", bd=0,
            padx=padx, pady=pady,
            cursor="hand2",
            activebackground=self._hover_bg,
            activeforeground=self._fg,
            disabledforeground=C["muted"],
            **kw
        )
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self._hover_bg)

    def _on_leave(self, _):
        if str(self["state"]) != "disabled":
            self.configure(bg=self._bg)

    def configure(self, **kw):
        # Keep internal _bg/_hover_bg in sync when bg is changed
        if "bg" in kw or "background" in kw:
            self._bg = kw.get("bg") or kw.get("background") or self._bg
            self._hover_bg = self._lighten(self._bg)
            kw.setdefault("activebackground", self._hover_bg)
        # tk.Button handles all valid keys; ignore canvas-only keys silently
        _ignore = {"highlightthickness", "highlightbackground",
                   "highlightcolor", "width", "height"}
        clean = {k: v for k, v in kw.items() if k not in _ignore}
        if clean:
            super().configure(**clean)

    config = configure
