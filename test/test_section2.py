from parser import *
import tkinter as tk
from tkinter import filedialog
import os

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()

    print("Please select an SDS PDF file")
    filepath = filedialog.askopenfilename(
        title="Select SDS PDF",
        filetypes=[("PDF files", "*.pdf")]
    )

    if not filepath:
        print("No file selected. Exiting")
        exit()

    print(f"File selected: {os.path.basename(filepath)}")
    text = extract_text_from_pdf(filepath)
    matches = other_hazards(text)
    # print(matches)