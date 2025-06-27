import json
import re
from rapidfuzz import fuzz

# Load GHS data
with open("ghs_annex1_pubchem.json", "r", encoding="utf-8") as f:
    ghs_data = json.load(f)

# Flatten rows
hazard_rows = []
if isinstance(ghs_data, dict):
    for section in ghs_data.values():
        if isinstance(section, list):
            hazard_rows.extend(row for row in section if isinstance(row, dict))
elif isinstance(ghs_data, list):
    hazard_rows = ghs_data

# Unique (Hazard Class, Category) pairs
pairs = set()
for row in hazard_rows:
    h = row.get("Hazard Class", "").strip()
    c = row.get("Category", "").strip()
    if h and c:
        pairs.add((h, c))

# === Flexible Input Parsing ===
def parse_input(raw):
    raw = raw.strip().replace('\n', ' ')
    category_match = re.search(r'category\s*[:\.]?\s*(\d+[A-Z]?)', raw, re.IGNORECASE)
    if not category_match:
        category_match = re.search(r'(\d+[A-Z]?)$', raw)
    category = category_match.group(1) if category_match else ""
    hazard_class = re.sub(r'\(?category\s*[:\.]?\s*\d+[A-Z]?\)?', '', raw, flags=re.IGNORECASE).strip()
    hazard_class = re.sub(r'[\n:]+$', '', hazard_class).strip()
    return hazard_class, f"Category {category}" if category else ""

# === Prioritized + Strict Fuzzy Matching ===
def get_best_pair(h_input, c_input, threshold=60):
    h_input = h_input.lower()
    c_input = c_input.lower()

    exact_category_matches = [pair for pair in pairs if pair[1].lower() == c_input]
    candidates = exact_category_matches if exact_category_matches else pairs

    best_pair = None
    best_score = -1

    for h, c in candidates:
        score_h = fuzz.ratio(h_input, h.lower())
        score_c = 100 if c.lower() == c_input else fuzz.ratio(c_input, c.lower())
        combined = (score_h + score_c) / 2

        if combined > best_score and combined >= threshold:
            best_score = combined
            best_pair = (h, c)

    return best_pair, best_score

# === Main Usage ===
if __name__ == "__main__":
    user_input = input("Enter hazard class + category (freeform): ")

    h_class, category = parse_input(user_input)

    print(f"\n🔍 Interpreted as:")
    print(f"- Hazard Class: {h_class}")
    print(f"- Category: {category}")

    match, score = get_best_pair(h_class, category)

    if match:
        print(f"\n✅ Best Match: {match[0]} - {match[1]} (Score: {score:.1f})")
        for row in hazard_rows:
            if row.get("Hazard Class") == match[0] and row.get("Category") == match[1]:
                hcode = row.get("H-Code")
                if hcode:
                    print(f"H-Code: {hcode}")
    else:
        print("❌ No suitable match found (score too low or no valid match).")