"""Message handler service for processing Telegram updates"""

import asyncio
from typing import Any

from app.agents.langchain_agent import FoodAnalysisAgent
from app.db.utils import (
    create_message,
    get_or_create_chat,
    get_or_create_user,
    get_recent_messages,
)
from app.services.command_handler import CommandHandler
from app.services.media_handler import MediaHandler
from app.services.telegram_service import TelegramService
from app.utils.logging import get_logger

logger = get_logger(__name__)


def determine_message_type(
    has_text: bool,
    has_photos: bool,
    has_document: bool,
) -> str:
    """
    Determine the message type based on content.
    Text presence is tracked separately in the text field.

    Args:
        has_text: Whether the message has text content
        has_photos: Whether the message has photos
        has_document: Whether the message has a document

    Returns:
        str: Message type ('text', 'photo', 'document')
    """
    if has_photos:
        return "photo"
    elif has_document:
        return "document"
    else:
        return "text"


class MessageHandler:
    """Handler for processing Telegram message updates"""

    def __init__(self):
        self.telegram_service = TelegramService()
        self.food_agent = FoodAnalysisAgent()
        self.command_handler = CommandHandler(self.telegram_service)
        self.media_handler = MediaHandler(self.telegram_service)

    def _validate_update(self, update: dict[str, Any]) -> bool:
        """
        Validate that the update contains a message or callback_query.

        Args:
            update: Telegram update JSON payload

        Returns:
            bool: True if update is valid, False otherwise
        """
        if "message" not in update and "callback_query" not in update:
            logger.debug("Update does not contain a message or callback_query, skipping")
            return False
        return True

    def _extract_callback_query_data(
        self, update: dict[str, Any]
    ) -> tuple[dict[str, Any], int, int, str | None] | None:
        """
        Extract and convert callback_query data to message-like structure.

        Args:
            update: Telegram update JSON payload with callback_query

        Returns:
            tuple containing (message, telegram_chat_id, telegram_message_id, chat_type) or None if invalid
        """
        callback_query = update.get("callback_query")
        if not callback_query:
            return None

        # Extract user info from callback_query
        from_user = callback_query.get("from")
        if not from_user or "id" not in from_user:
            logger.warning("Callback query missing 'from' user or 'id' field, skipping")
            return None

        # Extract chat info from the original message
        original_message = callback_query.get("message", {})
        chat_info = original_message.get("chat", {})
        if not chat_info or "id" not in chat_info:
            logger.warning("Callback query missing 'message.chat' or 'chat.id' field, skipping")
            return None

        telegram_chat_id: int = chat_info["id"]
        chat_type = chat_info.get("type")

        # Get original message_id and generate a unique one for the callback
        original_message_id = original_message.get("message_id")
        # Generate unique message_id: add prefix (1000000000) to original message_id
        # This ensures uniqueness in the database while staying within PostgreSQL INTEGER range
        telegram_message_id = 1000000000 + original_message_id if original_message_id else None

        # Extract callback data (the text the user clicked)
        callback_data = callback_query.get("data", "")

        # Create a message-like structure using callback_data as text
        message = {
            "message_id": telegram_message_id,
            "from": from_user,
            "chat": chat_info,
            "date": original_message.get("date", 0),  # Use original message date
            "text": callback_data,  # Use callback_data as the message text
        }

        return message, telegram_chat_id, telegram_message_id, chat_type

    def _extract_message_data(
        self, update: dict[str, Any]
    ) -> tuple[dict[str, Any], int, int, str | None] | None:
        """
        Extract and validate message data from update.
        Handles both regular messages and callback_query updates.

        Args:
            update: Telegram update JSON payload

        Returns:
            tuple containing (message, telegram_chat_id, telegram_message_id, chat_type) or None if invalid
        """
        # Check if it's a callback_query first
        if "callback_query" in update:
            return self._extract_callback_query_data(update)

        # Otherwise, handle as regular message
        message = update["message"]
        telegram_message_id = message.get("message_id")

        chat_info = message.get("chat")
        if not chat_info or "id" not in chat_info:
            logger.warning("Message missing 'chat' or 'chat.id' field, skipping")
            return None

        telegram_chat_id: int = chat_info["id"]
        chat_type = chat_info.get("type")

        return message, telegram_chat_id, telegram_message_id, chat_type

    def _extract_user_info(
        self, message: dict[str, Any]
    ) -> tuple[str, str | None, str | None] | None:
        """
        Extract user information from message.

        Args:
            message: Telegram message object

        Returns:
            tuple containing (external_user_id, username, first_name) or None if invalid
        """
        from_user = message.get("from")
        if not from_user or "id" not in from_user:
            logger.warning("Message missing 'from' user or 'id' field, skipping")
            return None

        external_user_id = str(from_user["id"])
        username = from_user.get("username")
        first_name = from_user.get("first_name")

        return external_user_id, username, first_name

    def _extract_content(
        self, message: dict[str, Any]
    ) -> tuple[str, list, dict[str, Any] | None, str]:
        """
        Extract content from message (text, photos, documents, caption).

        Args:
            message: Telegram message object

        Returns:
            tuple containing (message_text, photos, document, caption)
        """
        message_text = message.get("text", "")
        photos = message.get("photo", [])
        document = message.get("document")
        caption = message.get("caption", "")

        return message_text, photos, document, caption

    async def _ensure_user_and_chat(
        self,
        external_user_id: str,
        username: str | None,
        first_name: str | None,
        external_chat_id: str,
        chat_type: str | None,
    ) -> tuple[dict, dict]:
        """
        Ensure user and chat exist in database, create if necessary.

        Args:
            external_user_id: External user ID
            username: Telegram username
            first_name: Telegram first name
            telegram_chat_id: Telegram chat ID
            chat_type: Chat type (private, group, supergroup)

        Returns:
            tuple containing (user dict, chat dict)
        """
        user = await get_or_create_user(
            telegram_user_id=external_user_id,
            username=username,
            first_name=first_name,
        )

        logger.info(
            f"User processed | user_id={user['id']} | telegram_user_id={external_user_id} | "
            f"username={username}"
        )

        chat_user_id = None if chat_type in ("group", "supergroup") else user["id"]

        chat = await get_or_create_chat(
            external_chat_id=external_chat_id,
            user_id=chat_user_id,
            chat_type=chat_type,
        )

        logger.info(
            f"Chat processed | chat_id={chat['id']} | external_chat_id={external_chat_id} | "
            f"chat_type={chat_type}"
        )

        return user, chat

    def _prepare_conversation_history(
        self, conversation_history: list[dict]
    ) -> list[dict[str, str]]:
        """
        Prepare conversation history for agent.

        Args:
            conversation_history: List of message dictionaries from database

        Returns:
            List of formatted messages for agent
        """
        return [
            {"role": msg["role"], "text": msg["text"] or ""}
            for msg in conversation_history
            if msg["text"]  # Only include messages with text
        ]

    async def _save_user_message(
        self,
        chat_id: int,
        combined_text: str | None,
        message_type: str,
        telegram_message_id: int | None,
        user_id: int,
    ) -> None:
        """
        Save user message to database.

        Args:
            chat_id: Internal chat ID
            combined_text: Combined text from message text and caption
            message_type: Message type (text, photo, document)
            telegram_message_id: Telegram message ID
            user_id: Internal user ID
        """
        await create_message(
            chat_id=chat_id,
            text=combined_text if combined_text else None,
            role="user",
            message_type=message_type,
            telegram_message_id=telegram_message_id,
            from_user_id=user_id,
        )
        logger.debug(
            f"User message saved | telegram_message_id={telegram_message_id} | message_type={message_type}"
        )

    async def _save_and_send_bot_response(
        self, chat_id: int, response_text: str, telegram_chat_id: int
    ) -> None:
        """
        Save bot response to database and send it via Telegram.

        Args:
            chat_id: Internal chat ID
            response_text: Response text to send
            telegram_chat_id: Telegram chat ID for sending message
        """
        # Save bot response to database (bot responses are always text)
        await create_message(
            chat_id=chat_id,
            text=response_text,
            role="bot",
            message_type="text",
            telegram_message_id=None,  # Bot messages don't have Telegram IDs
            from_user_id=None,  # Bot messages don't have a user_id
        )
        logger.debug("Bot response saved")

        # Send message with Markdown formatting
        try:
            await self.telegram_service.send_message(
                chat_id=telegram_chat_id, text=response_text, parse_mode="Markdown"
            )
            logger.info(
                f"Response sent successfully | chat_id={telegram_chat_id} | response_length={len(response_text)}"
            )
        except Exception as e:
            logger.error(
                f"Failed to send message | chat_id={telegram_chat_id} | error={str(e)}",
                exc_info=True,
            )
            # Re-raise the error so it can be handled by outer exception handler
            raise

    async def _send_typing_action(self, chat_id: int) -> None:
        """
        Send typing action to indicate bot is processing.
        Silently handles errors to not interrupt the main flow.

        Args:
            chat_id: The chat ID to send the action to
        """
        try:
            await self.telegram_service.send_chat_action(chat_id=chat_id, action="typing")
        except Exception as e:
            logger.debug(f"Failed to send typing action | chat_id={chat_id} | error={str(e)}")
            # Silently fail - typing action is not critical

    async def _keep_typing_alive(
        self, chat_id: int, task: asyncio.Task, interval_seconds: float = 4.0
    ) -> None:
        """
        Keep typing action alive by sending it periodically while a task is running.
        Telegram typing actions expire after ~5 seconds, so we refresh them every 4 seconds.

        Args:
            chat_id: The chat ID to send the action to
            task: The asyncio task to wait for
            interval_seconds: Interval between typing actions (default 4 seconds)
        """
        # Send initial typing action
        await self._send_typing_action(chat_id=chat_id)

        # Keep sending typing actions every interval_seconds until task completes
        while not task.done():
            try:
                # Wait for either the task to complete or the interval to pass
                await asyncio.wait_for(asyncio.shield(task), timeout=interval_seconds)
                break  # Task completed
            except asyncio.TimeoutError:
                # Task still running, send another typing action
                await self._send_typing_action(chat_id=chat_id)
                continue

    async def process_message(
        self, update: dict[str, Any], redirect_uri: str | None = None
    ) -> None:
        """
        Process an incoming Telegram message update.
        Handles both text messages and photo messages.

        Args:
            update: Telegram update JSON payload
            redirect_uri: OAuth redirect URI (optional, for dynamic URL generation)
        """
        try:
            # Validate update
            if not self._validate_update(update):
                return

            # Extract message data
            message_data = self._extract_message_data(update)
            if not message_data:
                return

            message, telegram_chat_id, telegram_message_id, chat_type = message_data

            # If this is a callback_query, answer it to remove loading state
            if "callback_query" in update:
                callback_query_id = update["callback_query"].get("id")
                if callback_query_id:
                    try:
                        await self.telegram_service.answer_callback_query(
                            callback_query_id=callback_query_id
                        )
                    except Exception as e:
                        logger.debug(
                            f"Failed to answer callback query | callback_query_id={callback_query_id} | error={str(e)}"
                        )
                        # Continue processing even if answering fails

            # Send typing action at the beginning to show we're processing
            await self._send_typing_action(chat_id=telegram_chat_id)

            # Extract user info
            user_info = self._extract_user_info(message)
            if not user_info:
                return

            external_user_id, username, first_name = user_info
            external_chat_id = str(telegram_chat_id)

            # Extract content
            message_text, photos, document, caption = self._extract_content(message)

            # Handle commands (only for text messages in private chats)
            if message_text and message_text.startswith("/") and chat_type == "private":
                await self.command_handler.handle_command(
                    message_text=message_text,
                    telegram_chat_id=telegram_chat_id,
                    external_user_id=external_user_id,
                    username=username,
                    first_name=first_name,
                )
                return

            # Combine text and caption
            combined_text = message_text if message_text else caption

            # Check if we have text, photos, documents, or both
            has_text = bool(combined_text)
            has_photos = bool(photos)
            has_document = bool(document)

            if not has_text and not has_photos and not has_document:
                logger.debug("Message has no text, photos, or documents, skipping")
                return

            logger.debug(
                f"Processing message | chat_id={telegram_chat_id} | message_id={telegram_message_id} | "
                f"has_text={has_text} | has_photos={has_photos} | has_document={has_document}"
            )

            logger.debug(
                f"Extracted user info | external_user_id={external_user_id} | "
                f"username={username} | chat_type={chat_type}"
            )

            # Ensure user and chat exist
            user, chat = await self._ensure_user_and_chat(
                external_user_id=external_user_id,
                username=username,
                first_name=first_name,
                external_chat_id=external_chat_id,
                chat_type=chat_type,
            )

            # Get conversation history BEFORE saving current message (to exclude it)
            conversation_history = await get_recent_messages(chat_id=chat["id"], limit=10)
            history_for_agent = self._prepare_conversation_history(conversation_history)

            # Determine message type
            message_type = determine_message_type(
                has_text=has_text,
                has_photos=has_photos,
                has_document=has_document,
            )

            # Store user message in database
            await self._save_user_message(
                chat_id=chat["id"],
                combined_text=combined_text if combined_text else None,
                message_type=message_type,
                telegram_message_id=telegram_message_id,
                user_id=user["id"],
            )

            # Send typing action before generating response
            await self._send_typing_action(chat_id=telegram_chat_id)

            # Generate response using agent with conversation history
            response_text = await self._generate_response(
                message,
                combined_text,
                telegram_chat_id,
                history_for_agent,
                user["id"],
                redirect_uri,
            )

            # Save bot response and send it
            await self._save_and_send_bot_response(
                chat_id=chat["id"],
                response_text=response_text,
                telegram_chat_id=telegram_chat_id,
            )

        except Exception as e:
            logger.error(
                f"Error processing message | update_id={update.get('update_id')} | error={str(e)}",
                exc_info=True,
            )
            raise

    async def _generate_response(
        self,
        message: dict[str, Any],
        combined_text: str,
        chat_id: int,
        conversation_history: list[dict[str, str]] | None = None,
        user_id: int | None = None,
        redirect_uri: str | None = None,
    ) -> str:
        """
        Generate a response for the incoming message using the food analysis agent.

        Args:
            message: Telegram message object
            combined_text: Combined text from message text and caption
            chat_id: Telegram chat ID (required for sending typing action)
            conversation_history: Previous conversation messages for context
            user_id: Internal user ID (from database)
            redirect_uri: OAuth redirect URI (optional)

        Returns:
            str: Response text to send back
        """
        try:
            photos = message.get("photo", [])
            document = message.get("document")

            # Download all media using MediaHandler
            images, error_message = await self.media_handler.download_all_media(
                photos, document, combined_text
            )

            # If there's an error message and no text/content, return error
            if error_message and not combined_text and not images:
                return error_message

            # Prepare text input
            text_input = combined_text if combined_text else None

            # Send typing action before calling the agent (this is usually the longest operation)
            # Start the agent analysis task
            analyze_task = asyncio.create_task(
                self.food_agent.analyze(
                    text=text_input,
                    images=images if images else None,
                    conversation_history=conversation_history,
                    user_id=user_id,
                    redirect_uri=redirect_uri,
                )
            )
            # Keep typing action alive during the analysis
            await self._keep_typing_alive(chat_id=chat_id, task=analyze_task)
            # Get the result
            response_text = await analyze_task

            return response_text

        except Exception as e:
            logger.error(f"Error generating response | error={str(e)}", exc_info=True)
            return "I apologize, but I encountered an error while analyzing your food. Please try again."

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
