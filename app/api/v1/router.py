from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.catalog.router import router as catalog_router
from app.modules.scraper.router import router as scrape_router
from app.modules.saved_offers.router import router as saved_offers_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(catalog_router)
api_router.include_router(scrape_router)
api_router.include_router(saved_offers_router)

