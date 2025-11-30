import json
from pathlib import Path
from src.models.restaurant import RestaurantData
from src.db.qdrant import create_collection, upsert_vectors
from src.db.postgres import create_tables, insert_restaurant, insert_menu_item
import asyncio

VECTOR_SIZE = 384
COLLECTION_NAME = "menu_items"

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
                # Dummy embedding for now
                embedding = [float(hash(item.name + category) % 1000) / 1000 for _ in range(VECTOR_SIZE)]
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
