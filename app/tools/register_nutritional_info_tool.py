"""LangChain tool for registering nutritional information"""

from langchain_core.tools import tool

from app.db.utils import get_spreadsheet_config, save_nutritional_info
from app.services.google_sheets_service import append_nutritional_data
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_register_nutritional_info_tool(user_id: int):
    """
    Create a register_nutritional_info tool bound to a specific user_id.

    Args:
        user_id: Internal user ID (from database)

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
        Register nutritional information. Always saves to internal database.
        Optionally saves to Google Sheets if configured.

        Args:
            calories: Calories value
            proteins: Proteins value in grams
            carbs: Carbohydrates value in grams
            fats: Fats value in grams
            meal_type: Type of meal (e.g., Breakfast, Lunch, Dinner, Snack)
            extra_details: Detailed breakdown including: list of ingredients, estimated portions/quantities for each ingredient, and nutritional breakdown per ingredient (calories, proteins, carbs, fats). This field is highly recommended for proper record keeping.

        Returns:
            str: Success message with confirmation of where data was saved
        """
        try:
            # Always save to internal database first
            logger.info(f"Registering nutritional data | user_id={user_id} | calories={calories}")
            nutritional_record = await save_nutritional_info(
                user_id=user_id,
                calories=calories,
                proteins=proteins,
                carbs=carbs,
                fats=fats,
                meal_type=meal_type,
                extra_details=extra_details,
            )

            record_id = nutritional_record["id"]
            logger.info(f"Nutritional data saved to database | id={record_id} | user_id={user_id}")

            # Check if user has spreadsheet configuration
            config = await get_spreadsheet_config(user_id)
            spreadsheet_id = None

            if config:
                # User has spreadsheet config, try to save there too
                try:
                    spreadsheet_id = await append_nutritional_data(
                        user_id=user_id,
                        calories=calories,
                        proteins=proteins,
                        carbs=carbs,
                        fats=fats,
                        meal_type=meal_type,
                        extra_details=extra_details,
                        record_id=record_id,  # Use the same ID from database
                    )
                    logger.info(
                        f"Nutritional data also saved to spreadsheet | id={record_id} | spreadsheet_id={spreadsheet_id}"
                    )
                except Exception as spreadsheet_error:
                    # Log error but don't fail - data is already saved in database
                    logger.warning(
                        f"Failed to save to spreadsheet but data saved in database | "
                        f"id={record_id} | error={str(spreadsheet_error)}"
                    )

            # Build response message
            response_parts = [
                "Successfully registered your meal information!",
                f"Calories: {calories}",
                f"Proteins: {proteins}g",
                f"Carbs: {carbs}g",
                f"Fats: {fats}g",
                f"Meal Type: {meal_type}",
            ]

            if spreadsheet_id:
                # Data saved in both places
                spreadsheet_link = (
                    f"\n\n📊 View your spreadsheet: "
                    f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
                )
                response_parts.append(
                    f"The data has been saved to your internal records and Google Sheet.{spreadsheet_link}"
                )
            else:
                # Only saved in database
                response_parts.append("The data has been saved to your internal records, if you want to see it in your Google Sheet, you need to connect your Google account, ask me how in case you want to do that.")

            return "\n".join(response_parts)

        except Exception as e:
            logger.error(
                f"Error in register_nutritional_info | user_id={user_id} | error={str(e)}",
                exc_info=True,
            )
            return f"I encountered an error while trying to register your nutritional information: {str(e)}"

    return register_nutritional_info
