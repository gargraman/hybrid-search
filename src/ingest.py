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
    address_line = restaurant.address.as_string()
    city = restaurant.address.city or ""
    state = restaurant.address.state or ""
    location = restaurant.location or None
    latitude = float(location.latitude) if location and location.latitude is not None else 0.0
    longitude = float(location.longitude) if location and location.longitude is not None else 0.0
    cuisine_label = restaurant.cuisine_label()
    rating_value = restaurant_data.primary_rating()
    review_count = restaurant_data.primary_review_count()
    restaurant_description = restaurant.description or ""
    restaurant_history = restaurant.history or ""
    phone = restaurant.contact.phone if restaurant.contact else None
    website = restaurant.contact.website if restaurant.contact else None
    rewards = restaurant.catering_info.rewards if restaurant.catering_info else None

    items: List[Dict] = []
    for category_group in restaurant_data.menu.items or []:
        category_name = category_group.category
        for item in category_group.items:
            item_description = item.description or ""
            text = " ".join(filter(None, [item.name, item_description, restaurant_description]))
            external_id = f"{restaurant.name}_{category_name}_{item.name}".replace(" ", "_")
            items.append(
                {
                    "id": external_id,
                    "text": text.strip(),
                    "metadata": {
                        "restaurant": restaurant.name,
                        "restaurant_type": restaurant.type or "",
                        "address": address_line,
                        "city": city,
                        "state": state,
                        "latitude": latitude,
                        "longitude": longitude,
                        "cuisine": cuisine_label,
                        "category": category_name,
                        "price": float(item.price),
                        "rating": rating_value,
                        "review_count": review_count,
                        "description": item_description,
                        "text": text.strip(),
                        "restaurant_description": restaurant_description,
                        "restaurant_history": restaurant_history,
                        "contact_phone": phone or "",
                        "contact_website": website or "",
                        "rewards": rewards or "",
                    },
                }
            )
    return items


def _get_or_create_index():
    schema = Schema(
        id=ID(stored=True),
        text=TEXT(stored=True),
        restaurant=TEXT(stored=True),
        restaurant_type=TEXT(stored=True),
        address=TEXT(stored=True),
        city=TEXT(stored=True),
        state=TEXT(stored=True),
        cuisine=TEXT(stored=True),
        category=TEXT(stored=True),
        price=NUMERIC(stored=True, numtype=float),
        rating=NUMERIC(stored=True, numtype=float),
        review_count=NUMERIC(stored=True, numtype=int),
        latitude=NUMERIC(stored=True, numtype=float),
        longitude=NUMERIC(stored=True, numtype=float),
        description=TEXT(stored=True),
        restaurant_description=TEXT(stored=True),
        restaurant_history=TEXT(stored=True),
        contact_phone=TEXT(stored=True),
        contact_website=TEXT(stored=True),
        rewards=TEXT(stored=True),
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
            restaurant_type=metadata.get("restaurant_type", ""),
            address=metadata["address"],
            city=metadata["city"],
            state=metadata["state"],
            cuisine=metadata["cuisine"],
            category=metadata["category"],
            price=float(metadata["price"]),
            rating=float(metadata["rating"]),
            review_count=int(metadata.get("review_count", 0)),
            latitude=float(metadata["latitude"]),
            longitude=float(metadata["longitude"]),
            description=metadata["description"],
            restaurant_description=metadata.get("restaurant_description", ""),
            restaurant_history=metadata.get("restaurant_history", ""),
            contact_phone=metadata.get("contact_phone", ""),
            contact_website=metadata.get("contact_website", ""),
            rewards=metadata.get("rewards", ""),
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