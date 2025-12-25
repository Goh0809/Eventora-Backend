from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Query
from typing import Optional
from datetime import datetime
from app.api.deps import get_current_user 
from app.services import event_service
from app.services.event_service import EventService
from app.schemas.event import EventListResponse, EventResponse, EventUpdateSchema
from app.utils.storage import StorageService

router = APIRouter()
event_service = EventService()

@router.post("/", response_model = EventResponse, status_code = status.HTTP_201_CREATED)
def create_event(
    # Form Fields
    title: str = Form(..., min_length=3),
    description: Optional[str] = Form(None),
    location: str = Form(...),
    event_date: datetime = Form(...), 
    event_end_date: datetime = Form(...),
    max_slots: int = Form(..., gt=0),
    is_paid: bool = Form(False),
    ticket_price: float = Form(0.0, ge=0),
    currency: str = Form("usd"),
    category_id: str = Form(...),
    event_status: str = Form("published", pattern="^(draft|published|cancelled)$"),
    # File Upload
    image: UploadFile = File(...),
    # Authentication
    user = Depends(get_current_user)
):
    try:
        # Create Event Endpoint -> Accept Multipart / Form-Data
        event_payload_dict = {
            "title": title,
            "description": description,
            "location": location,
            "event_date": event_date.isoformat(),
            "event_end_date": event_end_date.isoformat(),
            "max_slots": max_slots,
            "is_paid": is_paid,
            "ticket_price": ticket_price,
            "currency": currency,
            "category_id": category_id,
            "event_status": event_status
        }
        
        result = event_service.create_event(
            user_id = user.id,
            event_data = event_payload_dict,
            image_file = image
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = f"Event Created Fail: {str(e)}"
        )

@router.get("/", status_code = status.HTTP_200_OK)
def list_events(
    page: int = Query(1, ge = 1),
    size: int = Query(9, ge = 1, le = 50),
    search: Optional[str] = None,
    category_id: Optional[str] = None,
    created_by: Optional[str] = None
):
    try:
        return event_service.list_events(page, size, search, category_id, created_by)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = f"Get Event List Fail: {str(e)}"
        )

@router.get("/{event_id}", status_code = status.HTTP_200_OK)
def get_event(
    event_id: str
):
    try:
        return event_service.get_event(event_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = f"Get Event Fail: {str(e)}"
        )

@router.delete("/{event_id}", status_code = status.HTTP_200_OK)
def delete_event(
    event_id: str,
    user = Depends(get_current_user)
):
    try:
        user_id = user.id
        if not user_id:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Could Not Validate User Credential"
            )
        return event_service.delete_event(event_id, user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Delete Event Fail: {str(e)}"
        )

@router.put("/{event_id}", status_code = status.HTTP_200_OK)
def update_event(
    event_id: str,
    payload: EventUpdateSchema,
    user = Depends(get_current_user)
): 
    """
    Update Event Details:
    1. If Have a New Image, Call Post /events/upload-image First Then Pass the Return URL in the Image_Url Field
    2. Handle the Stripe Update Automatically
    3. Handle Category Mapping Automatically
    """
    try:
        user_id = user.id
        if not user_id:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Could Not Validate User Credential"
            )
        return event_service.update_event(
            event_id = event_id,
            user_id = user_id,
            payload = payload
        )
    except HTTPException:
        raise 
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Event Update Fail: {str(e)}"
        )

@router.post("/upload-image", status_code = status.HTTP_201_CREATED)
def upload_event_image(
    event_id: str,
    file: UploadFile = File(...)
): 
    try: 
        storage = StorageService()
        return storage.upload_event_image(file, event_id)
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Upload Failed: {str(e)}"
        )
    