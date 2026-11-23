"""URL Classifier GUI - paste many URLs, analyse them in parallel, see clean / suspicious / phishing / malware."""
import concurrent.futures as cf
import csv
import os
import queue
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from urllib.parse import quote, urlsplit

import analyzer

BG, PANEL, FG, MUTED, ACCENT = "#14182a", "#1d2238", "#e8ebf7", "#8e95b5", "#4f8cff"
COLORS = {"clean": "#3fae5a", "suspicious": "#f0a524", "phishing": "#e8453c", "malware": "#b44bd6",
          "invalid": "#8e95b5", "pending": "#8e95b5", "skipped": "#8e95b5", "unknown": "#8e95b5"}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("URL Classifier - clean / phishing / malware")
        self.geometry("1100x760")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self.results = {}          # iid -> result dict
        self.queue = queue.Queue()          # worker -> GUI messages: ("a", iid, res|None) / ("v", iid, vt_out|None)
        self.vt_queue = queue.Queue()       # GUI -> VirusTotal thread: (iid, kind, target)
        self.vt_on = self.vt_only_bad = False
        self.vt_quit = threading.Event()
        self.stop_evt = threading.Event()
        self.total = self.done = 0
        self.running = False
        self._style()
        self._build()
        counts = analyzer.FEEDS.counts
        self.status.set("Feeds loaded: %s" % (", ".join("%d %s" % (n, c) for c, n in counts.items())
                                              or "none - press 'Update feeds' for blocklist matching"))

    # ------------------------------------------------------------------ UI
    def _style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL)
        s.configure("TLabel", background=BG, foreground=FG)
        s.configure("TCheckbutton", background=BG, foreground=FG)
        s.configure("TButton", background=PANEL, foreground=FG, padding=6, borderwidth=0)
        s.map("TButton", background=[("active", "#2a3150")])
        s.configure("Accent.TButton", background=ACCENT, foreground="white", font=("Segoe UI", 10, "bold"))
        s.map("Accent.TButton", background=[("active", "#6fa0ff"), ("disabled", "#34406b")])
        s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG, rowheight=24, borderwidth=0)
        s.configure("Treeview.Heading", background="#262d4a", foreground=FG, relief="flat", font=("Segoe UI", 9, "bold"))
        s.map("Treeview", background=[("selected", "#34406b")])
        s.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL, borderwidth=0)

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=12, pady=(12, 6))
        ttk.Label(top, text="Paste URLs or file hashes (MD5/SHA-1/SHA-256), one per line - defanged hxxp / [.] is fine:").pack(anchor="w")
        box = tk.Frame(top, bg=PANEL)
        box.pack(fill="x", pady=4)
        self.input = tk.Text(box, height=7, bg=PANEL, fg=FG, insertbackground=FG, relief="flat",
                             font=("Consolas", 10), undo=True, wrap="none")
        sb = ttk.Scrollbar(box, command=self.input.yview)
        self.input.configure(yscrollcommand=sb.set)
        self.input.pack(side="left", fill="x", expand=True)
        sb.pack(side="right", fill="y")

        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=12, pady=4)
        self.btn_go = ttk.Button(bar, text="Analyze", style="Accent.TButton", command=self.start)
        self.btn_go.pack(side="left")
        self.btn_stop = ttk.Button(bar, text="Stop", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=4)
        ttk.Button(bar, text="Load file…", command=self.load_file).pack(side="left", padx=4)
        ttk.Button(bar, text="Clear", command=self.clear).pack(side="left")
        ttk.Button(bar, text="Export CSV…", command=self.export).pack(side="left", padx=4)
        ttk.Button(bar, text="Update feeds", command=self.update_feeds).pack(side="left")

        ttk.Label(bar, text="Parallel workers:").pack(side="left", padx=(18, 4))
        self.workers = tk.IntVar(value=24)
        ttk.Spinbox(bar, from_=1, to=64, width=4, textvariable=self.workers).pack(side="left")
        self.opt_fetch, self.opt_rdap = tk.BooleanVar(value=True), tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Contact URLs to read page text (off = passive)", variable=self.opt_fetch).pack(side="left", padx=(14, 0))
        ttk.Checkbutton(bar, text="Domain age (RDAP)", variable=self.opt_rdap).pack(side="left", padx=8)

        vt = tk.Frame(self, bg=BG)
        vt.pack(fill="x", padx=12, pady=(0, 2))
        self.opt_vt, self.opt_vt_bad = tk.BooleanVar(value=False), tk.BooleanVar(value=True)
        ttk.Checkbutton(vt, text="VirusTotal IOC lookup", variable=self.opt_vt).pack(side="left")
        ttk.Label(vt, text="API key (session only, never saved):").pack(side="left", padx=(10, 4))
        self.vt_key = tk.StringVar(value=os.environ.get("VT_API_KEY", ""))
        tk.Entry(vt, textvariable=self.vt_key, show="•", width=26, bg=PANEL, fg=FG, insertbackground=FG,
                 relief="flat").pack(side="left")
        ttk.Checkbutton(vt, text="only non-clean URLs", variable=self.opt_vt_bad).pack(side="left", padx=8)
        ttk.Label(vt, text="requests/min:").pack(side="left")
        self.vt_rpm = tk.IntVar(value=4)
        ttk.Spinbox(vt, from_=1, to=1000, width=5, textvariable=self.vt_rpm).pack(side="left", padx=4)
        ttk.Label(vt, text="(free key = 4)", foreground=MUTED).pack(side="left")

        prog = tk.Frame(self, bg=BG)
        prog.pack(fill="x", padx=12, pady=(6, 2))
        self.progress = ttk.Progressbar(prog, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True)
        self.summary = tk.Label(prog, text="", bg=BG, fg=FG, font=("Segoe UI", 10, "bold"))
        self.summary.pack(side="left", padx=10)

        paned = ttk.PanedWindow(self, orient="vertical")
        paned.pack(fill="both", expand=True, padx=12, pady=6)
        tf = tk.Frame(paned, bg=BG)
        cols = ("verdict", "score", "url", "signal", "time")
        self.tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse")
        for c, w, t in (("verdict", 90, "Verdict"), ("score", 55, "Score"), ("url", 430, "URL"),
                        ("signal", 380, "Top signal"), ("time", 55, "Sec")):
            self.tree.heading(c, text=t, command=lambda c=c: self.sort_by(c))
            self.tree.column(c, width=w, anchor="w" if c in ("url", "signal") else "center", stretch=c in ("url", "signal"))
        vs = ttk.Scrollbar(tf, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        for v, col in COLORS.items():
            self.tree.tag_configure(v, foreground=col)
        self.tree.bind("<<TreeviewSelect>>", self.show_details)
        self.tree.bind("<Button-3>", self.context_menu)
        paned.add(tf, weight=3)

        self.details = tk.Text(paned, height=9, bg=PANEL, fg=FG, relief="flat", font=("Consolas", 10),
                               wrap="word", state="disabled")
        for v, col in COLORS.items():
            self.details.tag_configure(v, foreground=col, font=("Consolas", 10, "bold"))
        self.details.tag_configure("muted", foreground=MUTED)
        paned.add(self.details, weight=1)

        self.status = tk.StringVar()
        tk.Label(self, textvariable=self.status, bg=BG, fg=MUTED, anchor="w").pack(fill="x", padx=12, pady=(0, 8))
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Copy defanged URL", command=lambda: self.copy(defanged=True))
        self.menu.add_command(label="Copy URL", command=lambda: self.copy(defanged=False))

    # ------------------------------------------------------------------ actions
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text / CSV", "*.txt *.csv *.list"), ("All files", "*.*")])
        if path:
            with open(path, encoding="utf-8", errors="ignore") as f:
                self.input.insert("end", ("\n" if self.input.get("1.0", "end").strip() else "") + f.read().strip())

    def clear(self):
        if self.running:
            return
        self.tree.delete(*self.tree.get_children())
        self.results.clear()
        self.input.delete("1.0", "end")
        self.summary.config(text="")
        self.progress["value"] = 0
        self._set_details("")

    def update_feeds(self):
        self.status.set("Downloading feeds…")

        def work():
            out = analyzer.FEEDS.update()
            self.after(0, lambda: self.status.set("Feeds: " + "; ".join(out) + " | loaded " +
                                                  ", ".join("%d %s" % (n, c) for c, n in analyzer.FEEDS.counts.items())))
        threading.Thread(target=work, daemon=True).start()

    def start(self):
        if self.running:
            return
        urls, seen = [], set()
        for line in self.input.get("1.0", "end").splitlines():
            line = line.strip().split(",")[0].strip() if line.count(",") and "://" not in line.split(",")[0] else line.strip()
            if line and not line.startswith("#") and line not in seen:
                seen.add(line)
                urls.append(line)
        if not urls:
            messagebox.showinfo("URL Classifier", "Paste at least one URL or file hash first.")
            return
        key = self.vt_key.get().strip()
        self.vt_on = self.opt_vt.get() and bool(key)
        self.vt_only_bad = self.opt_vt_bad.get()
        note = ""
        if self.opt_vt.get() and not key:
            note = " VirusTotal is ticked but no API key was given - lookups skipped."
        self.tree.delete(*self.tree.get_children())
        self.results.clear()
        self._set_details("")
        self.stop_evt = threading.Event()
        self.vt_quit = threading.Event()
        self.vt_queue = queue.Queue()
        self.total, self.done, self.running = len(urls), 0, True
        self.progress.configure(maximum=self.total, value=0)
        self.btn_go.state(["disabled"])
        self.btn_stop.state(["!disabled"])
        items = []
        for i, u in enumerate(urls):
            iid = str(i)
            is_hash = bool(analyzer.HASH_RE.match(u))
            self.tree.insert("", "end", iid=iid, values=("queued", "", u, "hash lookup" if is_hash else "", ""), tags=("pending",))
            if is_hash:
                if self.vt_on:
                    self.vt_queue.put((iid, "hash", u))
                else:
                    res = {"input": u, "url": u, "final_url": u, "verdict": "unknown", "category": "", "score": 0,
                           "signals": [("generic", 0, "file hashes need a VirusTotal API key (tick the box and enter one)")],
                           "title": "", "status": None, "seconds": 0, "kind": "hash"}
                    self.queue.put(("a", iid, res))
            else:
                items.append((iid, u))
        opts = {"fetch": self.opt_fetch.get(), "rdap": self.opt_rdap.get()}
        n = max(1, min(64, int(self.workers.get() or 1)))
        if self.vt_on:
            analyzer.VT_LIMITER.set_rate(max(1, int(self.vt_rpm.get() or 4)))
            threading.Thread(target=self._vt_worker, args=(key, self.stop_evt, self.vt_quit, self.vt_queue), daemon=True).start()
        threading.Thread(target=self._run, args=(items, opts, n, self.stop_evt), daemon=True).start()
        self.status.set("Analyzing…" + note)
        self._update_summary()
        self.after(60, self._drain)

    def stop(self):
        self.stop_evt.set()
        self.btn_stop.state(["disabled"])
        self.status.set("Stopping… finishing URLs already in flight")

    def _run(self, items, opts, n, stop):
        def job(iid, raw):
            if stop.is_set():
                self.queue.put(("a", iid, None))
                return
            try:
                res = analyzer.analyze(raw, opts)
            except Exception as e:  # noqa: BLE001 - never let one URL kill the batch
                res = {"input": raw, "url": raw, "final_url": raw, "verdict": "invalid", "category": "", "score": 0,
                       "signals": [("generic", 0, "analysis error: %s" % e)], "title": "", "status": None, "seconds": 0}
            self.queue.put(("a", iid, res))
        with cf.ThreadPoolExecutor(max_workers=n) as ex:
            for iid, raw in items:
                ex.submit(job, iid, raw)

    def _vt_worker(self, key, stop, quit_evt, q):
        """Single thread, rate-limited: the VirusTotal quota is the bottleneck, not our workers."""
        while True:
            try:
                iid, kind, target = q.get(timeout=0.3)
            except queue.Empty:
                if quit_evt.is_set():
                    return
                continue
            if stop.is_set():
                self.queue.put(("v", iid, None))
                continue
            try:
                out = (analyzer.vt_lookup_hash if kind == "hash" else analyzer.vt_lookup_url)(target, key, stop)
            except Exception as e:  # noqa: BLE001
                out = {"signals": [], "note": "VirusTotal lookup error: %s" % e}
            out["kind"] = kind
            self.queue.put(("v", iid, out))

    def _refresh_row(self, iid):
        res = self.results[iid]
        top = next((s[2] for s in res["signals"] if s[1] > 0), "")
        if not top:
            top = next((s[2] for s in res["signals"] if s[1] == 0 and ("VirusTotal" in s[2] or res["verdict"] in ("invalid", "unknown"))), "")
        if not top and res["verdict"] == "clean":
            top = "no suspicious signals"
        self.tree.item(iid, values=(res["verdict"].upper(), res["score"], res["input"], top, res["seconds"]),
                       tags=(res["verdict"],))

    def _drain(self):
        try:
            while True:
                kind, iid, res = self.queue.get_nowait()
                if kind == "a":
                    if res is None:
                        self.done += 1
                        self.tree.item(iid, values=("skipped", "", self.tree.set(iid, "url"), "", ""), tags=("skipped",))
                        continue
                    self.results[iid] = res
                    self._refresh_row(iid)
                    wants_vt = self.vt_on and res["verdict"] != "invalid" and res.get("kind") != "hash" and \
                        (res["verdict"] != "clean" or not self.vt_only_bad)
                    if wants_vt:
                        self.tree.set(iid, "signal", "asking VirusTotal… | " + self.tree.set(iid, "signal"))
                        self.vt_queue.put((iid, "url", res["url"]))
                    else:
                        self.done += 1
                else:  # "v": VirusTotal answer (res is the lookup output)
                    self.done += 1
                    if res is None:
                        self.tree.set(iid, "signal", "VirusTotal skipped")
                        continue
                    cur = self.results.get(iid)
                    if cur is None:  # hash row: build its result from the lookup
                        raw = self.tree.set(iid, "url")
                        cur = self.results[iid] = {"input": raw, "url": raw, "final_url": raw, "verdict": "clean",
                                                   "category": "", "score": 0, "signals": [], "title": res.get("name") or "",
                                                   "status": None, "seconds": 0, "kind": "hash"}
                    sigs = list(res["signals"])
                    if res.get("note"):
                        sigs.append(("generic", 0, res["note"]))
                    analyzer.rescore(cur, sigs)
                    if res.get("sha256"):
                        cur["sha256"] = res["sha256"]
                    if cur.get("kind") == "hash" and not any(w != 0 for _, w, _ in cur["signals"]) and res.get("note"):
                        cur["verdict"] = "unknown"
                    self._refresh_row(iid)
                    if self.tree.selection() == (iid,):
                        self.show_details()
        except queue.Empty:
            pass
        self.progress["value"] = self.done
        self._update_summary()
        if self.done >= self.total:
            self.running = False
            self.vt_quit.set()
            self.btn_go.state(["!disabled"])
            self.btn_stop.state(["disabled"])
            self.status.set("Done: %d item(s) analysed." % len(self.results))
        else:
            self.after(80, self._drain)

    def _update_summary(self):
        c = {"clean": 0, "suspicious": 0, "phishing": 0, "malware": 0}
        for r in self.results.values():
            if r["verdict"] in c:
                c[r["verdict"]] += 1
        self.summary.config(text="%d/%d   clean %d · suspicious %d · phishing %d · malware %d" %
                            (self.done, self.total, c["clean"], c["suspicious"], c["phishing"], c["malware"]))

    # ------------------------------------------------------------------ details / misc
    def _set_details(self, text, tag=None):
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        if text:
            self.details.insert("end", text, tag)
        self.details.configure(state="disabled")

    def show_details(self, _=None):
        sel = self.tree.selection()
        r = self.results.get(sel[0]) if sel else None
        if not r:
            return
        d = self.details
        d.configure(state="normal")
        d.delete("1.0", "end")
        d.insert("end", "%s  (score %d/100)\n" % (r["verdict"].upper(), r["score"]), r["verdict"])
        d.insert("end", "URL:   %s\n" % r["input"], "muted")
        if r["final_url"] and r["final_url"] != r["url"]:
            d.insert("end", "Final: %s\n" % r["final_url"], "muted")
        if r["title"]:
            d.insert("end", "Title: %s\n" % r["title"][:150], "muted")
        if r.get("sha256"):
            d.insert("end", "Payload sha256 (IOC, not downloaded): %s\n" % r["sha256"], "muted")
        d.insert("end", "\nSignals:\n")
        for cat, w, text in r["signals"]:
            d.insert("end", "  %+4d  [%s] %s\n" % (w, cat, text))
        if not r["signals"]:
            d.insert("end", "  none\n")
        d.insert("end", "\nRight-click for VirusTotal / web-search links for this indicator.\n", "muted")
        d.configure(state="disabled")

    def sort_by(self, col):
        rows = [(self.tree.set(i, col), i) for i in self.tree.get_children()]
        numeric = col in ("score", "time")
        rows.sort(key=lambda t: float(t[0]) if numeric and t[0] not in ("",) else (t[0].lower() if not numeric else -1),
                  reverse=numeric and getattr(self, "_rev", True))
        if numeric:
            self._rev = not getattr(self, "_rev", True)
        for idx, (_, i) in enumerate(rows):
            self.tree.move(i, "", idx)

    def context_menu(self, ev):
        iid = self.tree.identify_row(ev.y)
        if not iid:
            return
        self.tree.selection_set(iid)
        item = self.tree.set(iid, "url")
        is_hash = bool(analyzer.HASH_RE.match(item))
        norm = item if is_hash else (analyzer.normalize(item)[0] or item)
        host = "" if is_hash else (urlsplit(norm).hostname or "")
        sha = (self.results.get(iid) or {}).get("sha256")
        m = tk.Menu(self, tearoff=0)
        m.add_command(label="Copy defanged URL", command=lambda: self.copy(defanged=True))
        m.add_command(label="Copy URL", command=lambda: self.copy(defanged=False))
        m.add_separator()
        m.add_command(label="Open on VirusTotal (in your browser)", command=lambda: webbrowser.open(analyzer.vt_gui_url(norm)))
        if sha:
            m.add_command(label="Open payload sha256 on VirusTotal", command=lambda: webbrowser.open(analyzer.vt_gui_url(sha)))
        q = item if is_hash else host
        m.add_command(label="Search the web for this IOC (blogs, reports)",
                      command=lambda: webbrowser.open("https://duckduckgo.com/?q=" + quote('"%s" malware OR phishing OR IOC' % (sha or q))))
        m.tk_popup(ev.x_root, ev.y_root)

    def copy(self, defanged):
        sel = self.tree.selection()
        if sel:
            u = self.tree.set(sel[0], "url")
            self.clipboard_clear()
            self.clipboard_append(analyzer.defang(u) if defanged else u)

    def export(self):
        if not self.results:
            messagebox.showinfo("URL Classifier", "Nothing to export yet.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["url", "final_url", "verdict", "score", "title", "signals"])
            for iid in self.tree.get_children():
                r = self.results.get(iid)
                if r:
                    w.writerow([r["input"], r["final_url"], r["verdict"], r["score"], r["title"],
                                " | ".join("%+d %s" % (s[1], s[2]) for s in r["signals"])])
        self.status.set("Exported to " + path)


if __name__ == "__main__":
    App().mainloop()
