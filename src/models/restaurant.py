from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class Address(BaseModel):
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None

    def as_string(self) -> str:
        parts = [self.street, self.city, self.state, self.zip, self.country]
        return ", ".join([part for part in parts if part])


class Contact(BaseModel):
    phone: Optional[str] = None
    website: Optional[str] = None


class Location(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Hours(BaseModel):
    delivery_hours: Optional[str] = None
    takeout_hours: Optional[str] = None


class CateringInfo(BaseModel):
    on_ezcater_since: Optional[str] = None
    delivery_fee: Optional[str] = None
    delivery_minimum: Optional[str] = None
    delivery_method: Optional[str] = None
    group_order: Optional[bool] = None
    rewards: Optional[str] = None


class Restaurant(BaseModel):
    name: str
    type: Optional[str] = None
    address: Address
    contact: Optional[Contact] = None
    location: Optional[Location] = None
    description: Optional[str] = None
    history: Optional[str] = None
    hours: Optional[Hours] = None
    catering_info: Optional[CateringInfo] = None

    def cuisine_label(self) -> str:
        if self.type:
            return self.type.lower()
        return ""


class Ratings(BaseModel):
    ezCater_rating: Optional[float] = None
    ezCater_review_count: Optional[int] = None
    tripadvisor_rating: Optional[float] = None
    tripadvisor_review_count: Optional[int] = None
    average_rating: Optional[float] = None
    top_review_sites: Optional[List[str]] = None


class Review(BaseModel):
    source: Optional[str] = None
    summary: Optional[str] = None
    date: Optional[str] = None


class MenuItem(BaseModel):
    name: str
    price: float
    description: Optional[str] = None


class MenuCategoryItems(BaseModel):
    category: str
    items: List[MenuItem]


class Menu(BaseModel):
    categories: Optional[List[str]] = None
    items: List[MenuCategoryItems]


class MetadataDerived(BaseModel):
    average_rating: Optional[str] = None
    top_review_sites_count: Optional[int] = None


class RestaurantMetadata(BaseModel):
    source_url: Optional[str] = None
    extraction_date: Optional[str] = None
    derived_fields: Optional[MetadataDerived] = None


class RestaurantData(BaseModel):
    restaurant: Restaurant
    ratings: Optional[Ratings] = None
    top_reviews: Optional[List[Review]] = None
    menu: Menu
    metadata: Optional[RestaurantMetadata] = None

    def primary_rating(self) -> float:
        ratings = self.ratings
        if not ratings:
            return 0.0
        for value in (
            ratings.average_rating,
            ratings.ezCater_rating,
            ratings.tripadvisor_rating,
        ):
            if value is not None:
                return float(value)
        return 0.0

    def primary_review_count(self) -> int:
        ratings = self.ratings
        if not ratings:
            return 0
        for value in (
            ratings.ezCater_review_count,
            ratings.tripadvisor_review_count,
        ):
            if value is not None:
                return int(value)
        return 0

    def to_plain_dict(self) -> Dict[str, Any]:
        return self.model_dump()