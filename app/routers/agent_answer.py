"""Router exposing endpoints for external frontends to converse with the agent."""

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status

from app.models.schemas import ExternalAgentHistoryResponse, ExternalAgentResponse
from app.services.external_agent_service import ExternalAgentService
from app.utils.logging import get_logger
from app.utils.request_helpers import get_redirect_uri_from_request

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["external agent"])
external_agent_service = ExternalAgentService()


@router.post(
    "/answer",
    response_model=ExternalAgentResponse,
    status_code=status.HTTP_200_OK,
)
async def obtain_agent_answer(
    request: Request,
    external_user_id: str = Form(..., description="External user identifier"),
    username: str | None = Form(
        default=None,
        description="Optional username for registering the external user",
    ),
    name: str | None = Form(
        default=None,
        description="Optional human-readable name for the external user",
    ),
    message_text: str | None = Form(
        default=None,
        description="Optional text message provided by the user",
    ),
    external_chat_id: str | None = Form(
        default=None,
        description=(
            "Optional external chat identifier. When omitted a general chat will be reused per user."
        ),
    ),
    images: list[UploadFile] | None = File(
        default=None,
        description="Optional collection of image files to analyze",
    ),
) -> ExternalAgentResponse:
    """
    Process a conversation turn for external clients (non-Telegram).

    The endpoint accepts multipart/form-data so frontends can upload images directly.
    """
    redirect_uri = get_redirect_uri_from_request(request)

    try:
        image_bytes: list[bytes] = []
        if images:
            for upload in images:
                content = await upload.read()
                if content:
                    image_bytes.append(content)

        result = await external_agent_service.process(
            external_user_id=external_user_id,
            external_chat_id=external_chat_id,
            username=username,
            name=name,
            redirect_uri=redirect_uri,
            message_text=message_text,
            image_files=image_bytes,
        )

        return ExternalAgentResponse(
            success=True,
            response_text=result["response_text"],
            user_id=int(result["user_id"]),
            chat_id=int(result["chat_id"]),
            external_chat_id=str(result["external_chat_id"]),
            bot_message_id=int(result["bot_message_id"]),
            timestamp=result["timestamp"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("External agent endpoint failure | error=%s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process external agent request",
        ) from exc


@router.get(
    "/messages",
    response_model=ExternalAgentHistoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_messages(
    external_user_id: str = Query(..., description="External user identifier"),
    external_chat_id: str | None = Query(
        default=None,
        description=(
            "Optional external chat identifier. When omitted a general chat will be reused per user."
        ),
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of recent messages to return (default: 20, max: 100).",
    ),
) -> ExternalAgentHistoryResponse:
    """
    Retrieve recent messages for an external user.

    The endpoint returns the most recent messages associated with the resolved chat identifier.
    """
    try:
        result = await external_agent_service.get_history(
            external_user_id=external_user_id,
            external_chat_id=external_chat_id,
            limit=limit,
        )
        return ExternalAgentHistoryResponse(
            success=True,
            user_id=int(result["user_id"]),
            chat_id=int(result["chat_id"]),
            external_chat_id=str(result["external_chat_id"]),
            messages=result["messages"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("External agent history retrieval failure | error=%s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve external agent history",
        ) from exc
