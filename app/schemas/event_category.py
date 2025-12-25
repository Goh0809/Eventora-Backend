from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class CategoryResponse(BaseModel):
    id: UUID
    name: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True