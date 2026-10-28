from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.db import engine
from app.core.logging import configure_logging
from app.modules.catalog.router import health_router
from app.modules.scraper.jobs import ScrapeJobs

from starlette.middleware.sessions import SessionMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    try:
        yield
    finally:
        await app.state.scrape_jobs.close()
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="pp-backend", version="0.1.0", lifespan=lifespan)

    if not settings.oauth_session_secret:
        raise RuntimeError("Falta configurar OAUTH_SESSION_SECRET")

    app.state.scrape_jobs = ScrapeJobs()

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.oauth_session_secret,
        session_cookie="pp_oauth",
        max_age=600,
        same_site="lax",
        https_only=settings.cookie_secure,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()

