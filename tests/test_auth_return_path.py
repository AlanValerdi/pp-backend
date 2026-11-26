from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from httpx import ASGITransport, AsyncClient
from starlette.middleware.sessions import SessionMiddleware

from app.api.deps import get_session
from app.core.config import get_settings
from app.modules.auth import router as auth_router
from app.modules.auth import service
from app.modules.auth.router import safe_return_path


@pytest.mark.parametrize(
    "value",
    [
        "/facultad/ingenieria-civil/123",
        "/guardados",
        "/facultad/x/y?tab=detalle",
    ],
)
def test_safe_return_path_accepts_relative_paths(value):
    assert safe_return_path(value) == value


@pytest.mark.parametrize(
    "value",
    [
        None,
        "",
        "facultad/x",
        "//evil.com",
        "/\\evil.com",
        "https://evil.com/x",
        "/x\nSet-Cookie: a=b",
        "/" + "a" * 2048,
    ],
)
def test_safe_return_path_rejects_unsafe_values(value):
    assert safe_return_path(value) is None


class FakeGoogle:
    async def authorize_redirect(self, request, redirect_uri):
        return RedirectResponse("https://accounts.google.test/auth", status_code=302)

    async def authorize_access_token(self, request):
        return {"userinfo": {"sub": "1", "email": "a@b.c", "email_verified": True, "name": "A"}}


@pytest.fixture
def auth_app(monkeypatch):
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000")
    get_settings.cache_clear()
    monkeypatch.setattr(
        auth_router, "get_oauth", lambda: SimpleNamespace(create_client=lambda name: FakeGoogle())
    )
    monkeypatch.setattr(
        service,
        "login_verified_google_user",
        AsyncMock(return_value=SimpleNamespace(token="tok", expires_at=None)),
    )
    app = FastAPI()
    app.add_middleware(SessionMiddleware, secret_key="test")
    app.include_router(auth_router.router, prefix="/api/v1")

    async def session_override():
        yield AsyncMock()

    app.dependency_overrides[get_session] = session_override
    yield app
    get_settings.cache_clear()


async def login_then_callback(app, query: str) -> str:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get(f"/api/v1/auth/google/login{query}")
        response = await client.get("/api/v1/auth/google/callback")
    assert response.status_code == 303
    return response.headers["location"]


async def test_callback_returns_to_the_page_that_started_login(auth_app):
    location = await login_then_callback(auth_app, "?next=/facultad/ingenieria-civil/123")
    assert location == "http://localhost:3000/facultad/ingenieria-civil/123"


async def test_callback_ignores_unsafe_next_and_goes_home(auth_app):
    location = await login_then_callback(auth_app, "?next=//evil.com")
    assert location == "http://localhost:3000"


async def test_callback_without_next_goes_home(auth_app):
    location = await login_then_callback(auth_app, "")
    assert location == "http://localhost:3000"
