"""
VitalStep API - Production-ready FastAPI Application
Main application entry point with middleware, error handlers, and router registration
"""
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.logging_config import setup_logging, log_error
from app.database import db_manager
from app.ml_service import get_ml_service

# Setup logging
setup_logging(log_level=settings.LOG_LEVEL, log_format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    
    # Initialize database connections
    logger.info("Initializing database connections...")
    db_initialized = db_manager.initialize()
    if not db_initialized:
        logger.warning("Database initialization failed - some features may not work")
    
    # Load ML model
    logger.info("Loading ML model...")
    ml_service = get_ml_service()
    model_loaded = ml_service.load_model()
    if not model_loaded:
        logger.warning("ML model not loaded - fallback predictions are marked explicitly in every response")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    db_manager.close()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready API for VitalStep - ML-powered grip strength analysis and HubSpot integration",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)


# ============================================================================
# Middleware
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ============================================================================
# Custom Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "value": error.get("input")
        })
    
    logger.warning(f"Validation error: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "detail": errors,
            "timestamp": time.time()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    log_error(exc, logger, {"path": request.url.path, "method": request.method})
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if settings.is_development else "An unexpected error occurred",
            "timestamp": time.time()
        }
    )


# ============================================================================
# Middleware for request logging
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests"""
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path}",
        extra={
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host if request.client else None
        }
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    duration = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} ({duration:.3f}s)",
        extra={
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2)
        }
    )
    
    return response


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Overall health check"""
    db_health = db_manager.health_check()
    ml_service = get_ml_service()
    ml_info = ml_service.get_model_info()
    
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "supabase_connected": db_health["primary"]["connected"],
        "hubspot_connected": True,  # Will be checked on first request
        "ml_model_loaded": ml_info["is_loaded"],
        "timestamp": time.time()
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Kubernetes readiness probe"""
    db_health = db_manager.health_check()
    
    if not db_health["primary"]["connected"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not ready"
        )
    
    return {"status": "ready"}


@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}


# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "ml_predictions": "/api/v1/ml",
            "hubspot_sync": "/api/v1/hubspot",
            "patients": "/api/v1/patients"
        }
    }


# ============================================================================
# Router Registration
# ============================================================================

from app.routers import ml, hubspot, patients, auth, users, tests, queue, devices, remarks, account_access

# Include routers with API prefix
app.include_router(ml.router, prefix=f"{settings.API_PREFIX}")
app.include_router(hubspot.router, prefix=f"{settings.API_PREFIX}")
app.include_router(patients.router, prefix=f"{settings.API_PREFIX}")
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}")
app.include_router(users.router, prefix=f"{settings.API_PREFIX}")
app.include_router(tests.router, prefix=f"{settings.API_PREFIX}")
app.include_router(queue.router, prefix=f"{settings.API_PREFIX}")
app.include_router(devices.router, prefix=f"{settings.API_PREFIX}")
app.include_router(remarks.router, prefix=f"{settings.API_PREFIX}")
app.include_router(account_access.router, prefix=f"{settings.API_PREFIX}")


# ============================================================================
# Legacy Endpoints (for backward compatibility)
# ============================================================================

@app.post("/sync/supabase")
async def legacy_sync_supabase(background_tasks, limit: int = 20):
    """Legacy endpoint - redirects to new API"""
    from app.routers.patients import run_supabase_to_hubspot_sync
    background_tasks.add_task(run_supabase_to_hubspot_sync, limit)
    return {"status": "started", "limit": limit, "message": "Use /api/v1/patients/sync/supabase instead"}


@app.post("/sync/app-contact")
async def legacy_sync_app_contact(payload: dict):
    """Legacy endpoint - redirects to new API"""
    from hubspot_utils import sync_app_contact_to_hubspot
    return sync_app_contact_to_hubspot(payload)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
