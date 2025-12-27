import json
import os
from pathlib import Path
from typing import Dict, List

from config.settings import settings
from src.models.restaurant import RestaurantData
from whoosh.fields import ID, NUMERIC, TEXT, Schema
from whoosh.index import create_in, open_dir


def load_restaurant_data(file_path: str) -> RestaurantData:
    with open(file_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return RestaurantData(**data)


def flatten_menu_items(restaurant_data: RestaurantData) -> List[Dict]:
    restaurant = restaurant_data.restaurant
    items: List[Dict] = []
    for category, menu_items in restaurant_data.menu.items():
        for item in menu_items:
            text = f"{item.name} {item.description or ''}".strip()
            city = restaurant.city or ""
            state = restaurant.state or ""
            latitude = float(restaurant.latitude) if restaurant.latitude is not None else 0.0
            longitude = float(restaurant.longitude) if restaurant.longitude is not None else 0.0
            cuisine = (restaurant.cuisine or "").lower()
            items.append(
                {
                    "id": f"{restaurant.name}_{category}_{item.name}".replace(" ", "_"),
                    "text": text,
                    "metadata": {
                        "restaurant": restaurant.name,
                        "address": restaurant.address,
                        "city": city,
                        "state": state,
                        "latitude": latitude,
                        "longitude": longitude,
                        "cuisine": cuisine,
                        "category": category,
                        "price": item.price,
                        "rating": restaurant.rating,
                        "description": item.description or "",
                        "text": text,
                    },
                }
            )
    return items


def _get_or_create_index():
    schema = Schema(
        id=ID(stored=True),
        text=TEXT(stored=True),
        restaurant=TEXT(stored=True),
        address=TEXT(stored=True),
        city=TEXT(stored=True),
        state=TEXT(stored=True),
        cuisine=TEXT(stored=True),
        category=TEXT(stored=True),
        price=NUMERIC(stored=True, numtype=float),
        rating=NUMERIC(stored=True, numtype=float),
        latitude=NUMERIC(stored=True, numtype=float),
        longitude=NUMERIC(stored=True, numtype=float),
        description=TEXT(stored=True),
    )
    if not os.path.exists(settings.whoosh_index_path):
        os.makedirs(settings.whoosh_index_path, exist_ok=True)
        return create_in(settings.whoosh_index_path, schema)
    return open_dir(settings.whoosh_index_path)


def ingest_to_whoosh(items: List[Dict]):
    index = _get_or_create_index()
    writer = index.writer()
    for item in items:
        metadata = item["metadata"]
        writer.add_document(
            id=item["id"],
            text=item["text"],
            restaurant=metadata["restaurant"],
            address=metadata["address"],
            city=metadata["city"],
            state=metadata["state"],
            cuisine=metadata["cuisine"],
            category=metadata["category"],
            price=float(metadata["price"]),
            rating=float(metadata["rating"]),
            latitude=float(metadata["latitude"]),
            longitude=float(metadata["longitude"]),
            description=metadata["description"],
        )
    writer.commit()


def main():
    input_dir = Path("input")
    if not input_dir.exists():
        raise FileNotFoundError("input directory not found")

    json_files = sorted(input_dir.rglob("*.json"))
    if not json_files:
        print("No input files found")
        return

    for file_path in json_files:
        data = load_restaurant_data(str(file_path))
        items = flatten_menu_items(data)
        ingest_to_whoosh(items)
    print("Whoosh ingestion complete")


if __name__ == "__main__":
    main()