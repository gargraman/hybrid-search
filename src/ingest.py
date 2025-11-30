def main():
    input_dir = Path("input")
    for file in input_dir.glob("*.json"):
        data = load_restaurant_data(str(file))
        items = flatten_menu_items(data)
        # For production semantic ingestion, use src/ingest_qdrant_postgres.py
        ingest_to_whoosh(items)
        try:
            ingest_to_elasticsearch(items)
        except Exception as e:
            print(f"Elasticsearch not available: {e}")
    print("Ingestion complete")


if __name__ == "__main__":
    main()
import json
import os
from pathlib import Path
from typing import List, Dict
from src.models.restaurant import RestaurantData, MenuItem
from config.settings import settings
## ChromaDB ingestion removed; use Qdrant+PostgreSQL for production semantic ingestion
from whoosh.index import create_in, open_dir
from whoosh.fields import Schema, TEXT, ID, NUMERIC
from whoosh.qparser import QueryParser
from elasticsearch import Elasticsearch

# For POC, use deterministic hash-based embeddings (consistent but not semantic)
# Note: SSL issues prevent downloading real models; replace with sentence-transformers in production


def load_restaurant_data(file_path: str) -> RestaurantData:
    with open(file_path, 'r') as f:
        data = json.load(f)
    return RestaurantData(**data)

def flatten_menu_items(restaurant_data: RestaurantData) -> List[Dict]:
    items = []
    restaurant = restaurant_data.restaurant
    for category, menu_items in restaurant_data.menu.items():
        for item in menu_items:
            text = f"{item.name} {item.description or ''}".strip()
            items.append({
                "id": f"{restaurant.name}_{category}_{item.name}".replace(" ", "_"),
                "text": text,
                "metadata": {
                    "restaurant": restaurant.name,
                    "address": restaurant.address,
                    "category": category,
                    "price": item.price,
                    "rating": restaurant.rating
                }
            })
    return items



def ingest_to_whoosh(items: List[Dict]):
    schema = Schema(id=ID(stored=True), text=TEXT(stored=True), restaurant=TEXT, price=NUMERIC(numtype=int))
    if not os.path.exists(settings.whoosh_index_path):
        os.mkdir(settings.whoosh_index_path)
        ix = create_in(settings.whoosh_index_path, schema)
    else:
        ix = open_dir(settings.whoosh_index_path)
    writer = ix.writer()
    for item in items:
        # Store price as int (cents) for Whoosh compatibility
        price = int(float(item["metadata"]["price"]) * 100)
        writer.add_document(
            id=item["id"],
            text=item["text"],
            restaurant=item["metadata"]["restaurant"],
            price=price
        )
    writer.commit()

def ingest_to_elasticsearch(items: List[Dict]):
    es = Elasticsearch([{"host": settings.es_host, "port": settings.es_port, "scheme": settings.es_scheme}])
    for item in items:
        es.index(index="menu_items", id=item["id"], body={
            "text": item["text"],
            **item["metadata"]
        })

    input_dir = Path("input")
    for file in input_dir.glob("*.json"):
        data = load_restaurant_data(str(file))
        items = flatten_menu_items(data)
        # For production semantic ingestion, use src/ingest_qdrant_postgres.py
        ingest_to_whoosh(items)
        try:
            ingest_to_elasticsearch(items)
        except Exception as e:
            print(f"Elasticsearch not available: {e}")
    print("Ingestion complete")


# Ensure main is defined before calling
if __name__ == "__main__":
    main()