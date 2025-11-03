"""Message handler service for processing Telegram updates"""

from typing import Any

from app.db.utils import create_message, get_or_create_chat, get_or_create_user
from app.services.telegram_service import TelegramService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class MessageHandler:
    """Handler for processing Telegram message updates"""

    def __init__(self):
        self.telegram_service = TelegramService()

    async def process_message(self, update: dict[str, Any]) -> None:
        """
        Process an incoming Telegram message update.

        Args:
            update: Telegram update JSON payload
        """
        try:
            if "message" in update and "text" in update["message"]:
                message = update["message"]
                message_text = message.get("text", "")
                telegram_message_id = message.get("message_id")

                chat_info = message.get("chat")
                if not chat_info or "id" not in chat_info:
                    logger.warning("Message missing 'chat' or 'chat.id' field, skipping")
                    return

                telegram_chat_id: int = chat_info["id"]
                chat_id = telegram_chat_id
                chat_type = chat_info.get("type")

                from_user = message.get("from")
                if not from_user or "id" not in from_user:
                    logger.warning("Message missing 'from' user or 'id' field, skipping")
                    return

                telegram_user_id: int = from_user["id"]
                username = from_user.get("username")
                first_name = from_user.get("first_name")

                logger.debug(
                    f"Processing message | chat_id={chat_id} | message_id={telegram_message_id} | "
                    f"text_length={len(message_text)}"
                )

                logger.debug(
                    f"Extracted user info | telegram_user_id={telegram_user_id} | "
                    f"username={username} | chat_type={chat_type}"
                )

                user = await get_or_create_user(
                    telegram_user_id=telegram_user_id,
                    username=username,
                    first_name=first_name,
                )

                logger.info(
                    f"User processed | user_id={user['id']} | telegram_user_id={telegram_user_id} | "
                    f"username={username}"
                )

                chat_user_id = None if chat_type in ("group", "supergroup") else user["id"]

                chat = await get_or_create_chat(
                    telegram_chat_id=telegram_chat_id,
                    user_id=chat_user_id,
                    chat_type=chat_type,
                )

                logger.info(
                    f"Chat processed | chat_id={chat['id']} | telegram_chat_id={telegram_chat_id} | "
                    f"chat_type={chat_type}"
                )

                if telegram_message_id:
                    await create_message(
                        chat_id=chat["id"],
                        telegram_message_id=telegram_message_id,
                        text=message_text,
                        from_user_id=user["id"],
                    )
                    logger.debug(f"Message saved | message_id={telegram_message_id}")

                response_text = await self._generate_response(message_text, update)
                await self.telegram_service.send_message(chat_id=chat_id, text=response_text)
                logger.info(
                    f"Response sent | chat_id={chat_id} | response_length={len(response_text)}"
                )

            else:
                logger.debug("Update is not a text message, skipping")
        except Exception as e:
            logger.error(
                f"Error processing message | update_id={update.get('update_id')} | error={str(e)}",
                exc_info=True,
            )
            raise

    async def _generate_response(self, message_text: str, update: dict[str, Any]) -> str:
        """
        Generate a response for the incoming message.

        Args:
            message_text: The text content of the message
            update: Full Telegram update object (for accessing images, attachments, etc.)

        Returns:
            str: Response text to send back
        """
        logger.debug(f"Generating response for message | text_length={len(message_text)}")
        return "Hello World"

    async def process_with_attachments(self, update: dict[str, Any]) -> None:
        """
        Process message with images and attachments.

        Args:
            update: Telegram update JSON payload
        """
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")

        if chat_id:
            await self.telegram_service.send_message(
                chat_id=chat_id, text="Attachment processing coming soon!"
            )
