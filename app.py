import os
import sys
import uuid
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from markitdown import MarkItDown


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ── Design tokens ──────────────────────────────────────────────────────────────
BG_BASE    = "#141414"   # window background
BG_SURFACE = "#1c1c1e"   # header / footer
BG_CARD    = "#242428"   # treeview rows
BG_ROW_ALT = "#1f1f23"   # alternating row tint
BG_HOVER   = "#2a2a2f"   # hover / selected row
BORDER     = "#2e2e32"   # subtle separators

ACCENT     = "#f5a623"   # amber — primary action, progress fill
ACCENT_DIM = "#c4841a"   # pressed state
FG_PRIMARY = "#f0f0f0"   # main text
FG_MUTED   = "#888891"   # secondary / placeholder text
FG_HEADER  = "#555560"   # column headers

SUCCESS    = "#3dd68c"   # ✓ converted
ERROR      = "#f2635f"   # ✕ failed
WORKING    = "#5ba4ff"   # converting…

# File-type badge colours  (bg, fg)
TYPE_COLORS = {
    "PDF":  ("#5a1e1e", "#f2635f"),
    "DOCX": ("#1a3a5c", "#5ba4ff"),
    "DOC":  ("#1a3a5c", "#5ba4ff"),
    "PPTX": ("#3d2210", "#f5a623"),
    "PPT":  ("#3d2210", "#f5a623"),
    "XLSX": ("#1a3a28", "#3dd68c"),
    "XLS":  ("#1a3a28", "#3dd68c"),
    "HTML": ("#2d1f4a", "#a78bfa"),
    "CSV":  ("#1a3a28", "#3dd68c"),
    "JSON": ("#2d2710", "#fcd34d"),
    "XML":  ("#2d2710", "#fcd34d"),
    "TXT":  ("#252528", "#888891"),
}
TYPE_DEFAULT = ("#252528", "#888891")

FONT_UI    = ("Helvetica Neue", 10)
FONT_BOLD  = ("Helvetica Neue", 10, "bold")
FONT_TITLE = ("Helvetica Neue", 13, "bold")
FONT_MONO  = ("Menlo", 9)
FONT_SMALL = ("Helvetica Neue", 9)
# ───────────────────────────────────────────────────────────────────────────────


class MarkThoseThingsUpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mark Those Things Up")
        self.root.geometry("860x560")
        self.root.minsize(700, 440)
        self.root.configure(bg=BG_BASE)

        self.file_queue     = {}    # { uuid_str: file_item_dict }
        self.output_directory = None
        self.is_processing  = False

        self.converter = MarkItDown()

        self.logo_img = None
        try:
            self.logo_img = tk.PhotoImage(file=resource_path("logo.png"))
            self.root.iconphoto(False, self.logo_img)
        except Exception as e:
            self._log(f"Logo asset failed to load: {e}")

        self._apply_styles()
        self._build_ui()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _log(self, message: str):
        try:
            log_path = os.path.join(os.path.dirname(sys.executable), "app.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception:
            pass

    def _ui(self, fn, *args, **kwargs):
        """Schedule fn on the main thread."""
        self.root.after(0, lambda: fn(*args, **kwargs))

    def _btn(self, parent, text, command, style="secondary", **kw):
        """Factory for flat, borderless buttons with two visual styles."""
        if style == "primary":
            bg, fg, abg = ACCENT, "#141414", ACCENT_DIM
            font = FONT_BOLD
        elif style == "ghost":
            bg, fg, abg = BG_BASE, FG_MUTED, BG_HOVER
            font = FONT_SMALL
        else:  # secondary
            bg, fg, abg = BG_CARD, FG_PRIMARY, BG_HOVER
            font = FONT_UI
        return tk.Button(
            parent, text=text, command=command,
            bg=bg, fg=fg, activebackground=abg, activeforeground=fg,
            bd=0, relief="flat", font=font,
            padx=kw.pop("padx", 14), pady=kw.pop("pady", 7),
            cursor="hand2", **kw,
        )

    # ── Styles ─────────────────────────────────────────────────────────────────

    def _apply_styles(self):
        s = ttk.Style()
        s.theme_use("default")

        s.configure("Queue.Treeview",
            background=BG_CARD,
            foreground=FG_PRIMARY,
            fieldbackground=BG_CARD,
            rowheight=34,
            font=FONT_UI,
            borderwidth=0,
            relief="flat",
        )
        s.configure("Queue.Treeview.Heading",
            background=BG_SURFACE,
            foreground=FG_HEADER,
            font=("Helvetica Neue", 9, "bold"),
            relief="flat",
            padding=(8, 6),
        )
        s.map("Queue.Treeview",
            background=[("selected", BG_HOVER)],
            foreground=[("selected", FG_PRIMARY)],
        )
        s.map("Queue.Treeview.Heading",
            background=[("active", BG_CARD)],
        )
        s.layout("Queue.Treeview", [
            ("Queue.Treeview.treearea", {"sticky": "nswe"}),
        ])

        s.configure("Accent.Horizontal.TProgressbar",
            thickness=3,
            troughcolor=BG_CARD,
            background=ACCENT,
            relief="flat",
            borderwidth=0,
        )

        s.configure("Slim.Vertical.TScrollbar",
            background=BG_CARD,
            troughcolor=BG_SURFACE,
            borderwidth=0,
            relief="flat",
            arrowsize=0,
        )
        s.map("Slim.Vertical.TScrollbar",
            background=[("active", BG_HOVER)],
        )

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_toolbar()
        self._build_destination_row()
        self._build_queue_table()
        self._build_footer()

    def _build_header(self):
        hdr = tk.Frame(self.root, bg=BG_SURFACE, height=48)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)

        # Left: logo + title
        left = tk.Frame(hdr, bg=BG_SURFACE)
        left.pack(side=tk.LEFT, padx=20, fill=tk.Y)

        if self.logo_img:
            tk.Label(left, image=self.logo_img, bg=BG_SURFACE).pack(
                side=tk.LEFT, pady=10, padx=(0, 8))

        tk.Label(left, text="Mark Those Things Up",
                 font=FONT_TITLE, bg=BG_SURFACE, fg=FG_PRIMARY).pack(
            side=tk.LEFT, pady=10)

        # Right: format badge legend
        right = tk.Frame(hdr, bg=BG_SURFACE)
        right.pack(side=tk.RIGHT, padx=20, fill=tk.Y)

        for fmt in ("PDF", "DOCX", "XLSX", "PPTX", "TXT"):
            bg, fg = TYPE_COLORS.get(fmt, TYPE_DEFAULT)
            tk.Label(right, text=fmt, font=("Helvetica Neue", 8, "bold"),
                     bg=bg, fg=fg, padx=5, pady=2).pack(
                side=tk.LEFT, padx=2, pady=14)

        # Bottom border line
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

    def _build_toolbar(self):
        bar = tk.Frame(self.root, bg=BG_BASE, padx=20, pady=12)
        bar.pack(fill=tk.X)

        self.btn_add = self._btn(bar, "+ Add Files", self.add_files, style="primary")
        self.btn_add.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_remove = self._btn(bar, "Remove", self.remove_selected)
        self.btn_remove.pack(side=tk.LEFT, padx=(0, 6))

        self.btn_clear = self._btn(bar, "Clear All", self.clear_queue, style="ghost")
        self.btn_clear.pack(side=tk.LEFT)

        # File count badge (right side)
        self.lbl_count = tk.Label(bar, text="0 files",
                                  font=FONT_SMALL, bg=BG_BASE, fg=FG_MUTED)
        self.lbl_count.pack(side=tk.RIGHT)

    def _build_destination_row(self):
        row = tk.Frame(self.root, bg=BG_BASE, padx=20, pady=0)
        row.pack(fill=tk.X)

        tk.Label(row, text="OUTPUT", font=("Helvetica Neue", 8, "bold"),
                 bg=BG_BASE, fg=FG_HEADER).pack(side=tk.LEFT, padx=(0, 10))

        self.dest_var = tk.IntVar(value=0)

        def _radio(text, value):
            return tk.Radiobutton(
                row, text=text, variable=self.dest_var, value=value,
                bg=BG_BASE, fg=FG_MUTED, selectcolor=BG_BASE,
                activebackground=BG_BASE, activeforeground=FG_PRIMARY,
                font=FONT_SMALL, bd=0, cursor="hand2",
                command=self.toggle_dest_mode,
            )

        _radio("Next to source", 0).pack(side=tk.LEFT, padx=(0, 4))
        _radio("Custom folder…", 1).pack(side=tk.LEFT)

        self.lbl_dest_path = tk.Label(row, text="",
                                      font=FONT_MONO, bg=BG_BASE, fg=ACCENT)
        self.lbl_dest_path.pack(side=tk.LEFT, padx=(10, 0))

        # Separator
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X, padx=0)

    def _build_queue_table(self):
        wrapper = tk.Frame(self.root, bg=BG_BASE)
        wrapper.pack(fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(wrapper, style="Slim.Vertical.TScrollbar")
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            wrapper,
            style="Queue.Treeview",
            columns=("name", "type", "size", "status"),
            show="headings",
            yscrollcommand=sb.set,
            selectmode="extended",
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self.tree.yview)

        self.tree.heading("name",   text="FILE",   anchor=tk.W)
        self.tree.heading("type",   text="FORMAT", anchor=tk.CENTER)
        self.tree.heading("size",   text="SIZE",   anchor=tk.CENTER)
        self.tree.heading("status", text="STATUS", anchor=tk.CENTER)

        self.tree.column("name",   width=400, minwidth=200, anchor=tk.W,      stretch=True)
        self.tree.column("type",   width=80,  minwidth=60,  anchor=tk.CENTER, stretch=False)
        self.tree.column("size",   width=90,  minwidth=60,  anchor=tk.CENTER, stretch=False)
        self.tree.column("status", width=130, minwidth=90,  anchor=tk.CENTER, stretch=False)

        # Alternating row tags
        self.tree.tag_configure("odd",      background=BG_CARD)
        self.tree.tag_configure("even",     background=BG_ROW_ALT)
        self.tree.tag_configure("success",  foreground=SUCCESS)
        self.tree.tag_configure("error",    foreground=ERROR)
        self.tree.tag_configure("working",  foreground=WORKING)

        # Empty-state overlay
        self.empty_lbl = tk.Label(
            wrapper,
            text="Drop files here  ·  or click  + Add Files",
            font=("Helvetica Neue", 12),
            bg=BG_CARD,
            fg=FG_HEADER,
        )
        self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # Context menu
        self.ctx = tk.Menu(self.root, tearoff=0,
                           bg=BG_CARD, fg=FG_PRIMARY,
                           activebackground=BG_HOVER,
                           activeforeground=FG_PRIMARY,
                           bd=0, relief="flat")
        self.ctx.add_command(label="Remove selected", command=self.remove_selected)
        self.ctx.add_separator()
        self.ctx.add_command(label="Clear all", command=self.clear_queue)
        self.tree.bind("<Button-2>", self._show_ctx)   # macOS right-click
        self.tree.bind("<Button-3>", self._show_ctx)   # Windows/Linux

    def _build_footer(self):
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill=tk.X)

        foot = tk.Frame(self.root, bg=BG_SURFACE, padx=20, pady=14)
        foot.pack(fill=tk.X, side=tk.BOTTOM)

        # Progress bar (full width, above status line)
        self.progress_bar = ttk.Progressbar(
            foot, style="Accent.Horizontal.TProgressbar", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Status label (left) + Start button (right)
        bottom = tk.Frame(foot, bg=BG_SURFACE)
        bottom.pack(fill=tk.X)

        self.status_lbl = tk.Label(
            bottom, text="Ready",
            font=FONT_SMALL, bg=BG_SURFACE, fg=FG_MUTED,
            anchor=tk.W,
        )
        self.status_lbl.pack(side=tk.LEFT)

        self.btn_start = self._btn(
            bottom, "Convert →", self.start_batch_thread,
            style="primary", state=tk.DISABLED,
        )
        self.btn_start.pack(side=tk.RIGHT)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _refresh_empty_state(self):
        if self.file_queue:
            self.empty_lbl.place_forget()
        else:
            self.empty_lbl.place(relx=0.5, rely=0.5, anchor="center")

    def _update_count(self):
        n = len(self.file_queue)
        self.lbl_count.config(text=f"{n} file{'s' if n != 1 else ''}")

    def _row_tag(self, index: int, status: str) -> tuple:
        base = "odd" if index % 2 == 0 else "even"
        if "Success" in status:  return (base, "success")
        if "Failed"  in status:  return (base, "error")
        if "Convert" in status:  return (base, "working")
        return (base,)

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _show_ctx(self, event):
        if self.is_processing:
            return
        try:
            self.ctx.tk_popup(event.x_root, event.y_root)
        finally:
            self.ctx.grab_release()

    def toggle_dest_mode(self):
        if self.dest_var.get() == 1:
            chosen = filedialog.askdirectory(title="Select output folder")
            if chosen:
                self.output_directory = chosen
                short = chosen if len(chosen) <= 40 else "…" + chosen[-38:]
                self.lbl_dest_path.config(text=short)
                self.status_lbl.config(text=f"Output → {os.path.basename(chosen)}", fg=ACCENT)
            else:
                self.dest_var.set(0)
                self.output_directory = None
                self.lbl_dest_path.config(text="")
        else:
            self.output_directory = None
            self.lbl_dest_path.config(text="")

    def add_files(self):
        if self.is_processing:
            return

        files = filedialog.askopenfilenames(
            title="Select files to convert",
            filetypes=[("Supported documents",
                        "*.pdf *.docx *.pptx *.xlsx *.html *.csv *.json *.xml *.txt")],
        )

        existing_paths = {item["path"] for item in self.file_queue.values()}
        added = 0

        for file_path in files:
            if file_path in existing_paths:
                continue

            filename = os.path.basename(file_path)
            _, ext = os.path.splitext(filename)
            fmt = ext.upper().replace(".", "")

            try:
                size_bytes = os.path.getsize(file_path)
                size_str = (f"{size_bytes / 1024:.1f} KB"
                            if size_bytes < 1_048_576
                            else f"{size_bytes / 1_048_576:.1f} MB")
            except Exception:
                size_str = "—"

            item_id = str(uuid.uuid4())
            file_item = {
                "id": item_id, "path": file_path,
                "name": filename, "type": fmt,
                "size": size_str, "status": "Ready",
            }
            self.file_queue[item_id] = file_item

            idx = len(self.file_queue) - 1
            self.tree.insert("", tk.END, iid=item_id,
                             values=(filename, fmt, size_str, "Ready"),
                             tags=self._row_tag(idx, "Ready"))
            added += 1

        if added:
            self.btn_start.config(state=tk.NORMAL)
            self._update_count()
            self._refresh_empty_state()
            self.status_lbl.config(
                text=f"Added {added} file{'s' if added != 1 else ''}.", fg=FG_MUTED)

    def remove_selected(self):
        if self.is_processing:
            return
        for iid in self.tree.selection():
            self.tree.delete(iid)
            self.file_queue.pop(iid, None)
        self._update_count()
        self._refresh_empty_state()
        if not self.file_queue:
            self.btn_start.config(state=tk.DISABLED)
            self.status_lbl.config(text="Ready", fg=FG_MUTED)
        else:
            self.status_lbl.config(
                text=f"{len(self.file_queue)} file(s) in queue.", fg=FG_MUTED)

    def clear_queue(self):
        if self.is_processing:
            return
        self.file_queue.clear()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self.btn_start.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self._update_count()
        self._refresh_empty_state()
        self.status_lbl.config(text="Ready", fg=FG_MUTED)

    def start_batch_thread(self):
        if self.is_processing or not self.file_queue:
            return
        self.is_processing = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_add.config(state=tk.DISABLED)
        self.btn_remove.config(state=tk.DISABLED)
        self.btn_clear.config(state=tk.DISABLED)
        threading.Thread(target=self._process_batch, daemon=True).start()

    # ── Batch processing (worker thread) ───────────────────────────────────────

    def _process_batch(self):
        items = list(self.file_queue.values())
        total = len(items)
        errors = []

        self._ui(self.progress_bar.config, maximum=total, value=0)

        for i, item in enumerate(items):
            iid = item["id"]
            idx = i  # capture for tag

            self._ui(self.tree.item, iid,
                     values=(item["name"], item["type"], item["size"], "Converting…"),
                     tags=self._row_tag(idx, "Converting"))
            self._ui(self.status_lbl.config,
                     text=f"{i + 1} / {total}  —  {item['name']}", fg=WORKING)

            try:
                result = self.converter.convert(item["path"])

                if self.dest_var.get() == 0 or not self.output_directory:
                    base, _ = os.path.splitext(item["path"])
                    out = base + ".md"
                else:
                    base_name = os.path.splitext(item["name"])[0]
                    out = os.path.join(self.output_directory, base_name + ".md")

                with open(out, "w", encoding="utf-8") as f:
                    f.write(result.text_content)

                self._ui(self.tree.item, iid,
                         values=(item["name"], item["type"], item["size"], "✓ Done"),
                         tags=self._row_tag(idx, "Success"))
            except Exception as e:
                msg = str(e)
                self._log(f"Error converting '{item['name']}': {msg}")
                errors.append((item["name"], msg))
                self._ui(self.tree.item, iid,
                         values=(item["name"], item["type"], item["size"], "✕ Failed"),
                         tags=self._row_tag(idx, "Failed"))

            self._ui(self.progress_bar.config, value=i + 1)

        self._ui(self._finish_batch, total, errors)

    def _finish_batch(self, total: int, errors: list):
        self.is_processing = False
        self.btn_add.config(state=tk.NORMAL)
        self.btn_remove.config(state=tk.NORMAL)
        self.btn_clear.config(state=tk.NORMAL)

        ok = total - len(errors)
        if errors:
            self.status_lbl.config(
                text=f"{ok}/{total} converted  ·  {len(errors)} failed", fg=ERROR)
            lines = "\n".join(f"• {n}: {m}" for n, m in errors)
            messagebox.showwarning(
                "Conversion complete — with errors",
                f"{ok} of {total} files converted.\n\nFailed:\n{lines}",
            )
        else:
            self.status_lbl.config(
                text=f"All {total} files converted successfully.", fg=SUCCESS)
            messagebox.showinfo("Done", f"All {total} files converted to Markdown.")


if __name__ == "__main__":
    root = tk.Tk()
    app = MarkThoseThingsUpApp(root)
    root.mainloop()