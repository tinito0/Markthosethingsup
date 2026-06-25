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


class MarkThoseThingsUpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mark Those things up")
        self.root.geometry("800x580")
        self.root.configure(bg="#1e1e1e")

        # Core batch data tracking — keyed by UUID string
        self.file_queue = {}   # { uuid_str: file_item_dict }
        self.output_directory = None
        self.is_processing = False

        # Initialize MarkItDown converter engine
        self.converter = MarkItDown()

        # Load and bind application window icon using cross-platform PNG
        self.logo_img = None
        try:
            self.logo_img = tk.PhotoImage(file=resource_path("logo.png"))
            self.root.iconphoto(False, self.logo_img)
        except Exception as e:
            self._log(f"Logo asset failed to load: {e}")

        self.apply_styles()
        self.setup_ui()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log(self, message: str):
        """Write diagnostic messages to a log file next to the executable."""
        try:
            log_path = os.path.join(os.path.dirname(sys.executable), "app.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except Exception:
            pass  # Last-resort: silently ignore log failures

    def _ui(self, fn, *args, **kwargs):
        """Schedule a callable on the main thread via root.after()."""
        self.root.after(0, lambda: fn(*args, **kwargs))

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------

    def apply_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("default")

        self.style.configure(
            "Treeview",
            background="#252526",
            foreground="#ffffff",
            fieldbackground="#252526",
            rowheight=30,
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Treeview.Heading",
            background="#2d2d2d",
            foreground="#aaaaaa",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
        )
        self.style.map("Treeview", background=[("selected", "#004b87")])
        self.style.map("Treeview.Heading", background=[("active", "#3e3e42")])

        self.style.configure(
            "Modern.Horizontal.TProgressbar",
            thickness=8,
            troughcolor="#2d2d2d",
            background="#007acc",
            relief="flat",
        )

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def setup_ui(self):
        # 1. Top Bar Brand Panel
        top_frame = tk.Frame(self.root, bg="#1a1a1a", height=60)
        top_frame.pack(fill=tk.X, side=tk.TOP)
        top_frame.pack_propagate(False)

        if self.logo_img:
            logo_display = tk.Label(top_frame, image=self.logo_img, bg="#1a1a1a")
            logo_display.image = self.logo_img
            logo_display.pack(side=tk.LEFT, padx=(20, 0))

        title_label = tk.Label(
            top_frame,
            text="Mark Those things up",
            font=("Segoe UI", 14, "bold"),
            bg="#1a1a1a",
            fg="#ffffff",
        )
        title_label.pack(side=tk.LEFT, padx=10)

        # 2. Workspace Control Layout Container
        main_container = tk.Frame(self.root, bg="#1e1e1e", padx=20, pady=15)
        main_container.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(main_container, bg="#1e1e1e")
        toolbar.pack(fill=tk.X, pady=(0, 10))

        self.btn_add = tk.Button(
            toolbar,
            text="+ Add Files",
            command=self.add_files,
            bg="#007acc",
            fg="#ffffff",
            bd=0,
            padx=14,
            pady=6,
            font=("Segoe UI", 9, "bold"),
            activebackground="#0062a3",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_add.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_remove = tk.Button(
            toolbar,
            text="Remove Selected",
            command=self.remove_selected,
            bg="#2d2d2d",
            fg="#ffffff",
            bd=0,
            padx=14,
            pady=6,
            font=("Segoe UI", 9),
            activebackground="#3e3e42",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_remove.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_clear = tk.Button(
            toolbar,
            text="Clear Queue",
            command=self.clear_queue,
            bg="#2d2d2d",
            fg="#ffffff",
            bd=0,
            padx=14,
            pady=6,
            font=("Segoe UI", 9),
            activebackground="#3e3e42",
            activeforeground="#ffffff",
            cursor="hand2",
        )
        self.btn_clear.pack(side=tk.LEFT, padx=8)

        self.dest_var = tk.IntVar(value=0)
        tk.Radiobutton(
            toolbar,
            text="Save next to source files",
            variable=self.dest_var,
            value=0,
            bg="#1e1e1e",
            fg="#bbbbbb",
            selectcolor="#1e1e1e",
            activebackground="#1e1e1e",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            command=self.toggle_dest_mode,
        ).pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(
            toolbar,
            text="Custom Folder...",
            variable=self.dest_var,
            value=1,
            bg="#1e1e1e",
            fg="#bbbbbb",
            selectcolor="#1e1e1e",
            activebackground="#1e1e1e",
            activeforeground="#ffffff",
            font=("Segoe UI", 9),
            command=self.toggle_dest_mode,
        ).pack(side=tk.RIGHT)

        # 3. Main Operational Spreadsheet Grid Display
        grid_frame = tk.Frame(main_container, bg="#1e1e1e")
        grid_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(grid_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            grid_frame,
            columns=("name", "type", "size", "status"),
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="extended",
        )
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)

        self.tree.heading("name", text="FILE NAME", anchor=tk.W)
        self.tree.heading("type", text="TYPE", anchor=tk.CENTER)
        self.tree.heading("size", text="SIZE", anchor=tk.CENTER)
        self.tree.heading("status", text="STATUS", anchor=tk.CENTER)

        self.tree.column("name", width=380, anchor=tk.W)
        self.tree.column("type", width=80, anchor=tk.CENTER)
        self.tree.column("size", width=90, anchor=tk.CENTER)
        self.tree.column("status", width=120, anchor=tk.CENTER)

        # Right-click context menu for the treeview
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#2d2d2d", fg="#ffffff",
                                    activebackground="#004b87", activeforeground="#ffffff")
        self.context_menu.add_command(label="Remove Selected", command=self.remove_selected)
        self.tree.bind("<Button-3>", self._show_context_menu)

        # 4. Lower Processing Console Footer Panel
        footer_frame = tk.Frame(self.root, bg="#1a1a1a", padx=15, pady=15)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.progress_bar = ttk.Progressbar(
            footer_frame, style="Modern.Horizontal.TProgressbar", mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))

        self.status_lbl = tk.Label(
            footer_frame,
            text="Queue empty. Ready to parse content.",
            font=("Segoe UI", 9),
            bg="#1a1a1a",
            fg="#888888",
        )
        self.status_lbl.pack(side=tk.LEFT)

        self.btn_start = tk.Button(
            footer_frame,
            text="Start Batch Processing",
            command=self.start_batch_thread,
            bg="#4ec9b0",
            fg="#1a1a1a",
            bd=0,
            padx=20,
            pady=8,
            font=("Segoe UI", 10, "bold"),
            activebackground="#3eb399",
            activeforeground="#1a1a1a",
            state=tk.DISABLED,
            cursor="hand2",
        )
        self.btn_start.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _show_context_menu(self, event):
        if self.is_processing:
            return
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def toggle_dest_mode(self):
        if self.dest_var.get() == 1:
            chosen = filedialog.askdirectory(title="Select Destination Folder")
            if chosen:
                self.output_directory = chosen
                self.status_lbl.config(
                    text=f"Destination locked to: {os.path.basename(chosen)}",
                    fg="#4ec9b0",
                )
            else:
                self.dest_var.set(0)
                self.output_directory = None

    def add_files(self):
        if self.is_processing:
            return

        files = filedialog.askopenfilenames(
            title="Select Documents for Batch Conversion",
            filetypes=[
                (
                    "Supported Documents",
                    "*.pdf *.docx *.pptx *.xlsx *.html *.csv *.json *.xml *.txt",
                )
            ],
        )

        existing_paths = {item["path"] for item in self.file_queue.values()}

        for file_path in files:
            if file_path in existing_paths:
                continue

            filename = os.path.basename(file_path)
            _, ext = os.path.splitext(filename)

            try:
                size_bytes = os.path.getsize(file_path)
                size_str = (
                    f"{size_bytes / 1024:.1f} KB"
                    if size_bytes < 1024 * 1024
                    else f"{size_bytes / (1024 * 1024):.1f} MB"
                )
            except Exception:
                size_str = "Unknown"

            item_id = str(uuid.uuid4())
            file_item = {
                "id": item_id,
                "path": file_path,
                "name": filename,
                "type": ext.upper().replace(".", ""),
                "size": size_str,
                "status": "Ready",
            }

            self.file_queue[item_id] = file_item
            self.tree.insert(
                "",
                tk.END,
                iid=item_id,
                values=(file_item["name"], file_item["type"], file_item["size"], "Ready"),
            )

        if self.file_queue:
            self.btn_start.config(state=tk.NORMAL)
            self.status_lbl.config(
                text=f"Loaded {len(self.file_queue)} files into the queue.",
                fg="#bbbbbb",
            )

    def remove_selected(self):
        """Remove individually selected rows from the queue."""
        if self.is_processing:
            return
        selected = self.tree.selection()
        if not selected:
            return
        for iid in selected:
            self.tree.delete(iid)
            self.file_queue.pop(iid, None)
        count = len(self.file_queue)
        if count == 0:
            self.btn_start.config(state=tk.DISABLED)
            self.status_lbl.config(text="Queue cleared.", fg="#888888")
        else:
            self.status_lbl.config(
                text=f"{count} file(s) remaining in queue.", fg="#bbbbbb"
            )

    def clear_queue(self):
        if self.is_processing:
            return
        self.file_queue.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.btn_start.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.status_lbl.config(text="Queue cleared.", fg="#888888")

    def start_batch_thread(self):
        if self.is_processing or not self.file_queue:
            return

        self.is_processing = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_add.config(state=tk.DISABLED)
        self.btn_remove.config(state=tk.DISABLED)
        self.btn_clear.config(state=tk.DISABLED)

        threading.Thread(target=self.process_batch, daemon=True).start()

    # ------------------------------------------------------------------
    # Batch processing (runs on worker thread — all UI via self._ui())
    # ------------------------------------------------------------------

    def process_batch(self):
        items = list(self.file_queue.values())
        total_files = len(items)
        errors = []  # accumulate (filename, error_message) tuples

        self._ui(self.progress_bar.config, maximum=total_files, value=0)

        for index, file_item in enumerate(items):
            item_id = file_item["id"]

            self._ui(
                self.tree.item,
                item_id,
                values=(file_item["name"], file_item["type"], file_item["size"], "Converting..."),
            )
            self._ui(
                self.status_lbl.config,
                text=f"Processing {index + 1}/{total_files}: {file_item['name']}",
                fg="#007acc",
            )

            try:
                result = self.converter.convert(file_item["path"])

                if self.dest_var.get() == 0 or not self.output_directory:
                    base, _ = os.path.splitext(file_item["path"])
                    output_path = base + ".md"
                else:
                    base_name = os.path.splitext(file_item["name"])[0]
                    output_path = os.path.join(self.output_directory, base_name + ".md")

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result.text_content)

                self._ui(
                    self.tree.item,
                    item_id,
                    values=(file_item["name"], file_item["type"], file_item["size"], "✓ Success"),
                )
            except Exception as e:
                error_msg = str(e)
                self._log(f"Error converting '{file_item['name']}': {error_msg}")
                errors.append((file_item["name"], error_msg))
                self._ui(
                    self.tree.item,
                    item_id,
                    values=(file_item["name"], file_item["type"], file_item["size"], "✕ Failed"),
                )

            self._ui(self.progress_bar.config, value=index + 1)

        # Done — re-enable controls and surface results on the main thread
        self._ui(self._finish_batch, total_files, errors)

    def _finish_batch(self, total_files: int, errors: list):
        """Called on the main thread after process_batch completes."""
        self.is_processing = False
        self.btn_add.config(state=tk.NORMAL)
        self.btn_remove.config(state=tk.NORMAL)
        self.btn_clear.config(state=tk.NORMAL)

        success_count = total_files - len(errors)
        self.status_lbl.config(
            text=f"Done — {success_count}/{total_files} succeeded.",
            fg="#4ec9b0" if not errors else "#e5a550",
        )

        if errors:
            error_lines = "\n".join(f"• {name}: {msg}" for name, msg in errors)
            messagebox.showwarning(
                "Batch Complete — Some Files Failed",
                f"{success_count} of {total_files} files converted successfully.\n\n"
                f"Failed files:\n{error_lines}",
            )
        else:
            messagebox.showinfo(
                "Conversion Pipeline Complete",
                f"All {total_files} documents were converted successfully!",
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = MarkThoseThingsUpApp(root)
    root.mainloop()