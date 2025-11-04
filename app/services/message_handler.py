"""Message handler service for processing Telegram updates"""

import asyncio
from typing import Any

from app.agents.langchain_agent import FoodAnalysisAgent
from app.db.utils import (
    create_message,
    get_or_create_chat,
    get_or_create_user,
    get_recent_messages,
    reset_user_account,
)
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
            if "message" not in update:
                logger.debug("Update does not contain a message, skipping")
                return

            message = update["message"]
            telegram_message_id = message.get("message_id")

            chat_info = message.get("chat")
            if not chat_info or "id" not in chat_info:
                logger.warning("Message missing 'chat' or 'chat.id' field, skipping")
                return

            telegram_chat_id: int = chat_info["id"]
            chat_id = telegram_chat_id
            chat_type = chat_info.get("type")

            # Send typing action at the beginning to show we're processing
            await self._send_typing_action(chat_id=chat_id)

            from_user = message.get("from")
            if not from_user or "id" not in from_user:
                logger.warning("Message missing 'from' user or 'id' field, skipping")
                return

            telegram_user_id: int = from_user["id"]
            username = from_user.get("username")
            first_name = from_user.get("first_name")

            # Extract text, photos, and documents
            message_text = message.get("text", "")
            photos = message.get("photo", [])
            document = message.get("document")
            caption = message.get("caption", "")

            # Handle commands (only for text messages in private chats)
            # Exclude /start so it can be handled by the agent for better welcome messages
            if (
                message_text
                and message_text.startswith("/")
                and chat_type == "private"
                and message_text.split()[0].lower() != "/start"
            ):
                await self._handle_command(
                    message_text=message_text,
                    telegram_chat_id=telegram_chat_id,
                    telegram_user_id=telegram_user_id,
                    username=username,
                    first_name=first_name,
                )
                return

            # Combine text and caption
            combined_text = ""
            if message_text:
                combined_text = message_text
            elif caption:
                combined_text = caption

            # Check if we have text, photos, documents, or both
            has_text = bool(combined_text)
            has_photos = bool(photos)
            has_document = bool(document)

            if not has_text and not has_photos and not has_document:
                logger.debug("Message has no text, photos, or documents, skipping")
                return

            logger.debug(
                f"Processing message | chat_id={chat_id} | message_id={telegram_message_id} | "
                f"has_text={has_text} | has_photos={has_photos} | has_document={has_document}"
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

            # Get conversation history BEFORE saving current message (to exclude it)
            conversation_history = await get_recent_messages(chat_id=chat["id"], limit=10)
            # Convert to format expected by agent
            history_for_agent = [
                {"role": msg["role"], "text": msg["text"] or ""}
                for msg in conversation_history
                if msg["text"]  # Only include messages with text
            ]

            # Determine message type
            message_type = determine_message_type(
                has_text=has_text,
                has_photos=has_photos,
                has_document=has_document,
            )

            # Store user message in database
            await create_message(
                chat_id=chat["id"],
                text=combined_text if combined_text else None,
                role="user",
                message_type=message_type,
                telegram_message_id=telegram_message_id,
                from_user_id=user["id"],
            )
            logger.debug(
                f"User message saved | telegram_message_id={telegram_message_id} | message_type={message_type}"
            )

            # Send typing action before generating response
            await self._send_typing_action(chat_id=chat_id)

            # Generate response using agent with conversation history
            response_text = await self._generate_response(
                message,
                combined_text,
                chat_id,
                history_for_agent,
                user["id"],
                redirect_uri,
            )

            # Save bot response to database (bot responses are always text)
            await create_message(
                chat_id=chat["id"],
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
                    chat_id=chat_id, text=response_text, parse_mode="Markdown"
                )
                logger.info(
                    f"Response sent successfully | chat_id={chat_id} | response_length={len(response_text)}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to send message | chat_id={chat_id} | error={str(e)}",
                    exc_info=True,
                )
                # Re-raise the error so it can be handled by outer exception handler
                raise

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
            images: list[bytes] = []

            # Download photos if present
            if photos:
                logger.debug(f"Downloading {len(photos)} photo(s)")
                # Download all photos (or just the largest one if there are multiple)
                # For simplicity, we'll use the largest photo (last in array)
                largest_photo = photos[-1]
                file_id = largest_photo.get("file_id")

                if file_id:
                    try:
                        # Get file path
                        file_info = await self.telegram_service.get_file_path(file_id)
                        if file_info.get("ok"):
                            file_path = file_info.get("result", {}).get("file_path")
                            if file_path:
                                # Download image
                                image_bytes = await self.telegram_service.download_file(file_path)
                                images.append(image_bytes)
                                logger.debug(
                                    f"Downloaded image | file_id={file_id} | size={len(image_bytes)}"
                                )
                    except Exception as e:
                        logger.error(
                            f"Error downloading image | file_id={file_id} | error={str(e)}"
                        )

            # Download document if present and it's an image
            if document:
                file_id = document.get("file_id")
                mime_type = document.get("mime_type", "")
                file_name = document.get("file_name", "")

                # Check if it's an image file
                is_image = mime_type.startswith("image/") or file_name.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".gif", ".webp")
                )

                if is_image and file_id:
                    logger.debug(
                        f"Downloading document image | file_id={file_id} | mime_type={mime_type}"
                    )
                    try:
                        # Get file path
                        file_info = await self.telegram_service.get_file_path(file_id)
                        if file_info.get("ok"):
                            file_path = file_info.get("result", {}).get("file_path")
                            if file_path:
                                # Download image
                                image_bytes = await self.telegram_service.download_file(file_path)
                                images.append(image_bytes)
                                logger.debug(
                                    f"Downloaded document image | file_id={file_id} | size={len(image_bytes)}"
                                )
                    except Exception as e:
                        logger.error(
                            f"Error downloading document image | file_id={file_id} | error={str(e)}"
                        )
                elif is_image and not file_id:
                    logger.warning(
                        f"Image document missing file_id | mime_type={mime_type} | file_name={file_name}"
                    )
                    # If no text provided and no images downloaded, return error message
                    if not combined_text and not images:
                        return (
                            "I received an image document but couldn't process it. "
                            "Please try sending the image again or send it as a photo."
                        )
                elif not is_image:
                    logger.debug(
                        f"Document is not an image | mime_type={mime_type} | file_name={file_name}"
                    )
                    # If document is not an image and no text provided, return a helpful message
                    if not combined_text and not images:
                        return (
                            "I can only analyze images of food. Please send me a photo or image file "
                            "(JPEG, PNG, GIF, or WEBP) of the food you'd like me to analyze."
                        )

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

    async def _handle_command(
        self,
        message_text: str,
        telegram_chat_id: int,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
    ) -> None:
        """
        Handle bot commands.

        Args:
            message_text: The command text (e.g., "/reset_account")
            telegram_chat_id: Telegram chat ID
            telegram_user_id: Telegram user ID
            username: Telegram username
            first_name: Telegram first name
        """
        try:
            # Get or create user to get internal user_id
            user = await get_or_create_user(
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
            )
            user_id = user["id"]

            command = message_text.split()[0].lower()  # Get command without arguments

            if command == "/reset_account":
                logger.info(f"Reset account command received | user_id={user_id}")
                try:
                    result = await reset_user_account(user_id)
                    response = (
                        "✅ Account reset completed successfully!\n\n"
                        f"• Messages deleted: {result['messages_deleted']}\n"
                        f"• Chats deleted: {result['chats_deleted']}\n"
                        f"• Configuration deleted: {result['config_deleted']}\n\n"
                        "You can now start fresh and configure your account again."
                    )
                except Exception as e:
                    logger.error(
                        f"Error resetting account | user_id={user_id} | error={str(e)}",
                        exc_info=True,
                    )
                    response = (
                        "❌ An error occurred while resetting your account. "
                        "Please try again later or contact support."
                    )
            else:
                # Unknown command
                response = (
                    f"Unknown command: {command}\n\n"
                    "Available commands:\n"
                    "• /start - Start chatting with the bot\n"
                    "• /reset_account - Reset your account data (messages, chats, configuration)"
                )

            await self.telegram_service.send_message(chat_id=telegram_chat_id, text=response)
            logger.info(f"Command response sent | command={command} | user_id={user_id}")

        except Exception as e:
            logger.error(
                f"Error handling command | command={message_text} | error={str(e)}",
                exc_info=True,
            )
            try:
                await self.telegram_service.send_message(
                    chat_id=telegram_chat_id,
                    text="❌ An error occurred while processing your command. Please try again later.",
                )
            except Exception:
                pass  # If we can't send error message, log it and continue

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
