from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

from app.modules.catalog.models import OfferAreaRow, OfferRow
from app.modules.catalog.repository import _offer_values, offers_for_area
from app.modules.catalog.schemas import Catalog
from app.modules.scraper.parsers.listing import parse_listing
from app.modules.scraper.service import ScraperService

FIXTURES = Path(__file__).parent / "fixtures"


def test_shared_folio_preserves_each_source_listing_without_details():
    row = parse_listing((FIXTURES / "listing.html").read_text())[0]
    service = ScraperService(None)
    areas, offers = {}, {}
    service._absorb_career("LIC. EN ACTUARÍA", [row], areas, offers)
    drama = replace(row, perfil_educativo="Lic. en Arte Dramático", coordinador="Drama coordinator")
    service._absorb_career("LIC. EN ARTE DRAMÁTICO", [drama], areas, offers)
    assert len(offers) == 1
    offer = offers[row.folio]
    for area in areas.values():
        service._ensure_area_detail(offer, area.uuid)
        listing = offer.area_details[area.uuid].listing
        expected = drama if area.name == "Arte Dramático" else row
        assert listing.perfil_educativo == expected.perfil_educativo
        assert listing.coordinador == expected.coordinador


async def test_area_query_uses_relationship_listing_and_safe_legacy_fallback():
    sample = Catalog.model_validate_json((FIXTURES / "catalog.json").read_text())
    offer = sample.offers[0]
    row = OfferRow(uuid=offer.uuid, folio=offer.listing.folio, **_offer_values(offer))
    listing = offer.listing.model_copy(update={"perfil_educativo": "Lic. en Arte Dramático"})
    link = OfferAreaRow(offer_uuid=offer.uuid, area_uuid="drama", listing=listing.model_dump())
    session = AsyncMock()
    session.get.return_value = row
    class Result:
        def all(self):
            return [link]
    session.exec.return_value = Result()
    result = await offers_for_area(session, "drama")
    assert result[0].listing.perfil_educativo == "Lic. en Arte Dramático"
    assert result[0].area_details[0].listing == listing
    assert row.listing_perfil_educativo == offer.listing.perfil_educativo
    link.listing = None
    result = await offers_for_area(session, "drama")
    assert result[0].listing.perfil_educativo == ""
