"""Telegram API service for interacting with Telegram Bot API"""

import httpx

from app.config import settings


class TelegramService:
    """Service for Telegram Bot API interactions"""

    @staticmethod
    async def set_webhook(webhook_url: str) -> dict:
        """
        Set webhook for Telegram bot.

        Args:
            webhook_url: The URL where Telegram should send updates

        Returns:
            dict: Telegram API response

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        url = f"{settings.TELEGRAM_API_BASE}{settings.TELEGRAM_BOT_TOKEN}/setWebhook"

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"url": webhook_url})
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

        async with httpx.AsyncClient() as client:
            response = await client.post(url)
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

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
