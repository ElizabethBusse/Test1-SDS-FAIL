import fitz # from PyMuPDF
import re
import requests
from rapidfuzz import fuzz
from pdf2image import convert_from_path
import pytesseract
import traceback

from haz_comp_full import *
from status_fetcher_firefox import fetch_nfpa_cameo, compare_nfpa_results
from pub_nfpa import *
from nist_name import get_nist_names
import json
from rapidfuzz import process, fuzz
import string

# for imported SDS documents

# NOTE: specified only for SigmaAldrich (Millipore Sigma) and AaronChem (no guarantees on functionality beyond)


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
        # Remove Merck KGaA/MilliporeSigma business footer
        section_text = re.sub(
            r"The life science business of Merck KGaA, Darmstadt, Germany\s*operates as MilliporeSigma in the US and Canada",
            "",
            section_text,
            flags=re.IGNORECASE | re.DOTALL
        )
        # Remove Aldrich page footer like "Aldrich - B17905\nPage 2  of  11"
        section_text = re.sub(
            r"Aldrich\s*-\s*[A-Z0-9]+\s*Page\s*\d+\s*of\s*\d+",
            "",
            section_text,
            flags=re.IGNORECASE
        )

        return section_text


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
    # Extract product name between Section 1 and Section 2
    section_1 = extract_between_sections(
        text,
        (1, r"identification"),
        (2, r"hazards\s+identification")
    )

    if not section_1 or section_1.strip() == "":
        section_1 = extract_between_sections(
            text,
            (1, r"product\s+and\s+company\s+identification"),
            (2, r"hazards\s+identification")
        )

    # Heuristic: look for line after "Product name" or "Product identifier"
    match = re.search(r"(Product name[\s:]*)(.*)", section_1, re.IGNORECASE)
    if match:
        return match.group(2).strip()
    return None


# SECTION 4. High confidence or all low confidence
def extract_best_guess_cas(text):
    cas_split = extract_all_cas_numbers(text)
    high_conf = cas_split["high_confidence"]
    low_conf = cas_split["low_confidence"]

    if high_conf:
        return {"cas": high_conf[0], "validated": True}
    elif low_conf:
        return {"cas": low_conf, "validated": False}
    else:
        return {"cas": None, "validated": False}


# SECTION 5. hazard statements
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


# SECTION 6. cv GHS by CAS with PubChem
def get_cid_from_cas(cas_number):
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{cas_number}/cids/JSON"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        try:
            return data['IdentifierList']['CID'][0]
        except KeyError:
            return None
    else:
        return None

def get_pubchem_ghs_by_cas(cas):
    try:
        # Step 1: Get CID from CAS
        cid = get_cid_from_cas(cas)

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


# SECTION 7. discrepancy comparison
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


