import json
from rapidfuzz import fuzz

# Load JSON
with open("ghs_annex1_pubchem.json", "r", encoding="utf-8") as f:
    ghs_data = json.load(f)

# Flatten all rows
hazard_rows = []
if isinstance(ghs_data, dict):
    for section in ghs_data.values():
        if isinstance(section, list):
            for row in section:
                if isinstance(row, dict):
                    hazard_rows.append(row)
elif isinstance(ghs_data, list):
    hazard_rows = ghs_data

# Collect unique (Hazard Class, Category) pairs
pairs = set()
for row in hazard_rows:
    h_class = row.get("Hazard Class", "").strip()
    cat = row.get("Category", "").strip()
    if h_class and cat:
        pairs.add((h_class, cat))

# Input
user_class = input("Enter hazard class (e.g., flammable): ").strip().lower()
user_cat = input("Enter category (e.g., 2): ").strip().lower()
if not user_cat.startswith("category"):
    user_cat = f"category {user_cat}"

# Find best match
best_pair = None
best_score = -1

for h_class, category in pairs:
    score_class = fuzz.token_sort_ratio(user_class, h_class.lower())
    score_cat = fuzz.token_sort_ratio(user_cat, category.lower())
    combined_score = (score_class + score_cat) / 2

    if combined_score > best_score:
        best_score = combined_score
        best_pair = (h_class, category)

# Output best pair
if best_pair:
    print("\n✅ Best Match:")
    print(f"Hazard Class: {best_pair[0]}")
    print(f"Category: {best_pair[1]}")
    print(f"Combined Fuzzy Score: {best_score:.2f}")
else:
    print("❌ No match found.")