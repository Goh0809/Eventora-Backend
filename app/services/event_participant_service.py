from fastapi import HTTPException, status
from typing import Dict, Any
from app.core.database import SupabaseClient

class EventParticipantService: 
    # Initialize the Service Needed to be Used in Event Participant API
    def __init__(self):
        self.supabase = SupabaseClient.get_client()
        self.table = "event_participants"
        
    def create_participant(self, user_id: str, event_id: str) -> Dict[str, Any]:
        """
        Register the User For An Event -> For the Actual Ticket
        User Upsert to Prevent Crashing If the Stripe Webhook Fires Twice ***
        """
        try:
            response = self.supabase.table(self.table).upsert({
                "user_id": user_id,
                "event_id": event_id
            }, on_conflict="event_id, user_id").execute()

            if not response.data:
                raise HTTPException(
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail = "Fail to Register Participant"
                )

            return response.data[0]
        except Exception as e:
            print(f"Error Participant Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Event Registration Failed: {str(e)}"
            )
        
    def get_participant_count(self, event_id: str) -> int:
        # Count How Many People Have the Ticket for the Event
        try:
            response = self.supabase.table(self.table).select("*", count = "exact", head = True).eq("event_id", event_id).execute()
            return response.count or 0
        except Exception:
            return 0
    
    def check_participant_exists(self, user_id: str, event_id: str) -> bool:
        # Check If the User Has Already Own a Ticket
        try:
            response = self.supabase.table(self.table).select("id").eq("user_id", user_id).eq("event_id", event_id).execute()
            return len(response.data) > 0
        except Exception:
            return False