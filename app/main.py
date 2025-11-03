"""FastAPI application initialization"""

from fastapi import FastAPI

from app.routers.auth import router as auth_router
from app.routers.webhook import router as webhook_router
from app.utils.logging import get_logger, setup_logging

# Initialize logging before creating app
setup_logging()

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Telegram Bot Webhook API",
        description="A FastAPI application for managing a Telegram bot using webhooks",
        version="1.0.0",
    )

    # Include routers
    app.include_router(webhook_router)
    app.include_router(auth_router)

    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint for health check"""
        return {"message": "Telegram Bot Webhook API is running"}

    logger.info("FastAPI application initialized")
    return app


# Create app instance
app = create_app()
