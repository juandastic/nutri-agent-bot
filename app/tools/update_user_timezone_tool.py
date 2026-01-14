"""LangChain tool for updating user timezone"""

from langchain_core.tools import tool

from app.db.utils import update_user_timezone
from app.utils.logging import get_logger
from app.utils.timezone import validate_timezone

logger = get_logger(__name__)


def create_update_user_timezone_tool(user_id: int):
    """
    Create an update_user_timezone tool bound to a specific user_id.

    Args:
        user_id: Internal user ID (from database)

    Returns:
        Tool: LangChain tool instance
    """

    @tool
    async def update_user_timezone_tool(timezone: str) -> str:
        """
        Update the user's timezone setting. This affects how dates and times are displayed
        in spreadsheets, queries, and agent responses.

        Args:
            timezone: IANA timezone identifier (e.g., 'America/New_York', 'Europe/Madrid', 'Asia/Tokyo', 'UTC').
                     Common examples:
                     - 'America/New_York' (Eastern Time)
                     - 'America/Chicago' (Central Time)
                     - 'America/Denver' (Mountain Time)
                     - 'America/Los_Angeles' (Pacific Time)
                     - 'Europe/London' (UK)
                     - 'Europe/Madrid' (Spain)
                     - 'Europe/Paris' (France)
                     - 'Asia/Tokyo' (Japan)
                     - 'UTC' (Coordinated Universal Time)

        Returns:
            str: Success or error message
        """
        try:
            # Validate timezone before updating
            if not validate_timezone(timezone):
                return (
                    f"Invalid timezone: '{timezone}'. "
                    f"Please provide a valid IANA timezone identifier (e.g., 'America/New_York', 'Europe/Madrid', 'UTC'). "
                    f"You can find a list of valid timezones at: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
                )

            logger.info(f"Updating user timezone | user_id={user_id} | timezone={timezone}")

            # Update user timezone
            await update_user_timezone(user_id, timezone)

            return (
                f"Successfully updated your timezone to '{timezone}'. "
                f"Dates and times will now be displayed in this timezone in your spreadsheets and queries."
            )

        except ValueError as e:
            # Invalid timezone
            logger.warning(
                f"Invalid timezone provided | user_id={user_id} | timezone={timezone} | error={str(e)}"
            )
            return f"Invalid timezone: '{timezone}'. {str(e)}"

        except Exception as e:
            logger.error(
                f"Error updating user timezone | user_id={user_id} | timezone={timezone} | error={str(e)}",
                exc_info=True,
            )
            return f"I encountered an error while trying to update your timezone: {str(e)}"

    return update_user_timezone_tool
