"""Timezone utility functions for converting UTC to user timezones"""

from datetime import datetime
from zoneinfo import ZoneInfo

from app.utils.logging import get_logger

logger = get_logger(__name__)

# Default timezone if user timezone is not set or invalid
DEFAULT_TIMEZONE = "UTC"


def convert_utc_to_user_timezone(
    utc_datetime: datetime, timezone_str: str | None
) -> datetime:
    """
    Convert UTC datetime to user's timezone.

    Args:
        utc_datetime: UTC datetime object (must be timezone-aware)
        timezone_str: User's timezone string (e.g., 'America/New_York', 'Europe/Madrid')
                     If None or invalid, defaults to UTC

    Returns:
        datetime: Datetime in user's timezone (timezone-aware)
    """
    # Default to UTC if timezone is not provided
    if not timezone_str:
        timezone_str = DEFAULT_TIMEZONE

    # Ensure UTC datetime is timezone-aware
    if utc_datetime.tzinfo is None:
        utc_datetime = utc_datetime.replace(tzinfo=ZoneInfo("UTC"))
    elif utc_datetime.tzinfo != ZoneInfo("UTC"):
        # Convert to UTC first if it's in a different timezone
        utc_datetime = utc_datetime.astimezone(ZoneInfo("UTC"))

    try:
        # Validate and convert timezone
        user_tz = ZoneInfo(timezone_str)
        return utc_datetime.astimezone(user_tz)
    except Exception as e:
        # Fallback to UTC if timezone is invalid
        logger.warning(
            f"Invalid timezone '{timezone_str}', falling back to UTC | error={str(e)}"
        )
        return utc_datetime.astimezone(ZoneInfo(DEFAULT_TIMEZONE))


def format_datetime_in_timezone(
    dt: datetime, timezone_str: str | None, format_str: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Format datetime in user's timezone.

    Args:
        dt: Datetime object (assumed to be UTC if timezone-aware, or naive)
        timezone_str: User's timezone string (e.g., 'America/New_York', 'Europe/Madrid')
                     If None or invalid, defaults to UTC
        format_str: Format string for datetime (default: '%Y-%m-%d %H:%M:%S')

    Returns:
        str: Formatted datetime string in user's timezone
    """
    # Default to UTC if timezone is not provided
    if not timezone_str:
        timezone_str = DEFAULT_TIMEZONE

    # Ensure datetime is timezone-aware (assume UTC if naive)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    elif dt.tzinfo != ZoneInfo("UTC"):
        # Convert to UTC first if it's in a different timezone
        dt = dt.astimezone(ZoneInfo("UTC"))

    try:
        # Convert to user timezone and format
        user_tz = ZoneInfo(timezone_str)
        dt_in_tz = dt.astimezone(user_tz)
        return dt_in_tz.strftime(format_str)
    except Exception as e:
        # Fallback to UTC if timezone is invalid
        logger.warning(
            f"Invalid timezone '{timezone_str}', falling back to UTC | error={str(e)}"
        )
        dt_in_tz = dt.astimezone(ZoneInfo(DEFAULT_TIMEZONE))
        return dt_in_tz.strftime(format_str)


def validate_timezone(timezone_str: str) -> bool:
    """
    Validate if a timezone string is valid.

    Args:
        timezone_str: Timezone string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not timezone_str:
        return False

    try:
        ZoneInfo(timezone_str)
        return True
    except Exception:
        return False
