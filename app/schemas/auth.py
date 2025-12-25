from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "blackhei364@gmail.com",
                "password": "123456",
                "full_name": "John Doe"
            }
        }

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "blackhei364@gmail.com",
                "password": "123456"
            }
        }

class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict

    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "user-uuid",
                    "email": "user@example.com"
                }
            }
        }

class OAuthUrlResponse(BaseModel):
    """Schema for OAuth URL response"""
    url: str
    provider: str

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://accounts.google.com/o/oauth2/v2/auth?...",
                "provider": "google"
            }
        }

class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    email: EmailStr
    redirect_url: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "redirect_url": "http://localhost:3000/auth/update-password"
            }
        }

class UserPasswordUpdate(BaseModel):
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    confirm_password: str

    def check_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Password Doesn't Match")

class VerifyResetCodeRequest(BaseModel):
    code: str

class GoogleLoginRequest(BaseModel):
    code: str

class GithubLoginRequest(BaseModel):
    code: str

