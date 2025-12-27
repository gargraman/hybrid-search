import json
from pathlib import Path
from typing import Dict


def summarize_restaurant_json(json_path: str) -> str:
    with open(json_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return summarize_restaurant_dict(data)


def summarize_restaurant_dict(data: Dict) -> str:
    restaurant = data.get("restaurant", {})
    name = restaurant.get("name", "Unknown Restaurant")
    type_ = restaurant.get("type") or ""
    address_data = restaurant.get("address", {})
    address = ", ".join(
        filter(
            None,
            [
                address_data.get("street"),
                address_data.get("city"),
                address_data.get("state"),
            ],
        )
    )
    ratings = data.get("ratings", {})
    avg_rating = ratings.get("average_rating")
    review_count = ratings.get("ezCater_review_count")

    menu = data.get("menu", {})
    groups = menu.get("items", []) if isinstance(menu, dict) else []
    highlights = []
    for group in groups:
        category = group.get("category", "Uncategorized")
        items = [item.get("name") for item in group.get("items", []) if item.get("name")]
        if items:
            highlights.append(f"{category}: {', '.join(items[:3])}")
        if len(highlights) >= 5:
            break

    lines = [f"{name} ({type_})" if type_ else name]
    if address:
        lines.append(f"Address: {address}")
    if avg_rating is not None or review_count is not None:
        rating_line = "Average rating: "
        rating_line += f"{avg_rating}" if avg_rating is not None else "N/A"
        if review_count is not None:
            rating_line += f" ({review_count} reviews)"
        lines.append(rating_line)
    if highlights:
        lines.append("Menu highlights: " + "; ".join(highlights))
    description = restaurant.get("description")
    if description:
        lines.append(f"Description: {description}")
    return "\n".join(lines)


if __name__ == "__main__":
    input_dir = Path("input")
    for file in input_dir.glob("*.json"):
        print(f"Source: {file}")
        print(summarize_restaurant_json(str(file)))
        print()
