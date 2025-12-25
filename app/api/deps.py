from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.database import SupabaseClient 
# We don't need decode_access_token anymore

security = HTTPBearer()

# 1. Initialize Client once to save resources
supabase_client = SupabaseClient.get_client()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Validates the Bearer Token directly with Supabase Auth Server.
    """
    token = credentials.credentials
    
    try:
        # This sends the token to Supabase. 
        # Supabase verifies the signature, expiration, and user existence for you.
        response = supabase_client.auth.get_user(token)
        
        if not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token or user not found"
            )
            
        # Return the Supabase User object
        # It contains .id, .email, .user_metadata, etc.
        return response.user

    except Exception as e:
        # If Supabase says "No", we say "No"
        print(f"Auth Validation Error: {e}") # Debugging help
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth Failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )