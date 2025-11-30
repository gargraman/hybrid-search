import json
from pathlib import Path
from src.models.restaurant import RestaurantData
from src.db.qdrant import create_collection, upsert_vectors
from src.db.postgres import create_tables, insert_restaurant, insert_menu_item
import asyncio
from sentence_transformers import SentenceTransformer

VECTOR_SIZE = 384
COLLECTION_NAME = "menu_items"
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> list:
    return model.encode([text])[0].tolist()

async def ingest():
    await create_tables()
    create_collection(COLLECTION_NAME, VECTOR_SIZE)
    input_dir = Path("input")
    for file in input_dir.glob("*.json"):
        with open(file, "r") as f:
            data = json.load(f)
        restaurant_data = RestaurantData(**data)
        rest = restaurant_data.restaurant
        rest_id = await insert_restaurant(rest.dict())
        points = []
        for category, items in restaurant_data.menu.items():
            for item in items:
                menu_item = {
                    "restaurant_id": rest_id,
                    "category": category,
                    "name": item.name,
                    "description": getattr(item, "description", None),
                    "price": item.price
                }
                await insert_menu_item(menu_item)
                embedding = get_embedding(f"{rest.name} {category} {item.name} {item.description if hasattr(item, 'description') else ''}")
                points.append({
                    "id": f"{rest.name}_{category}_{item.name}".replace(" ", "_"),
                    "vector": embedding,
                    "payload": {
                        "restaurant_id": rest_id,
                        "category": category,
                        "name": item.name,
                        "description": getattr(item, "description", None),
                        "price": item.price
                    }
                })
        upsert_vectors(COLLECTION_NAME, points)
    print("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(ingest())
