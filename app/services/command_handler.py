"""Command handler service for processing Telegram bot commands"""

from app.db.utils import get_or_create_user, reset_user_account
from app.services.telegram_service import TelegramService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class CommandHandler:
    """Handler for processing Telegram bot commands"""

    def __init__(self, telegram_service: TelegramService):
        """
        Initialize CommandHandler.

        Args:
            telegram_service: TelegramService instance for sending messages
        """
        self.telegram_service = telegram_service

    async def handle_command(
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
                response = await self._handle_reset_account(user_id)
            else:
                response = self._handle_unknown_command(command)

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

    async def _handle_reset_account(self, user_id: int) -> str:
        """
        Handle /reset_account command.

        Args:
            user_id: Internal user ID

        Returns:
            str: Response message
        """
        logger.info(f"Reset account command received | user_id={user_id}")
        try:
            result = await reset_user_account(user_id)
            return (
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
            return (
                "❌ An error occurred while resetting your account. "
                "Please try again later or contact support."
            )

    def _handle_unknown_command(self, command: str) -> str:
        """
        Handle unknown command.

        Args:
            command: The unknown command text

        Returns:
            str: Response message listing available commands
        """
        return (
            f"Unknown command: {command}\n\n"
            "Available commands:\n"
            "• /start - Start chatting with the bot\n"
            "• /reset_account - Reset your account data (messages, chats, configuration)"
        )
