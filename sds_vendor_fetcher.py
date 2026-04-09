
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



def find_sds_pdf_by_cas(cas):
    pdf = fetch_aaronchem_sds(cas)
    if pdf:
        return {
            "vendor": "AaronChem",
            "pdf_bytes": pdf,
            "source": "AaronChem"
        }

    pdf = fetch_sigma_sds(cas)
    if pdf:
        return {
            "vendor": "Millipore-Sigma",
            "pdf_bytes": pdf,
            "source": "Millipore-Sigma"
        }

    return {
        "vendor": None,
        "pdf_bytes": None,
        "source": None,
        "error": f"No SDS PDF found for CAS {cas} on AaronChem or Millipore-Sigma"
    }


