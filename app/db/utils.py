"""Database utility functions using Supabase SDK"""

from datetime import datetime
from typing import TypedDict

from app.db.supabase_client import supabase
from app.utils.logging import get_logger

logger = get_logger(__name__)


class UserDict(TypedDict):
    """User data structure"""

    id: int
    telegram_user_id: int
    username: str | None
    first_name: str | None
    created_at: str


class ChatDict(TypedDict):
    """Chat data structure"""

    id: int
    telegram_chat_id: int
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


async def get_or_create_user(
    telegram_user_id: int,
    username: str | None,
    first_name: str | None,
) -> UserDict:
    """
    Get existing user or create a new one using Supabase SDK.

    Args:
        telegram_user_id: Telegram user ID
        username: Telegram username (optional)
        first_name: Telegram first name (optional)

    Returns:
        UserDict: User data dictionary
    """
    try:
        response = (
            supabase.table("users").select("*").eq("telegram_user_id", telegram_user_id).execute()
        )

        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            logger.debug(
                f"User found | user_id={user_data['id']} | telegram_user_id={telegram_user_id}"
            )
            return UserDict(**user_data)

        logger.info(
            f"Creating new user | telegram_user_id={telegram_user_id} | username={username}"
        )
        insert_data = {
            "telegram_user_id": telegram_user_id,
            "username": username,
            "first_name": first_name,
        }
        insert_response = supabase.table("users").insert(insert_data).execute()

        if not insert_response.data:
            raise ValueError("Failed to create user")

        user_data = insert_response.data[0]
        logger.info(
            f"User created | user_id={user_data['id']} | telegram_user_id={telegram_user_id}"
        )
        return UserDict(**user_data)

    except Exception as e:
        logger.error(
            f"Error in get_or_create_user | telegram_user_id={telegram_user_id} | error={str(e)}",
            exc_info=True,
        )
        raise


async def get_or_create_chat(
    telegram_chat_id: int,
    user_id: int | None,
    chat_type: str | None,
) -> ChatDict:
    """
    Get existing chat or create a new one using Supabase SDK.

    Args:
        telegram_chat_id: Telegram chat ID
        user_id: User ID (None for group chats)
        chat_type: Chat type ('private', 'group', 'supergroup')

    Returns:
        ChatDict: Chat data dictionary
    """
    try:
        response = (
            supabase.table("chats").select("*").eq("telegram_chat_id", telegram_chat_id).execute()
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
                f"Chat updated | chat_id={chat_data['id']} | telegram_chat_id={telegram_chat_id}"
            )
            return ChatDict(**chat_data)

        logger.info(
            f"Creating new chat | telegram_chat_id={telegram_chat_id} | chat_type={chat_type}"
        )
        insert_data = {
            "telegram_chat_id": telegram_chat_id,
            "user_id": user_id,
            "chat_type": chat_type,
            "last_active_at": datetime.now().isoformat(),
        }
        insert_response = supabase.table("chats").insert(insert_data).execute()

        if not insert_response.data:
            raise ValueError("Failed to create chat")

        chat_data = insert_response.data[0]
        logger.info(
            f"Chat created | chat_id={chat_data['id']} | telegram_chat_id={telegram_chat_id}"
        )
        return ChatDict(**chat_data)

    except Exception as e:
        logger.error(
            f"Error in get_or_create_chat | telegram_chat_id={telegram_chat_id} | error={str(e)}",
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
    """
    try:
        response = (
            supabase.table("messages")
            .select("*")
            .eq("chat_id", chat_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )

        messages = []
        if response.data:
            for msg_data in response.data:
                messages.append(MessageDict(**msg_data))

        logger.debug(f"Retrieved {len(messages)} messages for chat_id={chat_id}")
        return messages

    except Exception as e:
        logger.error(
            f"Error in get_recent_messages | chat_id={chat_id} | error={str(e)}",
            exc_info=True,
        )
        raise
