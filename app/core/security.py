import secrets

from fastapi import Header, HTTPException, Request, status

from app.core.config import get_settings


async def require_admin(x_admin_key: str = Header(default="")) -> None:
    expected = get_settings().admin_api_key
    if not expected or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )

async def require_browser_request(request: Request) -> None:
    settings = get_settings()

    expected_origin = settings.frontend_url.rstrip("/")
    origin = request.headers.get("origin")
    requested_with = request.headers.get("x-requested-with")

    if (
        origin != expected_origin
        or requested_with != "XMLHttpRequest"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origen o encabezado de solicitud inválido",
            headers={"Cache-Control": "no-store"},
        )
