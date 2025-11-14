"""Google OAuth service for handling authentication flow"""

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Scopes required for Google Sheets and user info (needed for Clerk integration)
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def get_oauth_flow(redirect_uri: str) -> Flow:
    """
    Create OAuth flow instance.

    Args:
        redirect_uri: OAuth redirect URI

    Returns:
        Flow: OAuth flow instance
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError("Google OAuth credentials not configured")

    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = redirect_uri

    return flow


def get_authorization_url(user_id: int, redirect_uri: str) -> str:
    """
    Generate Google OAuth authorization URL.

    Args:
        user_id: Internal user ID (used as state)
        redirect_uri: OAuth redirect URI

    Returns:
        str: Authorization URL
    """
    flow = get_oauth_flow(redirect_uri)
    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        state=str(user_id),
        prompt="consent",
    )

    logger.info(f"Generated authorization URL for user_id={user_id}")
    return authorization_url


def exchange_code_for_tokens(code: str, redirect_uri: str) -> tuple[str, str]:
    """
    Exchange authorization code for access and refresh tokens.

    Args:
        code: Authorization code from callback
        redirect_uri: OAuth redirect URI

    Returns:
        tuple[str, str]: (access_token, refresh_token)
    """
    flow = get_oauth_flow(redirect_uri)
    flow.fetch_token(code=code)

    credentials = flow.credentials

    if not credentials.token:
        raise ValueError("Failed to obtain access token")

    if not credentials.refresh_token:
        raise ValueError("Failed to obtain refresh token")

    logger.info("Successfully exchanged code for tokens")
    return credentials.token, credentials.refresh_token


def refresh_access_token(refresh_token: str) -> str:
    """
    Refresh access token using refresh token.

    Args:
        refresh_token: OAuth refresh token

    Returns:
        str: New access token
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError("Google OAuth credentials not configured")

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    credentials.refresh(Request())

    if not credentials.token:
        raise ValueError("Failed to refresh access token")

    logger.info("Successfully refreshed access token")
    return credentials.token


def get_credentials_from_tokens(access_token: str, refresh_token: str) -> Credentials:
    """
    Create Credentials object from stored tokens.

    Args:
        access_token: OAuth access token
        refresh_token: OAuth refresh token

    Returns:
        Credentials: Google credentials object
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError("Google OAuth credentials not configured")

    credentials = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
    )

    return credentials
