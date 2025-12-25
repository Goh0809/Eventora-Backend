from pydantic import BaseModel
from typing import List, Optional 
from uuid import UUID
from datetime import datetime, date

class SalesChartData(BaseModel):
    date: date
    daily_revenue: float
    tickets_sold: int

class EventPerformance(BaseModel):
    event_title: str
    revenue: float
    tickets_sold: int
    occupancy_rate: float

class RecentSale(BaseModel):
    booking_id: UUID
    event_title: str
    buyer_name: str
    buyer_email: str
    amount: float
    created_at: datetime

class DashboardStats(BaseModel):
    total_revenue: float
    total_tickets_sold: int
    total_events_active: int

class DashboardResponse(BaseModel):
    stats: DashboardStats
    sales_chart: List[SalesChartData]
    top_events: List[EventPerformance]
    recent_sales: List[RecentSale]