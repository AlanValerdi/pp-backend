import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Self

import httpx

from app.core.config import get_settings

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "PPracticaSS-geocoder/1.0"
MIN_INTERVAL_SECONDS = 1.0


class NominatimClient:
    """Minimal Nominatim client honoring the public usage policy (1 req/s, identifying UA)."""

    def __init__(
        self,
        *,
        contact: str | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        clock: Callable[[], float] = time.monotonic,
        timeout: float = 20.0,
    ) -> None:
        contact = get_settings().geocoder_contact_email if contact is None else contact
        user_agent = f"{USER_AGENT} ({contact})" if contact else USER_AGENT
        self._http = httpx.AsyncClient(headers={"User-Agent": user_agent}, timeout=timeout)
        self._sleep = sleep
        self._clock = clock
        self._last_call: float | None = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._http.aclose()

    async def _throttle(self) -> None:
        if self._last_call is not None:
            wait = MIN_INTERVAL_SECONDS - (self._clock() - self._last_call)
            if wait > 0:
                await self._sleep(wait)
        self._last_call = self._clock()

    async def geocode(self, query: str) -> tuple[float, float] | None:
        return await self._search({"q": query})

    async def geocode_postal_code(self, postal_code: str, state: str) -> tuple[float, float] | None:
        """Structured search by postal code (approximate location)."""
        return await self._search({"postalcode": postal_code, "state": state, "country": "Mexico"})

    async def _search(self, query: dict[str, str]) -> tuple[float, float] | None:
        await self._throttle()
        response = await self._http.get(
            NOMINATIM_URL,
            params={**query, "format": "jsonv2", "limit": 1, "countrycodes": "mx"},
        )
        response.raise_for_status()
        results = response.json()
        if not results:
            return None
        return float(results[0]["lat"]), float(results[0]["lon"])
