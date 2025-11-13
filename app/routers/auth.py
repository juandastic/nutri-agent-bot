"""OAuth authentication router endpoints"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.db.utils import get_user_latest_chat, save_spreadsheet_config
from app.services.google_oauth_service import exchange_code_for_tokens
from app.services.telegram_service import TelegramService
from app.utils.logging import get_logger

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)

# Path to templates directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _get_redirect_uri_from_request(request: Request) -> str:
    """
    Dynamically construct redirect URI from request headers.

    Args:
        request: FastAPI Request object

    Returns:
        str: Redirect URI
    """
    scheme = request.url.scheme
    host = request.headers.get("host") or request.headers.get("x-forwarded-host")

    if not host:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot determine redirect URI from request headers. "
                "Make sure you're calling this endpoint via the public URL."
            ),
        )

    base_url = f"{scheme}://{host}"
    redirect_uri = f"{base_url}/auth/google/callback"

    return redirect_uri


@router.get("/auth/google/callback")
async def callback(
    request: Request, code: str | None = None, state: str | None = None, error: str | None = None
):
    """
    Handle Google OAuth callback.

    Args:
        request: FastAPI Request object
        code: Authorization code from Google
        state: State parameter (should contain user_id)
        error: Error message from Google (if authorization failed)

    Returns:
        HTMLResponse or JSONResponse
    """
    try:
        logger.info(f"OAuth callback | code={code} | state={state} | error={error}")
        if error:
            logger.error(f"OAuth authorization error | error={error}")
            return JSONResponse(
                content={"success": False, "error": f"Authorization failed: {error}"},
                status_code=400,
            )

        if not code or not state:
            logger.error("Missing code or state in callback")
            return JSONResponse(
                content={"success": False, "error": "Missing authorization code or state"},
                status_code=400,
            )

        # Extract user_id from state
        try:
            user_id = int(state)
        except ValueError:
            logger.error(f"Invalid state parameter | state={state}")
            return JSONResponse(
                content={"success": False, "error": "Invalid state parameter"},
                status_code=400,
            )

        # Exchange code for tokens
        redirect_uri = _get_redirect_uri_from_request(request)
        access_token, refresh_token = exchange_code_for_tokens(code, redirect_uri)

        # Save tokens to database
        await save_spreadsheet_config(
            user_id=user_id,
            spreadsheet_id=None,
            oauth_token=access_token,
            refresh_token=refresh_token,
        )

        logger.info(f"OAuth callback successful | user_id={user_id}")

        # Try to send confirmation message to user in Telegram
        # This is optional - if it fails, we still show the success page since OAuth succeeded
        try:
            chat = await get_user_latest_chat(user_id)
            chat_id_for_notification = None
            if chat:
                external_chat_id = chat.get("external_chat_id")
                if external_chat_id:
                    try:
                        chat_id_for_notification = int(external_chat_id)
                    except ValueError:
                        logger.debug(
                            "Latest chat external ID is not numeric, skipping Telegram notification",
                        )

            if chat_id_for_notification:
                success_message = (
                    "✅ Configuration completed successfully!\n\n"
                    "You can now request to register nutritional information. "
                    "Send a message with the details of your meal and I'll register it in your spreadsheet."
                )
                await TelegramService.send_message(
                    chat_id=chat_id_for_notification, text=success_message
                )
                logger.info(
                    f"Sent confirmation message to user | user_id={user_id} | chat_id={chat_id_for_notification}"
                )
        except Exception as notification_error:
            # Log error but don't fail the OAuth flow - configuration was successful
            logger.error(
                f"Failed to send Telegram notification | user_id={user_id} | error={str(notification_error)}",
                exc_info=True,
            )

        # Load HTML template
        template_path = TEMPLATES_DIR / "auth_success.html"
        try:
            html_content = template_path.read_text(encoding="utf-8")
        except Exception as template_error:
            logger.error(
                f"Failed to load HTML template | path={template_path} | error={str(template_error)}",
                exc_info=True,
            )
            # Fallback to simple HTML if template loading fails
            html_content = """
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Configuration Completed</title>
            </head>
            <body>
                <h1>Configuration Completed!</h1>
                <p>Your Google Sheets account has been successfully configured. You can now close this page.</p>
            </body>
            </html>
            """
        return HTMLResponse(content=html_content)

    except Exception as e:
        logger.error(
            f"Error in OAuth callback | code={code} | state={state} | error={str(e)}",
            exc_info=True,
        )
        return JSONResponse(
            content={"success": False, "error": f"Authorization failed: {str(e)}"},
            status_code=500,
        )
