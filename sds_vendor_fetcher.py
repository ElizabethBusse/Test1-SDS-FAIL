
import requests
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch_aaronchem_sds(cas):
    search_url = f"https://www.aaronchem.com/search?type=product&q={cas}"
    print(f"[AARONCHEM] Searching {search_url}")

    try:
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        print(f"[AARONCHEM] Status: {r.status_code}")
        print(f"[AARONCHEM] Response length: {len(r.text)}")
    except Exception as e:
        print(f"[AARONCHEM] Request failed: {e}")
        return None

    if not r.ok:
        print("[AARONCHEM] Response not OK")
        return None

    pdf_links = re.findall(r'https?://[^"\']+\.pdf', r.text, re.IGNORECASE)
    print(f"[AARONCHEM] Found {len(pdf_links)} PDF links")

    for link in pdf_links:
        print(f"[AARONCHEM] Checking PDF link: {link}")
        if "sds" in link.lower():
            try:
                pdf = requests.get(link, headers=HEADERS, timeout=15)
                print(f"[AARONCHEM] PDF status: {pdf.status_code}")
                print(f"[AARONCHEM] Content-Type: {pdf.headers.get('content-type')}")
                if pdf.ok and pdf.headers.get("content-type", "").lower().startswith("application/pdf"):
                    print(f"[AARONCHEM] ✅ SDS PDF downloaded ({len(pdf.content)} bytes)")
                    return pdf.content
            except Exception as e:
                print(f"[AARONCHEM] PDF fetch failed: {e}")
                continue

    print("[AARONCHEM] ❌ No SDS PDF found")
    return None




def fetch_sigma_sds(cas):
    search_url = f"https://www.sigmaaldrich.com/US/en/search/{cas}?focus=products"
    print(f"[SIGMA] Searching {search_url}")

    try:
        r = requests.get(search_url, headers=HEADERS, timeout=10)
        print(f"[SIGMA] Status: {r.status_code}")
        print(f"[SIGMA] Response length: {len(r.text)}")
    except Exception as e:
        print(f"[SIGMA] Request failed: {e}")
        return None

    if not r.ok:
        print("[SIGMA] Response not OK")
        return None

    pdf_links = re.findall(r'https?://[^"\']+\.pdf', r.text, re.IGNORECASE)
    print(f"[SIGMA] Found {len(pdf_links)} PDF links")

    for link in pdf_links:
        print(f"[SIGMA] Checking PDF link: {link}")
        if "sds" in link.lower():
            try:
                pdf = requests.get(link, headers=HEADERS, timeout=15)
                print(f"[SIGMA] PDF status: {pdf.status_code}")
                print(f"[SIGMA] Content-Type: {pdf.headers.get('content-type')}")
                if pdf.ok and pdf.headers.get("content-type", "").lower().startswith("application/pdf"):
                    print(f"[SIGMA] ✅ SDS PDF downloaded ({len(pdf.content)} bytes)")
                    return pdf.content
            except Exception as e:
                print(f"[SIGMA] PDF fetch failed: {e}")
                continue

    print("[SIGMA] ❌ No SDS PDF found")
    return None





def cas_reader(cas_list):
    from sds_vendor_fetcher import find_sds_pdf_by_cas

    if not cas_list:
        return {
            "cas_number": None,
            "source": None,
            "error": "No CAS provided"
        }

    cas = cas_list[0]

    vendor_result = find_sds_pdf_by_cas(cas)

    if vendor_result.get("pdf_bytes"):
        pdf_bytes = vendor_result["pdf_bytes"]
        vendor = vendor_result["vendor"]

        text = streamlit_pdf_upload(pdf_bytes)

        return parse_sds_file(
            input_val=text,
            source=f"CAS Lookup ({vendor})"
        )

    return {
        "cas_number": cas,
        "source": None,
        "error": vendor_result.get("error")
    }
