from pydantic import BaseModel
from typing import List, Dict, Optional

class MenuItem(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

class MenuCategory(BaseModel):
    name: str  # e.g., "boxed_lunches"
    items: List[MenuItem]

class RestaurantHours(BaseModel):
    mon_sun: str

class Restaurant(BaseModel):
    name: str
    address: str
    city: Optional[str] = None
    state: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    cuisine: Optional[str] = None
    rating: float
    review_count: int
    on_time_rate: str
    delivery_fee: float
    delivery_minimum: float
    delivery_hours: RestaurantHours
    takeout_hours: RestaurantHours

class RestaurantData(BaseModel):
    restaurant: Restaurant
    menu: Dict[str, List[MenuItem]]  # menu categories as dict