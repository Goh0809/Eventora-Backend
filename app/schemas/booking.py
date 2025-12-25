from pydantic import BaseModel, HttpUrl
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any

class BookingCreateSchema(BaseModel):
    event_id: str
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

class BookingResponse(BaseModel):
    booking_id: Optional[UUID] = None
    checkout_url: Optional[str] = None
    status: str
    message: str

class EventMiniSchema(BaseModel):
    title: str
    location: str
    event_date: datetime
    image_url: Optional[str] = None

class ProfileMiniSchema(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None

class BookingDetailResponse(BaseModel):
    id: UUID
    event_id: UUID
    user_id: UUID
    amount_total: int       
    currency: str         
    payment_status: str    
    payment_method: Optional[str] = None
    created_at: datetime
    stripe_session_id: Optional[str] = None

    event: Optional[EventMiniSchema] = None
    profile: Optional[ProfileMiniSchema] = None

    class Config:
        from_attributes = True