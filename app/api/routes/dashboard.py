from fastapi import APIRouter, Depends, status, HTTPException
from app.api.deps import get_current_user
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import DashboardResponse

router = APIRouter()
dashboard_service = DashboardService()

@router.get("/organizer", response_model=DashboardResponse)
def get_analytics(
    user = Depends(get_current_user),
):
    if not user.id: raise HTTPException(401, "Auth failed")
    return dashboard_service.get_organizer_dashboard(user.id)