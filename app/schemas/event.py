from pydantic import BaseModel, UUID4
from datetime import datetime
from typing import Optional, List

class CategoryResponse(BaseModel):
    id: UUID4
    name: str

class EventResponse(BaseModel):
    id: UUID4
    title: str
    description: Optional[str] = None
    location: str
    event_date: datetime
    event_end_date: datetime
    event_status: str
    image_url: Optional[str] = None
    max_slots: int
    is_paid: bool
    currency: str
    ticket_price: float
    created_by: UUID4
    created_at: datetime

    class Config:
        from_attributes = True

class EventListResponse(BaseModel):
    items: List[EventResponse]
    total: int
    page: int
    size: int

    class Config:
        from_attributes = True

class EventUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    event_date: Optional[str] = None
    event_end_date: Optional[str] = None
    max_slots: Optional[int] = None
    location: Optional[str] = None
    category_id: Optional[str] = None
    is_paid: Optional[bool] = None
    ticket_price: Optional[float] = None
    currency: Optional[str] = None
    event_status: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        from_attributes = True
    