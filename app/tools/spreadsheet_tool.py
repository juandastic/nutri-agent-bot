"""LangChain tool for registering nutritional information in Google Sheets"""

from langchain_core.tools import tool

from app.db.utils import get_spreadsheet_config
from app.services.google_oauth_service import get_authorization_url
from app.services.google_sheets_service import append_nutritional_data
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_register_nutritional_info_tool(user_id: int, redirect_uri: str | None = None):
    """
    Create a register_nutritional_info tool bound to a specific user_id.

    Args:
        user_id: Internal user ID (from database)
        redirect_uri: OAuth redirect URI (optional, for dynamic URL generation)

    Returns:
        Tool: LangChain tool instance
    """

    @tool
    async def register_nutritional_info(
        calories: float,
        proteins: float,
        carbs: float,
        fats: float,
        meal_type: str,
        extra_details: str | None = None,
    ) -> str:
        """
        Register nutritional information in the user's Google Sheet.

        This tool will:
        1. Check if the user has authorized Google Sheets access
        2. If not authorized, return an authorization URL
        3. If authorized, create/update spreadsheet and append the data

        Args:
            calories: Calories value
            proteins: Proteins value in grams
            carbs: Carbohydrates value in grams
            fats: Fats value in grams
            meal_type: Type of meal (e.g., Breakfast, Lunch, Dinner, Snack)
            extra_details: Detailed breakdown including: list of ingredients, estimated portions/quantities for each ingredient, and nutritional breakdown per ingredient (calories, proteins, carbs, fats). This field is highly recommended for complete record keeping.

        Returns:
            str: Success message or authorization URL with instructions
        """
        try:
            # Check if user has spreadsheet configuration
            config = await get_spreadsheet_config(user_id)

            if not config:
                # User not authorized, generate authorization URL
                logger.info(
                    f"User not authorized, generating authorization URL | user_id={user_id}"
                )

                # Use redirect_uri if provided, otherwise return error
                if not redirect_uri:
                    return (
                        "I need to connect your Google account to save nutritional data. "
                        "However, the server configuration is incomplete. Please contact support."
                    )

                authorization_url = get_authorization_url(user_id, redirect_uri)

                return (
                    f"To register your nutritional information, I need permission to access your Google Sheets. "
                    f"Please authorize the connection by clicking this link:\n\n"
                    f"{authorization_url}\n\n"
                    f"After authorizing, you can try registering your meal again."
                )

            # User is authorized, register the data
            logger.info(f"Registering nutritional data | user_id={user_id} | calories={calories}")

            await append_nutritional_data(
                user_id=user_id,
                calories=calories,
                proteins=proteins,
                carbs=carbs,
                fats=fats,
                meal_type=meal_type,
                extra_details=extra_details,
            )

            return (
                f"Successfully registered your meal information!\n"
                f"Calories: {calories}\n"
                f"Proteins: {proteins}g\n"
                f"Carbs: {carbs}g\n"
                f"Fats: {fats}g\n"
                f"Meal Type: {meal_type}\n"
                f"The data has been saved to your Google Sheet."
            )

        except Exception as e:
            logger.error(
                f"Error in register_nutritional_info | user_id={user_id} | error={str(e)}",
                exc_info=True,
            )
            return f"I encountered an error while trying to register your nutritional information: {str(e)}"

    return register_nutritional_info
