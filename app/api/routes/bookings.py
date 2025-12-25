from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional, List
from datetime import datetime
from app.api.deps import get_current_user 
from app.services import booking_service
from app.services.booking_service import BookingService
from app.schemas.booking import BookingCreateSchema, BookingDetailResponse, BookingResponse

router = APIRouter()
booking_service = BookingService()

@router.post("/checkout", response_model = BookingResponse, status_code = status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreateSchema,
    user = Depends(get_current_user)
):
    if not user.id: 
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Authentication Fail"
        )

    try:
        response = booking_service.create_checkout_session(user.id, user.email, payload)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Create Stripe Payment Session Fail: {str(e)}"
        )

@router.post("/webhook", include_in_schema = True)
async def stripe_webhook(
    request: Request
):
    try:
        response = await booking_service.handle_stripe_webhook(request)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Stripe Webhook Error: {str(e)}"
        )

@router.get("/organizer/event/{event_id}/participants", status_code = status.HTTP_200_OK)
def list_event_participants(
    event_id: str,
    user = Depends(get_current_user)
): 
    if not user.id: 
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Authentication Fail"
        )

    try:
        response = booking_service.get_event_bookings_for_organizer(event_id, user.id)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Event Participants List Get Fail: {str(e)}"
        )

@router.get("/my-history", response_model=List[BookingDetailResponse])
def get_my_booking_history(user = Depends(get_current_user)):
    if not user.id: 
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED, 
            detail="Authentication Fail"
        )
    return booking_service.list_my_bookings(user.id)

@router.get("/{booking_id}", response_model = BookingDetailResponse)
def get_booking_detail(booking_id: str, user = Depends(get_current_user)):
    if not user.id:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail = "Authentication Fail"
        )
    try: 
        return booking_service.get_booking_detail(booking_id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Booking Detail Found Error: {str(e)}"
        )

@router.get("/status/{event_id}", status_code=status.HTTP_200_OK)
def check_participation_status(
    event_id: str,
    user = Depends(get_current_user)
):
    """
    Check if the current logged-in user has booked this event.
    """
    return booking_service.get_booking_status(user.id, event_id)