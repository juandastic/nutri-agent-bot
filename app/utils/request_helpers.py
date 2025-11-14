"""Helpers for building absolute URLs from incoming FastAPI requests."""

from urllib.parse import urljoin

from fastapi import HTTPException, Request


def get_base_url_from_request(request: Request) -> str:
    """
    Return the base URL (scheme + host) inferred from the incoming request.

    Raises:
        HTTPException: If the host cannot be determined from the headers.
    """
    scheme = request.url.scheme
    host = request.headers.get("host") or request.headers.get("x-forwarded-host")

    if not host:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot determine base URL from request headers. "
                "Make sure you're calling this endpoint via the public URL (e.g., ngrok URL)."
            ),
        )

    return f"{scheme}://{host}"


def get_redirect_uri_from_request(request: Request) -> str:
    """
    Build the OAuth redirect URI using the incoming request headers.

    Raises:
        HTTPException: If the host cannot be determined from the headers.
    """
    base_url = get_base_url_from_request(request)
    return urljoin(base_url, "/auth/google/callback")
