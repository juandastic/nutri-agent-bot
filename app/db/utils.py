"""Database utility functions using Supabase SDK"""

import random
from datetime import datetime, timedelta, timezone
from typing import TypedDict

from app.db.supabase_client import supabase
from app.utils.logging import get_logger

logger = get_logger(__name__)


class UserDict(TypedDict):
    """User data structure"""

    id: int
    external_user_id: str | None
    telegram_user_id: str | None
    clerk_user_id: str | None
    email: str | None
    email_verified_at: str | None
    username: str | None
    first_name: str | None
    created_at: str


class ChatDict(TypedDict):
    """Chat data structure"""

    id: int
    external_chat_id: str | None
    user_id: int | None
    chat_type: str | None
    created_at: str
    last_active_at: str | None


class MessageDict(TypedDict):
    """Message data structure"""

    id: int
    chat_id: int
    telegram_message_id: int | None
    text: str | None
    role: str
    message_type: str
    from_user_id: int | None
    created_at: str
    updated_at: str | None


class SpreadsheetConfigDict(TypedDict):
    """Spreadsheet configuration data structure"""

    id: int
    user_id: int
    spreadsheet_id: str | None
    oauth_token: str
    refresh_token: str
    created_at: str
    updated_at: str


class NutritionalInfoDict(TypedDict):
    """Nutritional information data structure"""

    id: int
    user_id: int
    calories: float
    proteins: float
    carbs: float
    fats: float
    meal_type: str
    extra_details: str | None
    created_at: str


