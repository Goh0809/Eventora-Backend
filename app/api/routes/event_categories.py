from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.services.event_category_service import CategoryService
from app.schemas.event_category import CategoryResponse

router = APIRouter()
category_service = CategoryService()

@router.get("/", response_model = List[CategoryResponse], status_code = status.HTTP_200_OK)
def list_categories():
    try:
        return category_service.get_all_categories()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Category Service Error: {str(e)}"
        )