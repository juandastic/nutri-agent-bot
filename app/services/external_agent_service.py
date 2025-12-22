"""Service for handling external (non-Telegram) agent conversations."""

from collections.abc import Iterable
from datetime import datetime

from app.agents.langchain_agent import FoodAnalysisAgent
from app.db.utils import (
    ChatDict,
    MessageDict,
    UserDict,
    create_message,
    get_or_create_chat,
    get_or_create_user,
    get_recent_messages,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ExternalAgentService:
    """Service layer for processing messages coming from external frontends."""

    def __init__(self) -> None:
        self.food_agent = FoodAnalysisAgent()

    async def _prepare_history(self, chat_id: int, limit: int = 10) -> list[dict[str, str]]:
        """Fetch and format conversation history for the agent."""
        conversation = await get_recent_messages(chat_id=chat_id, limit=limit)
        return [
            {"role": message["role"], "text": message["text"] or ""}
            for message in conversation
            if message["text"]
        ]

    @staticmethod
    def _resolve_chat_identifier(clerk_user_id: str, external_chat_id: str | None) -> str:
        """
        Determine which chat identifier to use.

        If the frontend does not provide a chat identifier we namespace a general purpose chat
        identifier using the user id to keep it unique across users.
        """
        if external_chat_id:
            return external_chat_id
        return f"{clerk_user_id}__general_chat"

    @staticmethod
    def _determine_message_type(has_images: bool) -> str:
        """Return the message type label used in persistence."""
        return "photo" if has_images else "text"

    async def _ensure_user_and_chat(
        self,
        *,
        clerk_user_id: str,
        external_chat_id: str | None,
        username: str | None,
        name: str | None,
        email: str | None = None,
    ) -> tuple[UserDict, ChatDict, str]:
        """Guarantee that the user and chat exist in the database."""
        user = await get_or_create_user(
            clerk_user_id=clerk_user_id,
            username=username,
            first_name=name,
            email=email,
        )
        resolved_chat_id = self._resolve_chat_identifier(clerk_user_id, external_chat_id)
        chat = await get_or_create_chat(
            external_chat_id=resolved_chat_id,
            user_id=user["id"],
            chat_type="external",
        )
        logger.debug(
            "External agent user/chat ready | user_id=%s | clerk_user_id=%s | "
            "chat_id=%s | external_chat_id=%s",
            user["id"],
            clerk_user_id,
            chat["id"],
            resolved_chat_id,
        )
        return user, chat, resolved_chat_id

    async def _store_user_message(
        self,
        *,
        chat_id: int,
        user_id: int,
        message_text: str | None,
        has_images: bool,
    ) -> MessageDict:
        """Persist the inbound user message."""
        message_type = self._determine_message_type(has_images)
        logger.debug(
            "Persisting external user message | chat_id=%s | user_id=%s | message_type=%s",
            chat_id,
            user_id,
            message_type,
        )
        return await create_message(
            chat_id=chat_id,
            text=message_text if message_text else None,
            role="user",
            message_type=message_type,
            telegram_message_id=None,
            from_user_id=user_id,
        )

    async def _store_bot_message(self, *, chat_id: int, response_text: str) -> MessageDict:
        """Persist the agent response message."""
        return await create_message(
            chat_id=chat_id,
            text=response_text,
            role="bot",
            message_type="text",
            telegram_message_id=None,
            from_user_id=None,
        )

    async def process(
        self,
        *,
        clerk_user_id: str,
        external_chat_id: str | None,
        username: str | None,
        name: str | None,
        email: str | None,
        redirect_uri: str | None,
        message_text: str | None,
        image_files: Iterable[bytes] | None,
    ) -> dict[str, int | str]:
        """
        Process an external message and return the agent reply and metadata.

        Args:
            clerk_user_id: Clerk user ID from web authentication.
            external_chat_id: Optional chat identifier. When omitted, a general chat is used.
            username: Optional username for first-time user registration.
            name: Optional name for first-time user registration.
            email: Optional email from Clerk for first-time user registration.
            redirect_uri: Optional OAuth redirect URI for external flows.
            message_text: Optional textual message content.
            image_files: Optional iterable of raw image bytes.

        Returns:
            dict containing the response text plus identifiers for the persisted entities.
        """
        if not clerk_user_id:
            raise ValueError("clerk_user_id is required")

        images = list(image_files) if image_files else []
        has_text = bool(message_text and message_text.strip())
        has_images = bool(images)
        sanitized_username = username.strip() if username and username.strip() else None
        sanitized_name = name.strip() if name and name.strip() else None
        sanitized_email = email.strip().lower() if email and email.strip() else None
        sanitized_redirect_uri = (
            redirect_uri.strip() if redirect_uri and redirect_uri.strip() else None
        )

        if not has_text and not has_images:
            raise ValueError("Message must include text or at least one image")

        user, chat, resolved_chat_id = await self._ensure_user_and_chat(
            clerk_user_id=clerk_user_id,
            external_chat_id=external_chat_id,
            username=sanitized_username,
            name=sanitized_name,
            email=sanitized_email,
        )

        history_for_agent = await self._prepare_history(chat_id=chat["id"])

        await self._store_user_message(
            chat_id=chat["id"],
            user_id=user["id"],
            message_text=message_text.strip() if has_text else None,
            has_images=has_images,
        )

        logger.info(
            "Invoking agent for external message | user_id=%s | chat_id=%s | "
            "has_text=%s | image_count=%s",
            user["id"],
            chat["id"],
            has_text,
            len(images),
        )
        response_text = await self.food_agent.analyze(
            text=message_text.strip() if has_text else None,
            images=images if images else None,
            conversation_history=history_for_agent,
            user_id=user["id"],
            redirect_uri=sanitized_redirect_uri,
        )

        bot_message = await self._store_bot_message(chat_id=chat["id"], response_text=response_text)

        return {
            "response_text": response_text,
            "user_id": user["id"],
            "chat_id": chat["id"],
            "external_chat_id": resolved_chat_id,
            "bot_message_id": bot_message["id"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_history(
        self,
        *,
        clerk_user_id: str,
        external_chat_id: str | None,
        limit: int,
    ) -> dict[str, int | str | list[dict[str, str | int | None]]]:
        """
        Retrieve recent conversation history for a web user.

        Args:
            clerk_user_id: Clerk user ID from web authentication.
            external_chat_id: Optional chat identifier. When omitted, a general chat is used.
            limit: Maximum number of messages to return.

        Returns:
            dict containing the resolved identifiers and the list of recent messages.
        """
        if not clerk_user_id:
            raise ValueError("clerk_user_id is required")
        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        user, chat, resolved_chat_id = await self._ensure_user_and_chat(
            clerk_user_id=clerk_user_id,
            external_chat_id=external_chat_id,
            username=None,
            name=None,
        )

        messages = await get_recent_messages(chat_id=chat["id"], limit=limit)
        formatted_messages = [
            {
                "id": message["id"],
                "role": message["role"],
                "message_type": message["message_type"],
                "text": message["text"],
                "from_user_id": message["from_user_id"],
                "created_at": message["created_at"],
                "updated_at": message["updated_at"],
            }
            for message in messages
        ]

        return {
            "user_id": user["id"],
            "chat_id": chat["id"],
            "external_chat_id": resolved_chat_id,
            "messages": formatted_messages,
        }
