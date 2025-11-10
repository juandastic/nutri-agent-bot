"""LangChain tool for querying nutritional information"""

from langchain_core.tools import tool

from app.db.utils import get_nutritional_info
from app.utils.logging import get_logger

logger = get_logger(__name__)


def create_query_nutritional_info_tool(user_id: int):
    """
    Create a query_nutritional_info tool bound to a specific user_id.

    Args:
        user_id: Internal user ID (from database)

    Returns:
        Tool: LangChain tool instance
    """

    @tool
    async def query_nutritional_info(
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> str:
        """
        Query nutritional information records for the user. Returns all records if no dates are provided.
        Can filter by date range to answer questions like "how many calories did I consume today?" or
        "what did I eat in the last 2 days?".

        Args:
            start_date: Start date in YYYY-MM-DD format (e.g., "2024-01-15"). If provided, returns records from this date onwards.
                        If not provided and end_date is provided, returns all records up to end_date.
            end_date: End date in YYYY-MM-DD format (e.g., "2024-01-20"). If provided, returns records up to this date.
                      If not provided and start_date is provided, returns records from start_date to today.
                      If both are provided, returns records in the range [start_date, end_date].
                      If neither is provided, returns all records for the user.

        Returns:
            str: Simple list of nutritional records, one per line
        """
        try:
            logger.info(
                f"Querying nutritional data | user_id={user_id} | start_date={start_date} | end_date={end_date}"
            )

            # Get records from database
            records = await get_nutritional_info(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
            )

            if not records:
                return "No nutritional records found."

            # Return simple format: one record per line
            lines = []
            for record in records:
                # Extract date from created_at (format: YYYY-MM-DDTHH:MM:SS...)
                date = record["created_at"].split("T")[0]
                time = (
                    record["created_at"].split("T")[1].split(".")[0]
                    if "T" in record["created_at"]
                    else ""
                )

                line_parts = [
                    f"Date: {date}",
                    f"Time: {time}",
                    f"Meal: {record['meal_type']}",
                    f"Calories: {record['calories']}",
                    f"Proteins: {record['proteins']}g",
                    f"Carbs: {record['carbs']}g",
                    f"Fats: {record['fats']}g",
                ]

                if record.get("extra_details"):
                    line_parts.append(f"Details: {record['extra_details']}")

                lines.append(" | ".join(line_parts))

            return "\n".join(lines)

        except Exception as e:
            logger.error(
                f"Error in query_nutritional_info | user_id={user_id} | error={str(e)}",
                exc_info=True,
            )
            return f"I encountered an error while trying to query your nutritional information: {str(e)}"

    return query_nutritional_info
