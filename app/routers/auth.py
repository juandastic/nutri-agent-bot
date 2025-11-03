"""OAuth authentication router endpoints"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.db.utils import get_or_create_user, save_spreadsheet_config
from app.services.google_oauth_service import exchange_code_for_tokens, get_authorization_url
from app.utils.logging import get_logger

router = APIRouter(tags=["auth"])
logger = get_logger(__name__)


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


@router.get("/auth/google/authorize")
async def authorize(request: Request, telegram_user_id: int):
    """
    Generate Google OAuth authorization URL.

    Args:
        request: FastAPI Request object
        telegram_user_id: Telegram user ID

    Returns:
        JSONResponse with authorization_url
    """
    try:
        # Get or create user to obtain internal user_id
        user = await get_or_create_user(
            telegram_user_id=telegram_user_id,
            username=None,
            first_name=None,
        )
        user_id = user["id"]

        # Get redirect URI dynamically from request
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

        authorization_url = get_authorization_url(user_id, redirect_uri)

        logger.info(
            f"Generated authorization URL | user_id={user_id} | telegram_user_id={telegram_user_id}"
        )

        return JSONResponse(
            content={
                "success": True,
                "authorization_url": authorization_url,
                "message": "Please authorize the application to access your Google Sheets",
            }
        )

    except Exception as e:
        logger.error(
            f"Error generating authorization URL | telegram_user_id={telegram_user_id} | error={str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to generate authorization URL: {str(e)}"
        )


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
        RedirectResponse or JSONResponse
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

        # Return success response
        return JSONResponse(
            content={
                "success": True,
                "message": (
                    "Authorization successful! You can now register nutritional information. "
                    "Return to Telegram and try registering your meal again."
                ),
            }
        )

    except Exception as e:
        logger.error(
            f"Error in OAuth callback | code={code} | state={state} | error={str(e)}",
            exc_info=True,
        )
        return JSONResponse(
            content={"success": False, "error": f"Authorization failed: {str(e)}"},
            status_code=500,
        )
