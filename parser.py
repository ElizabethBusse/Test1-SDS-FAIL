import fitz # from PyMuPDF
import re
import requests
from rapidfuzz import fuzz
from pdf2image import convert_from_path
import pytesseract
from functools import lru_cache
import traceback
import json

from haz_comp_full import *
from status_fetcher_firefox import fetch_nfpa_cameo, compare_nfpa_results

# for imported SDS documents

# NOTE: specified only for SigmaAldrich (Millipore Sigma) and AaronChem (no guarantees on functionality beyond)

# TODO: in cas number search -> if no SDS found on SA or AC, then allow single file upload

# TODO: section 3 does not work (pdf name extractor, may just be irrelevant)
#       show synonyms under chemical name on UI

# TODO: fails when no wifi (pubchem lookup fails)
#       indicate no pubchem ref + error


# SECTION 1. extract text from PDF with OCR fallback
def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text += page.get_text()
            if len(text.strip()) > 100: # if <100, likely file is not readable, program continues to OCR
                return text
    except Exception as e:
        print(f"Text extraction failed: {e}")

    # OCR fallback
    print("Using OCR fallback...")
    images = convert_from_path(pdf_path) # converts to image to use in pytesseract OCR
    for img in images:
        text += pytesseract.image_to_string(img)
    return text

def streamlit_pdf_upload(pdf_input):
    try:
        text = ''
        if hasattr(pdf_input, "read"):  # Streamlit uploaded_file is a file-like object
            pdf_bytes = pdf_input.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        elif isinstance(pdf_input, bytes):
            doc = fitz.open(stream=pdf_input, filetype="pdf")
        else:
            doc = fitz.open(pdf_input)  # fallback for file path

        with doc:
            for page in doc:
                text += page.get_text()
            if len(text.strip()) > 100:
                return text
    except Exception as e:
        print(f"Text extraction failed: {e}")

    # OCR fallback
    print("Using OCR fallback...")
    try:
        if hasattr(pdf_input, "read"):
            # Reopen bytes since previous read() may have consumed the stream
            pdf_input.seek(0)
            images = convert_from_path(pdf_input.name)  # convert_from_path expects a filename
        elif isinstance(pdf_input, bytes):
            raise ValueError("OCR fallback not supported for byte stream without file path.")
        else:
            images = convert_from_path(pdf_input)

        for img in images:
            text += pytesseract.image_to_string(img)
    except Exception as e:
        print(f"OCR fallback failed: {e}")
    return text


# SECTION 2. extract CAS number from document (regex + heuristics) 
    # USED LATER - to cross reference GHS info with PubChem
def is_valid_cas(cas):
    # reference: https://www.cas.org/training/documentation/chemical-substances/checkdig
    if not re.match(r"^\d{2,7}-\d{2}-\d$", cas):
        return False
    
    parts = cas.split('-')
    digits = ''.join(parts[:-1])
    check_digit = int(parts[-1])

    # print("check digit", check_digit)

    total = sum(int(num) * (i + 1) for i, num in enumerate(reversed(digits)))
    valid = total % 10 == check_digit
    # print("valid cas = ", valid)
    return valid

