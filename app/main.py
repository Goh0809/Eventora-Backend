from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import auth, profiles, events, event_categories, event_participants, bookings, dashboard
from datetime import datetime
import uvicorn

# Initialize FastAPI Instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    version="1.0.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(profiles.router, prefix=f"{settings.API_V1_PREFIX}/profiles", tags=["Profiles"])
app.include_router(events.router, prefix=f"{settings.API_V1_PREFIX}/events", tags=["Events"])
app.include_router(event_categories.router, prefix=f"{settings.API_V1_PREFIX}/categories", tags=["Categories"])
# app.include_router(event_participants.router, prefix=f"{settings.API_V1_PREFIX}/event-participants", tags=["Event Participants"])
app.include_router(bookings.router, prefix=f"{settings.API_V1_PREFIX}/bookings", tags=["Bookings"])
app.include_router(dashboard.router, prefix=f"{settings.API_V1_PREFIX}/dashboard", tags=["Dashboard"])

# Testing Routes
@app.get("/")
async def root():
    return {
        "message": "Welcome to the Eventora API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


