from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.api.deps import get_current_user
from app.services.profile_service import ProfileService
from app.schemas.profile import ProfileResponse, ProfileUpdate
from app.utils.storage import StorageService

router = APIRouter()
profile_service = ProfileService()
storage_service = StorageService()

@router.get("/me", response_model = ProfileResponse, status_code= status.HTTP_200_OK)
def get_my_profile(user = Depends(get_current_user)):
    try:
        if not user.id:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Authentication Failed"
            )
        return profile_service.get_profile(user.id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Profile Detail Retrieved Error: {str(e)}"
        )

@router.post("/upload-avatar", status_code = status.HTTP_200_OK)
def upload_avatar_image(file: UploadFile = File(...), user = Depends(get_current_user)):
    try:
        if not user.id:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Authentication Failed"
            )
        return storage_service.upload_avatar(file, user.id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Upload Avatar Image Fail: {str(e)}"
        )

@router.put("/me", response_model = ProfileResponse, status_code = status.HTTP_200_OK)
def update_my_profile(payload: ProfileUpdate, user = Depends(get_current_user)):
    try:
        if not user.id: 
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Authentication Failed"
            )
        return profile_service.update_profile(user.id, payload)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Profile Update Fail: {str(e)}"
        )

@router.get("/{user_id}", status_code = status.HTTP_200_OK)
def get_public_profile(user_id: str):
    return profile_service.get_public_profile(user_id)
    
