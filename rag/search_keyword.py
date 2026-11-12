import re
from search_vector import load_index

ID_PATTERN = r"\d+[-.]\d+[A-Z]?"

def extract_identifiers(question):
    identifiers = re.findall(ID_PATTERN, question)
    return identifiers

def search(question, records):
    identifiers = extract_identifiers(question) 
    if not identifiers:    
        return []
    else:
        patterns = [rf"(?<![\d/]){re.escape(ident)}(?!\d)" for ident in identifiers]
        matches = [r for r in records if any(re.search(p, r["text"], re.IGNORECASE) for p in patterns)]
        return matches
        
if __name__ == "__main__":
    records = load_index("embeddings.json")
    for r in search("How much trouble is turbulence?", records):
        print(r["source_file"], r["page_start"])

