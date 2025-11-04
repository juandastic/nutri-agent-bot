"""Media handler service for downloading photos and documents from Telegram"""

from typing import Any

from app.services.telegram_service import TelegramService
from app.utils.logging import get_logger

logger = get_logger(__name__)


class MediaHandler:
    """Handler for processing media files from Telegram messages"""

    def __init__(self, telegram_service: TelegramService):
        """
        Initialize MediaHandler.

        Args:
            telegram_service: TelegramService instance for file operations
        """
        self.telegram_service = telegram_service

    async def download_photos(self, photos: list) -> list[bytes]:
        """
        Download photos from Telegram message.

        Args:
            photos: List of photo objects from Telegram message

        Returns:
            list[bytes]: List of downloaded image bytes
        """
        images: list[bytes] = []

        if not photos:
            return images

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
                logger.error(f"Error downloading image | file_id={file_id} | error={str(e)}")

        return images

    def is_image_document(self, document: dict) -> bool:
        """
        Check if a document is an image file.

        Args:
            document: Document object from Telegram message

        Returns:
            bool: True if document is an image, False otherwise
        """
        mime_type = document.get("mime_type", "")
        file_name = document.get("file_name", "")

        return mime_type.startswith("image/") or file_name.lower().endswith(
            (".jpg", ".jpeg", ".png", ".gif", ".webp")
        )

    async def download_document(
        self, document: dict[str, Any] | None, combined_text: str
    ) -> tuple[list[bytes], str | None]:
        """
        Download document if it's an image, otherwise return error message.

        Args:
            document: Document object from Telegram message (can be None)
            combined_text: Combined text from message text and caption

        Returns:
            tuple containing (list of image bytes, error message if applicable)
        """
        images: list[bytes] = []

        if not document:
            return images, None

        file_id = document.get("file_id")
        mime_type = document.get("mime_type", "")
        file_name = document.get("file_name", "")

        is_image = self.is_image_document(document)

        if is_image and file_id:
            logger.debug(f"Downloading document image | file_id={file_id} | mime_type={mime_type}")
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
                    images,
                    "I received an image document but couldn't process it. "
                    "Please try sending the image again or send it as a photo.",
                )
        elif not is_image:
            logger.debug(
                f"Document is not an image | mime_type={mime_type} | file_name={file_name}"
            )
            # If document is not an image and no text provided, return a helpful message
            if not combined_text and not images:
                return (
                    images,
                    "I can only analyze images of food. Please send me a photo or image file "
                    "(JPEG, PNG, GIF, or WEBP) of the food you'd like me to analyze.",
                )

        return images, None

    async def download_all_media(
        self, photos: list, document: dict[str, Any] | None, combined_text: str
    ) -> tuple[list[bytes], str | None]:
        """
        Download all media (photos and documents) from message.

        Args:
            photos: List of photo objects from Telegram message
            document: Document object from Telegram message (can be None)
            combined_text: Combined text from message text and caption

        Returns:
            tuple containing (list of image bytes, error message if applicable)
        """
        images: list[bytes] = []

        # Download photos
        photo_images = await self.download_photos(photos)
        images.extend(photo_images)

        # Download document if present
        doc_images, error_message = await self.download_document(document, combined_text)
        if error_message:
            return images, error_message

        images.extend(doc_images)

        return images, None
