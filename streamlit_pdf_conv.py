
from parser import streamlit_pdf_upload, parse_sds_file


def sds_upload(pdf_file):
    text = streamlit_pdf_upload(pdf_file)
    return parse_sds_file(input_val=text, source="PDF Upload")


def cas_reader(cas_list):
    results = []

    try:
        from sds_vendor_fetcher import find_sds_pdf_by_cas
    except Exception as e:
        return [{
            "error": "Failed to import sds_vendor_fetcher",
            "details": str(e),
            "cas_list": cas_list
        }]

    for cas in cas_list:
        try:
            vendor_result = find_sds_pdf_by_cas(cas)
        except Exception as e:
            results.append({
                "cas_number": cas,
                "status": "VENDOR LOOKUP ERROR",
                "error": str(e)
            })
            continue

        if vendor_result is None:
            results.append({
                "cas_number": cas,
                "status": "NOT FOUND",
                "vendor": None,
                "sds_url": None,
                "pdf_byte_size": 0
            })
            continue

        try:
            vendor = vendor_result.get("vendor")
            url = vendor_result.get("url")
            pdf_bytes = vendor_result.get("pdf_bytes")
            byte_size = vendor_result.get("byte_size")

            diagnostic = {
                "cas_number": cas,
                "status": "FOUND",
                "vendor": vendor,
                "sds_url": url,
                "pdf_byte_size": byte_size
            }

            text = streamlit_pdf_upload(pdf_bytes)

            if not text or len(text.strip()) < 50:
                diagnostic["parse_status"] = "PDF DOWNLOADED BUT TEXT EXTRACTION FAILED"
                results.append(diagnostic)
                continue

            parsed = parse_sds_file(
                input_val=text,
                source=f"CAS Lookup ({vendor})"
            )

            parsed.update(diagnostic)
            results.append(parsed)

        except Exception as e:
            results.append({
                "cas_number": cas,
                "status": "PARSER ERROR",
                "error": str(e)
            })

    return results

