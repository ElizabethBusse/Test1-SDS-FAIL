import json
import re
from rapidfuzz import fuzz
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

"""
uses classification_labels.js to scrape classification/category information from pubchem -> saved as json locally
compares input from SDS to dictionary of potential classification/categories to find best match (fuzzy)
compares input string to best match using word parsing algos to compare (outside of fuzzy score)
returns if both checks pass
"""


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

# String Similarity Functions
def normalized_levenshtein(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def jaccard_similarity(a, b):
    a_set = set(a.lower().split())
    b_set = set(b.lower().split())
    intersection = a_set & b_set
    union = a_set | b_set
    return len(intersection) / len(union) if union else 0

def cosine_similarity_score(a, b):
    vect = TfidfVectorizer().fit([a, b])
    vecs = vect.transform([a, b])
    return cosine_similarity(vecs[0], vecs[1])[0][0]

# Flexible Input Parser
def parse_input(raw):
    raw = raw.strip().replace('\n', ' ')
    category_match = re.search(r'category\s*[:\.]?\s*(\d+[A-Z]?)', raw, re.IGNORECASE)
    if not category_match:
        category_match = re.search(r'(\d+[A-Z]?)$', raw)
    category = category_match.group(1) if category_match else ""
    hazard_class = re.sub(r'\(?category\s*[:\.]?\s*\d+[A-Z]?\)?', '', raw, flags=re.IGNORECASE).strip()
    hazard_class = re.sub(r'[\n:]+$', '', hazard_class).strip()
    return hazard_class, f"Category {category}" if category else ""

# Prioritized + Strict Fuzzy Matcher
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

# Main Match Function with Similarity Check
def get_hazard_info(freeform_text, sim_thresholds=(0.5, 0.3, 0.25)):
    """
    sim_thresholds = (levenshtein_min, jaccard_min, cosine_min)
    """
    h_class, category = parse_input(freeform_text)
    match, score = get_best_pair(h_class, category)

    if not match:
        return None

    best_combined = f"{match[0]} {match[1]}"
    original_combined = f"{h_class} {category}"

    lev = normalized_levenshtein(original_combined, best_combined)
    jac = jaccard_similarity(original_combined, best_combined)
    cos = cosine_similarity_score(original_combined, best_combined)

    print("\n🔍 Similarity Checks:")
    print(f"User Input        : {original_combined}")
    print(f"Best Match String : {best_combined}")
    print(f"📐 Levenshtein Ratio     : {lev:.4f}")
    print(f"🧮 Jaccard Similarity     : {jac:.4f}")
    print(f"📊 Cosine Similarity (TF-IDF): {cos:.4f}")

    if lev < sim_thresholds[0] or jac < sim_thresholds[1] or cos < sim_thresholds[2]:
        print("❌ Match rejected due to low similarity.")
        return None

    for row in hazard_rows:
        if row.get("Hazard Class") == match[0] and row.get("Category") == match[1]:
            return {
                "hazard_class": match[0],
                "category": match[1],
                "h_code": row.get("H-Code"),
                "match_score": score
            }

    return None

# === CLI Mode for Testing ===
if __name__ == "__main__":
    user_input = input("Enter hazard class + category (freeform): ")
    result = get_hazard_info(user_input)

    if result:
        print(f"\n✅ Match: {result['hazard_class']} - {result['category']}")
        print(f"H-Code: {result['h_code']} (Score: {result['match_score']:.1f})")
    else:
        print("❌ No suitable match found.")