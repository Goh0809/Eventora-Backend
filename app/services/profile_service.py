from fastapi import HTTPException, status, UploadFile
from typing import Dict, Any
from datetime import datetime, timezone
from app.core.database import SupabaseClient
from app.schemas.profile import ProfileResponse, ProfileUpdate  
from app.utils.storage import StorageService

class ProfileService:
    # Initiate the Service Needed in Profile API
    def __init__(self):
        self.supabase = SupabaseClient.get_client()
        self.supabase_admin = SupabaseClient.get_service_client()
        self.table = "profile"
        self.storage = StorageService()

    # Get the Profile Detail
    def get_profile(self, user_id: str) -> Dict[str, Any]:
        try:
            profile_response = self.supabase.table(self.table).select("*").eq("id", user_id).execute()
            if not profile_response.data:
                raise HTTPException(
                    status_code = status.HTTP_404_NOT_FOUND,
                    detail = "Profile Not Found"
                )
            return profile_response.data[0]
        except Exception as e:
            if "JSON object requested, multiple" in str(e):
                raise HTTPException(
                    status_code = status.HTTP_404_NOT_FOUND,
                    detail = "Profile Not Found"
                )
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to Fetch Profile Detail"
            )

    # Update the Profile
    def update_profile(self, user_id: str, payload: ProfileUpdate) -> Dict[str, Any]:
        try:
            # Clean the Payload First -> Remove the None Value
            profile_update_data = payload.model_dump(exclude_unset = True)
            if not profile_update_data:
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = "No Profile Update Data Provided"
                )
            # Set the Updated_At Column Data = Current UTC TIMEZONE
            profile_update_data["updated_at"] = (datetime.now(timezone.utc)).isoformat()

            # Update the Profile Table
            profile_response = self.supabase.table(self.table).update(profile_update_data).eq("id", user_id).execute()
            if not profile_response.data:
                raise HTTPException(
                    status_code = status.HTTP_404_NOT_FOUND,
                    detail = "Failed to Update"
                )
            return profile_response.data[0]
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to Update the Profile"
            )
    

    # Get Public Profile
    def get_public_profile(self, user_id: str) -> Dict[str, Any]:
        try: 
            profile_response = self.supabase.table(self.table).select("full_name, email, bio, avatar_url").eq("id", user_id).execute()
            return profile_response.data[0]
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_404_NOT_FOUND,
                detail = "User Not Found"
            )
            