async def get_or_create_user(
    *,
    telegram_user_id: str | None = None,
    clerk_user_id: str | None = None,
    username: str | None = None,
    first_name: str | None = None,
    email: str | None = None,
) -> UserDict:
    """
    Get existing user or create a new one using Supabase SDK.

    Must provide either telegram_user_id (for Telegram users) or clerk_user_id (for web users).

    Args:
        telegram_user_id: Telegram user ID (for Telegram bot users)
        clerk_user_id: Clerk user ID (for web frontend users)
        username: User handle or username (optional)
        first_name: User first name (optional)
        email: Email address (optional, will be lowercased)

    Returns:
        UserDict: User data dictionary

    Raises:
        ValueError: If neither telegram_user_id nor clerk_user_id is provided
    """
    if not telegram_user_id and not clerk_user_id:
        raise ValueError("Must provide either telegram_user_id or clerk_user_id")

    try:
        # Determine which field to search by
        if telegram_user_id:
            # Telegram user: search by telegram_user_id or external_user_id (legacy)
            response = (
                supabase.table("users")
                .select("*")
                .or_(
                    f"telegram_user_id.eq.{telegram_user_id},external_user_id.eq.{telegram_user_id}"
                )
                .execute()
            )
            search_field = "telegram_user_id"
            search_value = telegram_user_id
        else:
            # Web user: search by clerk_user_id
            response = (
                supabase.table("users").select("*").eq("clerk_user_id", clerk_user_id).execute()
            )
            search_field = "clerk_user_id"
            search_value = clerk_user_id

        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            logger.debug(f"User found | user_id={user_data['id']} | {search_field}={search_value}")

            # Update missing fields if provided
            update_data = {}
            if username and not user_data.get("username"):
                update_data["username"] = username
            if first_name and not user_data.get("first_name"):
                update_data["first_name"] = first_name
            if email and not user_data.get("email"):
                update_data["email"] = email.lower()

            if update_data:
                logger.info(
                    f"Updating user with missing fields | user_id={user_data['id']} | "
                    f"fields={list(update_data.keys())}"
                )
                update_response = (
                    supabase.table("users").update(update_data).eq("id", user_data["id"]).execute()
                )
                if update_response.data:
                    user_data = update_response.data[0]

            return UserDict(**user_data)

        # User not found, create new one
        logger.info(f"Creating new user | {search_field}={search_value} | username={username}")

        insert_data = {
            "username": username,
            "first_name": first_name,
        }

        if telegram_user_id:
            insert_data["telegram_user_id"] = telegram_user_id
            insert_data["external_user_id"] = telegram_user_id  # Keep for legacy compatibility

        if clerk_user_id:
            insert_data["clerk_user_id"] = clerk_user_id
            # For web-only users, use clerk_user_id as external_user_id too
            if not telegram_user_id:
                insert_data["external_user_id"] = clerk_user_id

        if email:
            insert_data["email"] = email.lower()

        insert_response = supabase.table("users").insert(insert_data).execute()

        if not insert_response.data:
            raise ValueError("Failed to create user")

        user_data = insert_response.data[0]
        logger.info(f"User created | user_id={user_data['id']} | {search_field}={search_value}")
        return UserDict(**user_data)

    except Exception as e:
        logger.error(
            f"Error in get_or_create_user | telegram_user_id={telegram_user_id} | "
            f"clerk_user_id={clerk_user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def get_or_create_chat(
    external_chat_id: str,
    user_id: int | None,
    chat_type: str | None,
) -> ChatDict:
    """
    Get existing chat or create a new one using Supabase SDK.

    Args:
        external_chat_id: External chat ID (string identifier)
        user_id: User ID (None for group chats)
        chat_type: Chat type ('private', 'group', 'supergroup')

    Returns:
        ChatDict: Chat data dictionary
    """
    try:
        response = (
            supabase.table("chats").select("*").eq("external_chat_id", external_chat_id).execute()
        )

        if response.data and len(response.data) > 0:
            chat_data = response.data[0]
            update_response = (
                supabase.table("chats")
                .update({"last_active_at": datetime.now(timezone.utc).isoformat()})
                .eq("id", chat_data["id"])
                .execute()
            )
            chat_data = update_response.data[0]
            logger.debug(
                f"Chat updated | chat_id={chat_data['id']} | external_chat_id={external_chat_id}"
            )
            return ChatDict(**chat_data)

        logger.info(
            f"Creating new chat | external_chat_id={external_chat_id} | chat_type={chat_type}"
        )
        insert_data = {
            "external_chat_id": external_chat_id,
            "user_id": user_id,
            "chat_type": chat_type,
            "last_active_at": datetime.now(timezone.utc).isoformat(),
        }
        insert_response = supabase.table("chats").insert(insert_data).execute()

        if not insert_response.data:
            raise ValueError("Failed to create chat")

        chat_data = insert_response.data[0]
        logger.info(
            f"Chat created | chat_id={chat_data['id']} | external_chat_id={external_chat_id}"
        )
        return ChatDict(**chat_data)

    except Exception as e:
        logger.error(
            f"Error in get_or_create_chat | external_chat_id={external_chat_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def create_message(
    chat_id: int,
    text: str | None,
    role: str = "user",
    message_type: str = "text",
    telegram_message_id: int | None = None,
    from_user_id: int | None = None,
) -> MessageDict:
    """
    Create a new message record using Supabase SDK.

    Args:
        chat_id: Chat ID
        text: Message text content
        role: Message role ('user' or 'bot')
        message_type: Message type ('text', 'photo', 'document')
        telegram_message_id: Telegram message ID (optional, None for bot messages)
        from_user_id: User ID who sent the message (None for bot messages)

    Returns:
        MessageDict: Message data dictionary
    """
    try:
        logger.debug(
            f"Creating message | chat_id={chat_id} | role={role} | message_type={message_type} | "
            f"telegram_message_id={telegram_message_id} | from_user_id={from_user_id}"
        )
        insert_data = {
            "chat_id": chat_id,
            "text": text,
            "role": role,
            "message_type": message_type,
            "telegram_message_id": telegram_message_id,
            "from_user_id": from_user_id,
        }
        insert_response = supabase.table("messages").insert(insert_data).execute()

        if not insert_response.data:
            raise ValueError("Failed to create message")

        message_data = insert_response.data[0]
        logger.debug(
            f"Message created | message_id={message_data['id']} | role={role} | message_type={message_type}"
        )
        return MessageDict(**message_data)

    except Exception as e:
        logger.error(
            f"Error in create_message | chat_id={chat_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def get_recent_messages(
    chat_id: int,
    limit: int = 10,
) -> list[MessageDict]:
    """
    Get recent messages from a chat for conversation context.

    Args:
        chat_id: Chat ID
        limit: Maximum number of messages to retrieve (default: 10)

    Returns:
        List of MessageDict ordered by created_at (oldest first)
        Returns the most recent N messages in chronological order.
    """
    try:
        # Get the most recent messages (ordered by created_at desc)
        response = (
            supabase.table("messages")
            .select("*")
            .eq("chat_id", chat_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        messages = []
        if response.data:
            for msg_data in response.data:
                messages.append(MessageDict(**msg_data))

        # Reverse to get chronological order (oldest first) for conversation context
        messages.reverse()

        logger.debug(f"Retrieved {len(messages)} most recent messages for chat_id={chat_id}")
        return messages

    except Exception as e:
        logger.error(
            f"Error in get_recent_messages | chat_id={chat_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def get_user_latest_chat(user_id: int) -> ChatDict | None:
    """
    Get the most recent chat for a user.

    Args:
        user_id: User ID

    Returns:
        ChatDict if found, None otherwise
    """
    try:
        response = (
            supabase.table("chats")
            .select("*")
            .eq("user_id", user_id)
            .order("last_active_at", desc=True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data and len(response.data) > 0:
            chat_data = response.data[0]
            logger.debug(f"Latest chat found | user_id={user_id} | chat_id={chat_data['id']}")
            return ChatDict(**chat_data)

        logger.debug(f"No chat found for user | user_id={user_id}")
        return None

    except Exception as e:
        logger.error(
            f"Error in get_user_latest_chat | user_id={user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def get_spreadsheet_config(user_id: int) -> SpreadsheetConfigDict | None:
    """
    Get spreadsheet configuration for a user.

    Args:
        user_id: User ID

    Returns:
        SpreadsheetConfigDict if found, None otherwise
    """
    try:
        response = (
            supabase.table("spreadsheet_configs").select("*").eq("user_id", user_id).execute()
        )

        if response.data and len(response.data) > 0:
            config_data = response.data[0]
            logger.debug(f"Spreadsheet config found | user_id={user_id}")
            return SpreadsheetConfigDict(**config_data)

        logger.debug(f"No spreadsheet config found | user_id={user_id}")
        return None

    except Exception as e:
        logger.error(
            f"Error in get_spreadsheet_config | user_id={user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def save_spreadsheet_config(
    user_id: int,
    spreadsheet_id: str | None,
    oauth_token: str,
    refresh_token: str,
) -> SpreadsheetConfigDict:
    """
    Save or update spreadsheet configuration for a user.

    Args:
        user_id: User ID
        spreadsheet_id: Google Spreadsheet ID (optional)
        oauth_token: OAuth access token
        refresh_token: OAuth refresh token

    Returns:
        SpreadsheetConfigDict: Saved configuration data
    """
    try:
        # Check if config exists
        existing_config = await get_spreadsheet_config(user_id)

        if existing_config:
            logger.info(f"Updating spreadsheet config | user_id={user_id}")
            update_data = {
                "spreadsheet_id": spreadsheet_id,
                "oauth_token": oauth_token,
                "refresh_token": refresh_token,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            update_response = (
                supabase.table("spreadsheet_configs")
                .update(update_data)
                .eq("user_id", user_id)
                .execute()
            )

            if not update_response.data:
                raise ValueError("Failed to update spreadsheet config")

            config_data = update_response.data[0]
            logger.info(f"Spreadsheet config updated | user_id={user_id}")
            return SpreadsheetConfigDict(**config_data)
        else:
            logger.info(f"Creating spreadsheet config | user_id={user_id}")
            insert_data = {
                "user_id": user_id,
                "spreadsheet_id": spreadsheet_id,
                "oauth_token": oauth_token,
                "refresh_token": refresh_token,
            }
            insert_response = supabase.table("spreadsheet_configs").insert(insert_data).execute()

            if not insert_response.data:
                raise ValueError("Failed to create spreadsheet config")

            config_data = insert_response.data[0]
            logger.info(f"Spreadsheet config created | user_id={user_id}")
            return SpreadsheetConfigDict(**config_data)

    except Exception as e:
        logger.error(
            f"Error in save_spreadsheet_config | user_id={user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def reset_user_account(user_id: int) -> dict[str, int]:
    """
    Reset user account by deleting all associated data.
    Deletes messages, chats, spreadsheet configuration, and nutritional info for the user.
    The user record itself is NOT deleted.

    Args:
        user_id: User ID

    Returns:
        dict: Summary of deleted items with counts
    """
    try:
        logger.info(f"Resetting user account | user_id={user_id}")

        # Get all chats for this user first
        chats_response = supabase.table("chats").select("id").eq("user_id", user_id).execute()
        chat_ids = [chat["id"] for chat in (chats_response.data or [])]

        # 1. Delete all messages from user's chats OR where user is the sender
        # Use a single query to delete all related messages efficiently
        messages_deleted = 0
        if chat_ids:
            # Delete messages from user's chats
            for chat_id in chat_ids:
                messages_response = (
                    supabase.table("messages").delete().eq("chat_id", chat_id).execute()
                )
                # Supabase returns the deleted rows
                if messages_response.data:
                    messages_deleted += len(messages_response.data)

        # Also delete any remaining messages where user is the sender
        # (in case there are messages in chats not owned by the user)
        user_messages_response = (
            supabase.table("messages").delete().eq("from_user_id", user_id).execute()
        )
        if user_messages_response.data:
            messages_deleted += len(user_messages_response.data)

        # 2. Delete all chats for this user
        chats_deleted = 0
        if chat_ids:
            chats_delete_response = (
                supabase.table("chats").delete().eq("user_id", user_id).execute()
            )
            if chats_delete_response.data:
                chats_deleted = len(chats_delete_response.data)

        # 3. Delete spreadsheet configuration
        config_deleted = 0
        config_delete_response = (
            supabase.table("spreadsheet_configs").delete().eq("user_id", user_id).execute()
        )
        if config_delete_response.data:
            config_deleted = len(config_delete_response.data)

        # 4. Delete nutritional info records
        nutritional_info_deleted = 0
        nutritional_info_delete_response = (
            supabase.table("nutritional_info").delete().eq("user_id", user_id).execute()
        )
        if nutritional_info_delete_response.data:
            nutritional_info_deleted = len(nutritional_info_delete_response.data)

        result = {
            "messages_deleted": messages_deleted,
            "chats_deleted": chats_deleted,
            "config_deleted": config_deleted,
            "nutritional_info_deleted": nutritional_info_deleted,
        }

        logger.info(
            f"User account reset completed | user_id={user_id} | "
            f"messages={messages_deleted} | chats={chats_deleted} | "
            f"config={config_deleted} | nutritional_info={nutritional_info_deleted}"
        )

        return result

    except Exception as e:
        logger.error(
            f"Error resetting user account | user_id={user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def delete_user(user_id: int) -> bool:
    """
    Delete a user and all associated data from the database.
    This permanently removes the user record and all related data
    (messages, chats, spreadsheet config, nutritional info).

    Args:
        user_id: User ID to delete

    Returns:
        bool: True if user was deleted, False if user not found
    """
    try:
        logger.info(f"Deleting user | user_id={user_id}")

        # First reset all user data (messages, chats, config, nutritional_info)
        await reset_user_account(user_id)

        # Now delete the user record itself
        response = supabase.table("users").delete().eq("id", user_id).execute()

        if response.data:
            logger.info(f"User deleted successfully | user_id={user_id}")
            return True

        logger.warning(f"User not found for deletion | user_id={user_id}")
        return False

    except Exception as e:
        logger.error(
            f"Error deleting user | user_id={user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def save_nutritional_info(
    user_id: int,
    calories: float,
    proteins: float,
    carbs: float,
    fats: float,
    meal_type: str,
    extra_details: str | None = None,
) -> NutritionalInfoDict:
    """
    Save nutritional information to the database.

    Args:
        user_id: User ID
        calories: Calories value
        proteins: Proteins value (g)
        carbs: Carbohydrates value (g)
        fats: Fats value (g)
        meal_type: Meal type (e.g., Breakfast, Lunch, Dinner, Snack)
        extra_details: Extra details or description (optional)

    Returns:
        NutritionalInfoDict: Saved nutritional information data with generated ID
    """
    try:
        logger.info(
            f"Saving nutritional info | user_id={user_id} | calories={calories} | meal_type={meal_type}"
        )
        insert_data = {
            "user_id": user_id,
            "calories": calories,
            "proteins": proteins,
            "carbs": carbs,
            "fats": fats,
            "meal_type": meal_type,
            "extra_details": extra_details,
        }
        insert_response = supabase.table("nutritional_info").insert(insert_data).execute()

        if not insert_response.data:
            raise ValueError("Failed to create nutritional info record")

        nutritional_data = insert_response.data[0]
        logger.info(
            f"Nutritional info saved | id={nutritional_data['id']} | user_id={user_id} | calories={calories}"
        )
        return NutritionalInfoDict(**nutritional_data)

    except Exception as e:
        logger.error(
            f"Error in save_nutritional_info | user_id={user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def get_nutritional_info(
    user_id: int,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[NutritionalInfoDict]:
    """
    Get nutritional information for a user with optional date filters.

    Args:
        user_id: User ID
        start_date: Start date filter in ISO format (YYYY-MM-DD). If provided, returns records from this date onwards.
        end_date: End date filter in ISO format (YYYY-MM-DD). If provided, returns records up to this date.
                  If only end_date is provided, includes records up to end of that day.
                  If both dates are provided, returns records in the range [start_date, end_date].

    Returns:
        List of NutritionalInfoDict ordered by created_at (oldest first)
    """
    try:
        logger.info(
            f"Querying nutritional info | user_id={user_id} | start_date={start_date} | end_date={end_date}"
        )

        # Start with base query filtered by user_id
        query = supabase.table("nutritional_info").select("*").eq("user_id", user_id)

        # Apply date filters
        if start_date:
            # Include records from start of start_date
            query = query.gte("created_at", f"{start_date}T00:00:00")
        if end_date:
            # Include records up to end of end_date
            query = query.lte("created_at", f"{end_date}T23:59:59")

        # Order by created_at ascending (oldest first)
        query = query.order("created_at", desc=False)

        response = query.execute()

        records = []
        if response.data:
            for record_data in response.data:
                records.append(NutritionalInfoDict(**record_data))

        logger.info(
            f"Retrieved {len(records)} nutritional records | user_id={user_id} | "
            f"start_date={start_date} | end_date={end_date}"
        )
        return records

    except Exception as e:
        logger.error(
            f"Error in get_nutritional_info | user_id={user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def update_spreadsheet_config(user_id: int, **kwargs) -> SpreadsheetConfigDict:
    """
    Update specific fields in spreadsheet configuration.

    Args:
        user_id: User ID
        **kwargs: Fields to update (spreadsheet_id, oauth_token, refresh_token)

    Returns:
        SpreadsheetConfigDict: Updated configuration data
    """
    try:
        logger.info(
            f"Updating spreadsheet config fields | user_id={user_id} | fields={list(kwargs.keys())}"
        )
        update_data = {**kwargs, "updated_at": datetime.now(timezone.utc).isoformat()}
        update_response = (
            supabase.table("spreadsheet_configs")
            .update(update_data)
            .eq("user_id", user_id)
            .execute()
        )

        if not update_response.data:
            raise ValueError("Failed to update spreadsheet config")

        config_data = update_response.data[0]
        logger.info(f"Spreadsheet config updated | user_id={user_id}")
        return SpreadsheetConfigDict(**config_data)

    except Exception as e:
        logger.error(
            f"Error in update_spreadsheet_config | user_id={user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


# ============================================================================
# Account Linking Functions
# ============================================================================


async def get_user_by_email(email: str) -> UserDict | None:
    """
    Get user by verified email address.

    Args:
        email: Email address to search for

    Returns:
        UserDict if found, None otherwise
    """
    try:
        response = (
            supabase.table("users")
            .select("*")
            .eq("email", email.lower())
            .not_.is_("email_verified_at", "null")
            .execute()
        )

        if response.data and len(response.data) > 0:
            logger.debug(f"User found by email | email={email}")
            return UserDict(**response.data[0])

        logger.debug(f"No verified user found for email | email={email}")
        return None

    except Exception as e:
        logger.error(f"Error in get_user_by_email | email={email} | error={str(e)}", exc_info=True)
        raise


async def get_user_by_id(user_id: int) -> UserDict | None:
    """
    Get user by internal ID.

    Args:
        user_id: Internal user ID

    Returns:
        UserDict if found, None otherwise
    """
    try:
        response = supabase.table("users").select("*").eq("id", user_id).execute()

        if response.data and len(response.data) > 0:
            return UserDict(**response.data[0])

        return None

    except Exception as e:
        logger.error(f"Error in get_user_by_id | user_id={user_id} | error={str(e)}", exc_info=True)
        raise


async def update_user_email(user_id: int, email: str, verified: bool = False) -> UserDict:
    """
    Update user's email address.

    Args:
        user_id: User ID
        email: Email address (will be lowercased)
        verified: Whether to mark email as verified

    Returns:
        UserDict: Updated user data
    """
    try:
        update_data = {"email": email.lower()}
        if verified:
            update_data["email_verified_at"] = datetime.now(timezone.utc).isoformat()

        response = supabase.table("users").update(update_data).eq("id", user_id).execute()

        if not response.data:
            raise ValueError("Failed to update user email")

        logger.info(f"User email updated | user_id={user_id} | email={email} | verified={verified}")
        return UserDict(**response.data[0])

    except Exception as e:
        logger.error(
            f"Error in update_user_email | user_id={user_id} | error={str(e)}", exc_info=True
        )
        raise


async def update_user_telegram_id(user_id: int, telegram_user_id: str) -> UserDict:
    """
    Update user's Telegram ID.

    Args:
        user_id: User ID
        telegram_user_id: Telegram user ID

    Returns:
        UserDict: Updated user data
    """
    try:
        response = (
            supabase.table("users")
            .update({"telegram_user_id": telegram_user_id})
            .eq("id", user_id)
            .execute()
        )

        if not response.data:
            raise ValueError("Failed to update user telegram_id")

        logger.info(
            f"User telegram_id updated | user_id={user_id} | telegram_user_id={telegram_user_id}"
        )
        return UserDict(**response.data[0])

    except Exception as e:
        logger.error(
            f"Error in update_user_telegram_id | user_id={user_id} | error={str(e)}", exc_info=True
        )
        raise


async def merge_user_data(source_user_id: int, target_user_id: int) -> dict[str, int]:
    """
    Merge data from source user into target user.
    Transfers all user data: chats, messages, nutritional_info, and spreadsheet_configs.

    Args:
        source_user_id: User ID to merge FROM (will be cleaned up)
        target_user_id: User ID to merge INTO (will receive data)

    Returns:
        dict: Summary of transferred items
    """
    try:
        logger.info(f"Merging user data | source={source_user_id} | target={target_user_id}")

        transferred = {
            "chats": 0,
            "messages": 0,
            "nutritional_info": 0,
            "spreadsheet_config": 0,
        }

        # 1. Transfer chats (change owner to target user)
        chats_response = (
            supabase.table("chats")
            .update({"user_id": target_user_id})
            .eq("user_id", source_user_id)
            .execute()
        )
        if chats_response.data:
            transferred["chats"] = len(chats_response.data)

        # 2. Transfer messages where source user was the sender
        messages_response = (
            supabase.table("messages")
            .update({"from_user_id": target_user_id})
            .eq("from_user_id", source_user_id)
            .execute()
        )
        if messages_response.data:
            transferred["messages"] = len(messages_response.data)

        # 3. Transfer nutritional_info records
        nutritional_response = (
            supabase.table("nutritional_info")
            .update({"user_id": target_user_id})
            .eq("user_id", source_user_id)
            .execute()
        )
        if nutritional_response.data:
            transferred["nutritional_info"] = len(nutritional_response.data)

        # 4. Transfer spreadsheet_configs (if target doesn't have one)
        target_config = await get_spreadsheet_config(target_user_id)
        if not target_config:
            source_config = await get_spreadsheet_config(source_user_id)
            if source_config:
                supabase.table("spreadsheet_configs").update({"user_id": target_user_id}).eq(
                    "user_id", source_user_id
                ).execute()
                transferred["spreadsheet_config"] = 1

        logger.info(
            f"User data merged | source={source_user_id} | target={target_user_id} | "
            f"chats={transferred['chats']} | messages={transferred['messages']} | "
            f"nutritional_info={transferred['nutritional_info']} | "
            f"spreadsheet_config={transferred['spreadsheet_config']}"
        )

        return transferred

    except Exception as e:
        logger.error(
            f"Error in merge_user_data | source={source_user_id} | target={target_user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def get_user_link_status(user_id: int) -> dict:
    """
    Get the linking status for a user.

    Args:
        user_id: User ID

    Returns:
        dict with is_linked, email, telegram_user_id, linked_at
    """
    try:
        user = await get_user_by_id(user_id)
        if not user:
            return {"is_linked": False, "email": None, "telegram_user_id": None, "linked_at": None}

        is_linked = bool(user.get("email") and user.get("email_verified_at"))

        return {
            "is_linked": is_linked,
            "email": user.get("email"),
            "telegram_user_id": user.get("telegram_user_id"),
            "linked_at": user.get("email_verified_at"),
        }

    except Exception as e:
        logger.error(
            f"Error in get_user_link_status | user_id={user_id} | error={str(e)}", exc_info=True
        )
        raise


# ============================================================================
# Web-to-Telegram Linking Functions
# ============================================================================

# Code generation constants
CODE_LENGTH = 8
CODE_EXPIRY_MINUTES = 10
# Exclude ambiguous characters: 0/O, 1/I/L
CODE_CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class TelegramLinkingCodeDict(TypedDict):
    """Telegram linking code data structure"""

    id: int
    code: str
    clerk_user_id: str
    clerk_email: str
    expires_at: str
    used_at: str | None
    linked_user_id: int | None
    created_at: str


def generate_linking_code() -> str:
    """Generate a random 8-character alphanumeric code."""
    return "".join(random.choices(CODE_CHARSET, k=CODE_LENGTH))


async def create_linking_code(
    clerk_user_id: str,
    clerk_email: str,
) -> TelegramLinkingCodeDict:
    """
    Create a new linking code for a Clerk user.
    Deletes any existing unused codes for this Clerk user first.

    Args:
        clerk_user_id: Clerk user ID from web
        clerk_email: Email from Clerk (already verified)

    Returns:
        TelegramLinkingCodeDict: Created linking code record
    """
    try:
        # Delete any existing unused codes for this Clerk user
        supabase.table("telegram_linking_codes").delete().eq("clerk_user_id", clerk_user_id).is_(
            "used_at", "null"
        ).execute()

        code = generate_linking_code()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=CODE_EXPIRY_MINUTES)

        insert_data = {
            "code": code,
            "clerk_user_id": clerk_user_id,
            "clerk_email": clerk_email.lower(),
            "expires_at": expires_at.isoformat(),
        }
        response = supabase.table("telegram_linking_codes").insert(insert_data).execute()

        if not response.data:
            raise ValueError("Failed to create linking code")

        logger.info(f"Linking code created | clerk_user_id={clerk_user_id} | code={code}")
        return TelegramLinkingCodeDict(**response.data[0])

    except Exception as e:
        logger.error(
            f"Error in create_linking_code | clerk_user_id={clerk_user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def get_active_linking_code(clerk_user_id: str) -> TelegramLinkingCodeDict | None:
    """
    Get the active (non-expired, non-used) linking code for a Clerk user.

    Args:
        clerk_user_id: Clerk user ID

    Returns:
        TelegramLinkingCodeDict if found, None otherwise
    """
    try:
        response = (
            supabase.table("telegram_linking_codes")
            .select("*")
            .eq("clerk_user_id", clerk_user_id)
            .is_("used_at", "null")
            .gt("expires_at", datetime.now(timezone.utc).isoformat())
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if response.data and len(response.data) > 0:
            return TelegramLinkingCodeDict(**response.data[0])

        return None

    except Exception as e:
        logger.error(
            f"Error in get_active_linking_code | clerk_user_id={clerk_user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def validate_and_claim_linking_code(
    code: str,
    telegram_user_id: int,
) -> tuple[bool, str, dict | None]:
    """
    Validate a linking code and claim it for a Telegram user.

    Args:
        code: The linking code to validate
        telegram_user_id: Internal user ID of the Telegram user claiming the code

    Returns:
        tuple: (success, message, linking_data if successful)
            linking_data contains: clerk_user_id, clerk_email
    """
    try:
        # Find the code
        response = (
            supabase.table("telegram_linking_codes").select("*").eq("code", code.upper()).execute()
        )

        if not response.data or len(response.data) == 0:
            return False, "Invalid code. Please check and try again.", None

        linking_code = TelegramLinkingCodeDict(**response.data[0])

        # Check if already used
        if linking_code.get("used_at"):
            return False, "This code has already been used.", None

        # Check if expired
        expires_at = datetime.fromisoformat(linking_code["expires_at"].replace("Z", "+00:00"))
        if expires_at < datetime.now(expires_at.tzinfo):
            return False, "This code has expired. Please generate a new one from the web.", None

        # Mark as used
        supabase.table("telegram_linking_codes").update(
            {
                "used_at": datetime.now(timezone.utc).isoformat(),
                "linked_user_id": telegram_user_id,
            }
        ).eq("id", linking_code["id"]).execute()

        logger.info(
            f"Linking code claimed | code={code} | telegram_user_id={telegram_user_id} | "
            f"clerk_user_id={linking_code['clerk_user_id']}"
        )

        return (
            True,
            "Code validated successfully.",
            {
                "clerk_user_id": linking_code["clerk_user_id"],
                "clerk_email": linking_code["clerk_email"],
            },
        )

    except Exception as e:
        logger.error(
            f"Error in validate_and_claim_linking_code | code={code} | error={str(e)}",
            exc_info=True,
        )
        raise


async def get_user_by_clerk_id(clerk_user_id: str) -> UserDict | None:
    """
    Get user by Clerk user ID.
    First checks clerk_user_id column (for linked Telegram users),
    then falls back to external_user_id (for web-only users).

    Args:
        clerk_user_id: Clerk user ID

    Returns:
        UserDict if found, None otherwise
    """
    try:
        # First try to find by clerk_user_id (linked Telegram user)
        response = supabase.table("users").select("*").eq("clerk_user_id", clerk_user_id).execute()

        if response.data and len(response.data) > 0:
            return UserDict(**response.data[0])

        # Fall back to external_user_id (web-only user, not yet linked)
        response = (
            supabase.table("users").select("*").eq("external_user_id", clerk_user_id).execute()
        )

        if response.data and len(response.data) > 0:
            return UserDict(**response.data[0])

        return None

    except Exception as e:
        logger.error(
            f"Error in get_user_by_clerk_id | clerk_user_id={clerk_user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def update_user_clerk_id(user_id: int, clerk_user_id: str) -> UserDict:
    """
    Update user's Clerk user ID (for linking Telegram user to web account).

    Args:
        user_id: User ID
        clerk_user_id: Clerk user ID from web

    Returns:
        UserDict: Updated user data
    """
    try:
        response = (
            supabase.table("users")
            .update({"clerk_user_id": clerk_user_id})
            .eq("id", user_id)
            .execute()
        )

        if not response.data:
            raise ValueError("Failed to update user clerk_user_id")

        logger.info(
            f"User clerk_user_id updated | user_id={user_id} | clerk_user_id={clerk_user_id}"
        )
        return UserDict(**response.data[0])

    except Exception as e:
        logger.error(
            f"Error in update_user_clerk_id | user_id={user_id} | error={str(e)}", exc_info=True
        )
        raise


async def unlink_accounts(clerk_user_id: str) -> bool:
    """
    Unlink a Telegram account from a web account.
    Clears the clerk_user_id, email and email_verified_at from the linked Telegram user.

    Args:
        clerk_user_id: Clerk user ID of the web user

    Returns:
        bool: True if unlinked successfully
    """
    try:
        # Find user that has this clerk_user_id (the linked Telegram user)
        response = supabase.table("users").select("*").eq("clerk_user_id", clerk_user_id).execute()

        if response.data and len(response.data) > 0:
            # Clear linking data from the Telegram user
            supabase.table("users").update(
                {"clerk_user_id": None, "email": None, "email_verified_at": None}
            ).eq("clerk_user_id", clerk_user_id).execute()

            logger.info(f"Accounts unlinked | clerk_user_id={clerk_user_id}")
            return True

        logger.warning(f"No linked user found for unlinking | clerk_user_id={clerk_user_id}")
        return False

    except Exception as e:
        logger.error(
            f"Error in unlink_accounts | clerk_user_id={clerk_user_id} | error={str(e)}",
            exc_info=True,
        )
        raise
