from typing import List, Dict, Any
from fastapi import HTTPException, status
from app.core.database import SupabaseClient

class CategoryService:
    # Initialize the Service Needed in the Category API
    def __init__(self):
        self.supabase = SupabaseClient.get_client()
        self.table = "event_categories"

    # Get All Event Categories -> Move the Other Category to the End
    def get_all_categories(self) -> List[Dict[str, Any]]:
        try:
            # Fetch Data Sorted Alphabetically by Name From event_categories Table
            response = self.supabase.table(self.table).select("*").order("name").execute()
            if not response.data:
                raise HTTPException(
                    status_code = status.HTTP_404_NOT_FOUND,
                    detail = "Category Not Found"
                )
                return []
            
            items = response.data
            # Post Processing and Move the Other Category to the End
            regular_categories = []
            other_categories = []
            for item in items:
                if item["name"].strip().lower() == "other":
                    other_categories.append(item)
                else:
                    regular_categories.append(item)
            # Return the Combine List
            return regular_categories + other_categories
        except Exception as e:
            print(f"Category Service Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Category Service Error: {str(e)}"
            )

