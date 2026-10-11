import asyncio
import logging

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import CAREERS_PATH, Settings, get_settings

logger = logging.getLogger(__name__)


def _retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500
    return False


class SiiaaClient:
    def __init__(
        self,
        settings: Settings | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http = http
        self._owns_client = http is None
        self._semaphore = asyncio.Semaphore(self.settings.scrape_concurrency)

    async def __aenter__(self) -> "SiiaaClient":
        if self._http is None:
            timeout = httpx.Timeout(self.settings.scrape_timeout_seconds, connect=15.0)
            self._http = httpx.AsyncClient(
                base_url=self.settings.siiaa_base_url,
                timeout=timeout,
                headers={"User-Agent": "pp-backend-scraper/0.1"},
                follow_redirects=True,
            )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._owns_client and self._http is not None:
            await self._http.aclose()

    async def get_careers_html(self) -> str:
        return await self.get_text(CAREERS_PATH)

    async def get_text(self, path: str) -> str:
        return await self._request("GET", path)

    async def post_text(self, path: str, data: dict[str, str]) -> str:
        return await self._request("POST", path, data=data)

    async def _request(self, method: str, path: str, data: dict[str, str] | None = None) -> str:
        async with self._semaphore:
            if self.settings.scrape_delay_seconds > 0:
                await asyncio.sleep(self.settings.scrape_delay_seconds)
            response = await self._send(method, path, data)
            return response.content.decode("latin-1")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception(_retryable),
        reraise=True,
    )
    async def _send(
        self,
        method: str,
        path: str,
        data: dict[str, str] | None,
    ) -> httpx.Response:
        if self._http is None:
            raise RuntimeError("SiiaaClient must be used as an async context manager")
        response = await self._http.request(method, path, data=data)
        response.raise_for_status()
        return response
