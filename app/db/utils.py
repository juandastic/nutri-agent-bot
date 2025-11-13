"""Database utility functions using Supabase SDK"""

from datetime import datetime
from typing import TypedDict

from app.db.supabase_client import supabase
from app.utils.logging import get_logger

logger = get_logger(__name__)


class UserDict(TypedDict):
    """User data structure"""

    id: int
    external_user_id: str | None
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
    external_user_id: str,
    username: str | None,
    first_name: str | None,
) -> UserDict:
    """
    Get existing user or create a new one using Supabase SDK.

    Args:
        external_user_id: External user ID (may come from Telegram or other frontends)
        username: User handle or username (optional)
        first_name: User first name (optional)

    Returns:
        UserDict: User data dictionary
    """
    try:
        response = (
            supabase.table("users").select("*").eq("external_user_id", external_user_id).execute()
        )

        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            logger.debug(
                f"User found | user_id={user_data['id']} | external_user_id={external_user_id}"
            )
            return UserDict(**user_data)

        logger.info(
            f"Creating new user | external_user_id={external_user_id} | username={username}"
        )
        insert_data = {
            "external_user_id": external_user_id,
            "username": username,
            "first_name": first_name,
        }
        insert_response = supabase.table("users").insert(insert_data).execute()

        if not insert_response.data:
            raise ValueError("Failed to create user")

        user_data = insert_response.data[0]
        logger.info(
            f"User created | user_id={user_data['id']} | external_user_id={external_user_id}"
        )
        return UserDict(**user_data)

    except Exception as e:
        logger.error(
            f"Error in get_or_create_user | external_user_id={external_user_id} | error={str(e)}",
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
                .update({"last_active_at": datetime.now().isoformat()})
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
            "last_active_at": datetime.now().isoformat(),
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
                "updated_at": datetime.now().isoformat(),
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
        update_data = {**kwargs, "updated_at": datetime.now().isoformat()}
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