def extract_all_cas_numbers(text):
    cas_label_pattern = r"(?:\bCAS[-\s]?No\.?|\bCAS\b)" # looks for any version of CAS, CAS-NO, ETC., but not CAS[A-Z] (followed by some other letter)
    cas_number_pattern = r"(?<![\d-])\d{2,7}-\d{2}-\d(?![\d-])"
    # cas_number_pattern = r"\b\d{2,7}-\d{2}-\d\b" # 2-7 digits, 2 digits, 1 digit (CAS NO. FORMAT)
    lines = text.splitlines()

    high_conf_matches = set()
    low_conf_matches = set()

    # high confidence matches for the number pattern if "CAS" appears nearby
    for i, raw_line in enumerate(lines):
        line = raw_line.strip().lstrip(':').strip()

        if "index-no" in line.lower() or "index no" in line.lower():
            continue

        if re.search(cas_label_pattern, line, re.IGNORECASE):
            cas_match = re.search(cas_number_pattern, line)
            if cas_match:
                high_conf_matches.add(cas_match.group())
        else:
            window = '\n'.join(lines[max(0,i-2):min(len(lines), i+3)]) # looks for a +-2 line window to find cas no. (min of 0, max of total lines)
            if re.search(cas_label_pattern, window, re.IGNORECASE):
                cas_match = re.search(cas_number_pattern, line)
                if cas_match:
                    high_conf_matches.add(cas_match.group())

    # low confidence matches if "CAS" does not appear nearby
    all_matches = re.findall(cas_number_pattern, text)
    for match in all_matches:
        if match not in high_conf_matches:
            low_conf_matches.add(match)

    valid_high = {cas for cas in high_conf_matches if is_valid_cas(cas)}
    valid_low = {cas for cas in low_conf_matches if is_valid_cas(cas)}

    # print(f"Extracted CAS Numbers:\n  High Confidence: {list(valid_high)}\n  Low Confidence: {list(valid_low)}")

    return {
        "high_confidence": list(valid_high),
        "low_confidence": list(valid_low)
    }


