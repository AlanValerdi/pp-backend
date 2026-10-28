from authlib.integrations.base_client import OAuthError
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from httpx2 import HTTPError
from joserfc.errors import JoseError

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.modules.auth import service
from app.modules.auth.oauth import get_oauth
from app.modules.auth.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE = "pp_session"


def login_error_response() -> RedirectResponse:
    settings = get_settings()
    return RedirectResponse(
        url=f"{settings.frontend_url.rstrip('/')}/?authError=google_login_failed",
        status_code=303,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/google/login")
async def google_login(request: Request) -> RedirectResponse:
    settings = get_settings()
    google = get_oauth().create_client("google")

    # Este espacio se usa exclusivamente para la transacción OAuth.
    request.session.clear()

    response = await google.authorize_redirect(
        request,
        settings.google_redirect_uri,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/google/callback")
async def google_callback(
    request: Request,
    session: SessionDep,
) -> RedirectResponse:
    settings = get_settings()
    google = get_oauth().create_client("google")

    try:
        token = await google.authorize_access_token(request)
    except (OAuthError, JoseError, HTTPError):
        request.session.clear()
        return login_error_response()

    request.session.clear()

    # Authlib obtiene estos datos después de validar el ID token.
    profile = token.get("userinfo")

    if (
        not profile
        or not profile.get("sub")
        or not profile.get("email")
        or profile.get("email_verified") is not True
    ):
        return login_error_response()

    result = await service.login_verified_google_user(
        session,
        google_sub=profile["sub"],
        email=profile["email"],
        name=profile.get("name") or profile["email"],
        avatar_url=profile.get("picture"),
    )

    response = RedirectResponse(
        url=settings.frontend_url,
        status_code=303,
        headers={"Cache-Control": "no-store"},
    )
    response.set_cookie(
        key=SESSION_COOKIE,
        value=result.token,
        max_age=settings.session_ttl_seconds,
        expires=result.expires_at,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/me", response_model=UserRead)
async def read_current_user(
    request: Request,
    response: Response,
    session: SessionDep,
) -> UserRead:
    user = await service.get_current_user(
        session,
        token=request.cookies.get(SESSION_COOKIE),
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Sesión inválida o expirada",
            headers={"Cache-Control": "no-store"},
        )

    response.headers["Cache-Control"] = "no-store"
    return UserRead.model_validate(user)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    session: SessionDep,
) -> Response:
    settings = get_settings()

    if (
        request.headers.get("origin") != settings.frontend_url.rstrip("/")
        or request.headers.get("x-requested-with") != "XMLHttpRequest"
    ):
        raise HTTPException(
            status_code=403,
            detail="Origen o encabezado de solicitud inválido",
            headers={"Cache-Control": "no-store"},
        )

    await service.logout(
        session,
        token=request.cookies.get(SESSION_COOKIE),
    )

    response = Response(
        status_code=204,
        headers={"Cache-Control": "no-store"},
    )
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response