"""Webhook router endpoints"""

from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import WebhookDeleteResponse, WebhookSetupResponse
from app.services.message_handler import MessageHandler
from app.services.telegram_service import TelegramService

router = APIRouter(tags=["webhook"])
telegram_service = TelegramService()
message_handler = MessageHandler()


def _get_webhook_url_from_request(request: Request) -> str:
    """
    Dynamically construct webhook URL from request headers.

    Args:
        request: FastAPI Request object

    Returns:
        str: Webhook URL
    """
    scheme = request.url.scheme
    host = request.headers.get("host") or request.headers.get("x-forwarded-host")

    if not host:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot determine webhook URL from request headers. "
                "Make sure you're calling this endpoint via the public URL (e.g., ngrok URL)."
            ),
        )

    # Construct webhook URL
    base_url = f"{scheme}://{host}"
    webhook_url = urljoin(base_url, "/webhook")

    return webhook_url


@router.post("/setup-webhook", response_model=WebhookSetupResponse)
async def setup_webhook(request: Request):
    """
    Setup webhook for Telegram bot.

    The webhook URL is automatically detected from the request headers.
    Call this endpoint using your public URL (e.g., ngrok URL) and it will
    automatically set the webhook to {scheme}://{host}/webhook

    Example:
        curl -X POST https://your-ngrok-url.ngrok.io/setup-webhook
        # Sets webhook to: https://your-ngrok-url.ngrok.io/webhook
    """
    is_valid, error_msg = settings.validate()
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        # Auto-detect webhook URL from request
        webhook_url = _get_webhook_url_from_request(request)

        result = await telegram_service.set_webhook(webhook_url)

        if result.get("ok"):
            return WebhookSetupResponse(
                success=True,
                message="Webhook set successfully",
                telegram_response=result,
                webhook_url=webhook_url,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Telegram API error: {result.get('description', 'Unknown error')}",
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/delete-webhook", response_model=WebhookDeleteResponse)
async def delete_webhook():
    """
    Delete webhook for Telegram bot.
    Reads TELEGRAM_BOT_TOKEN from environment variable.
    """
    is_valid, error_msg = settings.validate()
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        result = await telegram_service.delete_webhook()

        if result.get("ok"):
            return WebhookDeleteResponse(
                success=True, message="Webhook deleted successfully", telegram_response=result
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Telegram API error: {result.get('description', 'Unknown error')}",
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/webhook")
async def webhook_handler(request: Request):
    """
    Receive Telegram updates via webhook.
    Processes incoming messages and responds with "Hello World".
    """
    is_valid, error_msg = settings.validate()
    if not is_valid:
        raise HTTPException(status_code=500, detail=error_msg)

    try:
        update = await request.json()

        # Process the message
        await message_handler.process_message(update)

        # Always return 200 OK to acknowledge receipt
        return JSONResponse(content={"ok": True}, status_code=200)

    except Exception as e:
        # Still return 200 OK even if there's an error processing
        # Telegram will retry if we don't acknowledge
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=200)
