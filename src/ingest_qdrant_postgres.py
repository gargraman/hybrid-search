"""
Data ingestion script for Qdrant + PostgreSQL.

Reads restaurant JSON files and populates:
1. PostgreSQL with restaurant and menu item metadata
2. Qdrant with vector embeddings for semantic search
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Optional
import asyncpg

from sentence_transformers import SentenceTransformer

from src.db.postgres import create_tables, insert_restaurant, insert_menu_item
from src.db.qdrant import create_collection, upsert_vectors
from src.models.restaurant import RestaurantData
from config.db_config import POSTGRES_DSN

VECTOR_SIZE = 384
COLLECTION_NAME = "menu_items"

# Initialize embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')


def get_embedding(text: str) -> list:
    """Generate embedding vector for text."""
    return model.encode([text])[0].tolist()


def parse_currency(value: Optional[str]) -> float:
    """Parse currency string to float."""
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
    """
    Ingest restaurant data into PostgreSQL and Qdrant.

    Creates connection pool for efficient database operations.
    Processes all JSON files in the input directory.
    """
    # Create connection pool for efficient database operations
    print("Creating database connection pool...")
    pool = await asyncpg.create_pool(
        POSTGRES_DSN,
        min_size=2,
        max_size=10,
        timeout=30,
        command_timeout=60
    )

    try:
        # Create database tables
        print("Creating database tables...")
        await create_tables(pool)

        # Create Qdrant collection
        print("Creating Qdrant collection...")
        create_collection(COLLECTION_NAME, VECTOR_SIZE)

        # Process all JSON files
        input_dir = Path("input")
        json_files = sorted(input_dir.rglob("*.json"))
        print(f"Found {len(json_files)} restaurant files to process...")

        for idx, file in enumerate(json_files, 1):
            print(f"Processing {idx}/{len(json_files)}: {file.name}")

            with file.open("r", encoding="utf-8") as f:
                data = json.load(f)

            restaurant_data = RestaurantData(**data)
            rest = restaurant_data.restaurant

            # Extract restaurant metadata
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

            # Prepare restaurant payload for PostgreSQL
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

            # Insert restaurant (using connection pool)
            rest_id = await insert_restaurant(pool, rest_payload)

            # Process menu items
            points = []
            for category_group in restaurant_data.menu.items:
                category = category_group.category
                for item in category_group.items:
                    external_id = f"{rest.name}_{category}_{item.name}".replace(" ", "_")

                    # Prepare menu item payload for PostgreSQL
                    menu_item = {
                        "restaurant_id": rest_id,
                        "category": category,
                        "name": item.name,
                        "description": getattr(item, "description", None),
                        "price": float(item.price),
                        "external_id": external_id,
                    }

                    # Insert menu item (using connection pool)
                    await insert_menu_item(pool, menu_item)

                    # Prepare text blob for embedding
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

                    # Generate embedding
                    embedding = get_embedding(text_blob)

                    # Prepare Qdrant point with rich payload
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

            # Upsert vectors to Qdrant (batch per restaurant)
            if points:
                upsert_vectors(COLLECTION_NAME, points)
                print(f"  Ingested {len(points)} menu items for {rest.name}")

        print(f"\nIngestion complete! Processed {len(json_files)} restaurants.")

    finally:
        # Close connection pool
        print("Closing database connection pool...")
        await pool.close()


if __name__ == "__main__":
    asyncio.run(ingest())
