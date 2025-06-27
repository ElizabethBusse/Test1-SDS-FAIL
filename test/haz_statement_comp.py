#!/usr/bin/env python3
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
    """
    hazards, precs = get_pubchem_ghs_phrases()
    matches = []
    low = text.lower()

    for category, phrases in (("Hazard", hazards), ("Precautionary", precs)):
        for code, official in phrases:
            score = fuzz.partial_ratio(low, official.lower())
            if score >= threshold:
                matches.append({
                    "category":      category,
                    "code":          code,
                    "official_text": official,
                    "score":         score
                })

    # sort descending by score
    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches

if __name__ == "__main__":
    candidate = input("Enter a candidate GHS phrase: ").strip()
    results = match_to_pubchem_ghs(candidate, threshold=60)

    if results:
        print("\n✅ Matches found (highest score first):")
        for r in results:
            print(f"  • [{r['category']}] {r['code']}: “{r['official_text']}” — score {r['score']}")
    else:
        print("\n❌ No matches above threshold.")