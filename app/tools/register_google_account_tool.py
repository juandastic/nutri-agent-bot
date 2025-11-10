"""LangChain tool for registering Google account for Google Sheets integration"""

from langchain_core.tools import tool

from app.db.utils import get_spreadsheet_config
from app.services.google_oauth_service import get_authorization_url
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_register_google_account_tool(user_id: int, redirect_uri: str | None = None):
    """
    Create a register_google_account tool bound to a specific user_id.

    Args:
        user_id: Internal user ID (from database)
        redirect_uri: OAuth redirect URI (optional, for dynamic URL generation)

    Returns:
        Tool: LangChain tool instance
    """

    @tool
    async def register_google_account() -> str:
        """
        Register or check Google account connection for Google Sheets integration.
        If not already registered, provides authorization link.
        If already registered, confirms the connection.

        Returns:
            str: Status message or authorization URL
        """
        try:
            # Check if user already has spreadsheet configuration
            config = await get_spreadsheet_config(user_id)

            if config:
                # User already registered
                logger.info(f"User already has Google account registered | user_id={user_id}")
                return (
                    "Your Google account is already connected! "
                    "Your nutritional data will be automatically saved to your Google Sheet when you register meals."
                )

            # User not registered, generate authorization URL
            logger.info(f"User not registered, generating authorization URL | user_id={user_id}")

            if not redirect_uri:
                return (
                    "I need to connect your Google account to enable Google Sheets integration. "
                    "However, the server configuration is incomplete. Please contact support."
                )

            authorization_url = get_authorization_url(user_id, redirect_uri)

            return (
                "To enable Google Sheets integration, I need permission to access your Google Sheets. "
                "Please authorize the connection by clicking this link:\n\n"
                f"{authorization_url}\n\n"
                "After authorizing, your nutritional data will be automatically saved to your Google Sheet."
            )

        except Exception as e:
            logger.error(
                f"Error in register_google_account | user_id={user_id} | error={str(e)}",
                exc_info=True,
            )
            return f"I encountered an error while trying to register your Google account: {str(e)}"

    return register_google_account
