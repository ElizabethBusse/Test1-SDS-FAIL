
# streamlit_pdf_conv.py
from sds_vendor_fetcher import find_sds_pdf_by_cas
from parser import streamlit_pdf_upload
from test_parser import run_parser

def cas_reader(cas_list):
    """
    CAS-based SDS reader that mirrors manual PDF upload behavior.
    """
    results = []

    for cas in cas_list:
        pdf_bytes, vendor = find_sds_pdf_by_cas(cas)

        if pdf_bytes is None:
            results.append({
                "cas": cas,
                "error": "SDS not found from AaronChem or Millipore-Sigma",
                "source": None
            })
            continue

        # ✅ EXACT SAME PIPELINE AS MANUAL UPLOAD
        text = streamlit_pdf_upload(pdf_bytes)
        parsed = run_parser(input_val=text)

        parsed["source"] = vendor
        results.append(parsed)

    return results