# SECTION 3. chemical name extractor (name on *doc*)
def extract_product_name(text):
    def extract_section_1(text):
        lines = text.splitlines()
        section_lines = []
        inside_section_1 = False

        # only looks in section 1 identification to reduce error
        for line in lines:
            if re.search(r"section\s*1[\.:]?", line, re.IGNORECASE):
                inside_section_1 = True
            elif inside_section_1 and re.search(r"section\s*2[\.:]?", line, re.IGNORECASE):
                break
            elif inside_section_1:
                section_lines.append(line.strip())
        return section_lines
    
    section_lines = extract_section_1(text)

    # fuzzy keyword search (flexibility)
    keywords = [
        "Product Name",
        "Substance Name",
        "Product Identifier",
        "Chemical Name",
        "GHS Product Identifier",
        "Identification of the substance"
    ]

    for i, raw_line in enumerate(section_lines):
        line = raw_line.strip().lstrip(':').strip()
        for keyword in keywords:
            if fuzz.partial_ratio(keyword.lower(), line.lower()) > 80: # adjust as necessary
                match = re.search(rf"{re.escape(keyword)}\s*[:\-]?\s*(.+)", line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                else:
                    # fallback, potentially at next non-empty line
                    name = ""
                    j = i + 1
                    while j < len(section_lines) and name.strip() == "":
                        name = section_lines[j].strip()
                        j += 1

                # clean up trailing descriptors
                name = re.split(r",|≥|;|for|\s\d+[%]", name, maxsplit=1)[0].strip()
                # print("Name found on SDS: ", name)
                return name
   
    return "Product name not found on SDS"


# SECTION 4. validate CAS against *PubChem* chemical name
@lru_cache(maxsize=128) # cache previously searched CAS no.
def get_pubchem_name(cas):
    # print("test name cache")
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/xref/rn/{cas}/JSON" # PUG REST API standard url for CAS no. lookup
    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        if 'PC_Compounds' not in data:
            print(f"[PubChem Error] 'PC_Compounds' key not found in response for CAS {cas}")
            print(f"Full JSON response: {json.dumps(data, indent=2)}")
            return None

        # refer to sample pubchem json structure
        compound = data['PC_Compounds'][0]
        
        # collects all synonyms
        iupac_names = []
        for prop in compound.get('props', []):
            urn = prop.get('urn', {})
            # allows any synonyms given by PubChem - preferred only: [and urn.get('name') == "Preferred"]
            if urn.get('label') == "IUPAC Name":
                iupac_names.append(prop['value']['sval'].strip().lower())
        # print("found iupac name:", iupac_names)
        iupac_names = list(dict.fromkeys(iupac_names))
        return iupac_names if iupac_names else None
    
    except Exception as e:
        print(f"PubChem lookup failed: {e}")
    
    return None


# SECTION 5. Pick best CAS with PubChem Validation
    # needs exact chemical name to validate, but can pass with no validation
def extract_best_guess_cas(text):
    cas_split = extract_all_cas_numbers(text)
    cas_candidates = cas_split["high_confidence"] + cas_split["low_confidence"]
    chemical_name_in_doc = extract_product_name(text).lower()

    for cas in cas_candidates:
        try:
            pubchem_names = get_pubchem_name(cas)
            if pubchem_names and chemical_name_in_doc in pubchem_names:
                return {"cas": cas, "validated": True}
        except Exception as e:
            print(f"PubChem name validation failed for CAS {cas}: {e}")
        
    return {"cas": cas_candidates[0] if cas_candidates else None, "validated": False}


# SECTION 6. hazard statements
def extract_ghs_statements(text, threshold=60):
    # extracts section 2, splits into GHS candidate phrases, returns top match
    lines = text.splitlines()
    section_lines = []
    inside_section = False

    for line in lines:
        if re.search(r"^(section\s*)?2[\.:]?\s", line, re.IGNORECASE):
            inside_section = True
        elif inside_section and re.search(r"^(section\s*)?3[\.:]?\s", line, re.IGNORECASE):
            break
        elif inside_section:
            section_lines.append(line.strip())

    # heuristically split into candidate phrases
    raw_section = " ".join(section_lines)
    # Narrow to after "Hazard Statements"
    hazard_start = re.search(r"hazard\s*statements[:\-]?", raw_section, re.IGNORECASE)
    if hazard_start:
        raw_section = raw_section[hazard_start.end():]
    # print(raw_section)
    # candidates = re.split(r"[.;•●\n]", raw_section)
    # candidates = [c.strip() for c in candidates if len(c.strip()) > 8]

    candidates = re.findall(r"(H\d{3}(?:\s*(?:\+|,|/)\s*H\d{3})*)(?:\s*[:-]?\s*)?(.*?)(?=[.;\n]|$)", raw_section)
    # print("candidates", candidates)

    def split_combined_hazard_statements(hazard_entries):
        """
        Takes a list of tuples (starting H-code, full hazard string),
        and returns a list of individual (H-code, description) pairs.
        """
        split_results = []

        for first_hcode, full_text in hazard_entries:
            pattern = re.compile(r"(H\d{3}(?:\s*\+\s*H\d{3})*)\s+(.*?)(?=\s+H\d{3}|\s+P\d{3}|$)")
            matches = pattern.findall(full_text)

            # If first code (e.g. H302) wasn't in the matches, prepend it
            if matches:
                first_found_code = matches[0][0]
                if first_hcode not in first_found_code:
                    # Extract up to the first matched H-code from text
                    preamble = full_text.split(first_found_code)[0].strip()
                    first_desc = preamble
                    if first_desc:  # Only add if there is actual description
                        split_results.append((first_hcode, first_desc))

            for h_code, desc in matches:
                cleaned_desc = desc.strip().rstrip(".;")
                split_results.append((h_code.strip(), cleaned_desc))

        return split_results
    
    split_candidates = split_combined_hazard_statements(candidates)

    # print("split", split_candidates)

    if split_candidates == []:
        candidates = [f"{codes.strip()} {desc.strip()}".strip() for codes, desc in candidates]
    else:
        candidates = [f"{codes.strip()} {desc.strip()}".strip() for codes, desc in split_candidates]



    all_results = []
    
    hazards, _ = get_pubchem_ghs_phrases()

    for phrase in candidates:
        # print("phrase", phrase)
        h_code_match = re.match(r"^(H\d{3}(?:\s*(?:\+|,|/)\s*H\d{3})*)\b", phrase)
        if len(phrase) > 200:
                continue  # ignore paragraph-length statements
        
        if h_code_match:
            h_code = h_code_match.group(1)
            match_entry = next((entry for entry in hazards if entry[0] == h_code), None)

            if match_entry:
                all_results.append({
                    "original_text": phrase,
                    "match_score": 100,
                    "ghs_code": match_entry[0],
                    "official_text": match_entry[1],
                    "category": "Hazard"
                })
                continue

        matches = match_to_pubchem_ghs(phrase, threshold=threshold)
        if matches:
            best = matches[0]
            all_results.append({
                "original_text": phrase,
                "match_score": best["score"],
                "ghs_code": best["code"],
                "category": best["category"],
                "official_text": best["official_text"]
            })
        else:
            all_results.append({
                "original_text": phrase,
                "matched": False,
                "match_score":  None,
                "ghs_code": None,
                "category": None,
                "official_text": None
            })

    return all_results


# SECTION 7. cv GHS by CAS with PubChem
def get_pubchem_ghs_by_cas(cas):
    try:
        # Step 1: Get CID from CAS
        cid_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/xref/rn/{cas}/JSON"
        cid_resp = requests.get(cid_url, timeout=10)
        cid_resp.raise_for_status()
        cid_data = cid_resp.json()

        cid = cid_data["PC_Compounds"][0]["id"]["id"]["cid"]

        # Step 2: Use CID to fetch detailed compound info
        ghs_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
        ghs_resp = requests.get(ghs_url, timeout=10)
        ghs_resp.raise_for_status()
        ghs_data = ghs_resp.json()

        # Step 3: Traverse into nested structure to get GHS Hazard Statements
        sections = ghs_data.get("Record", {}).get("Section", [])
        ghs_statements = []

        def find_ghs_hazard_statements(sections):
            for section in sections:
                if section.get("TOCHeading", "").lower() == "safety and hazards":
                    for sub in section.get("Section", []):
                        if sub.get("TOCHeading", "").lower() == "hazards identification":
                            for subsub in sub.get("Section", []):
                                if subsub.get("TOCHeading", "").lower() == "ghs classification":
                                    for info in subsub.get("Information", []):
                                        if info.get("Name", "").lower() == "ghs hazard statements":
                                            for item in info.get("Value", {}).get("StringWithMarkup", []):
                                                ghs_statements.append(item.get("String"))
                else:
                    # Recurse into deeper sections if needed
                    find_ghs_hazard_statements(section.get("Section", []))

        find_ghs_hazard_statements(sections)
        # print(ghs_statements)
        return ghs_statements, cid

    except Exception as e:
        print(f"Failed to fetch PubChem GHS from CAS: {e}")
        return []


# SECTION 8. discrepancy comparison
def compare_ghs_source(extracted_matches, pubhcem_h_statements):
    extracted_h_codes = set()
    for entry in extracted_matches:
        if entry.get("ghs_code"):
            # print(f"[DEBUG] Matched H code from SDS: {entry['ghs_code']}")
            extracted_h_codes.add(entry["ghs_code"])

    official_h_code = set()
    for stmt in pubhcem_h_statements:
        match = re.findall(r"\bH\d{3}\b", stmt)
        for m in match:
            # print(f"[DEBUG] H code from PubChem: {m}")
            official_h_code.add(m)

    # compare sets
    confirmed = extracted_h_codes & official_h_code
    extra = extracted_h_codes - official_h_code
    missing = official_h_code - extracted_h_codes

    # print("[RESULT] Confirmed:", confirmed)
    # print("[RESULT] Extra:", extra)
    # print("[RESULT] Missing:", missing)

    return {
        "confirmed": sorted(confirmed),
        "extra": sorted(extra),
        "missing": sorted(missing)
    }


def extract_between_sections(text, start_section, end_section):
        """
        extract all text between two specified section headers
        start_section = [section] 7. title
        end_section = [section] 8. title
        """

        lines = text.splitlines()
        start_pattern = rf"(section\s*)?{start_section[0]}[\.:]?\s*{start_section[1]}"
        end_pattern = rf"(section\s*)?{end_section[0]}[\.:]?\s*{end_section[1]}"

        inside = False
        section_lines = []

        for line in lines:
            if not inside and re.search(start_pattern, line, re.IGNORECASE):
                inside = True
                continue
            if inside:
                if re.search(end_pattern, line, re.IGNORECASE):
                    break
                section_lines.append(line.strip())

        section_text = "\n".join(section_lines)

        # remove footers
        section_text = re.sub(
            r"(?:SIGALD|Aldrich)\s*-\s*\d+\s*[\r\n]+\s*Page\s*\d+\s*of\s*\d+\s*[\r\n]+.*?MilliporeSigma\s+in\s+the\s+US\s+and\s+Canada",
            "",
            section_text,
            flags=re.IGNORECASE | re.DOTALL
        )

        return section_text

# SECTION 9. flash point, storage condition, reactivity info
def extract_additional_safety_info(text):

    # section_5 = extract_section(text,5)
    section_7 = extract_between_sections(text, (7, r"handling\s+and\s+storage"), (8, r"exposure\s+controls\s*/\s*personal\s+protection"))
    # print("\n\nsection 7 text", section_7)
    section_9 = extract_between_sections(text, (9, r"physical\s+and\s+chemical\s+properties"), (10, r"stability\s+and\s+reactivity"))
    # print("\n\nsection 9 text", section_9)
    section_10 = extract_between_sections(text, (10, r"stability\s+and\s+reactivity"), (11, r"toxicological\s+information"))
    # Normalize excessive empty lines to single empty line
    section_10 = re.sub(r'\n\s*\n+', '\n\n', section_10)
    # print("\n\nsection 10 text", section_10)

    info = {}
    info["reactivity"] = section_10


    # SUBSECTION 9A. flash point (section 9 SDS)
    flash_point_match = re.search(r"flash\s*point[:\s\-]*([^\n]+)", section_9, re.IGNORECASE)
    # print(flash_point_match)

    def truncate_after_temp_units(s):
        match = re.search(r"(.*?°[CF])", s)
        return match.group(1).strip() if match else s.strip()

    if re.search(r"no\s+data\s+available|not\s+applicable|n/?a|unknown", flash_point_match.group(0), re.IGNORECASE):
        info["flash_point"] = "Not available"
    else:
        raw_flash_line = flash_point_match.group(0).strip()
        # print(raw_flash_line)
        flash_line = truncate_after_temp_units(raw_flash_line)
        # print("\n\n", flash_line)
        fp_match = re.search(r"(-?\d+(?:\.\d+)?\s*°[CF])(?:\s*/\s*(-?\d+(?:\.\d+)?\s*°[CF]))?", flash_line)
        if fp_match:
            parts = [fp_match.group(1)]
            if fp_match.group(2):
                parts.append(fp_match.group(2))
            cup_match = re.search(r"(closed|open)?\s*cup", flash_line, re.IGNORECASE)
            cup_info = f"{cup_match.group(0)}" if cup_match else ""
            fp = " / ".join(parts)
            if cup_info:
                fp = f"{fp} - {cup_info.strip()}"
            info["flash_point"] = fp


    # SUBSECTION 9B. storage conditions (section 7 SDS)
    # Extract between "storage conditions" and "storage class" within section 7
    storage_between_match = re.search(r"storage\s*conditions\s*[:\-]?\s*(.*?)(?=\bstorage\s*class\b)", section_7, re.IGNORECASE | re.DOTALL)
    if storage_between_match:
        info["storage_conditions"] = storage_between_match.group(1).strip().replace('\n', ' ')
    else:
        # Search for text between "conditions for safe storage, including any incompatibilities" and "specific end use(s)"
        storage_between_match = re.search(
        r"conditions\s*for\s*safe\s*storage,\s*including\s*any\s*incompatibilities\s*[:\-]?\s*\n*(.*?)(?=\bspecific\s*end\s*use\(s\))",
        section_7,
        re.IGNORECASE | re.DOTALL
        )
        if storage_between_match:
            info["storage_conditions"] = storage_between_match.group(1).strip().replace('\n', ' ')


    # SUBSECTION 9C. appearance and odor (section 9 SDS
    # Extract 'appearance'
    appearance_match = re.search(
        r"(?i)\bappearance\s*[:\-]?\s*(.*?)(?=\n\s*(?:[a-zA-Z0-9]+\)|odou?r|pH|boiling|melting|flash|freezing))",
        section_9,
        re.IGNORECASE | re.DOTALL
    )

    if appearance_match:
        appearance = appearance_match.group(1).strip().replace('\n', ' ')
        appearance = re.sub(r'^[\s/]+', '', appearance)
        info["appearance"] = appearance

    # Extract 'odor'
    odor_match = re.search(r"(?i)\bodou?r\s*[:\-]?\s*(.*)", section_9)
    if odor_match:
        info["odor"] = odor_match.group(1).strip()

    return info


# 10. full parser function
def parse_sds_file(filepath=None, input_val=None, source="PDF Upload"):
    """
    full SDS parsing pipeline:
    - extract text from SDS (OCR fallback)
    - extract CAS number and chemical name
    - match GHS statement from SDS
    - fetch offical GHS from pubchem via CAS
    - compare and return results
    """

    result = {
        "filepath": filepath,
        "cas_number": None,
        "chemical_name": None,
        "pubchem_name": None,
        "cas_validated": False,
        "ghs_from_sds": [],
        "ghs_from_pubchem": [],
        "cid": None,
        "comparison": {},
        "notes": [],
        "source": source,
        "nfpa": None
    }

    try:
        if filepath != None:
            text = extract_text_from_pdf(filepath)
        elif input_val != None:
            text = input_val
        result["chemical_name"] = extract_product_name(text)
        cas_info = extract_best_guess_cas(text)
        result["cas_number"] = cas_info["cas"]
        result["cas_validated"] = cas_info["validated"]
        ghs_from_sds = extract_ghs_statements(text)
        result["ghs_from_sds"] = ghs_from_sds
        pubchem_name = get_pubchem_name(result["cas_number"])
        result["pubchem_name"] = pubchem_name

        if cas_info["cas"]:
            try:
                pubchem_ghs, cid = get_pubchem_ghs_by_cas(cas_info["cas"])
                result["cid"] = cid
                result["ghs_from_pubchem"] = pubchem_ghs
                result["comparison"] = compare_ghs_source(ghs_from_sds, pubchem_ghs)
                result["cas_validated"] = True
            except Exception as e:
                result["notes"].append(f"PubChem GHS lookup failed for CAS {cas_info['cas']}: {e}")
        else:
            result["notes"].append("No CAS number found; skipping PubChem GHS lookup")

        extra_info = extract_additional_safety_info(text)
        # print("\n[INFO] Additional Safety Info by Section:")
        # for k, v in extra_info.items():
            # print(f"    {k}: {v}")
        result.update(extra_info)
        
        if cas_info["cas"]:
            res = fetch_nfpa_cameo(cas_info["cas"])
            consensus = compare_nfpa_results(res)
            print('RANNNNNNNNN 617 PARSER')
            result["nfpa"] = consensus
            print("\n\n FINAL: ",consensus)
        else:
            print("no cas number found")

    except Exception as e:
        result["notes"].append(f"Error processing SDS file: {e}")
        tb = traceback.format_exc()
        result["notes"].append(f"Error on line:\n{tb}")

    return result