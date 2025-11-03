import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings loaded from environment variables"""

    TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    WEBHOOK_URL: str | None = os.getenv("WEBHOOK_URL")
    TELEGRAM_API_BASE: str = "https://api.telegram.org/bot"

    # Supabase settings
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str | None = os.getenv("SUPABASE_KEY")
    SUPABASE_DB_URL: str | None = os.getenv("SUPABASE_DB_URL")

    # OpenAI settings
    OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")

    # Google OAuth settings
    GOOGLE_CLIENT_ID: str | None = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str | None = os.getenv("GOOGLE_CLIENT_SECRET")

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # LangSmith settings
    LANGSMITH_API_KEY: str | None = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_TRACING: str = os.getenv("LANGSMITH_TRACING", "false").lower()
    LANGSMITH_PROJECT: str | None = os.getenv("LANGSMITH_PROJECT", "nutri-agent-bot")

    def validate(self) -> tuple[bool, str | None]:
        """Validate that required settings are present"""
        if not self.TELEGRAM_BOT_TOKEN:
            return False, "TELEGRAM_BOT_TOKEN environment variable is not set"
        if not self.SUPABASE_URL:
            return False, "SUPABASE_URL environment variable is not set"
        if not self.SUPABASE_KEY:
            return False, "SUPABASE_KEY environment variable is not set"
        if not self.OPENAI_API_KEY:
            return False, "OPENAI_API_KEY environment variable is not set"
        return True, None


# Global settings instance
settings = Settings()
