from functools import lru_cache

from authlib.integrations.starlette_client import OAuth

from app.core.config import get_settings


@lru_cache
def get_oauth() -> OAuth:
    settings = get_settings()

    if not settings.google_client_id or not settings.google_client_secret:
        raise RuntimeError("Faltan las credenciales OAuth de Google")

    oauth = OAuth()

    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url=(
            "https://accounts.google.com/.well-known/openid-configuration"
        ),
        client_kwargs={
            "scope": "openid email profile",
            "code_challenge_method": "S256",
        },
    )

    return oauth