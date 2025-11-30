import json
from pathlib import Path
from docling import Document  # type: ignore
from typing import List, Dict, Union

# Robust chunking for nested restaurant JSON

def chunk_restaurant_json(json_data: Dict) -> List[Dict]:
    doc = Document.from_dict(json_data)
    restaurant = json_data.get('restaurant', {})
    restaurant_id = restaurant.get('name', '').replace(' ', '_')
    chunks = []
    for category, items in json_data.get('menu', {}).items():
        for item in items:
            chunk = {
                "id": f"{restaurant_id}_{category}_{item['name'].replace(' ', '_')}",
                "text": f"Restaurant: {restaurant.get('name')} | Category: {category} | Item: {item['name']} | Description: {item.get('description', '')} | Price: ${item['price']}",
                "metadata": {
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant.get('name'),
                    "category": category,
                    "item_name": item['name'],
                    "price": item['price'],
                    "description": item.get('description', '')
                }
            }
            chunks.append(chunk)
    return chunks


def chunk_restaurant_directory(input_path: Union[str, Path]) -> List[Dict]:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Input path not found: {path}")

    aggregated: List[Dict] = []
    for json_file in path.rglob("*.json"):
        with json_file.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        file_chunks = chunk_restaurant_json(data)
        for chunk in file_chunks:
            chunk["metadata"]["source_file"] = str(json_file)
        aggregated.extend(file_chunks)
    return aggregated

# Validation function to ensure no cross-matching and all context is present
def validate_chunks(chunks: List[Dict]) -> bool:
    for chunk in chunks:
        meta = chunk['metadata']
        if not meta.get('restaurant_id') or not meta.get('category') or not meta.get('item_name'):
            return False
        if not chunk['id'].startswith(meta['restaurant_id']):
            return False
    return True

# Example usage
if __name__ == "__main__":
    chunks = chunk_restaurant_directory(Path("input"))
    assert validate_chunks(chunks), "Chunk validation failed!"
    for chunk in chunks[:2]:
        print(chunk)
