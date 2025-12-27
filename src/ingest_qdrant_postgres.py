import asyncio
import json
import re
from pathlib import Path
from typing import Optional

from sentence_transformers import SentenceTransformer

from src.db.postgres import create_tables, insert_restaurant, insert_menu_item
from src.db.qdrant import create_collection, upsert_vectors
from src.models.restaurant import RestaurantData

VECTOR_SIZE = 384
COLLECTION_NAME = "menu_items"
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> list:
    return model.encode([text])[0].tolist()


def parse_currency(value: Optional[str]) -> float:
    if not value:
        return 0.0
    cleaned = value.replace(",", "")
    matches = re.findall(r"[-+]?[0-9]*\.?[0-9]+", cleaned)
    if not matches:
        return 0.0
    try:
        return float(matches[0])
    except ValueError:
        return 0.0

async def ingest():
    await create_tables()
    create_collection(COLLECTION_NAME, VECTOR_SIZE)
    input_dir = Path("input")
    json_files = sorted(input_dir.rglob("*.json"))
    for file in json_files:
        with file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        restaurant_data = RestaurantData(**data)
        rest = restaurant_data.restaurant
        address_line = rest.address.as_string()
        city = rest.address.city or ""
        state = rest.address.state or ""
        location = rest.location or None
        latitude = float(location.latitude) if location and location.latitude is not None else 0.0
        longitude = float(location.longitude) if location and location.longitude is not None else 0.0
        cuisine_label = rest.cuisine_label()
        rating_value = restaurant_data.primary_rating()
        review_count = restaurant_data.primary_review_count()
        catering = rest.catering_info
        contact = rest.contact

        rest_payload = {
            "name": rest.name,
            "address": address_line,
            "city": city,
            "state": state,
            "latitude": latitude,
            "longitude": longitude,
            "cuisine": cuisine_label,
            "rating": rating_value,
            "review_count": review_count,
            "on_time_rate": "N/A",
            "delivery_fee": parse_currency(catering.delivery_fee if catering else None),
            "delivery_minimum": parse_currency(catering.delivery_minimum if catering else None),
        }

        rest_id = await insert_restaurant(rest_payload)
        points = []
        for category_group in restaurant_data.menu.items:
            category = category_group.category
            for item in category_group.items:
                external_id = f"{rest.name}_{category}_{item.name}".replace(" ", "_")
                menu_item = {
                    "restaurant_id": rest_id,
                    "category": category,
                    "name": item.name,
                    "description": getattr(item, "description", None),
                    "price": float(item.price),
                    "external_id": external_id,
                }
                await insert_menu_item(menu_item)
                item_description = getattr(item, "description", "")
                text_blob = " ".join(
                    filter(
                        None,
                        [
                            rest.name,
                            rest.type,
                            category,
                            item.name,
                            item_description,
                            rest.description,
                        ],
                    )
                ).strip()
                embedding = get_embedding(text_blob)
                points.append({
                    "id": external_id,
                    "vector": embedding,
                    "payload": {
                        "restaurant_id": rest_id,
                        "restaurant_name": rest.name,
                        "restaurant_type": rest.type or "",
                        "address": address_line,
                        "city": city,
                        "state": state,
                        "latitude": latitude,
                        "longitude": longitude,
                        "cuisine": cuisine_label,
                        "rating": rating_value,
                        "review_count": review_count,
                        "restaurant_description": rest.description,
                        "restaurant_history": rest.history,
                        "contact_phone": contact.phone if contact else None,
                        "contact_website": contact.website if contact else None,
                        "rewards": catering.rewards if catering else None,
                        "delivery_fee": rest_payload["delivery_fee"],
                        "delivery_minimum": rest_payload["delivery_minimum"],
                        "category": category,
                        "name": item.name,
                        "description": item_description,
                        "price": float(item.price),
                        "text": text_blob,
                    }
                })
        upsert_vectors(COLLECTION_NAME, points)
    print("Ingestion complete.")

if __name__ == "__main__":
    asyncio.run(ingest())
