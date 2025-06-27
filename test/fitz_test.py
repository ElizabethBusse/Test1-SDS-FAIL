import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    full_text = ""

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        print(f"--- Page {page_num} ---")
        print(text)
        full_text += text + "\n"

    doc.close()
    return full_text

# Launch file picker (Finder)
root = tk.Tk()
root.withdraw()  # Hide the root window
file_path = filedialog.askopenfilename(
    title="Select a PDF file",
    filetypes=[("PDF files", "*.pdf")]
)

if file_path:
    print(f"Selected: {file_path}")
    pdf_text = extract_text_from_pdf(file_path)
    # Optional: Save extracted text
    with open("extracted_text.txt", "w", encoding="utf-8") as f:
        f.write(pdf_text)
else:
    print("No file selected.")
