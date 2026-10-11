import httpx
import respx

from app.core.config import Settings
from app.modules.scraper.client import SiiaaClient


@respx.mock
async def test_client_posts_form_and_decodes_latin1() -> None:
    route = respx.post("http://siiaa.test/Ss_OFERTA_prog").respond(content="Actuaría".encode("latin-1"))
    settings = Settings(
        siiaa_base_url="http://siiaa.test/",
        scrape_concurrency=1,
        scrape_delay_seconds=0,
        scrape_timeout_seconds=5,
    )
    async with SiiaaClient(settings=settings) as client:
        text = await client.post_text("Ss_OFERTA_prog", {"un": "1", "se": "2"})
    assert text == "Actuaría"
    assert route.called
    body = route.calls[0].request.content.decode()
    assert "un=1" in body
    assert "se=2" in body


@respx.mock
async def test_client_retries_server_errors() -> None:
    route = respx.get("http://siiaa.test/ss_oferta_ss").mock(
        side_effect=[
            httpx.Response(503, text="no"),
            httpx.Response(200, content=b"ok"),
        ]
    )
    settings = Settings(
        siiaa_base_url="http://siiaa.test/",
        scrape_concurrency=1,
        scrape_delay_seconds=0,
        scrape_timeout_seconds=5,
    )
    async with SiiaaClient(settings=settings) as client:
        text = await client.get_text("ss_oferta_ss")
    assert text == "ok"
    assert route.call_count == 2
