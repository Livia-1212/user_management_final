from builtins import Exception
from fastapi import FastAPI
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from fastapi_utils.tasks import repeat_every  # Import for scheduling background tasks
from app.database import Database, get_db
from app.dependencies import get_settings
from app.routers import user_routes
from app.routers.user_routes import router as analytics_router  # Import analytics router
from app.services.analytics_service import AnalyticsService  # Import the analytics service
from app.utils.api_description import getDescription

app = FastAPI(
    title="User Management",
    description=getDescription(),
    version="0.0.1",
    contact={
        "name": "API Support",
        "url": "http://www.example.com/support",
        "email": "support@example.com",
    },
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,  # Support cookies and headers
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all HTTP headers
)

# Initialize database connection on startup
@app.on_event("startup")
async def startup_event():
    settings = get_settings()
    Database.initialize(settings.database_url, settings.debug)

# Background task for retention analytics
@app.on_event("startup")
@repeat_every(seconds=3600)  # Run every hour
async def periodic_retention_metrics():
    async with get_db() as db:
        await AnalyticsService.calculate_retention_metrics(db)

# Global exception handler
@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return JSONResponse(
        status_code=500, content={"message": "An unexpected error occurred."}
    )

# Include routers
app.include_router(user_routes.router)
app.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])  # Add analytics router
