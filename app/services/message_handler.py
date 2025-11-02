"""Message handler service for processing Telegram updates"""

from typing import Any

from app.services.telegram_service import TelegramService


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
        # Check if this is a message update
        if "message" in update and "text" in update["message"]:
            message = update["message"]
            chat_id = message["chat"]["id"]
            message_text = message.get("text", "")

            # Process the message and send response
            # TODO: Integrate LangChain agent here for future processing
            response_text = await self._generate_response(message_text, update)

            # Send response
            await self.telegram_service.send_message(chat_id=chat_id, text=response_text)

    async def _generate_response(self, message_text: str, update: dict[str, Any]) -> str:
        """
        Generate a response for the incoming message.

        Args:
            message_text: The text content of the message
            update: Full Telegram update object (for accessing images, attachments, etc.)

        Returns:
            str: Response text to send back
        """
        # Current simple implementation: return "Hello World"
        # TODO: Replace with LangChain agent processing
        return "Hello World"

    async def process_with_attachments(self, update: dict[str, Any]) -> None:
        """
        Process message with images and attachments.
        Placeholder for future LangChain agent integration.

        Args:
            update: Telegram update JSON payload
        """
        # TODO: Implement LangChain agent processing with image/attachment support
        message = update.get("message", {})
        chat_id = message.get("chat", {}).get("id")

        if chat_id:
            await self.telegram_service.send_message(
                chat_id=chat_id, text="Attachment processing coming soon!"
            )
