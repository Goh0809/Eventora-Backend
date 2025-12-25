from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class EventParticipantResponse(BaseModel):
    id: UUID
    event_id: UUID
    user_id: UUID
    registered_at: datetime

    class Config:
        from_attributes = True