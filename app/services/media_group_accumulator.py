"""Media group accumulator for handling multiple photos sent together in Telegram"""

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MediaGroupData:
    """Data structure for accumulating media group messages"""

    messages: list[dict[str, Any]] = field(default_factory=list)
    timer_task: asyncio.Task | None = None
    telegram_chat_id: int = 0
    chat_type: str | None = None
    redirect_uri: str | None = None


class MediaGroupAccumulator:
    """
    Accumulates messages belonging to the same media_group_id.

    When Telegram sends multiple photos at once, each photo arrives as a separate
    message with the same media_group_id. This class buffers these messages and
    processes them together after a timeout period of no new messages.
    """

    def __init__(self, timeout_seconds: float = 1.0):
        """
        Initialize the accumulator.

        Args:
            timeout_seconds: Time to wait after the last message before processing
        """
        self._groups: dict[str, MediaGroupData] = {}
        self._lock = asyncio.Lock()
        self._timeout = timeout_seconds

    async def add_message(
        self,
        media_group_id: str,
        message: dict[str, Any],
        telegram_chat_id: int,
        chat_type: str | None,
        redirect_uri: str | None,
        process_callback: Callable[
            [list[dict[str, Any]], int, str | None, str | None],
            Coroutine[Any, Any, None],
        ],
    ) -> bool:
        """
        Add a message to the media group buffer.

        Args:
            media_group_id: The Telegram media group ID
            message: The Telegram message object
            telegram_chat_id: The chat ID
            chat_type: The type of chat (private, group, etc.)
            redirect_uri: OAuth redirect URI
            process_callback: Async function to call when processing the group

        Returns:
            True if message was added to buffer (caller should NOT process it),
            False if something went wrong
        """
        async with self._lock:
            # Create group if it doesn't exist
            if media_group_id not in self._groups:
                self._groups[media_group_id] = MediaGroupData(
                    telegram_chat_id=telegram_chat_id,
                    chat_type=chat_type,
                    redirect_uri=redirect_uri,
                )
                logger.debug(f"Created new media group buffer | media_group_id={media_group_id}")

            group = self._groups[media_group_id]

            # Cancel existing timer if any
            if group.timer_task and not group.timer_task.done():
                group.timer_task.cancel()
                try:
                    await group.timer_task
                except asyncio.CancelledError:
                    pass

            # Add message to the group
            group.messages.append(message)
            logger.debug(
                f"Added message to media group | media_group_id={media_group_id} | "
                f"total_messages={len(group.messages)}"
            )

            # Schedule processing after timeout
            group.timer_task = asyncio.create_task(
                self._schedule_processing(media_group_id, process_callback)
            )

        return True

    async def _schedule_processing(
        self,
        media_group_id: str,
        process_callback: Callable[
            [list[dict[str, Any]], int, str | None, str | None],
            Coroutine[Any, Any, None],
        ],
    ) -> None:
        """
        Wait for timeout and then process the media group.

        Args:
            media_group_id: The media group ID to process
            process_callback: The callback to invoke for processing
        """
        try:
            # Wait for the timeout period
            await asyncio.sleep(self._timeout)

            # Get and remove the group data
            async with self._lock:
                if media_group_id not in self._groups:
                    logger.warning(
                        f"Media group not found after timeout | media_group_id={media_group_id}"
                    )
                    return

                group = self._groups.pop(media_group_id)

            logger.info(
                f"Processing media group | media_group_id={media_group_id} | "
                f"message_count={len(group.messages)}"
            )

            # Process the accumulated messages
            await process_callback(
                group.messages,
                group.telegram_chat_id,
                group.chat_type,
                group.redirect_uri,
            )

        except asyncio.CancelledError:
            # Timer was cancelled because a new message arrived
            logger.debug(
                f"Media group timer cancelled (new message arrived) | "
                f"media_group_id={media_group_id}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Error processing media group | media_group_id={media_group_id} | error={str(e)}",
                exc_info=True,
            )
            # Clean up on error
            async with self._lock:
                self._groups.pop(media_group_id, None)
