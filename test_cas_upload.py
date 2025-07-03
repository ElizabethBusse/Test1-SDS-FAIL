# if search by cas number:
#   1. fetcher_firefox -> create directory of SDSs
#   2. upload to parser.py and loop through all imported cas numbers

import os
from test_fetcher import test_fetch_cas, selected_dir
from test_parser import run_parser

# List of CAS numbers to process
# cas_list = ['64-19-7', '98327-87-8', '000-00-0']
cas_list = ['1245816-10-7', '1015484-22-6', '3734-67-6', '64-19-7']
# cas_list = ['3734-67-6']

for cas in cas_list:
    test_fetch_cas(cas)
    pdf_path = os.path.join(selected_dir, f"{cas}.pdf")
    if os.path.exists(pdf_path):
        print(f"Parsing {pdf_path}...")
        run_parser(pdf_path)
    else:
        print(f"SDS file for {cas} not found, skipping parser.")