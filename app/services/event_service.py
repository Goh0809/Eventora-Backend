import stripe
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, UploadFile, status
from app.core.database import SupabaseClient
from app.core.config import settings
from app.schemas.event import EventUpdateSchema
from app.utils.storage import StorageService
from collections import Counter

stripe.api_key = settings.STRIPE_SECRET_KEY

class EventService:
    # Initialize the Service Needed in the Event API
    def __init__(self):
        self.supabase = SupabaseClient.get_client()
        self.supabase_admin = SupabaseClient.get_service_client()
        self.storage = StorageService()
        self.table = "event"

    # Storage Path Helper Function -> Extracts the Relative Path From a Supabase Public URL
    def _extract_path_from_url(
        self,
        url: str
    ) -> Optional[str]:
        try:
            bucket_name = settings.EVENT_IMAGE_BUCKET
            # URL: https://.../storage/v1/object/public/events_bucket/folder/image.png
            if bucket_name in url:
                parts = url.split(f"/{bucket_name}/")
                if len(parts) > 1:
                    return parts[1]
            return None
        except Exception:
            return None

    # Stripe Helper Function -> Used to Create the Product and Price in Stripe and Return Their IDs
    def _ensure_stripe_product(
        self, 
        title: str, 
        description: str, 
        price: float, 
        currency: str
    ):
        try:
            # 1. Create the Product
            product = stripe.Product.create(name = title, description = description or "")
            # 2. Create the Product Price
            unit_amount = int(price * 100) # Due to Stripe Expects the Amount in Cents
            price_obj = stripe.Price.create(
                unit_amount = unit_amount,
                currency = currency.lower(),
                product = product.id
            )
            # 3. Return Both IDs
            return product.id, price_obj.id
        except Exception as e:
            print(f"Stripe Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = f"Stripe Error: {str(e)}"
            )

    # Event Create Function
    def create_event(
        self, 
        user_id: str, 
        event_data: dict, 
        image_file: UploadFile
    ) -> Dict[str, Any]:
        """
        Event Create Flow ->
            1. Insert Event -> Get Event ID
            2. Upload Image Using Event ID
            3. Create Stripe Product -> If the Event is Paid
            4. Update Event with Image URL and Stripe Product and Price ID
            5. Map the Event to Corresponding Category
        """
        # Initialize the Rollback ID
        created_event_id = None
        try: 
            # 1. Prepare the Initial Payload
            initial_payload = {
                "title": event_data["title"],
                "description": event_data["description"],
                "location": event_data["location"],
                "event_date": event_data["event_date"],
                "event_end_date": event_data["event_end_date"],
                "max_slots": event_data["max_slots"],
                "is_paid": event_data["is_paid"],
                "ticket_price": event_data.get("ticket_price", 0),
                "currency": event_data.get("currency", "MYR"),
                "event_status": event_data.get("event_status", "published"),
                "created_by": user_id
            }

            # 2. Insert the Initial Payload to the Event Table to Get the Event ID
            insert_response = self.supabase.table(self.table).insert(initial_payload).execute()
            if not insert_response or len(insert_response.data) == 0: 
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = "Fail to Initialize the Event"
                )
            # 2.1 Retrieve the Event ID
            created_event = insert_response.data[0]
            created_event_id = created_event["id"]

            # 3. Perform External Action
            # 3.1 Upload Image to the Supabase Bucket Storage
            upload_result = self.storage.upload_event_image(image_file, created_event_id)
            image_url = upload_result["url"]
            # 3.2 Generate the Stripe ID If the Event Requires Payment
            stripe_product_id = None
            stripe_price_id = None

            if event_data.get("is_paid") and event_data.get("ticket_price", 0) > 0:
                stripe_product_id, stripe_price_id = self._ensure_stripe_product(
                    title = event_data["title"],
                    description = event_data["description"],
                    price = event_data["ticket_price"],
                    currency = event_data.get("currency", "MYR")
                )

            # 4. Update the Event with New Data
            updated_payload = {
                "image_url": image_url or "",
                "stripe_product_id": stripe_product_id or "",
                "stripe_price_id": stripe_price_id or ""
            }

            update_response = (
                self.supabase.table(self.table).update(updated_payload).eq("id", created_event_id).execute()
            )

            if not update_response.data:
                raise HTTPException(
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail = "Failed to Update Event"
                )

            final_event = update_response.data[0]

            # 5. Map the Event to the Corresponding Category
            category_id = event_data["category_id"]
            if category_id:
                self.supabase.table("event_category_map").insert({
                    "event_id": created_event_id,
                    "category_id": category_id
                }).execute()

            return final_event
        except Exception as e:
            # If Image Upload or Stripe Fail, Delete the Zombie Event Row
            if created_event_id: 
                print(f"Error Occured. Rolling Back Event {created_event_id}...")
                self.supabase.table(self.table).delete().eq("id", created_event_id).execute()
            print(f"Create Event Fail: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Create Event Fail: {str(e)}"
            )

    # Get the Event List
    def list_events(
        self, 
        page: int = 1, 
        size: int = 9, 
        search: Optional[str] = None, 
        category_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            # 1. Start the Query - Construct Query Based on Category Filter
            if category_id:
                query = self.supabase.table(self.table).select("*, event_category_map!inner(category_id, event_categories(id, name))", count = "exact").eq("event_category_map.category_id", category_id)
            else:
                query = self.supabase.table(self.table).select(
                    "*, event_category_map(event_categories(id, name))", 
                    count="exact"
                )
            # 2. Apply the Filters - The Event be Perform to View Must Be Published Status
            query = query.eq("event_status", "published")
            if created_by:
                query = query.eq("created_by", created_by)
            if search:
                query = query.ilike("title", f"%{search}%")
            
            # 3. Apply Pagination
            start = (page - 1) * size
            end = start + size - 1
            query = query.order("created_at", desc = True).range(start, end)

            # 4. Execute
            response = query.execute()

            items = response.data
            if items:
                # 5.1 Extract IDs of the events we just fetched
                event_ids = [item["id"] for item in items]

                # 5.2 Fetch all PAID bookings for these specific events in one single query
                # We use supabase_admin to bypass RLS to ensure we get the accurate total count
                booking_res = (
                    self.supabase_admin.table("bookings")
                    .select("event_id")
                    .in_("event_id", event_ids)
                    .eq("payment_status", "paid")
                    .execute()
                )

                # 5.3 Aggregate counts in Python (Much faster than looping queries)
                # This creates a dictionary like: {'event_id_1': 5, 'event_id_2': 12}
                booking_counts = Counter(b["event_id"] for b in booking_res.data)

                # 5.4 Attach the count to each item
                for item in items:
                    item["current_bookings"] = booking_counts[item["id"]]
                    
                    # (Existing logic) Clean up category map
                    if category_id:
                        item.pop("Event_Category_Map", None)

            return {
                "items": items,
                "total": response.count or 0,
                "page": page,
                "size": size
            }
        except Exception as e:
            print(f"List Events Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "Failed to Fetch Event"
            )

    # Get the Event by Event ID
    def get_event(
        self, 
        event_id: str
    ) -> Dict[str, Any]:
        try:
            # Fetch the Event ID and the Associated Category ID
            response = self.supabase.table(self.table).select("*, event_category_map(category_id, event_categories(name))").eq("id", event_id).execute()
            if not response.data:
                raise HTTPException(
                    status_code = status.HTTP_404_NOT_FOUND,
                    detail = "Event Not Found"
                )       
            event = response.data[0]
            booking_count_response = self.supabase_admin.table("bookings").select("*", count="exact", head=True).eq("event_id", event_id).eq("payment_status", "paid").execute()
            # Attach the count to the event object
            event["current_bookings"] = booking_count_response.count if booking_count_response.count else 0
            # Get the Organizer Full Name
            event_organizer_response = self.supabase.table("profile").select("full_name").eq("id", event["created_by"]).execute()
            # Check if data exists and assign
            if event_organizer_response.data:
                event["organizer"] = event_organizer_response.data[0] 
            else:
                event["organizer"] = {"full_name": "Unknown Organizer"}
            return event
        except Exception as e:
            print(f"Get Even Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Failed to Get Event {str(e)}"
            )

    # Delete the Event by Event ID and User ID
    def delete_event(
        self,
        event_id: str,
        user_id: str
    ) -> Dict[str, str]:
        try:
            # 1. Fetch the Corresponding Event Row
            response = self.supabase.table(self.table).select("*").eq("id", event_id).eq("created_by", user_id).execute()
            if not response.data:
                raise HTTPException(
                    status_code = status.HTTP_404_NOT_FOUND,
                    detail = "Event Not Found"
                )

            # 1.1 If the Current Event Got the Bookings Inside Already, the System Should Reject the Event Delete Operation
            bookings = self.supabase.table("bookings").select("id", count = "exact").eq("event_id", event_id).execute()
            if bookings.count > 0:
                raise HTTPException(
                    status_code = status.HTTP_409_CONFLICT,
                    detail = "Cannot Delete Event, There Are Active Bookings Associate With It."
                )
            
            # 1.2 Retreive the Needed Data
            event = response.data[0]
            stripe_product_id = event.get("stripe_product_id")
            stripe_price_id = event.get("stripe_price_id")
            image_url = event.get("image_url")

            # 2. Archieve Stripe Product and Price - Note: Need to Remove Price First
            try:
                if stripe_price_id: 
                    stripe.Price.modify(stripe_price_id, active = False)
                if stripe_product_id:
                    stripe.Product.modify(stripe_product_id, active = False)
            except Exception as e:
                print(f"Stripe Cleanup Warning: {e}")

            # 3. Delete the Image In Supabase Bucket Storage 
            if image_url:
                file_path = self._extract_path_from_url(image_url)
                if file_path:
                    self.storage.delete_event_image(file_path)

            # 4. Delete Database Record 
            self.supabase_admin.table(self.table).delete().eq("id", event_id).execute()
            
            return {
                "message": "Event Successfully Deleted"
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            print(f"Delete Event Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Delete Event Error: {str(e)}"
            )

    # Update the Event 
    def update_event(
        self, 
        event_id: str,
        user_id: str,
        payload: EventUpdateSchema
    ) -> Dict[str, Any]:
        """
        Scneraio Needed to Be Considered:
            1. Update the Image URL -> Need to Delete the Old File and Link the New File to the Updated Image URL
            2. Update the Category -> Remove the Original Row in the Event Category Map Table and Insert the New One
            3. Price Update:
                3.1 Is Paid to Free -> Archieve the Price and Product in Stripe -> Update the Data
                3.2 Free to Paid -> Create the New Price and Product in Stripe -> Update the Data
                3.3 Price or Currency Change -> Achieve the Old Price -> Create the New Price and Associate to the Product -> Update the Data
        """
        try:
            # 1. Fetch the Old Data -> We Need the Current State to Determine What is Changed
            #    So We Need to Retreive the Category ID From the Event Category Map Table
            response = self.supabase.table(self.table).select("*, event_category_map(category_id)").eq("id", event_id).eq("created_by", user_id).execute()
            # 1.1 Consider Fail to Retrieve the Event Data
            if not response.data:
                raise HTTPException(
                    status_code = status.HTTP_404_NOT_FOUND,
                    detail = "Event Not Found"
                )
            # 1.2 Retrieve the Un-updated Event Data and Assign a Variable to It
            old_event = response.data[0]
            # 1.3 Convert the Pydantic Model to Dict, and Ignoring the Fields The User Didn't Send
            updates = payload.model_dump(exclude_unset=True)

            # 2. Handle the Image URL Update
            if "image_url" in updates:
                new_url = updates["image_url"]
                old_url = old_event.get("image_url")
                # 2.1 If URL Changed, Delete the Old File From Storage
                if old_url and new_url != old_url:
                    try:
                        # 2.2 Get the File Path
                        old_file_path = self._extract_path_from_url(old_url)
                        if old_file_path:
                            # 2.3 Delete the File in the Bucket Storage
                            self.storage.delete_event_image(old_file_path)
                    except Exception as e:
                        print(f"Image Cleanup Warning: {e}")

            # 3. Handle the Category Update
            category_changed = False
            new_category_id = None
            if "category_id" in updates:
                # 3.1 Remove the Category ID From the Updates Dict -> Due to the Event Table Doesn't Have Category ID Column
                new_category_id = updates.pop("category_id")
                # 3.2 Get the Old Category ID Safety
                old_map = old_event.get("event_category_map", [])
                old_category_id = old_map[0]["category_id"] if old_map else None
                # 3.3 Modify the Tabble If the Category Changed
                if str(new_category_id) != str(old_category_id):
                    # Delete the Old Mapping
                    self.supabase.table("event_category_map").delete().eq("event_id", event_id).execute()
                    # Insert the New Mapping
                    self.supabase.table("event_category_map").insert({
                        "event_id": event_id,
                        "category_id": new_category_id
                    }).execute()
                category_changed = True
            
            # 4. Handle Stripe State Transitions
            if "is_paid" in updates or "ticket_price" in updates or "currency" in updates or "title" in updates or "description" in updates:
                # 4.1.1 Resolve Current State
                new_is_paid = updates.get("is_paid", old_event["is_paid"])
                new_ticket_price = updates.get("ticket_price", old_event.get("ticket_price", 0))
                new_currency = updates.get("currency", old_event.get("currency", "MYR"))
                old_is_paid = old_event["is_paid"]

                current_title = updates.get("title", old_event["title"])
                current_desc = updates.get("description", old_event["description"])

                # 4.1.2 Detect Changes
                price_changed = new_ticket_price != old_event.get("ticket_price")
                currency_changed = new_currency != old_event.get("currency")

                text_changed = (
                    updates.get("title") is not None and updates["title"] != old_event["title"]
                ) or (
                    updates.get("description") is not None and updates["description"] != old_event["description"]
                ) 

                # 4.2 Scenario 1 - Paid -> Free
                if old_is_paid and not new_is_paid:
                    # 4.2.1 Archieve Old Stripe Artifacts
                    try: 
                        if old_event.get("stripe_price_id"):
                            stripe.Price.modify(old_event.get("stripe_price_id"), active = False)
                        if old_event.get("stripe_product_id"):
                            stripe.Product.modify(old_event.get("stripe_product_id"), active = False)
                    except Exception as e:
                        print(f"Stripe Archieving Warning: {e}")
                    # 4.2.1 Update the updates Dict
                    updates.update({
                        "stripe_price_id": None,
                        "stripe_product_id": None,
                        "ticket_price": 0,
                        "is_paid": False
                    })
                # 4.3 Scenario 2 - Free -> Paid
                elif not old_is_paid and new_is_paid:
                    # 4.3.1 Create the New Price and Product in the Stripe
                    prod_id, price_id = self._ensure_stripe_product(
                        title = current_title,
                        description = current_desc,
                        price = new_ticket_price,
                        currency = new_currency
                    )
                    # 4.3.2 Update the updates Dict
                    updates.update({
                        "stripe_price_id": price_id,
                        "stripe_product_id": prod_id,
                        "ticket_price": new_ticket_price,
                        "is_paid": True
                    })
                # 4.4 Scenario 3 - Price Changed
                elif old_is_paid and new_is_paid:
                    # 4.4.1 Retrieve the Product ID
                    prod_id = old_event["stripe_product_id"]
                    # 4.4.2 Handle Price and Currency Changed
                    if price_changed or currency_changed:
                        # 4.4.2.1 Archieve the Old Product Price First
                        if old_event.get("stripe_price_id"):
                            try:
                                stripe.Price.modify(old_event["stripe_price_id"], active=False)
                            except Exception as e:
                                print(f"Stripe Price Archieving Fail: {e}")
                            if prod_id:
                                # Add the New Created Price to the Current Product
                                try: 
                                    new_price_obj = stripe.Price.create(
                                        product = prod_id,
                                        unit_amount = int(new_ticket_price*100),
                                        currency = new_currency.lower()
                                    )
                                    updates["stripe_price_id"] = new_price_obj.id
                                except Exception as e:
                                    print(f"Stripe Price Creation Fail: {e}")
                                    # Fallback Function
                                    p_id, pr_id = self._ensure_stripe_product(current_title, current_desc, new_ticket_price, new_currency)
                                    updates["stripe_product_id"] = p_id
                                    updates["stripe_price_id"] = pr_id
                                    prod_id = p_id
                    # 4.4.3 Handle the Text Changed
                    if text_changed and prod_id:
                        try:
                            stripe.Product.modify(prod_id, name = current_title, description = current_desc or "")
                        except Exception as e:
                            print(f"Stripe Meta Data Update Warning: {e}")
                    
            # 5. Execute Event Table Update
            if updates:
                response = self.supabase.table(self.table).update(updates).eq("id", event_id).execute()
                if not response.data:
                    raise HTTPException(
                        status_code=500, 
                        detail="Database update failed. No data returned. Check RLS policies."
                    )
                final_data = response.data[0]
                if category_changed:
                    final_data["event_category_map"] = [{"category_id": new_category_id}]
            elif category_changed:
                final_data = old_event
                final_data["event_category_map"] = [{"category_id": new_category_id}]
            else:
                return {"message": "No changes detected", "updates": old_event}
                    
            return {
                "message": "Event Updated Successfully",
                "updates": final_data
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Update Event Fail: {str(e)}"
            )
