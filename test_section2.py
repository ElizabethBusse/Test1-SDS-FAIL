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
    cas_info = extract_best_guess_cas(text)
    if isinstance(cas_info["cas"], str):
        print(cas_info["cas"])
    elif isinstance(cas_info["cas"], list):
        print(cas_info["cas"][0])
        print(cas_info["cas"])