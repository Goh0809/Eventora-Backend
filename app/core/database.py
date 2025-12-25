from supabase import create_client, Client
from app.core.config import settings
from supabase.lib.client_options import ClientOptions
from typing import Optional
import httpx

class SupabaseClient:
    _client: Optional[Client] = None

    @classmethod
    def get_client(cls) -> Client:
        if cls._client is None:
            cls._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            cls._client.postgrest.timeout = 60
            try: 
                cls._client.auth._http_client.timeout = httpx.Timeout(60.0)
            except AttributeError:
                pass
        return cls._client

    @classmethod
    def get_service_client(cls) -> Client:
        """Get Supbase Client with Service Role Key for Admin Operations"""
        if settings.SUPABASE_SERVICE_ROLE_KEY:
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            client.postgrest.timeout = 60 
            try: 
                client.auth._http_client.timeout = httpx.Timeout(60.0)
            except AttributeError:
                pass
            return client  
        return cls.get_client()

# Initialize Supabase Client
supabase: Client = SupabaseClient.get_client()