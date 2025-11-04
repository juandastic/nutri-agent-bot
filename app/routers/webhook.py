"""Webhook router endpoints"""

from urllib.parse import urljoin

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.schemas import (
    CommandsSetupResponse,
    WebhookDeleteResponse,
    WebhookSetupResponse,
)
from app.services.message_handler import MessageHandler
from app.services.telegram_service import TelegramService
from app.utils.logging import get_logger

router = APIRouter(tags=["webhook"])
telegram_service = TelegramService()
message_handler = MessageHandler()

logger = get_logger(__name__)


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

    base_url = f"{scheme}://{host}"
    webhook_url = urljoin(base_url, "/webhook")

    return webhook_url


def _get_redirect_uri_from_request(request: Request) -> str:
    """
    Dynamically construct OAuth redirect URI from request headers.

    Args:
        request: FastAPI Request object

    Returns:
        str: OAuth redirect URI
    """
    scheme = request.url.scheme
    host = request.headers.get("host") or request.headers.get("x-forwarded-host")

    if not host:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot determine redirect URI from request headers. "
                "Make sure you're calling this endpoint via the public URL (e.g., ngrok URL)."
            ),
        )

    base_url = f"{scheme}://{host}"
    redirect_uri = f"{base_url}/auth/google/callback"

    return redirect_uri


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
    logger.info("Webhook setup requested")
    is_valid, error_msg = settings.validate()
    if not is_valid:
        logger.error(f"Webhook setup failed | validation_error={error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        webhook_url = _get_webhook_url_from_request(request)
        secret_token = settings.TELEGRAM_WEBHOOK_SECRET
        logger.info(f"Setting webhook | url={webhook_url} | has_secret_token={bool(secret_token)}")

        result = await telegram_service.set_webhook(webhook_url, secret_token=secret_token)

        if result.get("ok"):
            logger.info(f"Webhook set successfully | url={webhook_url}")

            # Register bot commands
            try:
                commands = [
                    {
                        "command": "reset_account",
                        "description": "Reset your account data (messages, chats, configuration)",
                    },
                ]
                commands_result = await telegram_service.set_my_commands(commands)
                if commands_result.get("ok"):
                    logger.info("Bot commands registered successfully")
                else:
                    logger.warning(
                        f"Failed to register bot commands | description={commands_result.get('description', 'Unknown error')}"
                    )
            except Exception as cmd_error:
                # Don't fail webhook setup if command registration fails
                logger.warning(
                    f"Error registering bot commands | error={str(cmd_error)}",
                    exc_info=True,
                )

            return WebhookSetupResponse(
                success=True,
                message="Webhook set successfully",
                telegram_response=result,
                webhook_url=webhook_url,
            )
        else:
            error_desc = result.get("description", "Unknown error")
            logger.error(f"Telegram API error | description={error_desc}")
            raise HTTPException(status_code=400, detail=f"Telegram API error: {error_desc}")
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error setting webhook | status={e.response.status_code} | error={str(e)}"
        )
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error setting webhook | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/delete-webhook", response_model=WebhookDeleteResponse)
async def delete_webhook():
    """
    Delete webhook for Telegram bot.
    Reads TELEGRAM_BOT_TOKEN from environment variable.
    """
    logger.info("Webhook deletion requested")
    is_valid, error_msg = settings.validate()
    if not is_valid:
        logger.error(f"Webhook deletion failed | validation_error={error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        result = await telegram_service.delete_webhook()

        if result.get("ok"):
            logger.info("Webhook deleted successfully")
            return WebhookDeleteResponse(
                success=True, message="Webhook deleted successfully", telegram_response=result
            )
        else:
            error_desc = result.get("description", "Unknown error")
            logger.error(f"Telegram API error | description={error_desc}")
            raise HTTPException(status_code=400, detail=f"Telegram API error: {error_desc}")
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error deleting webhook | status={e.response.status_code} | error={str(e)}"
        )
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error deleting webhook | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/setup-commands", response_model=CommandsSetupResponse)
async def setup_commands():
    """
    Register bot commands to be displayed in the command menu.

    This endpoint registers the available bot commands with Telegram.
    Users will see these commands when they type "/" in the chat.
    """
    logger.info("Bot commands setup requested")
    is_valid, error_msg = settings.validate()
    if not is_valid:
        logger.error(f"Commands setup failed | validation_error={error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        commands = [
            {
                "command": "reset_account",
                "description": "Reset your account data (messages, chats, configuration)",
            },
        ]
        result = await telegram_service.set_my_commands(commands)

        if result.get("ok"):
            logger.info("Bot commands registered successfully")
            return CommandsSetupResponse(
                success=True,
                message="Bot commands registered successfully",
                telegram_response=result,
            )
        else:
            error_desc = result.get("description", "Unknown error")
            logger.error(f"Telegram API error | description={error_desc}")
            raise HTTPException(status_code=400, detail=f"Telegram API error: {error_desc}")
    except httpx.HTTPStatusError as e:
        logger.error(
            f"HTTP error setting commands | status={e.response.status_code} | error={str(e)}"
        )
        raise HTTPException(status_code=e.response.status_code, detail=f"HTTP error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error setting commands | error={str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/webhook")
async def webhook_handler(request: Request):
    """
    Receive Telegram updates via webhook.
    Processes incoming messages and responds with "Hello World".
    """
    # Validate webhook secret token if configured
    if settings.TELEGRAM_WEBHOOK_SECRET:
        secret_token_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret_token_header != settings.TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Webhook request rejected | invalid_secret_token")
            return JSONResponse(
                content={"ok": False, "error": "Forbidden"},
                status_code=403,
            )

    is_valid, error_msg = settings.validate()
    if not is_valid:
        logger.error(f"Webhook handler configuration error | error={error_msg}")
        return JSONResponse(
            content={"ok": False, "error": "Server configuration error"},
            status_code=200,
        )

    update_id = None
    try:
        update = await request.json()
        update_id = update.get("update_id")

        logger.info(f"Webhook received | update_id={update_id}")

        # Get redirect URI dynamically from request
        try:
            redirect_uri = _get_redirect_uri_from_request(request)
        except HTTPException:
            logger.error("Cannot determine redirect URI from request headers")
            return JSONResponse(
                content={
                    "ok": False,
                    "error": "Server configuration error: Cannot determine redirect URI",
                },
                status_code=200,
            )

        await message_handler.process_message(update, redirect_uri=redirect_uri)

        logger.info(f"Webhook processed successfully | update_id={update_id}")
        return JSONResponse(content={"ok": True}, status_code=200)

    except Exception as e:
        logger.error(
            f"Error processing webhook | update_id={update_id} | error={str(e)}",
            exc_info=True,
        )
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=200)
