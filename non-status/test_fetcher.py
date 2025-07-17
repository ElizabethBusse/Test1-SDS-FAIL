from status_fetcher_firefox import *

# tests cas number lookup

def test_fetch_cas(cas_number):
    # print("OLD FILE RAN-TEST-FETCHER")
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
            print(f"\nFailed to fetch SDS from both sources for {cas_number}")
            source = "None"
    return source

if __name__ == "__main__":
    test_cases = [
        '64-19-7',         # Should succeed on Sigma
        '98327-87-8',      # Should succeed on AaronChem
        '000-00-0',        # Should fail both
    ]

    for cas in test_cases:
        test_fetch_cas(cas)