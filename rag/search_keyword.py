import re
import json
from eval import load_questions

ID_PATTERN = r"\d+[-.]\d+[A-Z]?"

def extract_identifiers(question):
    identifiers = re.findall(ID_PATTERN, question)
    return identifiers

if __name__ == "__main__":
    questions = load_questions("eval_questions.jsonl")
    for question in questions:
        print(extract_identifiers(question["question"]))


