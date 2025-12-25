import stripe
from fastapi import HTTPException, status, Request
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from app.core.database import SupabaseClient
from app.core.config import settings
from app.schemas.booking import BookingCreateSchema
from app.services.event_participant_service import EventParticipantService # -> Helper Service

stripe.api_key = settings.STRIPE_SECRET_KEY

class BookingService:
    # Initliaze the Service Needed for Booking API
    def __init__(self):
        self.supabase = SupabaseClient.get_client()
        self.supabase_admin = SupabaseClient.get_service_client()
        self.event_participant_service = EventParticipantService()
        self.table = "bookings"

    # Helper Function to Fullfill the Data in the Bookings Table
    def _fulfill_booking(self, session):
        # 1. Using .get() Everywhere to Prevent the App From Crashing If Data is Missing
        booking_id = session.get("metadata", {}).get("booking_id")
        user_id = session.get("metadata", {}).get("user_id")
        event_id = session.get("metadata", {}).get("event_id")

        if not booking_id:
            print(f"Webhook Received Without Booking ID")
            return

        # 2. Idempotency Check -> Checking the DB Before Doing Any Work
        current_booking = self.supabase_admin.table(self.table).select("payment_status").eq("id",booking_id).execute()
        if current_booking.data and current_booking.data[0]["payment_status"] == "paid":
            print(f"Booking {booking_id} is Already Fulfilled. Skipping")
            return

        # 3. Price Sync and Table Update
        amount_paid = session.get("amount_total")
        self.supabase_admin.table(self.table).update({
            "payment_status": "paid", 
            "stripe_payment_intent_id": session.get("payment_intent"),
            "amount_total": amount_paid
        }).eq("id", booking_id).execute()

        # 4. Issue the Event Participant Table
        self.event_participant_service.create_participant(user_id, event_id)

    # Initiate the Checkout Session - For Single Ticket ***
    def create_checkout_session(self, user_id: str, user_email: str, payload: BookingCreateSchema):
        try:
            # 1. Fetch the Event Detail First
            event_response = self.supabase_admin.table("event").select("*").eq("id", payload.event_id).execute()
            if not event_response.data: 
                raise HTTPException(
                    status_code = status.HTTP_404_NOT_FOUND,
                    detail = "Event Not Found"
                )
            event = event_response.data[0]
            # *** One User Can Only Register for One Event
            # 2. Check the Accessibility to Purchase a Ticket
            # 2.1 Check 1 - Check If the User Has Already Registered for the Event -> If Registered Stop the Payment Process
            is_registered = self.event_participant_service.check_participant_exists(user_id, payload.event_id)
            if is_registered: 
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = "You Are Already Registered for This Event Already"
                )

            # 2.2 Check 2 - Event Ticket Sold Out?
            # 2.2.1 - Get the Confirmed Participants
            confirmed_count = self.event_participant_service.get_participant_count(payload.event_id)
            # 2.2.2 - Get the Pending Booking For the Last 15 Minutes - Cart In Progress
            #         Assume a Ticket Session is 15 Minutes
            now_utc = datetime.now(timezone.utc)
            time_threshold = (now_utc - timedelta(minutes = 15)).isoformat()
            pending_response = (self.supabase_admin.table(self.table)
                                    .select("*", count = "exact", head = True)
                                    .eq("event_id", payload.event_id)
                                    .eq("payment_status", "pending")
                                    .gte("created_at", time_threshold)
                                    .execute()
                                )
            pending_count = pending_response.count or 0
            total_held = confirmed_count + pending_count
            if total_held + 1 > event["max_slots"]:
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = "The Event Ticket is Sold Out"
                )

            # 3. Handle the Free Event 
            if not event.get("is_paid"):
                # 3.1 Issue Ticket to the Event Participant Table Immediately
                self.event_participant_service.create_participant(user_id, payload.event_id)
                # 3.2 Record the Transaction Detail in the Bookings Table
                new_booking = self.supabase_admin.table(self.table).insert({
                    "user_id": user_id,
                    "event_id": payload.event_id,
                    "amount_total": 0,
                    "payment_status": "paid",
                    "payment_method": "card"
                }).execute()

                return {
                    "booking_id": new_booking.data[0]["id"],
                    "checkout_url": None,
                    "status": "Confirmed",
                    "message": "Registration Successful"
                }

            # 4. Handle the Paid Event
            if not event.get("stripe_price_id"):
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = "Stripe Price Configuration Missing for This Event"
                )
            # 4.1 Create the Pending Booking in the Bookings Table
            amount_cents = int(event["ticket_price"] * 100)
            booking_response = self.supabase_admin.table(self.table).insert({
                "user_id": user_id,
                "event_id": payload.event_id,
                "amount_total": amount_cents,
                "currency": event.get("currency", "myr"),
                "payment_status": "pending"
            }).execute()
            booking_id = booking_response.data[0]["id"]
            # 4.2 Call the Stripe API
            try: 
                session = stripe.checkout.Session.create(
                    payment_method_types = ["card"],
                    line_items = [{
                        "price": event["stripe_price_id"],
                        "quantity": 1
                    }],
                    mode = "payment",
                    success_url = payload.success_url,
                    cancel_url = payload.cancel_url,
                    customer_email = user_email,
                    expires_at = int((now_utc + timedelta(minutes= 30)).timestamp()),
                    metadata = {
                        "booking_id": booking_id,
                        "user_id": user_id,
                        "event_id": payload.event_id
                    }
                )
            except Exception as e:
                # Rollback Booking Table If Stripe Fails
                self.supabase_admin.table(self.table).delete().eq("id", booking_id).execute()
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = f"Stripe Create Session Error: {str(e)}"
                )

            # 5. If Stripe Session Created Successful
            self.supabase_admin.table(self.table).update({
                "stripe_session_id": session.id
            }).eq("id", booking_id).execute()
            print(session.id)
            return {
                "booking_id": booking_id,
                "checkout_url": session.url,
                "status": "pending",
                "message": "Redirecting to Payment..."
            }
        except HTTPException as e:
            raise e
        except Exception as e:
            print(f"Booking Error: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Booking Fail: {str(e)}"
            )

    # Handle Stripe Webhook
    async def handle_stripe_webhook(self, request: Request):
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = f"Stripe Webhook Error: {str(e)}"
            )

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            self._fulfill_booking(session)

        return {"status": "success"}

    # Event Organizer Get the Booking and Participants Details For Their Own Event
    def get_event_bookings_for_organizer(self, event_id: str, organizer_id: str):
        # List All Booking Details For a Specific Event 
        try:
            # 1. Check Whether If the Event is Belong to the Organizer
            event_response = self.supabase.table("event").select("created_by").eq("id", event_id).single().execute()
            if not event_response.data or event_response.data["created_by"] != organizer_id:
                raise HTTPException (
                    status_code = status.HTTP_403_FORBIDDEN,
                    detail = "You are Not the Organizer for This Event"
                )
            # 2. Fetch the Data
            booking_response = self.supabase.table(self.table).select("*, profile(full_name, email), event(title)").eq("event_id", event_id).eq("payment_status", "paid").order("created_at", desc = True).execute()
            return booking_response.data
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Failed to Get the Participant Detail: {str(e)}"
            )

    # Get All Booking Details of the User
    def list_my_bookings(self, user_id: str):
        booking_response = (
            self.supabase.table(self.table)
            .select("*, event(title, location, event_date, image_url)")
            .eq("user_id", user_id)
            .order("created_at", desc=True) 
            .execute()
        )

        if not booking_response.data:
            return [] 
            
        return booking_response.data

    # Get Specific Booking Detail
    def get_booking_detail(self, booking_id: str):
        try: 
            booking_response = self.supabase.table(self.table).select("*, event(*), profile(full_name, email)").eq("id", booking_id).single().execute()
            if not booking_response.data:
                raise HTTPException(
                    status_code = status.HTTP_404_NOT_FOUND, 
                    detail = "Booking Not Found"
                )
            return booking_response.data
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"Booking Detail Found Error: {str(e)}"
            )

    # Check the User Accessibility to Take Participate a Event
    def get_booking_status(self, user_id: str, event_id: str) -> Dict[str, Any]:
        try:
            # Check for any booking for this user + event
            # We assume 'paid' is the only status that counts as "Already Participating"
            response = (
                self.supabase.table(self.table)
                .select("id, payment_status")
                .eq("user_id", user_id)
                .eq("event_id", event_id)
                .eq("payment_status", "paid") # Only fetch confirmed bookings
                .execute()
            )
            if response.data and len(response.data) > 0:
                return {
                    "has_booked": True,
                    "booking_id": response.data[0]['id'],
                    "status": response.data[0]['payment_status']
                }
            return {
                "has_booked": False,
                "booking_id": None,
                "status": None
            }       
        except Exception as e:
            print(f"Check Booking Status Error: {e}")
            # Fail safe: assume they haven't booked so they aren't blocked unnecessarily
            return {"has_booked": False}