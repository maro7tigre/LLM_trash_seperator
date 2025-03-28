"""
Trash Analyzer Application - Entry Point
A multimodal LLM application for analyzing trash images
"""

import tkinter as tk
from app import TrashAnalyzerApp

if __name__ == "__main__":
    root = tk.Tk()
    app = TrashAnalyzerApp(root)
    root.mainloop()