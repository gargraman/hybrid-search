import json
import random
from pathlib import Path
from typing import Dict, List, Any

SEED_COUNT = 200
OUTPUT_DIR = Path("input/seed")

CITIES = [
    ("New York", "NY"),
    ("San Francisco", "CA"),
    ("Los Angeles", "CA"),
    ("Chicago", "IL"),
    ("Austin", "TX"),
    ("Boston", "MA"),
    ("Seattle", "WA"),
    ("Denver", "CO"),
    ("Atlanta", "GA"),
    ("Miami", "FL"),
    ("Portland", "OR"),
    ("Dallas", "TX"),
    ("Houston", "TX"),
    ("Philadelphia", "PA"),
    ("Phoenix", "AZ"),
    ("San Diego", "CA"),
    ("Nashville", "TN"),
    ("Charlotte", "NC"),
    ("Minneapolis", "MN"),
    ("Washington", "DC"),
]

CUISINES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "italian": {
        "pasta": [
            {"name": "Spaghetti Carbonara", "description": "Classic carbonara with guanciale", "price": 15.95},
            {"name": "Fettuccine Alfredo", "price": 14.5},
            {"name": "Penne Arrabbiata", "price": 13.75},
        ],
        "pizza": [
            {"name": "Margherita Pizza", "description": "San Marzano tomatoes, mozzarella, basil", "price": 18.0},
            {"name": "Prosciutto Pizza", "price": 19.5},
            {"name": "Funghi Pizza", "price": 17.5},
        ],
        "antipasti": [
            {"name": "Bruschetta Trio", "price": 10.25},
            {"name": "Arancini", "price": 11.0},
        ],
        "desserts": [
            {"name": "Tiramisu", "price": 6.5},
            {"name": "Panna Cotta", "price": 6.0},
        ],
        "beverages": [
            {"name": "San Pellegrino", "price": 3.75},
            {"name": "Italian Soda", "price": 4.25},
        ],
    },
    "mexican": {
        "tacos": [
            {"name": "Al Pastor Taco", "price": 4.5},
            {"name": "Carne Asada Taco", "price": 4.75},
            {"name": "Veggie Taco", "price": 4.0},
        ],
        "burritos": [
            {"name": "Chicken Burrito", "price": 11.25},
            {"name": "Carnitas Burrito", "price": 11.95},
            {"name": "Barbacoa Burrito", "price": 12.5},
        ],
        "bowls": [
            {"name": "Chicken Fajita Bowl", "price": 12.25},
            {"name": "Steak Fajita Bowl", "price": 13.5},
            {"name": "Veggie Bowl", "price": 11.75},
        ],
        "sides": [
            {"name": "Chips & Salsa", "price": 5.0},
            {"name": "Queso Dip", "price": 6.0},
            {"name": "Elote", "price": 5.5},
        ],
        "desserts": [
            {"name": "Churros", "price": 4.75},
            {"name": "Mexican Chocolate Brownie", "price": 5.0},
        ],
    },
    "japanese": {
        "sushi": [
            {"name": "Salmon Nigiri", "price": 5.5},
            {"name": "Spicy Tuna Roll", "price": 6.75},
            {"name": "Avocado Roll", "price": 5.0},
        ],
        "ramen": [
            {"name": "Tonkotsu Ramen", "price": 14.0},
            {"name": "Shoyu Ramen", "price": 13.0},
            {"name": "Miso Ramen", "price": 13.5},
        ],
        "bento": [
            {"name": "Chicken Teriyaki Bento", "price": 16.5},
            {"name": "Salmon Bento", "price": 17.25},
            {"name": "Tofu Bento", "price": 15.25},
        ],
        "appetizers": [
            {"name": "Edamame", "price": 4.25},
            {"name": "Gyoza", "price": 6.25},
        ],
        "desserts": [
            {"name": "Mochi Ice Cream", "price": 4.5},
            {"name": "Matcha Cheesecake", "price": 5.75},
        ],
    },
    "indian": {
        "curries": [
            {"name": "Butter Chicken", "price": 13.5},
            {"name": "Palak Paneer", "price": 12.25},
            {"name": "Lamb Rogan Josh", "price": 14.75},
        ],
        "tandoor": [
            {"name": "Chicken Tikka", "price": 13.25},
            {"name": "Paneer Tikka", "price": 12.5},
            {"name": "Tandoori Shrimp", "price": 15.5},
        ],
        "biryani": [
            {"name": "Chicken Biryani", "price": 13.75},
            {"name": "Vegetable Biryani", "price": 12.5},
            {"name": "Goat Biryani", "price": 14.5},
        ],
        "breads": [
            {"name": "Garlic Naan", "price": 3.5},
            {"name": "Butter Naan", "price": 3.25},
            {"name": "Roti", "price": 2.75},
        ],
        "desserts": [
            {"name": "Gulab Jamun", "price": 4.5},
            {"name": "Kheer", "price": 4.25},
        ],
    },
    "mediterranean": {
        "mezze": [
            {"name": "Hummus Platter", "price": 8.5},
            {"name": "Falafel", "price": 7.75},
            {"name": "Baba Ghanoush", "price": 8.0},
        ],
        "wraps": [
            {"name": "Chicken Shawarma Wrap", "price": 11.5},
            {"name": "Beef Gyro Wrap", "price": 11.75},
            {"name": "Falafel Wrap", "price": 10.5},
        ],
        "plates": [
            {"name": "Mixed Grill Plate", "price": 16.5},
            {"name": "Salmon Kabob Plate", "price": 17.75},
            {"name": "Veggie Platter", "price": 14.0},
        ],
        "salads": [
            {"name": "Greek Salad", "price": 10.0},
            {"name": "Tabbouleh", "price": 9.25},
        ],
        "desserts": [
            {"name": "Baklava", "price": 4.75},
            {"name": "Orange Blossom Cake", "price": 5.25},
        ],
    },
    "thai": {
        "noodles": [
            {"name": "Pad Thai", "price": 12.5},
            {"name": "Pad See Ew", "price": 12.25},
            {"name": "Drunken Noodles", "price": 12.75},
        ],
        "curries": [
            {"name": "Green Curry", "price": 13.25},
            {"name": "Panang Curry", "price": 13.5},
            {"name": "Massaman Curry", "price": 13.75},
        ],
        "rice": [
            {"name": "Thai Basil Fried Rice", "price": 12.0},
            {"name": "Pineapple Fried Rice", "price": 12.25},
        ],
        "appetizers": [
            {"name": "Fresh Spring Rolls", "price": 6.5},
            {"name": "Chicken Satay", "price": 7.25},
        ],
        "desserts": [
            {"name": "Mango Sticky Rice", "price": 5.5},
            {"name": "Thai Tea Cheesecake", "price": 5.25},
        ],
    },
    "american": {
        "burgers": [
            {"name": "Classic Angus Burger", "price": 12.5},
            {"name": "BBQ Bacon Burger", "price": 13.75},
            {"name": "Veggie Burger", "price": 11.25},
        ],
        "sandwiches": [
            {"name": "Turkey Club", "price": 11.5},
            {"name": "Fried Chicken Sandwich", "price": 12.75},
            {"name": "Pulled Pork Sandwich", "price": 12.5},
        ],
        "salads": [
            {"name": "Cobb Salad", "price": 11.25},
            {"name": "Kale Caesar", "price": 10.75},
        ],
        "sides": [
            {"name": "Truffle Fries", "price": 5.5},
            {"name": "Sweet Potato Fries", "price": 5.25},
            {"name": "Mac & Cheese", "price": 6.25},
        ],
        "desserts": [
            {"name": "New York Cheesecake", "price": 5.75},
            {"name": "Apple Pie", "price": 5.25},
        ],
    },
    "middle_eastern": {
        "grills": [
            {"name": "Chicken Kabob", "price": 13.25},
            {"name": "Beef Kofta", "price": 13.5},
            {"name": "Lamb Kabob", "price": 14.75},
        ],
        "mezze": [
            {"name": "Hummus Trio", "price": 8.75},
            {"name": "Stuffed Grape Leaves", "price": 7.5},
            {"name": "Labneh", "price": 6.75},
        ],
        "wraps": [
            {"name": "Chicken Shawarma Wrap", "price": 11.0},
            {"name": "Falafel Wrap", "price": 10.25},
            {"name": "Beef Shawarma Wrap", "price": 11.5},
        ],
        "sides": [
            {"name": "Turmeric Rice", "price": 4.75},
            {"name": "Roasted Cauliflower", "price": 5.75},
        ],
        "desserts": [
            {"name": "Pistachio Baklava", "price": 4.75},
            {"name": "Semolina Cake", "price": 4.5},
        ],
    },
}

