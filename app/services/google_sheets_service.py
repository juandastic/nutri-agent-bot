"""Google Sheets service for creating and updating spreadsheets"""

from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.db.utils import get_spreadsheet_config, update_spreadsheet_config
from app.services.google_oauth_service import get_credentials_from_tokens, refresh_access_token
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Spreadsheet headers
SHEET_HEADERS = [
    "Id",
    "Date",
    "Meal Type",
    "Calories",
    "Proteins",
    "Carbs",
    "Fats",
    "Extra Details",
]

# Default worksheet name
DEFAULT_WORKSHEET_NAME = "Nutritional Log"


def get_sheets_service(credentials: Credentials):
    """
    Build Google Sheets API service.

    Args:
        credentials: Google OAuth credentials

    Returns:
        Resource: Google Sheets API service
    """
    return build("sheets", "v4", credentials=credentials)


async def ensure_valid_credentials(user_id: int, config) -> Credentials:
    """
    Ensure credentials are valid, refresh if necessary.

    Args:
        user_id: User ID
        config: SpreadsheetConfigDict

    Returns:
        Credentials: Valid credentials
    """
    credentials = get_credentials_from_tokens(config["oauth_token"], config["refresh_token"])

    # Check if token is expired or about to expire
    if not credentials.valid:
        logger.info(f"Refreshing access token for user_id={user_id}")
        try:
            new_access_token = refresh_access_token(config["refresh_token"])
            # Update stored token
            await update_spreadsheet_config(user_id, oauth_token=new_access_token)
            credentials = get_credentials_from_tokens(new_access_token, config["refresh_token"])
        except Exception as e:
            logger.error(f"Failed to refresh token | user_id={user_id} | error={str(e)}")
            raise

    return credentials


async def create_spreadsheet(user_id: int, credentials: Credentials) -> str:
    """
    Create a new Google Spreadsheet.

    Args:
        user_id: User ID
        credentials: Google OAuth credentials

    Returns:
        str: Spreadsheet ID
    """
    try:
        sheets_service = get_sheets_service(credentials)

        spreadsheet_title = "Nutritional Log"

        spreadsheet = {
            "properties": {"title": spreadsheet_title},
            "sheets": [
                {
                    "properties": {
                        "title": DEFAULT_WORKSHEET_NAME,
                    },
                    "data": [
                        {
                            "rowData": [
                                {
                                    "values": [
                                        {"userEnteredValue": {"stringValue": header}}
                                        for header in SHEET_HEADERS
                                    ]
                                }
                            ]
                        }
                    ],
                }
            ],
        }

        result = sheets_service.spreadsheets().create(body=spreadsheet).execute()
        spreadsheet_id = result.get("spreadsheetId")

        logger.info(f"Created spreadsheet | user_id={user_id} | spreadsheet_id={spreadsheet_id}")

        # Update user config with spreadsheet_id
        await update_spreadsheet_config(user_id, spreadsheet_id=spreadsheet_id)

        # Add headers to the first row
        await add_headers_to_sheet(credentials, spreadsheet_id)

        return spreadsheet_id

    except HttpError as e:
        logger.error(f"Error creating spreadsheet | user_id={user_id} | error={str(e)}")
        raise


async def add_headers_to_sheet(credentials: Credentials, spreadsheet_id: str) -> None:
    """
    Add headers to the first row of the spreadsheet.

    Args:
        credentials: Google OAuth credentials
        spreadsheet_id: Spreadsheet ID
    """
    try:
        sheets_service = get_sheets_service(credentials)

        body = {"values": [SHEET_HEADERS]}

        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range="A1:H1",
            valueInputOption="RAW",
            body=body,
        ).execute()

        logger.debug(f"Added headers to spreadsheet | spreadsheet_id={spreadsheet_id}")

    except HttpError as e:
        logger.error(f"Error adding headers | spreadsheet_id={spreadsheet_id} | error={str(e)}")
        raise


