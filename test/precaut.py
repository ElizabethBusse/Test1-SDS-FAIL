import json
from rapidfuzz import fuzz, process

# Load the precautionary JSON file
with open("/Users/sophiezhou/Downloads/purdue/[10] summer 25/evonik/SDS GHS Extractor/chemsafety_precautionary.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Extract just the phrases to match against
phrases = [entry["phrase"] for entry in data]

def fuzzy_match(input_phrase, limit=5):
    # Get top N matches by similarity score
    results = process.extract(input_phrase, phrases, scorer=fuzz.token_sort_ratio, limit=limit)
    
    # Format with codes
    matches = []
    for match_phrase, score, _ in results:
        match = next((entry for entry in data if entry["phrase"] == match_phrase), None)
        if match:
            matches.append({
                "code": match["code"],
                "phrase": match_phrase,
                "score": score
            })

    return matches

# Example usage
user_input = input("Enter a precautionary phrase to search: ")
top_matches = fuzzy_match(user_input)

print("\nTop Matches:")
for match in top_matches:
    print(f"{match['code']} - {match['phrase']} (Score: {match['score']})")