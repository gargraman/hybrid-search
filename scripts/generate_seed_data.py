import json
import random
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timedelta

SEED_COUNT = 500
OUTPUT_DIR = Path("input/seed")

CITIES = [
    ("New York", "NY", 40.7128, -74.0060),
    ("San Francisco", "CA", 37.7749, -122.4194),
    ("Los Angeles", "CA", 34.0522, -118.2437),
    ("Chicago", "IL", 41.8781, -87.6298),
    ("Austin", "TX", 30.2672, -97.7431),
    ("Boston", "MA", 42.3601, -71.0589),
    ("Seattle", "WA", 47.6062, -122.3321),
    ("Denver", "CO", 39.7392, -104.9903),
    ("Atlanta", "GA", 33.7490, -84.3880),
    ("Miami", "FL", 25.7617, -80.1918),
    ("Portland", "OR", 45.5152, -122.6784),
    ("Dallas", "TX", 32.7767, -96.7970),
    ("Houston", "TX", 29.7604, -95.3698),
    ("Philadelphia", "PA", 39.9526, -75.1652),
    ("Phoenix", "AZ", 33.4484, -112.0740),
    ("San Diego", "CA", 32.7157, -117.1611),
    ("Nashville", "TN", 36.1627, -86.7816),
    ("Charlotte", "NC", 35.2271, -80.8431),
    ("Minneapolis", "MN", 44.9778, -93.2650),
    ("Washington", "DC", 38.9072, -77.0369),
]

STREET_NAMES = [
    "Main St", "Market St", "Elm St", "Broadway", "Sunset Blvd",
    "Lakeview Ave", "Province St", "Milk St", "Washington St",
    "Park Ave", "Ocean Dr", "State St", "1st Ave", "2nd St"
]

RESTAURANT_NAME_PREFIXES = {
    "sandwich": ["Sam's", "Max's", "Tony's", "Corner", "Downtown"],
    "italian": ["Angelo's", "La Trattoria", "Bella", "Giuseppe's", "Villa"],
    "mexican": ["El Mariachi", "La Casa", "Fiesta", "Taqueria", "Casa"],
    "japanese": ["Sushi", "Sakura", "Tokyo", "Ramen", "Izakaya"],
    "indian": ["Tandoori", "Curry", "Spice", "Bombay", "Delhi"],
    "mediterranean": ["Mediterranean", "Olive", "Petra", "Cedars", "Athens"],
    "thai": ["Thai", "Bangkok", "Siam", "Phuket", "Jasmine"],
    "american": ["The Burger", "Grill House", "American", "Classic", "Diner"],
    "middle_eastern": ["Shawarma", "Falafel", "Kebab", "Levant", "Arabian"],
}

RESTAURANT_NAME_SUFFIXES = {
    "sandwich": ["Deli", "Sandwich Shop", "Cafe", "Market", "Company"],
    "italian": ["Kitchen", "Ristorante", "Cucina", "Bistro", "House"],
    "mexican": ["Grill", "Cantina", "Kitchen", "Cocina", "Express"],
    "japanese": ["Bar", "House", "Kitchen", "Express", "Grill"],
    "indian": ["Palace", "Kitchen", "House", "Grill", "Express"],
    "mediterranean": ["Grill", "Kitchen", "Cafe", "House", "Express"],
    "thai": ["Kitchen", "Cuisine", "House", "Bistro", "Express"],
    "american": ["Joint", "House", "Kitchen", "Grill", "Cafe"],
    "middle_eastern": ["House", "Kitchen", "Grill", "Cafe", "Express"],
}

REVIEW_SOURCES = ["ezCater", "TripAdvisor", "Yelp", "Grubhub", "Google"]

REVIEW_TEMPLATES = [
    "Can't go wrong! Always order again, {item} fresh and delicious.",
    "Whole company order for {count} people; food was demolished. {item} raved about.",
    "Expensive but worth it; best {item} and efficient service.",
    "{item} large and delicious; very good value.",
    "Probably the best {item} ever had. Generous portion.",
    "Reliable good {cuisine} food!",
    "Huge catering delivery; friendly staff and fast order pickup.",
    "Best {cuisine} worldwide; {item} amazing.",
    "Great {cuisine} but pricey.",
    "Perfect for office catering. {item} was a hit!",
    "Food was demolished. Everyone loved the {item}.",
    "Always our go-to for corporate events.",
    "Delivery was on time and food was hot."
]

