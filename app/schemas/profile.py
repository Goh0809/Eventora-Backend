from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None

class ProfileResponse(BaseModel):
    id: UUID
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    email: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True