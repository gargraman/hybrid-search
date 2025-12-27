import json
from pathlib import Path
from typing import Dict, List, Union

# Robust chunking for nested restaurant JSON

def chunk_restaurant_json(json_data: Dict) -> List[Dict]:
    restaurant = json_data.get('restaurant', {})
    restaurant_id = restaurant.get('name', '').replace(' ', '_')
    menu = json_data.get('menu', {})
    items_groups = menu.get('items', []) if isinstance(menu, dict) else []

    chunks: List[Dict] = []
    for group in items_groups:
        category = group.get('category', 'uncategorized')
        for item in group.get('items', []):
            item_name = item.get('name', 'item').replace(' ', '_')
            description = item.get('description', '')
            price = item.get('price', 0)
            rating_info = json_data.get('ratings', {}) or {}
            avg_rating = rating_info.get('average_rating')
            review_count = rating_info.get('ezCater_review_count')
            chunk = {
                "id": f"{restaurant_id}_{category}_{item_name}",
                "text": (
                    f"Restaurant: {restaurant.get('name')} | "
                    f"Category: {category} | "
                    f"Item: {item.get('name')} | "
                    f"Description: {description or 'N/A'} | "
                    f"Price: ${price} | "
                    f"Average Rating: {avg_rating if avg_rating is not None else 'N/A'} | "
                    f"Reviews: {review_count if review_count is not None else 'N/A'}"
                ),
                "metadata": {
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant.get('name'),
                    "category": category,
                    "item_name": item.get('name'),
                    "price": price,
                    "description": description,
                    "average_rating": avg_rating,
                    "review_count": review_count,
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
