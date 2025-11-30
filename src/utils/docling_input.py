from docling import Document
import json
from pathlib import Path

# Parse restaurant JSON using docling for LLM context

def parse_restaurant_json_with_docling(json_path: str):
    with open(json_path, 'r') as f:
        data = json.load(f)
    # Convert JSON to docling Document
    doc = Document.from_dict(data)
    # Extract structured text for LLM prompt
    return doc.to_text()

# Example usage for feeding LLM
if __name__ == "__main__":
    input_dir = Path("input")
    for file in input_dir.glob("*.json"):
        llm_context = parse_restaurant_json_with_docling(str(file))
        print(llm_context)
