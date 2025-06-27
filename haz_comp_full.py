import re
import requests
from bs4 import BeautifulSoup
from functools import lru_cache
from rapidfuzz import fuzz

@lru_cache(maxsize=1)
def get_pubchem_ghs_phrases():
    """
    Scrape PubChem’s GHS page for hazard and precautionary statements.
    Returns two lists of (code, statement) tuples.
    """
    url = "https://pubchem.ncbi.nlm.nih.gov/ghs/#_prec"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    def extract_from_section(header_text):
        hdr = soup.find(
            lambda tag: tag.name in ("h2", "h3")
                        and header_text in tag.get_text()
        )
        phrases = []
        if hdr:
            tbl = hdr.find_next("table")
            if tbl:
                for row in tbl.find_all("tr"):
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        code = cols[0].get_text(strip=True)
                        text = cols[1].get_text(strip=True)
                        phrases.append((code, text))
        return phrases

    hazard_phrases    = extract_from_section("Hazard Statements")
    precaution_phrases = extract_from_section("Precautionary Statements")
    return hazard_phrases, precaution_phrases

def match_to_pubchem_ghs(text: str, threshold: int = 60):
    """
    Fuzzy-match `text` against PubChem’s GHS tables.
    Returns a list of dicts with: category, code, official_text, and score.
    Prefers full phrase matches over partial matches.
    """
    if re.match(r"^P\d{3}", text.strip()):
        return []  # ignore precautionary codes

    if len(text.strip()) > 200:
        return []  # ignore paragraph-length statements


    hazards, precs = get_pubchem_ghs_phrases()
    matches = []
    low = text.lower()

    for category, phrases in (("Hazard", hazards), ("Precautionary", precs)):
        for code, official in phrases:
            if code.strip() == "-" or official.strip() == "-":
                continue

            official_low = official.lower()
            full_score = fuzz.ratio(low, official_low)
            partial_score = fuzz.partial_ratio(low, official_low)

            # Prefer full matches by weighting them slightly higher
            final_score = max(full_score, partial_score - 10)

            if final_score >= threshold:
                matches.append({
                    "category":      category,
                    "code":          code,
                    "official_text": official,
                    "score":         final_score
                })

    # Prefer longer (full) matches if scores are similar
    matches.sort(key=lambda x: (x["score"], len(x["official_text"])), reverse=True)
    
    # Return only hazard statements (exclude precautionary)
    hazard_matches = [m for m in matches if m["category"] == "Hazard"]
    return hazard_matches


# if __name__ == "__main__":
#     candidate = input("Enter a candidate GHS phrase: ").strip()
#     results = match_to_pubchem_ghs(candidate, threshold=60)

#     if results:
#         print("\nMatches found (highest score first):")
#         for r in results:
#             print(f"  • [{r['category']}] {r['code']}: “{r['official_text']}” — score {r['score']}")
#     else:
#         print("\nNo matches above threshold.")