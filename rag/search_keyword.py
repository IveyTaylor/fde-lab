import re
import json
from eval import load_questions
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
        pattern = rf"(?<![\d/]){re.escape(identifiers[0])}(?!\d)"
        matches = [r for r in records if re.search(pattern, r["text"], re.IGNORECASE)]
        return matches
        
if __name__ == "__main__":
    questions = load_questions("eval_questions.jsonl")
    for question in questions:
        print(extract_identifiers(question["question"]))

    records = load_index("embeddings.json")
    for r in search("How much does AC 00-45D cost?", records):
        print(r["source_file"], r["page_start"])

