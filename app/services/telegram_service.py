"""Telegram API service for interacting with Telegram Bot API"""

import httpx

from app.config import settings

# HTTP timeout configuration (connection: 10s, read: 30s)
HTTP_TIMEOUT = httpx.Timeout(10.0, read=30.0)


class TelegramService:
    """Service for Telegram Bot API interactions"""

    @staticmethod
    async def set_webhook(webhook_url: str, secret_token: str | None = None) -> dict:
        """
        Set webhook for Telegram bot.

        Args:
            webhook_url: The URL where Telegram should send updates
            secret_token: Optional secret token to validate webhook requests

        Returns:
            dict: Telegram API response

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}/setWebhook"

        payload = {"url": webhook_url}
        if secret_token:
            payload["secret_token"] = secret_token

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def delete_webhook() -> dict:
        """
        Delete webhook for Telegram bot.

        Returns:
            dict: Telegram API response

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}/deleteWebhook"

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(url)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def set_my_commands(commands: list[dict[str, str]]) -> dict:
        """
        Set bot commands to be displayed in the command menu.

        Args:
            commands: List of command dictionaries with 'command' and 'description' keys

        Returns:
            dict: Telegram API response

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}/setMyCommands"

        payload = {"commands": commands}

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def send_message(chat_id: int, text: str, **kwargs) -> dict:
        """
        Send a message to a Telegram chat.

        Args:
            chat_id: The chat ID to send the message to
            text: The message text
            **kwargs: Additional parameters for sendMessage API

        Returns:
            dict: Telegram API response

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

        payload = {"chat_id": chat_id, "text": text, **kwargs}

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_file_path(file_id: str) -> dict:
        """
        Get file path from Telegram Bot API.

        Args:
            file_id: The file ID from Telegram message

        Returns:
            dict: Telegram API response with file_path

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}/getFile"

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(url, json={"file_id": file_id})
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def download_file(file_path: str) -> bytes:
        """
        Download a file from Telegram.

        Args:
            file_path: The file path from getFile API response

        Returns:
            bytes: The file content as bytes

        Raises:
            httpx.HTTPStatusError: If download fails
        """
        file_url = f"https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}"

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(file_url)
            response.raise_for_status()
            return response.content

    @staticmethod
    async def answer_callback_query(
        callback_query_id: str, text: str | None = None, show_alert: bool = False
    ) -> dict:
        """
        Answer a callback query from an inline keyboard button.

        Args:
            callback_query_id: The ID of the callback query to answer
            text: Optional text to show to the user
            show_alert: If True, shows an alert instead of a notification

        Returns:
            dict: Telegram API response

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}/answerCallbackQuery"

        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = show_alert

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def send_chat_action(chat_id: int, action: str) -> dict:
        """
        Send a chat action to indicate that the bot is processing a message.

        Args:
            chat_id: The chat ID to send the action to
            action: The action type (e.g., 'typing', 'upload_photo', 'record_video')

        Returns:
            dict: Telegram API response

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}/sendChatAction"

        payload = {"chat_id": chat_id, "action": action}

        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
