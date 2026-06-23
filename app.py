import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from markitdown import MarkItDown

class BatchMarkItDownApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MarkItDown - Bulk Production Suite")
        self.root.geometry("800x550")
        self.root.configure(bg="#1e1e1e")
        
        # Core data tracking
        self.file_queue = []  # Elements: {"id": i, "path": "...", "status": "Pending", "size": "..."}
        self.output_directory = None
        self.is_processing = False
        self.converter = MarkItDown()
        
        # Apply premium UI styling
        self.apply_styles()
        self.setup_ui()

    def apply_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
        
        # Configure Table/Treeview Custom Styling
        self.style.configure("Treeview", 
            background="#252526", 
            foreground="#ffffff", 
            fieldbackground="#252526", 
            rowheight=30,
            font=("Segoe UI", 10)
        )
        self.style.configure("Treeview.Heading", 
            background="#2d2d2d", 
            foreground="#aaaaaa", 
            font=("Segoe UI", 10, "bold"),
            relief="flat"
        )
        self.style.map("Treeview", background=[("selected", "#004b87")])
        self.style.map("Treeview.Heading", background=[("active", "#3e3e42")])
        
        # Configure Progress Bar Styling
        self.style.configure("Modern.Horizontal.TProgressbar", 
            thickness=8, 
            troughcolor="#2d2d2d", 
            background="#007acc", 
            relief="flat"
        )

    def setup_ui(self):
        # 1. Top Control Bar Frame
        top_frame = tk.Frame(self.root, bg="#1a1a1a", height=60)
        top_frame.pack(fill=tk.X, side=tk.TOP)
        top_frame.pack_propagate(False)
        
        title_label = tk.Label(top_frame, text="MarkItDown Studio", font=("Segoe UI", 14, "bold"), bg="#1a1a1a", fg="#ffffff")
        title_label.pack(side=tk.LEFT, padx=20)
        
        # 2. Main Dashboard Layout Area
        main_container = tk.Frame(self.root, bg="#1e1e1e", padx=20, pady=15)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Toolbar actions grid
        toolbar = tk.Frame(main_container, bg="#1e1e1e")
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        self.btn_add = tk.Button(toolbar, text="+ Add Files", command=self.add_files, bg="#007acc", fg="#ffffff", bd=0, padx=12, pady=6, font=("Segoe UI", 9, "bold"), activebackground="#0062a3", activeforeground="#ffffff", cursor="hand2")
        self.btn_add.pack(side=tk.LEFT, padx=(0, 8))
        
        self.btn_clear = tk.Button(toolbar, text="Clear Queue", command=self.clear_queue, bg="#2d2d2d", fg="#ffffff", bd=0, padx=12, pady=6, font=("Segoe UI", 9), activebackground="#3e3e42", activeforeground="#ffffff", cursor="hand2")
        self.btn_clear.pack(side=tk.LEFT, padx=8)
        
        # Output directory destination choice control
        self.dest_var = tk.IntVar(value=0) # 0 = same directory, 1 = custom destination
        tk.Radiobutton(toolbar, text="Save next to source files", variable=self.dest_var, value=0, bg="#1e1e1e", fg="#bbbbbb", selectcolor="#1e1e1e", activebackground="#1e1e1e", activeforeground="#ffffff", font=("Segoe UI", 9), command=self.toggle_dest_mode).pack(side=tk.RIGHT, padx=10)
        tk.Radiobutton(toolbar, text="Custom Folder...", variable=self.dest_var, value=1, bg="#1e1e1e", fg="#bbbbbb", selectcolor="#1e1e1e", activebackground="#1e1e1e", activeforeground="#ffffff", font=("Segoe UI", 9), command=self.toggle_dest_mode).pack(side=tk.RIGHT)
        
        # 3. Central Batch Queue Spreadsheet Grid (Treeview)
        grid_frame = tk.Frame(main_container, bg="#1e1e1e")
        grid_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(grid_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(grid_frame, columns=("name", "type", "size", "status"), show="headings", yscrollcommand=scrollbar.set)
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
        
        # 4. Footer Console Processing Panel
        footer_frame = tk.Frame(self.root, bg="#1a1a1a", padding=15)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.progress_bar = ttk.Progressbar(footer_frame, style="Modern.Horizontal.TProgressbar", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(0, 8))
        
        self.status_lbl = tk.Label(footer_frame, text="Queue empty. Ready to accept files.", font=("Segoe UI", 9), bg="#1a1a1a", fg="#888888")
        self.status_lbl.pack(side=tk.LEFT)
        
        self.btn_start = tk.Button(footer_frame, text="Start Batch Processing", command=self.start_batch_thread, bg="#4ec9b0", fg="#1a1a1a", bd=0, padx=20, pady=8, font=("Segoe UI", 10, "bold"), activebackground="#3eb399", activeforeground="#1a1a1a", state=tk.DISABLED, cursor="hand2")
        self.btn_start.pack(side=tk.RIGHT)

    def toggle_dest_mode(self):
        if self.dest_var.get() == 1:
            chosen = filedialog.askdirectory(title="Select Destination Directory")
            if chosen:
                self.output_directory = chosen
                self.status_lbl.config(text=f"Destination locked to: {os.path.basename(chosen)}", fg="#4ec9b0")
            else:
                self.dest_var.set(0) # Reset if aborted
                self.output_directory = None

    def add_files(self):
        if self.is_processing: return
        
        files = filedialog.askopenfilenames(
            title="Select Documents for Batch Conversion",
            filetypes=[("Supported Documents", "*.pdf *.docx *.pptx *.xlsx *.html *.csv *.json *.xml *.txt")]
        )
        
        for file_path in files:
            # Prevent duplicate files in the list
            if any(item['path'] == file_path for item in self.file_queue):
                continue
                
            filename = os.path.basename(file_path)
            _, ext = os.path.splitext(filename)
            
            try:
                size_bytes = os.path.getsize(file_path)
                size_str = f"{size_bytes / 1024:.1f} KB" if size_bytes < 1024 * 1024 else f"{size_bytes / (1024 * 1024):.1f} MB"
            except:
                size_str = "Unknown"
                
            file_item = {
                "id": len(self.file_queue),
                "path": file_path,
                "name": filename,
                "type": ext.upper().replace(".", ""),
                "size": size_str,
                "status": "Ready"
            }
            
            self.file_queue.append(file_item)
            # Insert item natively into graphical grid
            self.tree.insert("", tk.END, iid=str(file_item["id"]), values=(file_item["name"], file_item["type"], file_item["size"], file_item["status"]))
            
        if self.file_queue:
            self.btn_start.config(state=tk.NORMAL)
            self.status_lbl.config(text=f"Loaded {len(self.file_queue)} files into the queue.", fg="#bbbbbb")

    def clear_queue(self):
        if self.is_processing: return
        self.file_queue.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.btn_start.config(state=tk.DISABLED)
        self.progress_bar["value"] = 0
        self.status_lbl.config(text="Queue cleared.", fg="#888888")

    def start_batch_thread(self):
        if self.is_processing or not self.file_queue: return
        
        self.is_processing = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_add.config(state=tk.DISABLED)
        self.btn_clear.config(state=tk.DISABLED)
        
        # Spin up execution on a separate safe worker thread
        threading.Thread(target=self.process_batch, daemon=True).start()

    def process_batch(self):
        total_files = len(self.file_queue)
        self.progress_bar["maximum"] = total_files
        self.progress_bar["value"] = 0
        
        for index, file_item in enumerate(self.file_queue):
            # Update grid to show running conversion thread state
            self.tree.item(str(file_item["id"]), values=(file_item["name"], file_item["type"], file_item["size"], "Converting..."))
            self.status_lbl.config(text=f"Processing {index + 1}/{total_files}: {file_item['name']}", fg="#007acc")
            self.root.update_idletasks()
            
            try:
                # Execute engine parser logic
                result = self.converter.convert(file_item["path"])
                
                # Determine output target path
                if self.dest_var.get() == 0 or not self.output_directory:
                    base, _ = os.path.splitext(file_item["path"])
                    output_path = base + ".md"
                else:
                    base_name = os.path.splitext(file_item["name"])[0]
                    output_path = os.path.join(self.output_directory, base_name + ".md")
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(result.text_content)
                    
                self.tree.item(str(file_item["id"]), values=(file_item["name"], file_item["type"], file_item["size"], "✓ Success"))
            except Exception as e:
                print(f"Error parsing file: {e}")
                self.tree.item(str(file_item["id"]), values=(file_item["name"], file_item["type"], file_item["size"], "✕ Failed"))
                
            self.progress_bar["value"] = index + 1
            self.root.update_idletasks()
            
        # UI Restoration Phase post batch run completion
        self.is_processing = False
        self.status_lbl.config(text=f"Batch job complete! Verified {total_files} files evaluated.", fg="#4ec9b0")
        self.btn_add.config(state=tk.NORMAL)
        self.btn_clear.config(state=tk.NORMAL)
        messagebox.showinfo("Batch Conversion Complete", f"Successfully evaluated and structured your batch pipeline.")

if __name__ == "__main__":
    root = tk.Tk()
    app = BatchMarkItDownApp(root)
    root.mainloop()