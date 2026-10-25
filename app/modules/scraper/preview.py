import asyncio
import logging
from time import monotonic
from typing import Literal
from urllib.parse import urljoin
from uuid import uuid4

import httpx
from pydantic import Field

from app.core.config import CAREERS_PATH, Settings, get_settings
from app.modules.catalog.schemas import APIModel, Offer
from app.modules.scraper.parsers import parse_careers, parse_detail, parse_listing
from app.modules.scraper.service import AreaDraft, OfferDraft, ScraperService, _finalize
from app.modules.scraper.tracing import event, trace_scope

logger = logging.getLogger(__name__)


class PreviewRequest(APIModel):
    stage: Literal["careers", "listing", "detail"]
    url: str
    parameters: dict[str, str] = Field(default_factory=dict)
    http_status: int | None = None
    duration_seconds: float = 0
    error: str | None = None
    response_excerpt: str | None = None


class PreviewRead(APIModel):
    status: Literal["succeeded", "partial", "failed"] = "failed"
    request_count: int = 0
    detail_attempts: int = 0
    successful_parses: int = 0
    failures: int = 0
    duration_seconds: float = 0
    stop_reason: str = ""
    offers: list[Offer] = Field(default_factory=list)
    requests: list[PreviewRequest] = Field(default_factory=list)


class ScrapePreview:
    """Bounded, sequential diagnostic collection; never publishes a catalog."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._last_start: float | None = None
        self.result = PreviewRead()
        self.areas: dict[tuple[str, str], AreaDraft] = {}
        self.offers: dict[str, OfferDraft] = {}
        self.successful_offers: set[str] = set()

    async def run(self) -> PreviewRead:
        with trace_scope(f"preview-{uuid4().hex}"):
            event(logger, "preview_started", detail_limit=10)
            try:
                return await self._run()
            except BaseException as exc:
                event(
                    logger,
                    "preview_cancelled" if isinstance(exc, asyncio.CancelledError) else "preview_failed",
                    logging.ERROR,
                    error_type=type(exc).__name__,
                )
                raise

    async def _run(self) -> PreviewRead:
        started = monotonic()
        try:
            async with (
                asyncio.timeout(120),
                httpx.AsyncClient(
                    base_url=self.settings.siiaa_base_url,
                    timeout=httpx.Timeout(15),
                    follow_redirects=False,
                    headers={"User-Agent": "pp-backend-scraper/0.1"},
                ) as http,
            ):
                await self._collect(http)
        except TimeoutError:
            self.result.stop_reason = "overall_deadline"
        self.result.offers = [
            _finalize(offer) for key, offer in self.offers.items() if key in self.successful_offers
        ]
        self.result.failures = sum(item.error is not None for item in self.result.requests)
        self.result.request_count = len(self.result.requests)
        self.result.duration_seconds = round(monotonic() - started, 3)
        if self.result.successful_parses:
            self.result.status = (
                "succeeded"
                if self.result.detail_attempts == 10
                and not self.result.failures
                and self.result.stop_reason == "detail_limit"
                else "partial"
            )
        event(
            logger,
            "preview_completed",
            status=self.result.status,
            stop_reason=self.result.stop_reason,
            requests=self.result.request_count,
            parsed=self.result.successful_parses,
            failed=self.result.failures,
            offers=len(self.result.offers),
            duration_seconds=self.result.duration_seconds,
        )
        return self.result

    async def _fetch(self, http, stage, path, parameters=None):
        if self._last_start is not None:
            await asyncio.sleep(max(0, 1 - (monotonic() - self._last_start)))
        started = self._last_start = monotonic()
        diagnostic = PreviewRequest(
            stage=stage, url=urljoin(self.settings.siiaa_base_url, path), parameters=parameters or {}
        )
        self.result.requests.append(diagnostic)
        if stage == "detail":
            self.result.detail_attempts += 1
        event(logger, "preview_fetch_started", stage=stage, path=path)
        try:
            response = await http.request("POST" if parameters is not None else "GET", path, data=parameters)
            diagnostic.http_status = response.status_code
            event(
                logger,
                "preview_fetched",
                stage=stage,
                path=path,
                http_status=response.status_code,
                bytes=len(response.content),
                duration_seconds=round(monotonic() - started, 3),
            )
            if not 200 <= response.status_code < 300:
                response.raise_for_status()
            return response.content.decode("latin-1"), diagnostic
        except httpx.HTTPError as exc:
            # Avoid exception strings containing headers, credentials, or redirect URLs.
            diagnostic.error = type(exc).__name__
            event(logger, "preview_fetch_failed", logging.ERROR, stage=stage, error_type=type(exc).__name__)
            return None, diagnostic
        except asyncio.CancelledError:
            diagnostic.error = "Request cancelled or overall deadline reached"
            raise
        finally:
            diagnostic.duration_seconds = round(monotonic() - started, 3)

    @staticmethod
    def _parse(parser, html, diagnostic):
        try:
            result = parser(html)
            event(logger, "preview_parsed", stage=diagnostic.stage)
            return result
        except ValueError as exc:
            diagnostic.error = str(exc)
            diagnostic.response_excerpt = html[:500]
            event(
                logger, "preview_parse_failed", logging.ERROR, stage=diagnostic.stage, error_type="ValueError"
            )
            return None

    async def _collect(self, http: httpx.AsyncClient) -> None:
        html, diagnostic = await self._fetch(http, "careers", CAREERS_PATH)
        careers = self._parse(parse_careers, html, diagnostic) if html is not None else None
        if careers is None:
            self.result.stop_reason = "careers_failed"
            return
        service = ScraperService(client=None)  # type: ignore[arg-type]
        selected: list[tuple[OfferDraft, str, str, str, str]] = []
        for career in careers[:10]:
            html, diagnostic = await self._fetch(
                http, "listing", "Ss_OFERTA_prog", {"un": career.un, "se": career.se}
            )
            rows = self._parse(parse_listing, html, diagnostic) if html is not None else None
            if rows is None:
                continue
            service._absorb_career(career.name, rows, self.areas, self.offers)
            selected = [
                (offer, area_id, v_01, ca, perfil)
                for offer in self.offers.values()
                for area_id, (v_01, ca, perfil) in offer.fetches.items()
            ][:10]
            if len(selected) == 10:
                break
        self.result.stop_reason = "detail_limit" if len(selected) == 10 else "discovery_exhausted"
        for offer, area_id, v_01, ca, perfil in selected:
            event(logger, "preview_sample_started", folio=offer.listing.folio, area_id=area_id)
            html, diagnostic = await self._fetch(
                http, "detail", "Ss_OFERTA_CAR_PROG", {"v_01": v_01, "ca": ca}
            )
            detail = self._parse(parse_detail, html, diagnostic) if html is not None else None
            if detail is None:
                event(
                    logger, "preview_sample_failed", logging.ERROR, folio=offer.listing.folio, area_id=area_id
                )
                continue
            service._apply_detail(offer, area_id, perfil, detail, self.areas)
            self.successful_offers.add(offer.listing.folio)
            self.result.successful_parses += 1
            event(logger, "preview_sample_normalized", folio=offer.listing.folio, area_id=area_id)
