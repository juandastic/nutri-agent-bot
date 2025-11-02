"""Pydantic models/schemas for API requests and responses"""

from typing import Any

from pydantic import BaseModel


class WebhookSetupResponse(BaseModel):
    """Response model for webhook setup"""

    success: bool
    message: str
    telegram_response: dict[str, Any]
    webhook_url: str | None = None


class WebhookDeleteResponse(BaseModel):
    """Response model for webhook deletion"""

    success: bool
    message: str
    telegram_response: dict[str, Any]


class TelegramUpdate(BaseModel):
    """Model for Telegram update payload"""

    update_id: int
    message: dict[str, Any] | None = None
    edited_message: dict[str, Any] | None = None
    channel_post: dict[str, Any] | None = None
    # Add other update types as needed
