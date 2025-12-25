from uuid import uuid4
from fastapi import UploadFile, HTTPException, status
from app.core.database import SupabaseClient
from app.core.config import settings
from storage3.utils import StorageException

class StorageService:
    # Service for Handling Supabase Bucket Storage
    def __init__(self):
        self.supabase = SupabaseClient.get_service_client()
        self.event_bucket = settings.EVENT_IMAGE_BUCKET
        self.event_folder = settings.EVENT_IMAGE_FOLDER
        self.avatar_bucket = settings.AVATAR_BUCKET

    # Generic Upload File to Handle Multiple Supabase Bucket Storage File Upload
    def _generic_upload(self, file: UploadFile, bucket: str, folder_path: str) -> dict:
        # Check the File Content Type is Image or Not
        if not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = "Only Image Files are Allowed to Upload"
            )    
        try:
            # Read File Content 
            bytes_data = file.file.read()
            # Get the File Etension
            extension = file.filename.split(".")[-1]
            # Contract the File Path
            path = f"{folder_path}/{uuid4()}.{extension}"
            # Upload the FIle to the Supabase Bucket Storage
            response = self.supabase.storage.from_(bucket).upload(
                path = path,
                file = bytes_data,
                file_options = {"content_type": file.content_type, "upsert": "true"}
            )
            # Get Public URL
            public_url = self.supabase.storage.from_(bucket).get_public_url(path)

            return {
                "url": public_url,
                "path": path
            }
        except StorageException as e:
            print(f"Storage API Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Storage Upload Failed"
            )
        except Exception as e:
            print(f"Upload Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "An Unexpected Error Occured During Upload"
            )


    # Upload the Event Image
    def upload_event_image(self, file: UploadFile, event_id: str) -> dict:
        return self._generic_upload(file, self.event_bucket, f"{self.event_folder}/{event_id}")

    # Upload the Profile Avatar
    def upload_avatar(self, file: UploadFile, user_id: str) -> str:
        result = self._generic_upload(file, self.avatar_bucket, f"{user_id}")
        return result["url"]


    # Generic Delete File to Handle Multiple Supabase Bucket Storage Delete Operation
    def _generic_delete(self, bucket: str, path: str) -> bool:
        # Delete a File From Storage -> Return TRUE If Success Else Return Fasle
        if not path:
            return False
        try:
            # Supabase Function to Remove File
            self.supabase.storage.from_(bucket).remove([path])
            return True
        except Exception as e:
            print(f"Warning: Failed to Delete File {path}: {e}")
            return False

    # Delete the Event Image
    def delete_event_image(self, path: str) -> bool:
        return self._generic_delete(self.event_bucket, path)

    # Delete the Avatar Image
    def delete_avatar_image(self, path: str) -> bool:
        return self._generic_delete(self.avatar_bucket, path)
