# if search by cas number:
#   1. fetcher_firefox -> create directory of SDSs
#   2. upload to parser.py and loop through all imported cas numbers

import os
from status_test_fetcher import test_fetch_cas, selected_dir
from test_parser import run_parser
import streamlit as st

# List of CAS numbers to process
cas_list = ['64-19-7', '3734-67-6']
# cas_list = ['1245816-10-7', '1015484-22-6', '3734-67-6', '64-19-7']
# cas_list = ['3734-67-6']

def search_by_cas(cas_list):
    source = []
    results = []
    for cas in cas_list:
        with st.spinner(f"Searching for CAS Number: {cas}..."):
            source1 = test_fetch_cas(cas)
            source.append(source1)
            print("source", source)
            pdf_path = os.path.join(selected_dir, f"{cas}.pdf")
            if os.path.exists(pdf_path):
                print(f"Parsing {pdf_path}...")
                result1 = run_parser(pdf_path, source=source1, cas=cas)
                results.append(result1)
                print(f"PASSING IN SOURCE1: {source1}")
            else:
                print(f"SDS file for {cas} not found, skipping parser.")
    # st.rerun()
    return results

if __name__ == "__main__":
    results = search_by_cas(cas_list)
    print(results)