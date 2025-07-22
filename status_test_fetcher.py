from status_fetcher_firefox import *
import streamlit as st

# tests cas number lookup

def test_fetch_cas(cas_number):
    # print("RUNNING ON STATUS FILE")
    print(f"Searching for CAS number: {cas_number}")
    print(f"\n\nTesting CAS: {cas_number}")
    success = fetch_sds_sigma_aldrich(cas_number, selected_dir)
    if success:
        print(f"\nFetched from Sigma-Aldrich: {cas_number}")
        source = "Sigma-Aldrich"
        return source
    else:
        print(f"\nSigma-Aldrich failed for {cas_number}. Trying AaronChem...")

        success = fetch_sds_aaron_chem(cas_number, selected_dir)
        if success:
            source = "AaronChem"
            print(f"\nFetched from AaronChem: {cas_number}")
        else:
            st.warning(f"\nFailed to fetch SDS from both sources for {cas_number}")
            source = "None"
    return source