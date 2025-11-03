"""Supabase client initialization"""

from supabase import Client, create_client

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

supabase: Client = create_client(
    settings.SUPABASE_URL or "",
    settings.SUPABASE_KEY or "",
)

logger.info("Supabase client initialized successfully")
