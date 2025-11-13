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


class CommandsSetupResponse(BaseModel):
    """Response model for bot commands setup"""

    success: bool
    message: str
    telegram_response: dict[str, Any] | None = None


class ExternalAgentResponse(BaseModel):
    """Response model for external agent interactions"""

    success: bool
    response_text: str
    user_id: int
    chat_id: int
    external_chat_id: str
    bot_message_id: int
    timestamp: str
