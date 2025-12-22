"""Command handler service for processing Telegram bot commands"""

from app.db.utils import (
    delete_user,
    get_or_create_user,
    get_user_by_clerk_id,
    merge_user_data,
    reset_user_account,
    update_user_clerk_id,
    update_user_email,
    validate_and_claim_linking_code,
)
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
        external_user_id: str,
        username: str | None,
        first_name: str | None,
    ) -> None:
        """
        Handle bot commands.

        Args:
            message_text: The command text (e.g., "/reset_account")
            telegram_chat_id: Telegram chat ID
            external_user_id: External user ID
            username: Telegram username
            first_name: Telegram first name
        """
        try:
            # Get or create user to get internal user_id
            user = await get_or_create_user(
                telegram_user_id=external_user_id,
                username=username,
                first_name=first_name,
            )
            user_id = user["id"]

            command = message_text.split()[0].lower()  # Get command without arguments

            if command == "/start":
                await self._handle_start(telegram_chat_id)
            elif command == "/reset_account":
                response = await self._handle_reset_account(user_id)
                await self.telegram_service.send_message(chat_id=telegram_chat_id, text=response)
            elif command == "/linkweb":
                # Extract code from command arguments
                parts = message_text.split()
                code = parts[1] if len(parts) > 1 else None
                response = await self._handle_linkweb(user_id, code)
                await self.telegram_service.send_message(
                    chat_id=telegram_chat_id, text=response, parse_mode="Markdown"
                )
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

    async def _handle_start(self, telegram_chat_id: int) -> None:
        """
        Handle /start command.
        Sends a welcome message in English and asks for language preference.

        Args:
            telegram_chat_id: Telegram chat ID
        """
        logger.info(f"Start command received | chat_id={telegram_chat_id}")
        welcome_text = (
            "Welcome to NutriAgentBot! 👋\n\n"
            "I'm here to help you analyze your food and provide nutritional insights.\n\n"
            "Please select your preferred language:"
        )

        await self.telegram_service.send_message(
            chat_id=telegram_chat_id,
            text=welcome_text,
            reply_markup={
                "inline_keyboard": [
                    [
                        {
                            "text": "English",
                            "callback_data": "Welcome me in English, explain me how it works",
                        },
                        {
                            "text": "Español",
                            "callback_data": "Dame la bienvenida en español, explicame como funciona",
                        },
                    ]
                ]
            },
        )

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
                f"• Configuration deleted: {result['config_deleted']}\n"
                f"• Nutritional records deleted: {result['nutritional_info_deleted']}\n\n"
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
            "• /linkweb CODE - Link your Telegram to your web account\n"
            "• /reset_account - Reset your account data"
        )

    async def _handle_linkweb(self, user_id: int, code: str | None) -> str:
        """
        Handle /linkweb command to link Telegram account with web account.

        Args:
            user_id: Internal user ID
            code: The linking code from web (optional)

        Returns:
            str: Response message
        """
        logger.info(f"Linkweb command received | user_id={user_id} | has_code={bool(code)}")

        if not code:
            return (
                "🔗 *Link Web Account*\n\n"
                "To link your Telegram account with your web account:\n\n"
                "1. Go to your account settings on the web\n"
                "2. Click 'Link Telegram'\n"
                "3. Copy the code shown\n"
                "4. Send: `/linkweb YOUR_CODE`\n\n"
                "Example: `/linkweb A7K9M2X4`"
            )

        try:
            # Validate and claim the code
            success, message, linking_data = await validate_and_claim_linking_code(
                code=code,
                telegram_user_id=user_id,
            )

            if not success:
                return f"❌ {message}"

            # Check if web user has existing data to merge
            clerk_user_id = linking_data["clerk_user_id"]
            clerk_email = linking_data["clerk_email"]

            web_user = await get_user_by_clerk_id(clerk_user_id)
            merge_info = []

            if web_user and web_user["id"] != user_id:
                # Merge web user's data into Telegram user
                merge_result = await merge_user_data(
                    source_user_id=web_user["id"],
                    target_user_id=user_id,
                )

                if merge_result["chats"] > 0:
                    merge_info.append(f"{merge_result['chats']} chats")
                if merge_result["messages"] > 0:
                    merge_info.append(f"{merge_result['messages']} messages")
                if merge_result["nutritional_info"] > 0:
                    merge_info.append(f"{merge_result['nutritional_info']} nutrition records")
                if merge_result["spreadsheet_config"] > 0:
                    merge_info.append("Google Sheets configuration")

                # Delete the orphaned web user after merge (now empty)
                await delete_user(web_user["id"])
                logger.info(f"Deleted merged web user | web_user_id={web_user['id']}")

            # Update Telegram user with email and clerk_user_id
            await update_user_email(user_id, clerk_email, verified=True)
            await update_user_clerk_id(user_id, clerk_user_id)

            # Build success message
            response = f"✅ *Account Linked Successfully!*\n\nEmail: `{clerk_email}`\n\n"

            if merge_info:
                response += (
                    "I also transferred the following data from your web account:\n"
                    f"• {', '.join(merge_info)}\n\n"
                )

            response += "Your Telegram and Web accounts are now unified! 🎉"

            logger.info(
                f"Account linked | user_id={user_id} | clerk_email={clerk_email} | "
                f"merged={bool(merge_info)}"
            )

            return response

        except Exception as e:
            logger.error(
                f"Error linking account | user_id={user_id} | code={code} | error={str(e)}",
                exc_info=True,
            )
            return "❌ An error occurred while linking your account. Please try again."
