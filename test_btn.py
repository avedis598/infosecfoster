import tkinter as tk

class FlatBtn(tk.Label):
    def __init__(self, parent, text="", command=None, bg=None, fg=None, font=None, padx=14, pady=8, **kw):
        self._bg = bg or "#313131"
        self._fg = fg or "#ffffff"
        self._hover_bg = "#444444"
        
        self.command = command or (lambda: None)
        self.state = kw.pop("state", "normal")
        
        for _k in ("activebackground", "activeforeground", "disabledforeground", 
                   "highlightthickness", "highlightbackground", "highlightcolor", 
                   "relief", "bd", "borderwidth"):
            kw.pop(_k, None)
            
        super().__init__(
            parent, text=text, bg=self._bg, fg=self._fg, padx=padx, pady=pady, cursor="hand2", **kw
        )

    def configure(self, **kw):
        print(f"Inside FlatBtn.configure BEFORE pop: kw = {kw}")
        if "command" in kw:
            self.command = kw.pop("command") or (lambda: None)
            
        if "state" in kw:
            self.state = kw.pop("state")
            if self.state == "disabled":
                kw["fg"] = "#a3a3a3"
            else:
                kw["fg"] = self._fg
                
        if "bg" in kw or "background" in kw:
            self._bg = kw.get("bg") or kw.get("background") or self._bg
            self._hover_bg = "#444444"
            kw["bg"] = self._bg
            
        print(f"Inside FlatBtn.configure AFTER pop: kw = {kw}")
        if kw:
            super().configure(**kw)

    config = configure

root = tk.Tk()
btn = FlatBtn(root, text="Test", command=lambda: print("test"))
btn.pack()
try:
    btn.config(text="New Text", bg="red", command=lambda: print("new command"))
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
