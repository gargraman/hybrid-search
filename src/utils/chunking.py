from docling import Document
from typing import List, Dict

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
    import json
    with open("input/restaurant1.json", "r") as f:
        data = json.load(f)
    chunks = chunk_restaurant_json(data)
    assert validate_chunks(chunks), "Chunk validation failed!"
    for chunk in chunks[:2]:
        print(chunk)
