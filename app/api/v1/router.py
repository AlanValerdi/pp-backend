from fastapi import APIRouter

from app.modules.catalog.router import router as catalog_router
from app.modules.scraper.router import router as scrape_router

api_router = APIRouter()
api_router.include_router(catalog_router)
api_router.include_router(scrape_router)
