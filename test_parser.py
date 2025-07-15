import os
import json
import tkinter as tk
from tkinter import filedialog
from parser import *

# tests SDS upload

def run_parser(filepath):
    results = parse_sds_file(filepath)

    print("\n\n\n\n\nSDS Parsing Result:\n")
    print(json.dumps(results, indent=2))

    print("\nValid Hazard Matches from SDS:\n")
    valid_ghs = [
        entry for entry in results["ghs_from_sds"]
        if all([
            entry.get("original_text"),
            entry.get("match_score") is not None,
            entry.get("ghs_code"),
            entry.get("category"),
            entry.get("official_text")
        ])
    ]
    print(json.dumps(valid_ghs, indent=2))
    return results


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
    results = run_parser(filepath)