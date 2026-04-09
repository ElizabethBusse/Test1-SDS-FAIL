
import requests
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def fetch_aaronchem_sds(cas):
    search_url = f"https://www.aaronchem.com/search?type=product&q={cas}"

    try:
        r = requests.get(search_url, headers=HEADERS, timeout=10)
    except Exception:
        return None

    if not r.ok:
        return None

    pdf_links = re.findall(r'https?://[^"\']+\.pdf', r.text, re.IGNORECASE)

    for link in pdf_links:
        if "sds" in link.lower():
            try:
                pdf = requests.get(link, headers=HEADERS, timeout=15)
                if pdf.ok and pdf.headers.get(
                    "content-type", ""
                ).lower().startswith("application/pdf"):
                    return pdf.content
            except Exception:
                continue

    return None


def fetch_sigma_sds(cas):
    search_url = (
        f"https://www.sigmaaldrich.com/US/en/search/{cas}"
        "?focus=products"
    )

    try:
        r = requests.get(search_url, headers=HEADERS, timeout=10)
    except Exception:
        return None

    if not r.ok:
        return None

    pdf_links = re.findall(r'https?://[^"\']+\.pdf', r.text, re.IGNORECASE)

    for link in pdf_links:
        if "sds" in link.lower():
            try:
                pdf = requests.get(link, headers=HEADERS, timeout=15)
                if pdf.ok and pdf.headers.get(
                    "content-type", ""
                ).lower().startswith("application/pdf"):
                    return pdf.content
            except Exception:
                continue

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
