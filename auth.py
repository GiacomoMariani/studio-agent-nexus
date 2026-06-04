import os

from fastapi import Header, HTTPException

API_KEY_ENV_NAME = "APP_API_KEY"


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    expected_api_key = os.getenv(API_KEY_ENV_NAME)

    if not expected_api_key:
        raise HTTPException(
            status_code=500,
            detail="Server API key is not configured.",
        )

    if x_api_key != expected_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key.",
        )