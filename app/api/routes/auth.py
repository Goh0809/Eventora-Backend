from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.api.deps import get_current_user
from app.schemas import auth
from app.schemas.auth import ForgotPasswordRequest, GithubLoginRequest, GoogleLoginRequest, OAuthUrlResponse, UserLogin, UserPasswordUpdate, UserRegister, TokenResponse, VerifyResetCodeRequest
from app.services import auth_service
from app.services.auth_service import AuthService
from app.core.database import supabase
from typing import Union
from fastapi.responses import JSONResponse

router = APIRouter()
security = HTTPBearer()
auth_service = AuthService()

@router.post("/register", response_model=Union[TokenResponse, dict], status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserRegister
):
    # Register a new User
    try:
        result = auth_service.register_user(user_data)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post('/login', response_model = TokenResponse, status_code = status.HTTP_201_CREATED)
def login(
    user_data: UserLogin
):
    # Login User and Return Access Token
    try: 
        result = auth_service.login_user(user_data)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid Email or Password"
        )

@router.get("/oauth/google/url", response_model = OAuthUrlResponse)
def get_google_oauth_url(
    redirect_url: str
):
    # Get Google OAuth URL for Authentication
    try: 
        result = auth_service.get_google_oauth_url(redirect_url)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = str(e)
        )

@router.post("/oauth/google/callback", response_model = TokenResponse)
def google_oauth_callback(
    payload: GoogleLoginRequest
):
    # Verify the Code Send by the Frontend and Return the Session
    try: 
        result = auth_service.login_with_google_code(payload.code)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = str(e)
        )

@router.get("/oauth/github/url", status_code=status.HTTP_200_OK)
def get_github_url(redirect_url: str):
    return auth_service.get_github_oauth_url(redirect_url)

@router.post("/oauth/github/callback", response_model = TokenResponse, status_code = status.HTTP_200_OK)
def github_oauth_callback(
    payload: GithubLoginRequest
):
    return auth_service.login_with_github_code(payload.code)

@router.post("/logout", status_code = status.HTTP_200_OK)
def logout(
    auth: HTTPAuthorizationCredentials = Depends(security)
):
    # Logout User Requries a Valid Access Token in the Authorization Bearer
    try: 
        token = auth.credentials
        result = auth_service.logout_user(token)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = str(e)
        )



@router.post("/refresh", response_model = TokenResponse)
def refresh_token(
    refresh_token: str
):
    # Get a New Access Token Using the Refresh Token
    try:
        result = auth_service.refresh_token(refresh_token)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Token Refresh Failed"
        )

@router.post("/forgot-password", status_code = status.HTTP_200_OK)
def forgot_password(
    request: ForgotPasswordRequest
):
    # Request Password Reset Email
    try: 
        result = auth_service.forgot_password(request.email, request.redirect_url)
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_400_BAD_REQUEST,
            detail = str(e)
        )

@router.put("/reset-password", status_code = status.HTTP_200_OK)
def reset_password(payload: UserPasswordUpdate, user = Depends(get_current_user)):
    try:
        if not user.id: 
            raise HTTPException(
                status_code = status.HTTP_401_UNAUTHORIZED,
                detail = "Authentication Fail"
            )
        return auth_service.reset_password(user.id, payload)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail = f"Reset Password Operation Fail: {str(e)}"
        )

@router.post("/verify-reset-code", response_model = TokenResponse, status_code = status.HTTP_200_OK)
def verify_reset_code(payload: VerifyResetCodeRequest):
    return auth_service.verify_reset_code(payload.code)