# SECTION 8: GHS classification category 1
def ghs_category_1(text):
    section_2 = extract_between_sections(
        text,
        (2, r"hazards\s+identification"),
        (3, r"composition\s*/\s*information\s+on\s+ingredients")
    )
    # Find GHS classification section in Section 2
    pattern_start = r"(GHS Classification in accordance with 29 CFR 1910 \(OSHA HCS\)|GHS classification in accordance with the OSHA Hazard Communication Standard\s*\(29 CFR 1910\.1200\))"
    pattern_end = r"(pictogram|signal word|2\.2\s*GHS Label elements, including precautionary statements|GHS Label elements, including precautionary statements)"

    match_start = re.search(pattern_start, section_2, re.IGNORECASE)
    if match_start:
        start_idx = match_start.end()
        # Find end after start
        # Find end after start
        match_end = re.search(pattern_end, section_2[start_idx:], re.IGNORECASE)
        if match_end:
            end_idx = start_idx + match_end.start()
            ghs_classification_text = section_2[start_idx:end_idx].strip()
        else:
            ghs_classification_text = section_2[start_idx:].strip()
    else:
        ghs_classification_text = ""

    # print(ghs_classification_text)

    # Extract all lines with a GHS category pattern (e.g., "Acute toxicity, Category 1", "Category 1A", etc.)
    # Handles patterns like: "Acute toxicity, oral,(Category 4), H302"
    # Updated pattern to match lines like "Flammable liquids\n: Category 2" or "Pyrophoric liquids\n: Category 1"
    # Also matches "Skin corrosion\n: Sub-category 1B" and "Serious eye damage\n: Category 1"

    # category_pattern = r"(.*?)(?:\n\s*[:\-]\s*(?:Sub-)?Category\s*([0-9][a-zA-Z]?))" # OPTION: ALL GHS CODES, NOT JUST CATEGORY 1
    category_pattern = r"(.*?)(?:\n\s*[:\-]\s*(?:Sub-)?Category\s*(1[a-zA-Z]?))"


    # Also match inline: "Category 1" in parentheses, e.g. "Acute toxicity, oral,(Category 1), H300"
    # inline_pattern = r"(.*?)(?:\(\s*category\s*([0-9][a-zA-Z]?)\s*\))" # OPTION
    inline_pattern = r"(.*?)(?:\(\s*category\s*(1[a-zA-Z]?)\s*\))"

    matches = re.findall(category_pattern, ghs_classification_text, re.IGNORECASE)
    matches += re.findall(inline_pattern, ghs_classification_text, re.IGNORECASE)

    # Only keep those with category "1" (including "1A", "1B", etc.)
    category_1_entries = []
    for text, cat in matches:
        # if re.match(r"[0-9][a-zA-Z]?$", cat.strip(), re.IGNORECASE): # OPTION
        if re.match(r"1[a-zA-Z]?$", cat.strip(), re.IGNORECASE):
            entry = {
                "text": text.strip().rstrip(","),
                "category": cat.strip()
            }
            category_1_entries.append(entry)

    # Match entries to GHS category names
    ghs_names = [
        "Explosives",
        "Flammable Gases",
        "Chemically Unstable Gases",
        "Pyrophoric Gases",
        "Aerosols",
        "Oxidizing Gases",
        "Gases Under Pressure",
        "Flammable Liquids",
        "Flammable Solids",
        "Self-reactive Substances",
        "Pyrophoric Liquids",
        "Pyrophoric Solids",
        "Self-heating Substances",
        "Chemicals which emit flammable gas when in contact with water",
        "Oxidizing Liquids",
        "Oxidizing Solids",
        "Organic Peroxides",
        "Corrosive to Metals",
        "Desensitized Explosives",
        "Acute Toxicity",
        "Skin Corrosion/Irritation",
        "Serious Eye Damage/Eye Irritation",
        "Respiratory Sensitization",
        "Skin Sensitization",
        "Germ Cell Mutagenicity",
        "Carcinogenicity",
        "Reproductive Toxicity",
        "Specific Target Organ Toxicity (Single Exposure)",
        "Specific Target Organ Toxicity (Repeated Exposure)",
        "Aspiration Hazard",
        "Hazardous to the Aquatic Environment (Acute)",
        "Hazardous to the Aquatic Environment (Chronic)",
        "Hazardous to the Ozone Layer"
    ]

    for item in category_1_entries:
        # Fuzzy match item[0] (the hazard name) to all in ghs_names, save highest match score
        best_match = None
        best_score = 0
        for ghs_name in ghs_names:
            score = fuzz.partial_ratio(item["text"].lower(), ghs_name.lower())
            if score > best_score:
                best_score = score
                best_match = ghs_name
        item["ghs_name_match"] = best_match
        item["ghs_name_score"] = best_score

    # # Optionally, print or return these entries for further use
    # if category_1_entries:
    #     print("GHS Category 1 entries found:", category_1_entries)
    return category_1_entries


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


# SECTION 10: other hazards
def other_hazards(text):
    section_2 = extract_between_sections(
        text,
        (2, r"hazards\s+identification"),
        (3, r"composition\s*/\s*information\s+on\s+ingredients")
    )
    # Search for text after "Hazards not otherwise classified (HNOC) or not covered by GHS"
    hnoc_pattern = r"Hazards not otherwise classified \(HNOC\) or not covered by GHS[:\-]?\s*(.*)"
    hnoc_match = re.search(hnoc_pattern, section_2, re.IGNORECASE | re.DOTALL)
    def strip_punctuation(s):
        return s.translate(str.maketrans('', '', string.punctuation))

    result_lines = []
    if hnoc_match:
        hnoc_text = hnoc_match.group(1).lstrip().strip()
        hnoc_text = re.sub(r"^-+\s*", "", hnoc_text)
        hnoc_text = re.split(r"\n\s*(?:GHS label elements|Section\s*\d+)", hnoc_text, maxsplit=1)[0].strip()
        lines = [strip_punctuation(line.strip()) for line in hnoc_text.splitlines() if line.strip()]
        result_lines = list(dict.fromkeys(lines))  # remove duplicates, preserve order
        # print("HNOC TEXT", result_lines)
        return result_lines if result_lines else None

    other_hazards_pattern = r"Other Hazards[:\-]?\s*(.*?)(?=\n\s*GHS label elements)"
    other_match = re.search(other_hazards_pattern, section_2, re.IGNORECASE | re.DOTALL)
    if other_match:
        other_text = other_match.group(1).lstrip().strip()
        other_text = re.sub(r"^-+\s*", "", other_text)
        lines = [strip_punctuation(line.strip()) for line in other_text.splitlines() if line.strip()]
        result_lines = list(dict.fromkeys(lines))
        # print("OTHER TEXT", result_lines)
        return result_lines if result_lines else None

    return None


