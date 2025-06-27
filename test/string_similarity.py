from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

if __name__ == "__main__":
    str1 = input("Enter first string: ").strip()
    str2 = input("Enter second string: ").strip()

    print("\n🔍 String Similarity Comparison:")
    print(f"String 1: {str1}")
    print(f"String 2: {str2}\n")

    print(f"📐 Levenshtein Ratio     : {normalized_levenshtein(str1, str2):.4f}")
    print(f"🧮 Jaccard Similarity     : {jaccard_similarity(str1, str2):.4f}")
    print(f"📊 Cosine Similarity (TF-IDF): {cosine_similarity_score(str1, str2):.4f}")