"""Router for user-related endpoints"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from app.db.utils import (
    create_linking_code,
    get_active_linking_code,
    get_user_by_clerk_id,
    get_user_link_status,
    unlink_accounts,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])

# Constants
CODE_EXPIRY_MINUTES = 10


class LinkStatusResponse(BaseModel):
    """Response model for link status endpoint"""

    success: bool
    is_linked: bool
    email: str | None = None
    telegram_user_id: str | None = None
    linked_at: str | None = None


class GenerateLinkCodeRequest(BaseModel):
    """Request model for generate link code endpoint"""

    clerk_user_id: str
    clerk_email: str


class GenerateLinkCodeResponse(BaseModel):
    """Response model for generate link code endpoint"""

    success: bool
    code: str
    expires_in_minutes: int
    message: str


class UnlinkRequest(BaseModel):
    """Request model for unlink endpoint"""

    clerk_user_id: str


class UnlinkResponse(BaseModel):
    """Response model for unlink endpoint"""

    success: bool
    message: str


@router.get(
    "/link-status",
    response_model=LinkStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_link_status(
    clerk_user_id: str = Query(..., description="Clerk user ID from web authentication"),
) -> LinkStatusResponse:
    """
    Get the account linking status for a Clerk user.

    This endpoint checks if the web user's account is linked to Telegram.
    It first looks for a Telegram user with this clerk_user_id (linked),
    then falls back to checking external_user_id (web-only user).

    Args:
        clerk_user_id: Clerk user ID from web authentication

    Returns:
        LinkStatusResponse with linking status and details
    """
    try:
        # Try to find user by clerk_user_id (checks both clerk_user_id and external_user_id)
        user = await get_user_by_clerk_id(clerk_user_id)

        if not user:
            # User doesn't exist yet - not linked
            return LinkStatusResponse(
                success=True,
                is_linked=False,
                email=None,
                telegram_user_id=None,
                linked_at=None,
            )

        # Get link status
        status_data = await get_user_link_status(user["id"])

        return LinkStatusResponse(
            success=True,
            is_linked=status_data["is_linked"],
            email=status_data["email"],
            telegram_user_id=status_data["telegram_user_id"],
            linked_at=status_data["linked_at"],
        )

    except Exception as exc:
        logger.error(
            "Error getting link status | clerk_user_id=%s | error=%s",
            clerk_user_id,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get link status",
        ) from exc


@router.post(
    "/generate-link-code",
    response_model=GenerateLinkCodeResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_link_code(request: GenerateLinkCodeRequest) -> GenerateLinkCodeResponse:
    """
    Generate a linking code for a Clerk user to link their Telegram account.

    The code is 8 characters alphanumeric and expires in 10 minutes.
    The user should send this code to the Telegram bot using /linkweb CODE.

    Args:
        request: Contains clerk_user_id and clerk_email

    Returns:
        GenerateLinkCodeResponse with the generated code
    """
    try:
        # Check if there's already an active code for this user
        existing_code = await get_active_linking_code(request.clerk_user_id)

        if existing_code:
            # Return existing code instead of creating a new one
            logger.info(f"Returning existing linking code | clerk_user_id={request.clerk_user_id}")
            return GenerateLinkCodeResponse(
                success=True,
                code=existing_code["code"],
                expires_in_minutes=CODE_EXPIRY_MINUTES,
                message="Use this code with /linkweb in Telegram",
            )

        # Create new linking code
        linking_code = await create_linking_code(
            clerk_user_id=request.clerk_user_id,
            clerk_email=request.clerk_email,
        )

        logger.info(
            f"Linking code generated | clerk_user_id={request.clerk_user_id} | code={linking_code['code']}"
        )

        return GenerateLinkCodeResponse(
            success=True,
            code=linking_code["code"],
            expires_in_minutes=CODE_EXPIRY_MINUTES,
            message="Use this code with /linkweb in Telegram",
        )

    except Exception as exc:
        logger.error(
            "Error generating link code | clerk_user_id=%s | error=%s",
            request.clerk_user_id,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate link code",
        ) from exc


@router.post(
    "/unlink",
    response_model=UnlinkResponse,
    status_code=status.HTTP_200_OK,
)
async def unlink(request: UnlinkRequest) -> UnlinkResponse:
    """
    Unlink a Telegram account from the web account.

    This clears the email association from the linked Telegram user,
    allowing them to link to a different account if needed.

    Args:
        request: Contains clerk_user_id

    Returns:
        UnlinkResponse with success status
    """
    try:
        success = await unlink_accounts(request.clerk_user_id)

        if success:
            logger.info(f"Account unlinked | clerk_user_id={request.clerk_user_id}")
            return UnlinkResponse(
                success=True,
                message="Telegram account unlinked successfully",
            )
        else:
            return UnlinkResponse(
                success=False,
                message="No linked account found",
            )

    except Exception as exc:
        logger.error(
            "Error unlinking account | clerk_user_id=%s | error=%s",
            request.clerk_user_id,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlink account",
        ) from exc