# SECTION 11. full parser function
def parse_sds_file(filepath=None, cas_number = None, input_val=None, source="PDF Upload"):
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
        "cas_number": cas_number,
        "chemical_name": None,
        "pubchem_name": None,
        "cas_validated": False,
        "ghs_from_sds": [],
        "ghs_from_pubchem": [],
        "cid": None,
        "comparison": {},
        "notes": [],
        "source": source,
        "nfpa": None,
        "ghs_categories": None,
        "other_hazards": None,
        "additional_cas": None
    }

    try:
        if filepath != None:
            text = extract_text_from_pdf(filepath)
        elif input_val != None:
            text = input_val

        result["chemical_name"] = extract_product_name(text)
        ghs_from_sds = extract_ghs_statements(text)
        result["ghs_from_sds"] = ghs_from_sds
        ghs_category = ghs_category_1(text)
        result["ghs_categories"] = ghs_category
        other_haz = other_hazards(text)
        result["other_hazards"] = other_haz
        extra_info = extract_additional_safety_info(text)
        # print("\n[INFO] Additional Safety Info by Section:")
        # for k, v in extra_info.items():
            # print(f"    {k}: {v}")
        result.update(extra_info)


        cas_info = extract_best_guess_cas(text)
        result["cas_validated"] = cas_info["validated"]
        if not cas_number:
            print("RAN FINDING CAS NUMBER FROM SDS")
            if isinstance(cas_info["cas"], str):
                result["cas_number"] = cas_info["cas"]
            elif isinstance(cas_info["cas"], list):
                result["cas_number"] = cas_info["cas"]
                result["additional_cas"] = secondary_parse(result)
                # print(result["additional_cas"])
                result["cas_number"] = cas_info["cas"][0] # LIST, including [0]


        pubchem_name = get_nist_names(result["cas_number"])
        result["pubchem_name"] = pubchem_name
        # print("CATS:", result["ghs_categories"])

        if result["cas_number"]:
            try:
                pubchem_ghs, cid = get_pubchem_ghs_by_cas(result["cas_number"])
                result["cid"] = cid
                result["ghs_from_pubchem"] = pubchem_ghs
                result["comparison"] = compare_ghs_source(ghs_from_sds, pubchem_ghs)
                result["cas_validated"] = True
            except Exception as e:
                result["notes"].append(f"PubChem GHS lookup failed for CAS {result["cas_number"]}: {e}")
        else:
            result["notes"].append("No CAS number found; skipping PubChem GHS lookup")
        
        if result["cas_number"]:
            res = fetch_nfpa_cameo(result["cas_number"])
            if res is not None:
                consensus = compare_nfpa_results(res)
                result["nfpa"] = consensus
                # print("\n\n FINAL: ",consensus)
            else:
                consensus = None
        else:
            print("no cas number found")


        if consensus is None:
            result["nfpa"] = extract_nfpa_hazard(result["cid"])

    except Exception as e:
        result["notes"].append(f"Error processing SDS file: {e}")
        tb = traceback.format_exc()
        result["notes"].append(f"Error on line:\n{tb}")

    return result

def secondary_parse(result):
    additional_results = []

    # Repeat for each CAS in result["cas_number"] (excluding the first one)
    cas_list = result["cas_number"]
    if isinstance(cas_list, list) and len(cas_list) > 1:
        for cas in cas_list[1:]:
            temp_result = result.copy()
            temp_result["cas_number"] = cas
            temp_result["pubchem_name"] = get_nist_names(cas)

            if cas:
                try:
                    pubchem_ghs, cid = get_pubchem_ghs_by_cas(cas)
                    temp_result["cid"] = cid
                    temp_result["ghs_from_pubchem"] = pubchem_ghs
                    temp_result["comparison"] = compare_ghs_source(temp_result["ghs_from_sds"], pubchem_ghs)
                    temp_result["cas_validated"] = True
                except Exception as e:
                    temp_result["notes"].append(f"PubChem GHS lookup failed for CAS {cas}: {e}")
            else:
                temp_result["notes"].append("No CAS number found; skipping PubChem GHS lookup")

            if cas:
                res = fetch_nfpa_cameo(cas)
                if res is not None:
                    consensus = compare_nfpa_results(res)
                    temp_result["nfpa"] = consensus
                else:
                    consensus = None
            else:
                print("no cas number found")

            if consensus is None:
                temp_result["nfpa"] = extract_nfpa_hazard(temp_result["cid"])

            temp_result["additional_cas"] = True

            additional_results.append(temp_result)
    return additional_results