ABOUT_DESCRIPTIONS = [
    "Family-owned since {year}, legendary {cuisine} and corporate catering.",
    "Chef-driven restaurant specializing in seasonal ingredients and regional flavors.",
    "Popular local favorite offering customizable catering packages for events of all sizes.",
    "Fast-casual concept focused on fresh, made-to-order dishes for modern teams.",
    "Award-winning kitchen with a focus on sustainable sourcing and bold flavors.",
    "Known nationwide for premium {cuisine} and corporate catering.",
    "Family-operated with handcrafted ingredients and authentic recipes."
]

# Comprehensive cuisine data matching sample.json format
CUISINES = {
    "sandwich": {
        "type": "Catering & Sandwich Shop",
        "history": "Family-owned restaurant known for premium sandwiches and corporate catering.",
        "categories": ["All-in-One Orders", "Luncheon Packages", "Bagged Lunches", "Specialty Sandwiches",
                      "Build Your Own Sandwiches", "Salads", "Sides", "Desserts", "Beverages"],
        "menu_items": [
            {"category": "Luncheon Packages", "name": "Medley Deluxe Sandwich Lunch Package",
             "description": "Choice of sandwiches with potato chips, dessert, beverage. Sandwiches cut in half and labeled.", "price": 35.50},
            {"category": "Luncheon Packages", "name": "Corporate Deluxe Sandwich Lunch Package",
             "description": "Choice of sandwiches with garden salad, pasta salad, chips, dessert, beverage.", "price": 45.50},
            {"category": "Bagged Lunches", "name": "Medley Deluxe Bagged Lunch",
             "description": "Individually bagged sandwich, chips, dessert, assorted drinks.", "price": 37.50},
            {"category": "Specialty Sandwiches", "name": "Pastrami Reuben Sandwich",
             "description": "Premium pastrami, Swiss, sauerkraut, Russian dressing", "price": 27.95},
            {"category": "Specialty Sandwiches", "name": "Turkey Club Sandwich",
             "description": "Roasted turkey, bacon, lettuce, tomato, mayo", "price": 22.95},
            {"category": "Specialty Sandwiches", "name": "Italian Sub",
             "description": "Salami, ham, provolone, lettuce, tomato, Italian dressing", "price": 24.95},
            {"category": "Build Your Own Sandwiches", "name": "Roast Turkey Sandwich", "price": 18.95},
            {"category": "Build Your Own Sandwiches", "name": "Roast Beef Sandwich", "price": 19.95},
            {"category": "Salads", "name": "Garden Salad", "price": 10.95},
            {"category": "Salads", "name": "Caesar Salad", "price": 12.95},
            {"category": "Sides", "name": "Bag of Chips", "price": 2.50},
            {"category": "Sides", "name": "Pasta Salad Tray", "price": 35.70},
            {"category": "Desserts", "name": "Chocolate Chip Cookie", "price": 3.95},
            {"category": "Desserts", "name": "Fudge Nut Brownie", "price": 3.95},
            {"category": "Beverages", "name": "Poland Springs Water", "price": 2.75},
            {"category": "Beverages", "name": "Coke Can", "price": 2.75},
        ],
        "signature_items": ["Pastrami Reuben Sandwich", "Turkey Club Sandwich", "Italian Sub"]
    },
    "italian": {
        "type": "Italian Restaurant & Catering",
        "history": "Authentic Italian cuisine with family recipes passed down through generations.",
        "categories": ["All-in-One Orders", "Luncheon Packages", "Pasta", "Pizza", "Antipasti", "Salads", "Desserts", "Beverages"],
        "menu_items": [
            {"category": "Luncheon Packages", "name": "Deluxe Italian Lunch Package",
             "description": "Choice of pasta or pizza with salad, dessert, beverage.", "price": 38.50},
            {"category": "Pasta", "name": "Spaghetti Carbonara",
             "description": "Classic carbonara with guanciale and pecorino", "price": 18.95},
            {"category": "Pasta", "name": "Fettuccine Alfredo",
             "description": "Creamy parmesan sauce", "price": 16.50},
            {"category": "Pasta", "name": "Lasagna Bolognese",
             "description": "Layered pasta with meat sauce and bechamel", "price": 19.95},
            {"category": "Pizza", "name": "Margherita Pizza",
             "description": "San Marzano tomatoes, fresh mozzarella, basil", "price": 22.00},
            {"category": "Pizza", "name": "Prosciutto Pizza",
             "description": "Prosciutto di Parma, arugula, parmesan", "price": 24.50},
            {"category": "Antipasti", "name": "Bruschetta Trio",
             "description": "Tomato basil, olive tapenade, roasted pepper", "price": 12.25},
            {"category": "Salads", "name": "Caesar Salad",
             "description": "Romaine, parmesan, croutons, Caesar dressing", "price": 11.95},
            {"category": "Desserts", "name": "Tiramisu", "price": 7.50},
            {"category": "Desserts", "name": "Cannoli", "price": 6.50},
            {"category": "Beverages", "name": "San Pellegrino Sparkling Water", "price": 3.75},
        ],
        "signature_items": ["Spaghetti Carbonara", "Margherita Pizza", "Tiramisu"]
    },
    "mexican": {
        "type": "Mexican Restaurant & Catering",
        "history": "Authentic Mexican cuisine with fresh ingredients and traditional recipes.",
        "categories": ["All-in-One Orders", "Luncheon Packages", "Tacos", "Burritos", "Bowls", "Sides", "Desserts", "Beverages"],
        "menu_items": [
            {"category": "Luncheon Packages", "name": "Taco Bar Package",
             "description": "Build-your-own taco bar with choice of proteins, toppings, sides", "price": 32.50},
            {"category": "Tacos", "name": "Al Pastor Taco",
             "description": "Marinated pork, pineapple, cilantro, onions", "price": 4.50},
            {"category": "Tacos", "name": "Carne Asada Taco",
             "description": "Grilled steak, cilantro, onions, lime", "price": 4.75},
            {"category": "Burritos", "name": "Chicken Burrito",
             "description": "Grilled chicken, rice, beans, cheese, salsa", "price": 11.25},
            {"category": "Burritos", "name": "Carnitas Burrito",
             "description": "Slow-cooked pork, rice, beans, guacamole", "price": 11.95},
            {"category": "Bowls", "name": "Chicken Fajita Bowl",
             "description": "Grilled chicken, peppers, onions, rice, beans", "price": 12.25},
            {"category": "Sides", "name": "Chips & Salsa", "price": 5.00},
            {"category": "Sides", "name": "Queso Dip", "price": 6.00},
            {"category": "Desserts", "name": "Churros", "price": 4.75},
            {"category": "Beverages", "name": "Horchata", "price": 3.50},
        ],
        "signature_items": ["Al Pastor Taco", "Carnitas Burrito", "Churros"]
    },
    "japanese": {
        "type": "Japanese Restaurant & Catering",
        "history": "Traditional Japanese cuisine with modern presentation.",
        "categories": ["All-in-One Orders", "Bento Boxes", "Sushi", "Ramen", "Appetizers", "Desserts", "Beverages"],
        "menu_items": [
            {"category": "Bento Boxes", "name": "Chicken Teriyaki Bento",
             "description": "Teriyaki chicken, rice, salad, California roll, gyoza", "price": 16.50},
            {"category": "Bento Boxes", "name": "Salmon Bento",
             "description": "Grilled salmon, rice, salad, edamame, miso soup", "price": 17.25},
            {"category": "Sushi", "name": "Spicy Tuna Roll",
             "description": "Tuna, spicy mayo, cucumber, sesame seeds", "price": 6.75},
            {"category": "Sushi", "name": "California Roll",
             "description": "Crab, avocado, cucumber", "price": 6.00},
            {"category": "Ramen", "name": "Tonkotsu Ramen",
             "description": "Pork bone broth, chashu pork, soft egg, scallions", "price": 14.00},
            {"category": "Ramen", "name": "Miso Ramen",
             "description": "Miso broth, vegetables, tofu, nori", "price": 13.50},
            {"category": "Appetizers", "name": "Edamame", "price": 4.25},
            {"category": "Appetizers", "name": "Gyoza",
             "description": "Pan-fried pork dumplings", "price": 6.25},
            {"category": "Desserts", "name": "Mochi Ice Cream", "price": 4.50},
            {"category": "Beverages", "name": "Green Tea", "price": 2.50},
        ],
        "signature_items": ["Tonkotsu Ramen", "Spicy Tuna Roll", "Chicken Teriyaki Bento"]
    },
    "indian": {
        "type": "Indian Restaurant & Catering",
        "history": "Authentic Indian spices and traditional cooking methods.",
        "categories": ["All-in-One Orders", "Luncheon Packages", "Curries", "Tandoor", "Biryani", "Breads", "Desserts", "Beverages"],
        "menu_items": [
            {"category": "Luncheon Packages", "name": "Indian Feast Package",
             "description": "Choice of curry, rice, naan, samosas, dessert", "price": 34.50},
            {"category": "Curries", "name": "Butter Chicken",
             "description": "Tender chicken in creamy tomato sauce", "price": 13.50},
            {"category": "Curries", "name": "Palak Paneer",
             "description": "Spinach and paneer cheese curry", "price": 12.25},
            {"category": "Tandoor", "name": "Chicken Tikka",
             "description": "Marinated chicken grilled in tandoor oven", "price": 13.25},
            {"category": "Tandoor", "name": "Paneer Tikka",
             "description": "Marinated paneer with peppers and onions", "price": 12.50},
            {"category": "Biryani", "name": "Chicken Biryani",
             "description": "Fragrant rice with spiced chicken", "price": 13.75},
            {"category": "Breads", "name": "Garlic Naan", "price": 3.50},
            {"category": "Breads", "name": "Butter Naan", "price": 3.25},
            {"category": "Desserts", "name": "Gulab Jamun", "price": 4.50},
            {"category": "Beverages", "name": "Mango Lassi", "price": 4.00},
        ],
        "signature_items": ["Butter Chicken", "Chicken Tikka", "Garlic Naan"]
    },
    "thai": {
        "type": "Thai Restaurant & Catering",
        "history": "Traditional Thai flavors with fresh herbs and authentic spices.",
        "categories": ["All-in-One Orders", "Noodles", "Curries", "Rice", "Appetizers", "Desserts", "Beverages"],
        "menu_items": [
            {"category": "Noodles", "name": "Pad Thai",
             "description": "Rice noodles, shrimp, peanuts, bean sprouts, lime", "price": 12.50},
            {"category": "Noodles", "name": "Drunken Noodles",
             "description": "Wide rice noodles, basil, chili, vegetables", "price": 12.75},
            {"category": "Curries", "name": "Green Curry",
             "description": "Coconut milk, basil, bamboo, green curry paste", "price": 13.25},
            {"category": "Curries", "name": "Panang Curry",
             "description": "Rich coconut curry with peanuts", "price": 13.50},
            {"category": "Rice", "name": "Thai Basil Fried Rice",
             "description": "Jasmine rice, basil, chili, vegetables", "price": 12.00},
            {"category": "Appetizers", "name": "Fresh Spring Rolls",
             "description": "Vegetables, herbs, rice paper, peanut sauce", "price": 6.50},
            {"category": "Appetizers", "name": "Chicken Satay",
             "description": "Grilled chicken skewers with peanut sauce", "price": 7.25},
            {"category": "Desserts", "name": "Mango Sticky Rice", "price": 5.50},
            {"category": "Beverages", "name": "Thai Iced Tea", "price": 3.75},
        ],
        "signature_items": ["Pad Thai", "Green Curry", "Mango Sticky Rice"]
    },
    "american": {
        "type": "American Grill & Catering",
        "history": "Classic American favorites with modern twists.",
        "categories": ["All-in-One Orders", "Burgers", "Sandwiches", "Salads", "Sides", "Desserts", "Beverages"],
        "menu_items": [
            {"category": "Burgers", "name": "Classic Angus Burger",
             "description": "1/2 lb beef, lettuce, tomato, onion, pickles", "price": 12.50},
            {"category": "Burgers", "name": "BBQ Bacon Burger",
             "description": "BBQ sauce, bacon, cheddar, onion rings", "price": 13.75},
            {"category": "Sandwiches", "name": "Turkey Club",
             "description": "Triple-decker with turkey, bacon, lettuce, tomato", "price": 11.50},
            {"category": "Sandwiches", "name": "Fried Chicken Sandwich",
             "description": "Crispy chicken, pickles, coleslaw, spicy mayo", "price": 12.75},
            {"category": "Salads", "name": "Cobb Salad",
             "description": "Chicken, bacon, egg, avocado, blue cheese", "price": 11.25},
            {"category": "Sides", "name": "Truffle Fries",
             "description": "Hand-cut fries with truffle oil and parmesan", "price": 5.50},
            {"category": "Sides", "name": "Mac & Cheese", "price": 6.25},
            {"category": "Desserts", "name": "New York Cheesecake", "price": 5.75},
            {"category": "Beverages", "name": "Craft Root Beer", "price": 3.25},
        ],
        "signature_items": ["BBQ Bacon Burger", "Truffle Fries", "New York Cheesecake"]
    },
    "mediterranean": {
        "type": "Mediterranean Grill & Catering",
        "history": "Fresh Mediterranean cuisine with healthy, flavorful ingredients.",
        "categories": ["All-in-One Orders", "Mezze", "Wraps", "Plates", "Salads", "Desserts", "Beverages"],
        "menu_items": [
            {"category": "Mezze", "name": "Hummus Platter",
             "description": "House-made hummus, pita, vegetables", "price": 8.50},
            {"category": "Mezze", "name": "Falafel",
             "description": "Crispy chickpea fritters with tahini", "price": 7.75},
            {"category": "Wraps", "name": "Chicken Shawarma Wrap",
             "description": "Marinated chicken, tahini, pickles, tomatoes", "price": 11.50},
            {"category": "Wraps", "name": "Falafel Wrap",
             "description": "Falafel, hummus, vegetables, tahini", "price": 10.50},
            {"category": "Plates", "name": "Mixed Grill Plate",
             "description": "Chicken, lamb, kafta, rice, salad", "price": 16.50},
            {"category": "Salads", "name": "Greek Salad",
             "description": "Feta, olives, cucumber, tomato, vinaigrette", "price": 10.00},
            {"category": "Salads", "name": "Tabbouleh",
             "description": "Bulgur, parsley, tomato, lemon, olive oil", "price": 9.25},
            {"category": "Desserts", "name": "Baklava", "price": 4.75},
            {"category": "Beverages", "name": "Mint Lemonade", "price": 3.50},
        ],
        "signature_items": ["Chicken Shawarma Wrap", "Mixed Grill Plate", "Baklava"]
    },
    "middle_eastern": {
        "type": "Middle Eastern Kitchen & Catering",
        "history": "Traditional Middle Eastern recipes with modern presentation.",
        "categories": ["All-in-One Orders", "Grills", "Mezze", "Wraps", "Sides", "Desserts", "Beverages"],
        "menu_items": [
            {"category": "Grills", "name": "Chicken Kabob",
             "description": "Marinated chicken skewers with rice", "price": 13.25},
            {"category": "Grills", "name": "Beef Kofta",
             "description": "Spiced ground beef kabobs", "price": 13.50},
            {"category": "Grills", "name": "Lamb Kabob",
             "description": "Tender lamb skewers with vegetables", "price": 14.75},
            {"category": "Mezze", "name": "Hummus Trio",
             "description": "Classic, roasted red pepper, garlic hummus", "price": 8.75},
            {"category": "Mezze", "name": "Labneh",
             "description": "Strained yogurt with olive oil and za'atar", "price": 6.75},
            {"category": "Wraps", "name": "Beef Shawarma Wrap",
             "description": "Shaved beef, tahini, onions, tomatoes", "price": 11.50},
            {"category": "Wraps", "name": "Falafel Wrap",
             "description": "Crispy falafel, vegetables, tahini", "price": 10.25},
            {"category": "Sides", "name": "Turmeric Rice", "price": 4.75},
            {"category": "Sides", "name": "Roasted Cauliflower", "price": 5.75},
            {"category": "Desserts", "name": "Pistachio Baklava", "price": 4.75},
            {"category": "Beverages", "name": "Turkish Coffee", "price": 3.00},
        ],
        "signature_items": ["Lamb Kabob", "Hummus Trio", "Pistachio Baklava"]
    },
}


