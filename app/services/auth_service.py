from fastapi import HTTPException, status
from app.schemas.auth import UserPasswordUpdate, UserRegister, TokenResponse, UserLogin
from app.core.database import SupabaseClient
from app.core.config import settings
from typing import Dict, Any
from gotrue.errors import AuthApiError
from datetime import datetime, timezone
from urllib.parse import urlencode

class AuthService:
    """Service for handling authentication operations"""
    def __init__(self):
        self.supabase = SupabaseClient.get_client()
        self.supabase_admin = SupabaseClient.get_service_client()
    
    # New User Registration Function 
    def register_user(self, user_data: UserRegister) -> TokenResponse:
        """
        Register a new user with Supabase Auth, Profile Creation is Handled Automatically by Postrege Triggers
        """
        try:
            # 1. Register user with Supabase Auth
            response = self.supabase.auth.sign_up({
                "email": user_data.email,
                "password": user_data.password,
                "options": {
                    "data": {
                        "full_name": user_data.full_name or ""
                    }
                }
            })
            # If There is Not User in the Response, Raise the Corresponding HTTPException
            if not response.user:
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = "Failed to create user"
                ) 

            # Create User Profile in Profiles Table if the Profile Doesn't Exist - Be Implemented in the Supabase Function Already
            
            # 2. Check If Session Exists 
            session = response.session
            # 2.1 Case 1 - Email COnfirmation is Required - Due to Email Auto-Confirmed Isn't Work
            if not session:
                # Return Response without Token
                return {
                    "message": "Registration Successful. Please check your email.",
                    "user_id": response.user.id,
                    "email": response.user.email,
                    "requires_confirmation": True
                }      

            # 2.1 Case 2 - Email Auto Confirmed Operation is Working -> Return the Response with the Token
            return TokenResponse(
                access_token = session.access_token,
                refresh_token = session.refresh_token,
                token_type = "Bearer",
                expires_in = session.expires_in,
                user = {
                    "id": response.user.id,
                    "email": response.user.email,
                    "full_name": user_data.full_name
                }
            )
        except AuthApiError as e:
            # Handle the Specific Supabase Authentication Error
            msg = str(e).lower()
            if "already registered" in msg or "already exists" in msg:
                raise HTTPException(
                    status_code = status.HTTP_409_CONFLICT,
                    detail = "Email is Already Been Registered" 
                )
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = e.message
            )
        except Exception as e:
            print(f"Registration Failed: {e}")
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = "An Unexcepted Error Occured During Registration"
            )
            

    # User Login Function 
    def login_user(self, user_data: UserLogin) -> TokenResponse:
        """
        Login User, Returning Access and Refereh Tokens
        """
        try: 
            # 1. Authentication with Supabase
            response = self.supabase.auth.sign_in_with_password({
                "email": user_data.email,
                "password": user_data.password
            })
            # 1.1 Check If the Response Has Returned the User
            if not response.user or not response.session:
                raise HTTPException(
                    status_code = status.HTTP_401_UNAUTHORIZED,
                    detail = "Login Failed. No Session Created."
                )

            # 2. Check Email Confirmation 
            if response.user.email_confirmed_at is None:
                raise HTTPException(
                    status_code = status.HTTP_403_FORBIDDEN,
                    detail = "Email is Not Verified. Please Check Your Email."
                )

            # 3. Update Profile Last Login Timestampz
            try:
                self.supabase.table("profile").update({
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("id", response.user.id).execute()
            except Exception as e:
                print(f"Failed to Updated Profile updated_at: {e}")
            
            # 3.1 Fetch Profile Detail
            profile_data = {}
            try: 
                profile_result = (
                    self.supabase.table("profile")
                    .select("full_name", "avatar_url", "bio")
                    .eq("id", response.user.id)
                    .single()
                    .execute()
                )
                profile_data = profile_result.data
            except Exception as e:
                print(f"Warning: Profile Fetch Failed For User {response.user.id}: {e}")
            
            user_info = {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": profile_data.get("full_name"),
                "bio": profile_data.get("bio", ""),
                "avatar_url": profile_data.get("avatar_url", "")
            }

            # 4. Return Token Response When Login Successful
            session = response.session
            return TokenResponse(
                access_token = session.access_token,
                refresh_token = session.refresh_token,
                token_type = "bearer",
                expires_in = session.expires_in,
                user = user_info
            )
        except AuthApiError as e:
            # Handle Supabase Specific Auth Error
            msg = str(e).lower() 
            print(msg)
            if "invalid_grant" in msg or "invalid login" in msg:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
            elif "email not confirmed" in msg:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email not confirmed"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=e.message
                )
        except HTTPException as e:
            raise e
        except Exception as e:
            # Catch-all for unexpected server errors
            print(f"Login System Error: {e}") 
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred during login."
            )

    # Login With Goolge Function -> Get Google Login URL
    def get_google_oauth_url(self, redirect_url: str) -> dict:
        """
        Generate the Google OAuth Consent Screen URL
        """
        try:
            # Generate OAuth URL using Supabase
            response = self.supabase.auth.sign_in_with_oauth({
                "provider": "google",
                "options": {
                    "redirect_to": redirect_url,
                    "query_params": {
                        "access_type": "offline",
                        "prompt": "consent"
                    }
                },
            })

            return {
                "url": response.url,
                "provider": "google"
            }
        
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = f"Failed to Generate OAuth URL: {str(e)}"
            )

    
    # Google Login Function -> Login with the Code Return By the Google OAuth
    def login_with_google_code(self, code: str) -> TokenResponse:
        """
        Exchange the Auth Code From the Client for a User Session
        """
        try:
            # 1. Exchange the Code for the Session
            response = self.supabase.auth.exchange_code_for_session({"auth_code": code})
            if not response.user or not response.session:
                raise HTTPException(
                    status_code = status.HTTP_401_UNAUTHORIZED,
                    detail = "Goolge Login Failed: No Session Created"
                )

            user_info = {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.user_metadata.get("full_name", ""),
                "avatar_url": response.user.user_metadata.get("avatar_url", "")
            }

            session = response.session

            return TokenResponse(
                access_token = session.access_token,
                refresh_token = session.refresh_token,
                token_type = "bearer",
                expires_in = session.expires_in,
                user = user_info
            )
        except AuthApiError as e:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = f"Supabase Authentication Failed: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = f"Google Login Error: {str(e)}"
            )

    # Github Login Function -> Get Github Login URL
    def get_github_oauth_url(self, redirect_url: str) -> dict:
        """
        Generate the Github Oauth Consent Screen URL
        """
        try: 
            response = self.supabase.auth.sign_in_with_oauth({
                "provider": "github",
                "options": {
                    "redirect_to": redirect_url
                }
            })
            return { "url": response.url, "provider": "github"}
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = f"Failed to Generate Github OAuth URL: {str(e)}"
            )

    # Login With Github Code
    def login_with_github_code(self, code: str) -> TokenResponse:
        """Exchange the GitHub Auth Code for a User Session"""
        try:
            response = self.supabase.auth.exchange_code_for_session({"auth_code": code})
            if not response.user or not response.session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="GitHub Login Failed: No Session Created"
                )
            user_info = {
                "id": response.user.id,
                "email": response.user.email,
                "full_name": response.user.user_metadata.get("full_name", ""),
                "avatar_url": response.user.user_metadata.get("avatar_url", "")
            }

            session = response.session
            return TokenResponse(
                access_token=session.access_token,
                refresh_token=session.refresh_token,
                token_type="bearer",
                expires_in=session.expires_in,
                user=user_info
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"GitHub Login Error: {str(e)}"
            )


    # User Logout Function     
    def logout_user(self, access_token: str, refresh_token: str = None) -> dict:
        """
        Logout User By Invalidating the Session
        """
        try:
            # 1. Hydrate the Session So the Client Know Who is Talking
            if refresh_token: 
                self.supabase.auth.set_session(access_token, refresh_token)
            else: 
                # Just Set the Header
                self.supabase.postgrest.auth(access_token)
            # 2. Sign Out
            self.supabase.auth.sign_out()
            # 3. Return the Sign Out Success message
            return {
                "message": "Logged Out Successfully"
            }
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_400_BAD_REQUEST,
                detail = f"Logout Failed: {str(e)}"
            )

    # Refresh Access Token Function
    def refresh_token(self, refresh_token: str) -> TokenResponse:
        """
        Refresh Access Token Using Refresh Token -> Keep User Stay Login Without Re-entering Password
        """
        try:
            # Call Supabase Function to Refresh Access Token
            response = self.supabase.auth.refresh_session(refresh_token)

            if not response.session:
                raise HTTPException(
                    status_code = status.HTTP_401_UNAUTHORIZED,
                    detail = "Failed to Refresh Token, Due to Invalid or Expired Refresh Token"
                )

            session = response.session

            # Return the Response with Token Once Refreshing Successfully
            return TokenResponse(
                access_token = session.access_token,
                refresh_token = session.refresh_token,
                token_type = "bearer",
                expires_in = session.expires_in,
                user = {
                    "id": response.user.id,
                    "email": response.user.email
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Token Refresh Failed. Please Login Again"
            )

    # Forgot Password Function
    def forgot_password(self, email: str, redirect_url: str) -> dict:
        """
        Trigger a Password Reset Email Through Supabase
        """
        try: 
            # Supabase Handle the Token Generation and Email Sending
            self.supabase.auth.reset_password_email(email, options={
                "redirect_to": redirect_url
            })
            # Return Success Message to Prevent Email Enumeration
            return {
                "message": "If An Account with That Email Exists, A Password Reset Link Has Been Sent.",
                "success": True
            }
        except Exception as e:
            print(f"Password Reset Request Error: {e}")
            return {
                "message": "If An Account with That Email Exists, A Password Reset Link Has Been Sent.",
                "success": True
            }

    # Reset Password Function
    def reset_password(self, user_id: str, payload: UserPasswordUpdate):
        # Update the Password for a Specific User ID
        try: 
            # Validate the Password Matching
            if payload.password != payload.confirm_password:
                raise HTTPException(
                    status_code = status.HTTP_400_BAD_REQUEST,
                    detail = "Password Do Not Match"
                )
            # Update the User Password Through Supabase Admin API
            response = self.supabase_admin.auth.admin.update_user_by_id(
                user_id,
                {"password": payload.password}
            )

            if not response.user:
                raise HTTPException(
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail = "Failed to Update Password in Supabase"
                )

            return {"message": "User Password Updated Successfully"}
        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail = f"User Password Update Fail: {str(e)}"
            )

    # Verify Reset Code Function
    def verify_reset_code(self, code: str) -> TokenResponse:
        """
        Exchange the Email Code For a Valid Session Token,
        Frontend Calls This Prove the User Clicked on the Link
        """
        try:
            response = self.supabase.auth.exchange_code_for_session({"auth_code": code})
            
            if not response.session:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired reset link."
                )
            
            return TokenResponse(
                access_token=response.session.access_token,
                refresh_token=response.session.refresh_token,
                token_type="bearer",
                expires_in=response.session.expires_in,
                user={
                    "id": response.user.id,
                    "email": response.user.email
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Verification Failed: {str(e)}"
            )