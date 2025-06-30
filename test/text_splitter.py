import re

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

input_data = [
    ('H302', 'Harmful if swallowed H315 Causes skin irritation H319 Causes serious eye irritation H335 May cause respiratory irritation Precautionary statements P280 Wear protective gloves/protective clothing/eye protection/face protection')
]

result = split_combined_hazard_statements(input_data)
for entry in result:
    print(entry)