from rapidfuzz import fuzz

def compare_statements(s1, s2):
    print(f"\n📋 Statement 1: {s1}")
    print(f"📋 Statement 2: {s2}\n")
    
    print("🔍 Similarity Scores:")
    print(f" - Ratio: {fuzz.ratio(s1, s2):.2f}")
    print(f" - Partial Ratio: {fuzz.partial_ratio(s1, s2):.2f}")
    print(f" - Token Sort Ratio: {fuzz.token_sort_ratio(s1, s2):.2f}")
    print(f" - Token Set Ratio: {fuzz.token_set_ratio(s1, s2):.2f}")

if __name__ == "__main__":
    print("=== Fuzzy Statement Similarity Tester ===")
    while True:
        s1 = input("\nEnter first statement (or 'q' to quit): ").strip()
        if s1.lower() == 'q':
            break
        s2 = input("Enter second statement: ").strip()
        compare_statements(s1, s2)