async def ensure_spreadsheet_exists(user_id: int) -> tuple[str, Credentials]:
    """
    Ensure spreadsheet exists for user, create if necessary.

    Args:
        user_id: User ID

    Returns:
        tuple[str, Credentials]: (spreadsheet_id, credentials)
    """
    config = await get_spreadsheet_config(user_id)

    if not config:
        raise ValueError(f"No spreadsheet config found for user_id={user_id}")

    credentials = await ensure_valid_credentials(user_id, config)

    spreadsheet_id = config.get("spreadsheet_id")

    if not spreadsheet_id:
        logger.info(f"Creating new spreadsheet for user_id={user_id}")
        spreadsheet_id = await create_spreadsheet(user_id, credentials)
    else:
        # Verify spreadsheet exists and has headers
        try:
            await verify_spreadsheet_has_headers(credentials, spreadsheet_id)
        except HttpError as e:
            if e.resp.status == 404:
                # Spreadsheet was deleted, create new one
                logger.warning(
                    f"Spreadsheet not found, creating new one | spreadsheet_id={spreadsheet_id}"
                )
                spreadsheet_id = await create_spreadsheet(user_id, credentials)
            else:
                raise

    return spreadsheet_id, credentials


async def verify_spreadsheet_has_headers(credentials: Credentials, spreadsheet_id: str) -> None:
    """
    Verify spreadsheet has headers, add if missing.

    Args:
        credentials: Google OAuth credentials
        spreadsheet_id: Spreadsheet ID
    """
    try:
        sheets_service = get_sheets_service(credentials)
        result = (
            sheets_service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range="A1:H1")
            .execute()
        )
        values = result.get("values", [])

        if not values or values[0] != SHEET_HEADERS:
            logger.info(
                f"Headers missing or incorrect, adding headers | spreadsheet_id={spreadsheet_id}"
            )
            await add_headers_to_sheet(credentials, spreadsheet_id)

    except HttpError as e:
        logger.error(f"Error verifying headers | spreadsheet_id={spreadsheet_id} | error={str(e)}")
        raise


async def append_nutritional_data(
    user_id: int,
    calories: float,
    proteins: float,
    carbs: float,
    fats: float,
    meal_type: str,
    extra_details: str | None = None,
    record_id: int | None = None,
) -> str:
    """
    Append nutritional data to user's spreadsheet.

    Args:
        user_id: User ID
        calories: Calories value
        proteins: Proteins value (g)
        carbs: Carbohydrates value (g)
        fats: Fats value (g)
        meal_type: Meal type (e.g., Breakfast, Lunch, Dinner, Snack)
        extra_details: Extra details or description (optional)
        record_id: Optional record ID from database to use instead of timestamp

    Returns:
        str: Spreadsheet ID where the data was saved
    """
    try:
        spreadsheet_id, credentials = await ensure_spreadsheet_exists(user_id)

        # Use record_id if provided, otherwise use timestamp
        id_value = record_id if record_id is not None else datetime.now().isoformat()
        date_str = datetime.now().strftime("%Y-%m-%d")

        row_data = [
            id_value,  # Id (from database or timestamp)
            date_str,  # Date
            meal_type,  # Meal Type
            calories,  # Calories
            proteins,  # Proteins
            carbs,  # Carbs
            fats,  # Fats
            extra_details or "",  # Extra Details
        ]

        sheets_service = get_sheets_service(credentials)

        body = {"values": [row_data]}

        sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{DEFAULT_WORKSHEET_NAME}!A:H",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body=body,
        ).execute()

        logger.info(
            f"Added nutritional data | user_id={user_id} | spreadsheet_id={spreadsheet_id} | "
            f"calories={calories} | meal_type={meal_type} | has_extra_details={bool(extra_details)}"
        )
        if extra_details:
            logger.debug(
                f"Extra details included | length={len(extra_details)} | preview={extra_details[:100]}..."
            )

        return spreadsheet_id

    except Exception as e:
        logger.error(
            f"Error appending nutritional data | user_id={user_id} | error={str(e)}", exc_info=True
        )
        raise
