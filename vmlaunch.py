"""
VMlaunch — QEMU frontend with a phosphor-green terminal UI.
Matches the VMlaunch landing-page aesthetic exactly.

Requirements:
  Python 3.8+  ·  tkinter (stdlib)  ·  QEMU installed

  macOS  : brew install qemu
  Linux  : sudo apt install qemu-system-x86
  Windows: winget install QEMU  (or grab the .exe from qemu.org)

Run:
  python vmlaunch.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess, threading, shutil, os, sys, platform, json
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════════════════════════════════════
#  Colour palette  (mirrors the HTML :root variables)
# ══════════════════════════════════════════════════════════════════════════════

BG        = "#080c08"
SURFACE   = "#0d130d"
SURFACE2  = "#111811"
BORDER    = "#1a2e1a"
GREEN     = "#39ff5a"
GREEN_DIM = "#1a7a2e"
AMBER     = "#ffb830"
TEXT      = "#c8e8c8"
MUTED     = "#4a6a4a"
DIM       = "#2e4e2e"
RED       = "#f85149"
RED_DIM   = "#2d0e0c"

_OS = platform.system()
FONT_MONO = ("Consolas"    if _OS == "Windows" else
             "Menlo"       if _OS == "Darwin"  else
             "Ubuntu Mono")
FONT_UI   = ("Segoe UI"    if _OS == "Windows" else
             "SF Pro Text" if _OS == "Darwin"  else
             "Ubuntu")

# ══════════════════════════════════════════════════════════════════════════════
#  Settings persistence
# ══════════════════════════════════════════════════════════════════════════════

SETTINGS_FILE = Path.home() / ".vmlaunch.json"
DEFAULTS = dict(
    ram_mb=2048, cpus=2,
    enable_kvm=True, enable_usb=True, enable_audio=False,
    vga="std", net="user", qemu_path="", recent=[],
)

def load_cfg():
    try:
        if SETTINGS_FILE.exists():
            return {**DEFAULTS, **json.loads(SETTINGS_FILE.read_text())}
    except Exception:
        pass
    return DEFAULTS.copy()

def save_cfg(d):
    try:
        SETTINGS_FILE.write_text(json.dumps(d, indent=2))
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  QEMU helpers
# ══════════════════════════════════════════════════════════════════════════════

def find_qemu():
    for name in ("qemu-system-x86_64", "qemu-system-x86_64.exe"):
        p = shutil.which(name)
        if p:
            return p
    if _OS == "Windows":
        for c in [r"C:\Program Files\qemu\qemu-system-x86_64.exe",
                  r"C:\Program Files (x86)\qemu\qemu-system-x86_64.exe"]:
            if Path(c).exists():
                return c
    return None

def build_cmd(image, cfg, qemu):
    cmd = [qemu, "-m", str(cfg["ram_mb"]), "-smp", str(cfg["cpus"]),
           "-vga", cfg["vga"]]
    ext = Path(image).suffix.lower()
    if ext == ".iso":
        cmd += ["-cdrom", image, "-boot", "d"]
    else:
        fmt = {"img":"raw","qcow2":"qcow2","vmdk":"vmdk",
               "vdi":"vdi","vhd":"vpc","raw":"raw"}.get(ext.lstrip("."), "raw")
        cmd += ["-drive", f"file={image},format={fmt},if=virtio"]
    if cfg["enable_kvm"]:
        if _OS == "Linux":    cmd += ["-enable-kvm", "-cpu", "host"]
        elif _OS == "Darwin": cmd += ["-accel", "hvf", "-cpu", "host"]
        elif _OS == "Windows":cmd += ["-accel", "whpx,kernel-irqchip=off"]
    cmd += (["-netdev", "user,id=n0", "-device", "e1000,netdev=n0"]
            if cfg["net"] == "user" else ["-nic", "none"])
    if cfg["enable_usb"]:
        cmd += ["-usb", "-device", "usb-tablet"]
    if cfg["enable_audio"]:
        cmd += ["-audiodev", "pa,id=a0",
                "-device", "ich9-intel-hda",
                "-device", "hda-output,audiodev=a0"]
    return cmd

def human_size(path):
    try:
        b = os.path.getsize(path)
        for u in ["B","KB","MB","GB","TB"]:
            if b < 1024: return f"{b:.1f} {u}"
            b /= 1024
    except Exception:
        return "?"

# ══════════════════════════════════════════════════════════════════════════════
#  Widget helpers
# ══════════════════════════════════════════════════════════════════════════════

def _lighten(h, amt=25):
    r,g,b = int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)
    return f"#{min(255,r+amt):02x}{min(255,g+amt):02x}{min(255,b+amt):02x}"

def _btn(parent, text, cmd, primary=False, danger=False, small=False, fill_x=False):
    if primary:   bg, fg, hbg = GREEN,   BG,   _lighten(GREEN)
    elif danger:  bg, fg, hbg = RED_DIM, RED,  "#3d1210"
    else:         bg, fg, hbg = SURFACE2, MUTED, BORDER
    fs = 8 if small else 9
    b = tk.Button(parent, text=text, command=cmd,
                  bg=bg, fg=fg, activebackground=hbg, activeforeground=fg,
                  font=(FONT_MONO, fs, "bold" if primary else "normal"),
                  relief="flat", bd=0,
                  padx=12 if small else 20, pady=5 if small else 9,
                  cursor="hand2", highlightthickness=0)
    b.bind("<Enter>", lambda _: b.config(bg=hbg))
    b.bind("<Leave>", lambda _: b.config(bg=bg))
    if fill_x:
        b.pack(fill="x")
    return b

def _rule(parent, color=BORDER, pady=(0, 0)):
    tk.Frame(parent, bg=color, height=1).pack(fill="x", pady=pady)

def _section_hdr(parent, title):
    row = tk.Frame(parent, bg=BG)
    row.pack(fill="x", pady=(22, 8))
    tk.Label(row, text=title, bg=BG, fg=DIM,
             font=(FONT_MONO, 7), anchor="w").pack(side="left")
    tk.Frame(row, bg=BORDER, height=1).pack(
        side="left", fill="x", expand=True, padx=(10, 0), pady=5)

def _bordered(parent):
    return tk.Frame(parent, bg=SURFACE,
                    highlightbackground=BORDER, highlightthickness=1)

def _combo(parent, var, values, width=10):
    s = ttk.Style()
    s.theme_use("default")
    s.configure("V.TCombobox",
        fieldbackground=SURFACE2, background=SURFACE2,
        foreground=TEXT, selectbackground=GREEN_DIM,
        selectforeground=TEXT, arrowcolor=MUTED,
        borderwidth=0, relief="flat", padding=4)
    return ttk.Combobox(parent, textvariable=var, values=values,
                        state="readonly", font=(FONT_MONO, 8),
                        width=width, style="V.TCombobox")

# ══════════════════════════════════════════════════════════════════════════════
#  Toggle switch
# ══════════════════════════════════════════════════════════════════════════════

class Toggle(tk.Frame):
    W, H = 36, 18

    def __init__(self, parent, label, var, **kw):
        super().__init__(parent, bg=BG, cursor="hand2", **kw)
        self._var = var
        self._c = tk.Canvas(self, width=self.W, height=self.H,
                            bg=BG, highlightthickness=0)
        self._c.pack(side="left", padx=(0, 10), pady=2)
        self._lbl = tk.Label(self, text=label, bg=BG,
                             font=(FONT_MONO, 9), cursor="hand2")
        self._lbl.pack(side="left")
        self._refresh()
        for w in (self, self._c, self._lbl):
            w.bind("<Button-1>", self._toggle)

    def _refresh(self):
        on = self._var.get()
        self._c.delete("all")
        track = GREEN_DIM if on else SURFACE2
        thumb = GREEN     if on else MUTED
        r = self.H // 2
        self._c.create_rectangle(0, 2, self.W, self.H - 2,
                                  fill=track, outline=BORDER)
        x = self.W - r - 2 if on else r - 2
        self._c.create_oval(x - r + 4, 3, x + r - 2, self.H - 3,
                             fill=thumb, outline="")
        self._lbl.config(fg=TEXT if on else MUTED)

    def _toggle(self, _=None):
        self._var.set(not self._var.get())
        self._refresh()

# ══════════════════════════════════════════════════════════════════════════════
#  Slider row
# ══════════════════════════════════════════════════════════════════════════════

class SliderRow(tk.Frame):
    def __init__(self, parent, label, key, cfg, lo, hi, res, fmt, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._cfg, self._key, self._fmt = cfg, key, fmt
        self._var = tk.IntVar(value=cfg[key])

        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x")
        tk.Label(hdr, text=label, bg=BG, fg=MUTED,
                 font=(FONT_MONO, 9)).pack(side="left")
        self._vl = tk.Label(hdr, text=fmt(cfg[key]),
                             bg=BG, fg=AMBER, font=(FONT_MONO, 9))
        self._vl.pack(side="right")

        tk.Scale(self, variable=self._var, from_=lo, to=hi,
                 resolution=res, orient="horizontal",
                 command=self._on, bg=BG, fg=DIM,
                 troughcolor=SURFACE2, activebackground=GREEN,
                 highlightthickness=0, sliderrelief="flat",
                 bd=0, showvalue=False).pack(fill="x", pady=(3, 0))

    def _on(self, v):
        iv = int(float(v))
        self._cfg[self._key] = iv
        self._vl.config(text=self._fmt(iv))

# ══════════════════════════════════════════════════════════════════════════════
#  Application
# ══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.cfg    = load_cfg()
        self._procs = []
        self._img   = ""
        self.title("VMlaunch")
        self.configure(bg=BG)
        self.minsize(880, 580)
        self.geometry("1040, 700".replace(", ", "x"))
        self._icon()
        self._ui()
        self._detect_qemu()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _icon(self):
        try:
            img = tk.PhotoImage(width=16, height=16)
            for y in range(4, 12):
                for x in range(4, 12):
                    img.put(GREEN, (x, y))
            self.iconphoto(True, img)
        except Exception:
            pass

    # ── master layout ─────────────────────────────────────────────────────

    def _ui(self):
        self._titlebar()
        _rule(self)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)
        self._sidebar(body)
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")
        self._console(body)

    # ── title bar ─────────────────────────────────────────────────────────

    def _titlebar(self):
        bar = tk.Frame(self, bg=SURFACE)
        bar.pack(fill="x")
        row = tk.Frame(bar, bg=SURFACE)
        row.pack(fill="x", padx=24, pady=13)

        tk.Label(row, text="VM", bg=SURFACE, fg=GREEN,
                 font=(FONT_MONO, 15, "bold")).pack(side="left")
        tk.Label(row, text="launch", bg=SURFACE, fg=TEXT,
                 font=(FONT_MONO, 15)).pack(side="left", padx=(0, 16))
        tk.Label(row, text="// QEMU frontend", bg=SURFACE, fg=DIM,
                 font=(FONT_MONO, 8)).pack(side="left")

        tk.Label(row, text=f"  {_OS}  ", bg=SURFACE2, fg=DIM,
                 font=(FONT_MONO, 7), padx=8, pady=4).pack(side="right", padx=(8, 0))

        self._badge_var = tk.StringVar(value="  detecting QEMU…  ")
        self._badge = tk.Label(row, textvariable=self._badge_var,
                                bg=SURFACE2, fg=AMBER,
                                font=(FONT_MONO, 8), padx=10, pady=4)
        self._badge.pack(side="right")

    # ── sidebar with scroll ───────────────────────────────────────────────

    def _sidebar(self, parent):
        outer = tk.Frame(parent, bg=BG, width=350)
        outer.pack(side="left", fill="y")
        outer.pack_propagate(False)

        cvs = tk.Canvas(outer, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=cvs.yview,
                           bg=BG, troughcolor=SURFACE2, width=5)
        cvs.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        cvs.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(cvs, bg=BG)
        wid = cvs.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e):
            cvs.configure(scrollregion=cvs.bbox("all"))
            cvs.itemconfig(wid, width=cvs.winfo_width())
        inner.bind("<Configure>", _resize)
        cvs.bind("<Configure>", lambda e: cvs.itemconfig(wid, width=e.width))

        # mousewheel scroll
        def _scroll(e):
            delta = -1 * (e.delta // 120) if _OS == "Windows" else (
                    -1 if e.num == 4 else 1)
            cvs.yview_scroll(delta, "units")
        cvs.bind_all("<MouseWheel>", _scroll)
        cvs.bind_all("<Button-4>", _scroll)
        cvs.bind_all("<Button-5>", _scroll)

        pad = tk.Frame(inner, bg=BG)
        pad.pack(fill="both", expand=True, padx=22, pady=18)

        self._s_image(pad)
        self._s_hardware(pad)
        self._s_options(pad)
        self._s_display(pad)
        self._s_qemu(pad)
        self._s_actions(pad)

    # ── sidebar sections ──────────────────────────────────────────────────

    def _s_image(self, p):
        _section_hdr(p, "// DISK IMAGE")
        box = _bordered(p)
        box.pack(fill="x")

        self._img_lbl = tk.Label(box, text="No image selected",
                                  bg=SURFACE, fg=MUTED,
                                  font=(FONT_MONO, 9),
                                  anchor="w", padx=12, pady=8,
                                  wraplength=270, justify="left")
        self._img_lbl.pack(fill="x")

        self._img_meta = tk.Label(box, text="",
                                   bg=SURFACE, fg=DIM,
                                   font=(FONT_MONO, 7),
                                   anchor="w", padx=12)
        self._img_meta.pack(fill="x")

        br = tk.Frame(box, bg=SURFACE)
        br.pack(fill="x", padx=10, pady=8)
        _btn(br, "Browse…",  self._browse,       small=True).pack(side="left")
        _btn(br, "✕ Clear",  self._clear_img,    small=True).pack(side="left", padx=(6,0))

        # recent
        recent = [r for r in self.cfg.get("recent",[]) if Path(r).exists()]
        self.cfg["recent"] = recent
        if recent:
            _section_hdr(p, "// RECENT")
            self._recent_var = tk.StringVar()
            cb = _combo(p, self._recent_var, recent, width=32)
            cb.pack(fill="x", pady=(4, 0))
            cb.bind("<<ComboboxSelected>>", self._on_recent)

    def _s_hardware(self, p):
        _section_hdr(p, "// HARDWARE")
        SliderRow(p, "RAM", "ram_mb", self.cfg, 256, 16384, 256,
                  lambda v: f"{v} MB").pack(fill="x", pady=(4, 0))
        SliderRow(p, "CPU Cores", "cpus", self.cfg, 1, 16, 1,
                  lambda v: f"{v} core{'s' if v!=1 else ''}"
                  ).pack(fill="x", pady=(10, 0))

    def _s_options(self, p):
        _section_hdr(p, "// OPTIONS")
        self._kvm_v   = tk.BooleanVar(value=self.cfg["enable_kvm"])
        self._usb_v   = tk.BooleanVar(value=self.cfg["enable_usb"])
        self._audio_v = tk.BooleanVar(value=self.cfg["enable_audio"])
        Toggle(p, "Hardware acceleration  (KVM / HVF / WHPX)", self._kvm_v
               ).pack(anchor="w", pady=5)
        Toggle(p, "USB tablet  (smoother mouse)", self._usb_v
               ).pack(anchor="w", pady=5)
        Toggle(p, "Audio", self._audio_v).pack(anchor="w", pady=5)

    def _s_display(self, p):
        _section_hdr(p, "// DISPLAY  &  NETWORK")
        row = tk.Frame(p, bg=BG)
        row.pack(fill="x", pady=(4, 0))

        tk.Label(row, text="VGA", bg=BG, fg=MUTED,
                 font=(FONT_MONO, 8), width=5, anchor="w").pack(side="left")
        self._vga_v = tk.StringVar(value=self.cfg["vga"])
        _combo(row, self._vga_v,
               ["std","virtio","vmware","qxl","cirrus"],
               width=10).pack(side="left", padx=(4, 20))

        tk.Label(row, text="NET", bg=BG, fg=MUTED,
                 font=(FONT_MONO, 8), width=4, anchor="w").pack(side="left")
        self._net_v = tk.StringVar(value=self.cfg["net"])
        _combo(row, self._net_v, ["user","none"], width=7
               ).pack(side="left", padx=4)

    def _s_qemu(self, p):
        _section_hdr(p, "// QEMU PATH  (optional override)")
        self._qemu_v = tk.StringVar(value=self.cfg["qemu_path"])
        box = _bordered(p)
        box.pack(fill="x", pady=(4, 0))
        tk.Entry(box, textvariable=self._qemu_v,
                 bg=SURFACE, fg=MUTED, insertbackground=TEXT,
                 font=(FONT_MONO, 8), relief="flat", bd=0
                 ).pack(side="left", fill="x", expand=True, padx=10, pady=8)
        _btn(box, "…", self._browse_qemu, small=True
             ).pack(side="right", padx=6, pady=5)

    def _s_actions(self, p):
        tk.Frame(p, bg=BG, height=10).pack()
        _rule(p, pady=(4, 16))
        _btn(p, "▶   LAUNCH VM", self._launch, primary=True,
             fill_x=True).pack(fill="x", pady=(0, 8))
        _btn(p, "■   Stop All VMs", self._stop_all, danger=True,
             fill_x=True).pack(fill="x")
        tk.Frame(p, bg=BG, height=24).pack()

    # ── console ───────────────────────────────────────────────────────────

    def _console(self, parent):
        pane = tk.Frame(parent, bg=SURFACE)
        pane.pack(side="left", fill="both", expand=True)

        # header
        hdr = tk.Frame(pane, bg=SURFACE)
        hdr.pack(fill="x", padx=20, pady=12)
        tk.Label(hdr, text="// CONSOLE LOG", bg=SURFACE, fg=DIM,
                 font=(FONT_MONO, 8)).pack(side="left")
        _btn(hdr, "Clear", self._clear_log, small=True).pack(side="right")

        _rule(pane)

        # text widget
        wrap = tk.Frame(pane, bg=SURFACE)
        wrap.pack(fill="both", expand=True)

        self._log = tk.Text(
            wrap, bg=SURFACE, fg=MUTED,
            font=(FONT_MONO, 9),
            relief="flat", bd=0, wrap="word",
            state="disabled",
            padx=20, pady=14,
            selectbackground=GREEN_DIM,
            insertbackground=GREEN,
            spacing1=1, spacing3=4,
        )
        self._log.pack(side="left", fill="both", expand=True)

        sb = ttk.Scrollbar(wrap, orient="vertical", command=self._log.yview)
        sb.pack(side="right", fill="y")
        self._log["yscrollcommand"] = sb.set

        # tags
        self._log.tag_config("hd",   foreground=TEXT,
                              font=(FONT_MONO, 9, "bold"))
        self._log.tag_config("ok",   foreground=GREEN)
        self._log.tag_config("err",  foreground=RED)
        self._log.tag_config("cmd",  foreground=AMBER)
        self._log.tag_config("dim",  foreground=DIM)
        self._log.tag_config("info", foreground=MUTED)
        self._log.tag_config("warn", foreground=AMBER)

        # status bar
        _rule(pane)
        sb2 = tk.Frame(pane, bg=SURFACE2)
        sb2.pack(fill="x")
        self._status  = tk.StringVar(value="ready")
        self._vmcount = tk.StringVar(value="0 VMs running")
        tk.Label(sb2, textvariable=self._status,
                 bg=SURFACE2, fg=MUTED,
                 font=(FONT_MONO, 7), anchor="w",
                 padx=16, pady=5).pack(side="left")
        tk.Label(sb2, textvariable=self._vmcount,
                 bg=SURFACE2, fg=DIM,
                 font=(FONT_MONO, 7), anchor="e",
                 padx=16, pady=5).pack(side="right")

    # ── QEMU detection ────────────────────────────────────────────────────

    def _detect_qemu(self):
        def _check():
            override = self._qemu_v.get().strip()
            path = (override if override and Path(override).exists()
                    else find_qemu())
            if path:
                try:
                    r = subprocess.run([path, "--version"],
                                       capture_output=True, text=True, timeout=5)
                    ver = (r.stdout.splitlines()[0] if r.stdout else "QEMU found")
                    self.after(0, lambda: self._badge.config(
                        text=f"  ✓ {ver[:36]}  ",
                        fg=GREEN, bg=GREEN_DIM))
                    self.after(0, lambda: self._log_w(f"QEMU  {path}", "ok"))
                    self.after(0, lambda: self._log_w(ver, "dim"))
                except Exception as e:
                    self.after(0, lambda: self._no_qemu(str(e)))
            else:
                self.after(0, self._no_qemu)
        threading.Thread(target=_check, daemon=True).start()

    def _no_qemu(self, detail=""):
        self._badge.config(text="  ✗ QEMU not found  ", fg=RED, bg=RED_DIM)
        self._log_w("QEMU not found on PATH", "err")
        for line in ["  macOS  →  brew install qemu",
                     "  Linux  →  sudo apt install qemu-system-x86",
                     "  Win    →  winget install QEMU"]:
            self._log_w(line, "cmd")
        if detail:
            self._log_w(detail, "dim")

    # ── image pick ────────────────────────────────────────────────────────

    def _browse(self):
        p = filedialog.askopenfilename(
            title="Select Disk Image",
            filetypes=[
                ("Disk Images","*.iso *.img *.qcow2 *.vmdk *.vdi *.vhd *.raw"),
                ("ISO","*.iso"),("All","*.*"),
            ])
        if p:
            self._set_img(p)

    def _browse_qemu(self):
        p = filedialog.askopenfilename(
            title="QEMU binary",
            filetypes=[("Executable","*.exe *"),("All","*.*")])
        if p:
            self._qemu_v.set(p)

    def _set_img(self, path):
        self._img = path
        name = Path(path).name
        ext  = Path(path).suffix.upper().lstrip(".")
        self._img_lbl.config(text=f"📀  {name}", fg=TEXT)
        self._img_meta.config(text=f"{ext}  ·  {human_size(path)}", pady=5)
        r = self.cfg["recent"]
        if path in r: r.remove(path)
        r.insert(0, path)
        self.cfg["recent"] = r[:8]

    def _clear_img(self):
        self._img = ""
        self._img_lbl.config(text="No image selected", fg=MUTED)
        self._img_meta.config(text="", pady=0)

    def _on_recent(self, _):
        p = self._recent_var.get()
        if Path(p).exists():
            self._set_img(p)
        else:
            self._log_w(f"File missing: {p}", "warn")

    # ── launch / stop ─────────────────────────────────────────────────────

    def _launch(self):
        if not self._img:
            messagebox.showwarning("No Image",
                "Select a disk image or ISO first.")
            return
        if not Path(self._img).exists():
            messagebox.showerror("Not Found", f"File not found:\n{self._img}")
            return
        override = self._qemu_v.get().strip()
        qemu = (override if override and Path(override).exists()
                else find_qemu())
        if not qemu:
            messagebox.showerror("QEMU Missing",
                "QEMU not found.\nInstall it or set the path override.")
            return

        self.cfg.update(
            enable_kvm=self._kvm_v.get(),
            enable_usb=self._usb_v.get(),
            enable_audio=self._audio_v.get(),
            vga=self._vga_v.get(),
            net=self._net_v.get(),
            qemu_path=override,
        )
        save_cfg(self.cfg)

        cmd  = build_cmd(self._img, self.cfg, qemu)
        name = Path(self._img).name

        self._log_w("", "dim")
        self._log_w(f"── launching  {name} ──", "hd")
        self._log_w(f"ram {self.cfg['ram_mb']} MB  ·  "
                    f"cpu {self.cfg['cpus']}  ·  "
                    f"vga {self.cfg['vga']}  ·  "
                    f"accel {'on' if self.cfg['enable_kvm'] else 'off'}", "info")
        self._log_w("$ " + " ".join(cmd), "cmd")
        self._log_w("", "dim")
        self._status.set(f"starting  {name}…")

        def _run():
            try:
                proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True, bufsize=1)
                self._procs.append(proc)
                self.after(0, self._refresh_count)
                self.after(0, lambda: self._log_w(
                    f"✓ started  PID {proc.pid}", "ok"))
                self.after(0, lambda: self._status.set(
                    f"running  {name}  (PID {proc.pid})"))
                for line in proc.stdout:
                    l = line.rstrip()
                    if l:
                        self.after(0, lambda x=l: self._log_w(x, "dim"))
                proc.wait()
                self._procs = [p for p in self._procs if p.poll() is None]
                rc = proc.returncode
                self.after(0, lambda: self._log_w(
                    f"VM exited  (code {rc})",
                    "ok" if rc == 0 else "warn"))
                self.after(0, self._refresh_count)
                self.after(0, lambda: self._status.set(
                    f"exited  (code {rc})"))
            except Exception as e:
                self.after(0, lambda: self._log_w(f"error: {e}", "err"))
                self.after(0, lambda: self._status.set("error"))

        threading.Thread(target=_run, daemon=True).start()

    def _stop_all(self):
        alive = [p for p in self._procs if p.poll() is None]
        if not alive:
            self._log_w("No running VMs.", "warn"); return
        for p in alive:
            try:
                p.terminate()
                self._log_w(f"SIGTERM → PID {p.pid}", "warn")
            except Exception as e:
                self._log_w(str(e), "err")
        self._procs.clear()
        self._refresh_count()

    def _refresh_count(self):
        n = sum(1 for p in self._procs if p.poll() is None)
        self._vmcount.set(f"{n} VM{'s' if n!=1 else ''} running")

    # ── log ───────────────────────────────────────────────────────────────

    def _log_w(self, text, tag="info"):
        ts  = datetime.now().strftime("%H:%M:%S")
        msg = f"[{ts}]  {text}\n" if text.strip() else "\n"
        self._log.config(state="normal")
        self._log.insert("end", msg, tag)
        self._log.see("end")
        self._log.config(state="disabled")

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0","end")
        self._log.config(state="disabled")

    # ── close ─────────────────────────────────────────────────────────────

    def _on_close(self):
        alive = [p for p in self._procs if p.poll() is None]
        if alive:
            if not messagebox.askyesno("VMs Running",
                    f"{len(alive)} VM(s) still running. Quit anyway?",
                    icon="warning"):
                return
            for p in alive:
                try: p.terminate()
                except Exception: pass
        save_cfg(self.cfg)
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    app._log_w("VMlaunch ready", "ok")
    app._log_w(f"platform  {_OS} {platform.release()}", "dim")
    app._log_w(f"python    {sys.version.split()[0]}", "dim")
    app._log_w("", "dim")
    app._log_w("Select an ISO or disk image, then press LAUNCH VM.", "info")
    app.mainloop()
