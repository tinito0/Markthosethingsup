import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from markitdown import MarkItDown

class MarkItDownApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MarkItDown Converter")
        self.root.geometry("520x360")
        self.root.configure(bg="#121212")
        self.root.resizable(False, False)
        
        self.selected_file = None
        # Initialize Microsoft's MarkItDown converter
        self.converter = MarkItDown()
        
        self.setup_ui()

    def setup_ui(self):
        # App Header
        title_label = tk.Label(
            self.root, 
            text="MarkItDown Document Converter", 
            font=("Segoe UI", 16, "bold"), 
            bg="#121212", 
            fg="#ffffff"
        )
        title_label.pack(pady=(25, 5))
        
        subtitle_label = tk.Label(
            self.root, 
            text="Convert PDF, DOCX, XLSX, PPTX, HTML, and more to Markdown", 
            font=("Segoe UI", 9), 
            bg="#121212", 
            fg="#888888"
        )
        subtitle_label.pack(pady=(0, 20))

        # File display container
        self.file_label = tk.Label(
            self.root, 
            text="Drag files here or click 'Browse File' to start", 
            font=("Segoe UI", 10, "italic"), 
            bg="#1e1e1e", 
            fg="#666666",
            wraplength=440,
            justify="center",
            width=50,
            height=4,
            relief="flat"
        )
        self.file_label.pack(pady=15)

        # Actions Button Frame
        btn_frame = tk.Frame(self.root, bg="#121212")
        btn_frame.pack(pady=20)

        # Browse Button
        self.browse_btn = tk.Button(
            btn_frame, 
            text="Browse File", 
            command=self.browse_file,
            bg="#2d2d2d", 
            fg="#ffffff", 
            activebackground="#3e3e42",
            activeforeground="#ffffff",
            bd=0, 
            padx=18, 
            pady=8,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2"
        )
        self.browse_btn.pack(side=tk.LEFT, padx=10)

        # Convert Button
        self.convert_btn = tk.Button(
            btn_frame, 
            text="Convert to .md", 
            command=self.convert_file,
            bg="#007acc", 
            fg="#ffffff", 
            activebackground="#0062a3",
            activeforeground="#ffffff",
            bd=0, 
            padx=18, 
            pady=8,
            font=("Segoe UI", 10, "bold"),
            state=tk.DISABLED,
            cursor="hand2"
        )
        self.convert_btn.pack(side=tk.LEFT, padx=10)

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Document for Conversion",
            filetypes=[
                ("All Supported Files", "*.pdf *.docx *.pptx *.xlsx *.html *.csv *.json *.xml"),
                ("PDF Documents", "*.pdf"),
                ("Word Documents", "*.docx"),
                ("PowerPoint Presentations", "*.pptx"),
                ("Excel Sheets", "*.xlsx"),
                ("Text/Web Data", "*.html *.csv *.json *.xml"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.selected_file = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=filename, fg="#ffffff", bg="#1e1e1e")
            self.convert_btn.config(state=tk.NORMAL)

    def convert_file(self):
        if not self.selected_file:
            return
        
        # Generate target save path mirroring the input directory
        base_path, _ = os.path.splitext(self.selected_file)
        output_md_path = base_path + ".md"
        
        try:
            self.file_label.config(text="Processing conversion...", fg="#007acc")
            self.root.update_idletasks()
            
            # Perform library conversion
            result = self.converter.convert(self.selected_file)
            
            # Write out markdown payload
            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write(result.text_content)
                
            messagebox.showinfo("Success", f"Markdown successfully generated at:\n{output_md_path}")
            self.file_label.config(text=f"Saved: {os.path.basename(output_md_path)}", fg="#4ec9b0")
        except Exception as e:
            messagebox.showerror("Conversion Error", f"Failed to translate document:\n{str(e)}")
            self.file_label.config(text="Conversion failed.", fg="#f44336")

if __name__ == "__main__":
    root = tk.Tk()
    app = MarkItDownApp(root)
    root.mainloop()