def rand_range(low: float, high: float, precision: int = 2) -> float:
    """Generate random float in range with specified precision"""
    return round(random.uniform(low, high), precision)


def generate_phone_number() -> str:
    """Generate realistic phone number"""
    area_code = random.randint(200, 999)
    exchange = random.randint(200, 999)
    number = random.randint(1000, 9999)
    return f"{area_code}-{exchange}-{number}"


def generate_website(restaurant_name: str, city: str) -> str:
    """Generate realistic website URL"""
    clean_name = restaurant_name.lower().replace("'s", "").replace(" ", "")
    return f"https://{clean_name}.com/"


def generate_reviews(cuisine: str, signature_items: List[str], count: int = 10) -> List[Dict[str, Any]]:
    """Generate realistic reviews"""
    reviews = []
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for _ in range(count):
        source = random.choice(REVIEW_SOURCES)
        template = random.choice(REVIEW_TEMPLATES)
        item = random.choice(signature_items) if signature_items else f"{cuisine} dishes"

        summary = template.format(
            item=item,
            cuisine=cuisine,
            count=random.choice([50, 75, 100, 150, 200])
        )

        # Generate date
        if random.random() < 0.3:  # 30% recent
            date = f"{random.choice(['5 days ago', '2 weeks ago', '1 month ago', 'Recent'])}"
        else:
            month = random.choice(months)
            year = random.choice([2023, 2024, 2025])
            date = f"{month} {year}"

        reviews.append({
            "source": source,
            "summary": summary,
            "date": date
        })

    return reviews


