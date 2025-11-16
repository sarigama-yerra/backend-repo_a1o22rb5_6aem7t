"""
Database Schemas for VisitPazar

Each Pydantic model represents one MongoDB collection. The collection name is the lowercase
class name (e.g., Place -> "place").
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime

class Place(BaseModel):
    name: str = Field(..., description="Naziv lokacije ili biznisa")
    type: str = Field(..., description="tip: restoran, hotel, kafic, muzej, znamenitost")
    description: Optional[str] = Field(None, description="Kratak opis")
    address: Optional[str] = Field(None, description="Adresa")
    latitude: Optional[float] = Field(None, description="Geo latituda")
    longitude: Optional[float] = Field(None, description="Geo longituda")
    images: List[str] = Field(default_factory=list, description="URL-ovi fotografija")
    is_recommended: bool = Field(False, description="Da li je istaknuto mesto (sponzorisano)")
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    price_level: Optional[int] = Field(None, ge=1, le=5)
    tags: List[str] = Field(default_factory=list)

class Guide(BaseModel):
    name: str = Field(..., description="Ime i prezime vodiča")
    bio: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    rating: Optional[float] = Field(None, ge=0, le=5)
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None

class Event(BaseModel):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_featured: bool = False

class Tour(BaseModel):
    title: str
    description: Optional[str] = None
    guide_id: Optional[str] = None
    price_eur: Optional[float] = Field(None, ge=0)
    duration_minutes: Optional[int] = Field(None, ge=0)
    language: Optional[str] = None
    is_premium: bool = False

class Booking(BaseModel):
    user_name: str
    user_email: str
    resource_type: str = Field(..., description="tour | guide | place | event")
    resource_id: str
    guests: int = Field(1, ge=1)
    notes: Optional[str] = None
    amount_eur: Optional[float] = Field(None, ge=0)
    status: str = Field("pending", description="pending|confirmed|cancelled")

class PremiumContent(BaseModel):
    title: str
    content_type: str = Field(..., description="audio|ar|3d|story")
    price_eur: float = Field(..., ge=0)
    asset_url: Optional[HttpUrl] = None
    description: Optional[str] = None
    is_active: bool = True
