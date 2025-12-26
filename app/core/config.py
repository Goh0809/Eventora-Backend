from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Supabase Configuration
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # Supabase Bucket Configuration
    EVENT_IMAGE_BUCKET: str = "event-images"
    EVENT_IMAGE_FOLDER: str = "banners"
    AVATAR_BUCKET: str = "avatars"

    # JWT Configuration
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    # Stripe Configuration
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    # CORS Configuration
    CORS_ORIGINS: list = ["*"]

    # APP Configuration
    PROJECT_NAME: str = "Eventora API"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()