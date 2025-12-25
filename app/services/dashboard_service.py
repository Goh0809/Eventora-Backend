from fastapi import HTTPException, status
from typing import Dict, Any, List
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
from app.core.database import SupabaseClient

class DashboardService:
    # Initiate the Service Needed in Dashboard API
    def __init__(self):
        self.supabase = SupabaseClient.get_client()
        self.supabase_admin = SupabaseClient.get_service_client()

    def _empty_dashboard(self):
        return {
            "stats": {"total_revenue": 0, "total_tickets_sold": 0, "total_events_active": 0},
            "sales_chart": [],
            "top_events": [],
            "recent_sales": []
        }
    
    # Perform the Dashboard Data Calculation
    def get_organizer_dashboard(self, user_id: str) -> Dict[str, Any]:
        try:
            # 1. Retrieve the Event Information
            event_response = self.supabase.table("event").select("id, title, max_slots").eq("created_by", user_id).execute()
            if not event_response.data:
                return self._empty_dashboard()

            my_events = event_response.data
            my_event_ids = [e["id"] for e in my_events]
            event_map = {e["id"]: e for e in my_events} # -> Quick Look Up by ID

            # 2. Retrieve All Paid Bookings
            booking_response = self.supabase.table("bookings").select("*, profile(full_name, email)").in_("event_id", my_event_ids).eq("payment_status", "paid").order("created_at", desc = True).execute()
            bookings = booking_response.data or []

            # 3. Calculate the Stats & LeaderBoard Data
            total_revenue = 0.0
            total_tickets = len(bookings)

            # 3.1 Aggregators
            event_revenue = defaultdict[Any, float](float)
            event_tickets = Counter[Any]()
            daily_stats = defaultdict(lambda: {"revenue": 0.0, "tickets": 0})

            for b in bookings:
                amount = b["amount_total"] / 100.0 # -> Convert to MYR
                clean_date_str = b["created_at"].replace('Z', '+00:00')
                created_date = datetime.fromisoformat(clean_date_str).date()
                eid = b["event_id"]

                # Global Stats
                total_revenue += amount

                # Per Event Stats
                event_revenue[eid] += amount
                event_tickets[eid] += 1

                # Time Series
                daily_stats[created_date]["revenue"] += amount
                daily_stats[created_date]["tickets"] += 1

            # 4. Top Event 
            top_events = []
            for eid, event_data in event_map.items():
                tickets = event_tickets[eid]
                revenue = event_revenue[eid]
                max_slots = event_data["max_slots"]

                # Occupancy Rate Calculation
                occupancy = (tickets / max_slots * 100) if max_slots > 0 else 0.0

                top_events.append({
                    "event_title": event_data["title"],
                    "revenue": revenue,
                    "tickets_sold": tickets,
                    "occupancy_rate": round(occupancy , 1)
                })

            # Sort By Revenue
            top_events.sort(key = lambda x: x["revenue"], reverse = True)

            # 5. Build Sales Chart
            sales_chart = []
            today = datetime.now(timezone.utc).date()
            for i in range(29, -1, -1):
                d = today - timedelta(days = i)
                stat = daily_stats.get(d, {"revenue": 0.0, "tickets": 0})
                sales_chart.append({
                    "date": d,
                    "daily_revenue": stat["revenue"],
                    "tickets_sold": stat["tickets"]
                })

            # 6. Build Recent Sales List
            recent_sales = []
            for b in bookings[:10]:
                profile = b.get("profile") or {}
                recent_sales.append({
                    "booking_id": b["id"],
                    "event_title": event_map[b["event_id"]]["title"],
                    "buyer_name": profile.get("full_name") or "Unknown",
                    "buyer_email": profile.get("email") or "Hidden",
                    "amount": b["amount_total"] / 100.0,
                    "created_at": b["created_at"]
                })

            return {
                "stats": {
                    "total_revenue": total_revenue,
                    "total_tickets_sold": total_tickets,
                    "total_events_active": len(my_events)
                },
                "sales_chart": sales_chart,
                "top_events": top_events[:5], # Return top 5 best sellers
                "recent_sales": recent_sales
            }

        except Exception as e:
            print("Dashboard Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Analytics Fail: {str(e)}"
            )