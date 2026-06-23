# Mark Those things up 🚀

A modern, dark-themed desktop application built with Python and Tkinter for multi-threaded batch conversion of documents into clean Markdown syntax. Powered by Microsoft's `markitdown` and Google's `magika` classification engine.

## Features ✨

* **Multi-Threaded Processing:** Convert large batches of files simultaneously without the UI freezing or locking up.
* **Wide Format Support:** Seamlessly converts PDF, DOCX, XLSX, PPTX, HTML, CSV, JSON, and XML.
* **Custom Output Paths:** Save generated `.md` files right next to their source files or route them all to a dedicated directory.
* **Minimalist Dark UI:** Clean, data-rich spreadsheet dashboard optimized for readability.

## Supported Formats 📂

| File Type | Extension |
| :--- | :--- |
| **Word Documents** | `.docx` |
| **PDF Documents** | `.pdf` |
| **Excel Sheets** | `.xlsx` / `.csv` |
| **PowerPoint Presentations** | `.pptx` |
| **Web Data** | `.html` / `.json` / `.xml` |

## Production Builds 📦

Windows standalone executables (`.exe`) are compiled automatically using GitHub Actions and PyInstaller. You can grab the latest standalone app from the **Releases** tab on the right side of this repository page—no Python installation required.