DELIVERY_WINDOWS = [
    "10am–9pm",
    "11am–8pm",
    "11am–10pm",
    "12pm–9pm",
    "7am–2pm",
]

TAKEOUT_WINDOWS = [
    "10am–10pm",
    "11am–9pm",
    "12pm–11pm",
    "8am–3pm",
    "7am–8pm",
]

ABOUT_DESCRIPTIONS = [
    "Family-owned spot known for catering corporate lunches and private events.",
    "Chef-driven restaurant specializing in seasonal ingredients and regional flavors.",
    "Popular local favorite offering customizable catering packages for events of all sizes.",
    "Fast-casual concept focused on fresh, made-to-order dishes for modern teams.",
    "Award-winning kitchen with a focus on sustainable sourcing and bold flavors.",
]

ONBOARDING_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


def rand_range(low: float, high: float, precision: int = 2) -> float:
    return round(random.uniform(low, high), precision)


def build_restaurant(index: int) -> Dict[str, Any]:
    cuisine_name, cuisine_data = random.choice(list(CUISINES.items()))
    city, state = random.choice(CITIES)
    restaurant_name = f"{cuisine_name.title()} Table {index:03d}"

    delivery_hours = {"mon_sun": random.choice(DELIVERY_WINDOWS)}
    takeout_hours = {"mon_sun": random.choice(TAKEOUT_WINDOWS)}

    restaurant = {
        "name": restaurant_name,
        "address": f"{random.randint(100, 999)} {random.choice(['Main St', 'Market St', 'Elm St', 'Broadway', 'Sunset Blvd', 'Lakeview Ave'])}, {city}, {state} {random.randint(10000, 99999)}",
        "rating": rand_range(3.6, 4.9, 1),
        "review_count": random.randint(80, 2600),
        "on_time_rate": f"{random.randint(90, 100)}%",
        "delivery_fee": rand_range(0, 45, 2),
        "delivery_minimum": rand_range(80, 250, 2),
        "delivery_hours": delivery_hours,
        "takeout_hours": takeout_hours,
    }

    menu: Dict[str, List[Dict[str, Any]]] = {}
    category_names = list(cuisine_data.keys())
    for category in category_names:
        items = cuisine_data[category]
        selected_items = random.sample(items, k=min(len(items), random.randint(2, len(items))))
        menu[category] = selected_items

    menu = {category: [dict(item) for item in items] for category, items in menu.items()}

    onboard_month = random.choice(ONBOARDING_MONTHS)
    onboard_day = random.randint(1, 28)
    onboard_year = random.randint(2017, 2025)

    about_section = {
        "on_ezCater_since": f"{onboard_month} {onboard_day}, {onboard_year}",
        "description": random.choice(ABOUT_DESCRIPTIONS),
    }

    return {
        "restaurant": restaurant,
        "menu": menu,
        "about": about_section,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for idx in range(1, SEED_COUNT + 1):
        data = build_restaurant(idx)
        output_path = OUTPUT_DIR / f"restaurant_{idx:03d}.json"
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    random.seed(42)
    main()