def generate_ratings() -> Dict[str, Any]:
    """Generate multi-source ratings"""
    ezcater_rating = rand_range(4.3, 4.9, 1)
    tripadvisor_rating = rand_range(4.2, 4.8, 1)

    ratings = {
        "ezCater_rating": ezcater_rating,
        "ezCater_review_count": random.randint(500, 2500),
        "tripadvisor_rating": tripadvisor_rating,
        "tripadvisor_review_count": random.randint(300, 2000),
        "average_rating": round((ezcater_rating + tripadvisor_rating) / 2, 1),
        "top_review_sites": random.sample(REVIEW_SOURCES, k=4)
    }

    return ratings


def build_menu(cuisine_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build menu matching sample.json format"""
    categories = cuisine_data["categories"]
    menu_items = cuisine_data["menu_items"]

    # Select random subset of items
    min_items = min(10, len(menu_items))
    max_items = len(menu_items)
    num_items = random.randint(min_items, max_items) if max_items > min_items else min_items
    selected_items = random.sample(menu_items, k=num_items)

    # Organize by category
    items_by_category = []
    seen_categories = set()

    for item in selected_items:
        category = item["category"]
        if category not in seen_categories:
            seen_categories.add(category)
            category_items = [i for i in selected_items if i["category"] == category]
            items_by_category.append({
                "category": category,
                "items": category_items
            })

    return {
        "categories": [cat for cat in categories if cat in seen_categories],
        "items": items_by_category
    }


def build_restaurant(index: int) -> Dict[str, Any]:
    """Build restaurant matching sample.json format"""
    cuisine_name, cuisine_data = random.choice(list(CUISINES.items()))
    city, state, latitude, longitude = random.choice(CITIES)

    # Generate restaurant name
    prefix = random.choice(RESTAURANT_NAME_PREFIXES[cuisine_name])
    suffix = random.choice(RESTAURANT_NAME_SUFFIXES[cuisine_name])
    restaurant_name = f"{prefix} {suffix}"

    # Address
    street_num = random.randint(10, 999)
    street_name = random.choice(STREET_NAMES)
    zip_code = random.randint(10000, 99999)

    address = {
        "street": f"{street_num} {street_name}",
        "city": city,
        "state": state,
        "zip": str(zip_code),
        "country": "USA"
    }

    # Contact info
    contact = {
        "phone": generate_phone_number(),
        "website": generate_website(restaurant_name, city)
    }

    # Location
    location = {
        "latitude": latitude + rand_range(-0.05, 0.05, 4),
        "longitude": longitude + rand_range(-0.05, 0.05, 4)
    }

    # Hours
    delivery_windows = ["10am–9pm", "11am–8pm", "11am–10pm", "12pm–9pm", "Mon-Fri: 10am-2pm"]
    takeout_windows = ["10am–10pm", "11am–9pm", "12pm–11pm", "8am–3pm", "Mon-Fri: 10am-2pm"]

    hours = {
        "delivery_hours": random.choice(delivery_windows),
        "takeout_hours": random.choice(takeout_windows)
    }

    # Catering info
    onboard_year = random.randint(2008, 2024)
    onboard_month = random.choice(["January", "February", "March", "April", "May", "June",
                                   "July", "August", "September", "October", "November", "December"])
    onboard_day = random.randint(1, 28)

    catering_info = {
        "on_ezcater_since": f"{onboard_month} {onboard_day}, {onboard_year}",
        "delivery_fee": f"USD {rand_range(0, 15, 2)} & up",
        "delivery_minimum": f"USD {rand_range(25, 100, 2)}",
        "delivery_method": random.choice(["Caterer's driver", "ezCater's drivers", "Customer pickup"]),
        "group_order": random.choice([True, False]),
        "rewards": random.choice(["1X Rewards", "2X Rewards", "3X Rewards"])
    }

    # Description and history
    description_template = random.choice(ABOUT_DESCRIPTIONS)
    description = description_template.format(year=onboard_year, cuisine=cuisine_name)
    history = cuisine_data["history"]

    # Build complete restaurant object
    restaurant = {
        "name": restaurant_name,
        "type": cuisine_data["type"],
        "address": address,
        "contact": contact,
        "location": location,
        "description": description,
        "history": history,
        "hours": hours,
        "catering_info": catering_info
    }

    # Ratings
    ratings = generate_ratings()

    # Reviews
    reviews = generate_reviews(cuisine_name, cuisine_data["signature_items"])

    # Menu
    menu = build_menu(cuisine_data)

    # Metadata
    metadata = {
        "source_url": f"https://www.ezcater.com/catering/{restaurant_name.lower().replace(' ', '-')}-{city.lower().replace(' ', '-')}",
        "extraction_date": datetime.now().strftime("%Y-%m-%d"),
        "derived_fields": {
            "average_rating": "Computed from ezCater & Tripadvisor values",
            "top_review_sites_count": len(ratings["top_review_sites"])
        }
    }

    return {
        "restaurant": restaurant,
        "ratings": ratings,
        "top_reviews": reviews,
        "menu": menu,
        "metadata": metadata
    }


def main() -> None:
    """Generate seed data files"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {SEED_COUNT} restaurant files...")
    for idx in range(1, SEED_COUNT + 1):
        data = build_restaurant(idx)
        output_path = OUTPUT_DIR / f"restaurant_{idx:03d}.json"

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        if idx % 20 == 0:
            print(f"  Generated {idx}/{SEED_COUNT} files...")

    print(f"✓ Successfully generated {SEED_COUNT} restaurant files in {OUTPUT_DIR}")


if __name__ == "__main__":
    random.seed(42)  # For reproducible data
    main()
