from dataclasses import dataclass

from selectolax.lexbor import LexborHTMLParser

from app.modules.scraper.parsers.htmlutil import cell_text


@dataclass(frozen=True)
class CareerLink:
    name: str
    un: str
    se: str


def parse_careers(html: str) -> list[CareerLink]:
    tree = LexborHTMLParser(html)
    careers: list[CareerLink] = []
    for form in tree.css("form"):
        action = (form.attributes.get("action") or "").lower()
        if "oferta_prog" not in action or "car_prog" in action:
            continue
        inputs = {
            (node.attributes.get("name") or ""): node.attributes.get("value") or ""
            for node in form.css("input")
        }
        button = form.css_first("button")
        name = cell_text(button.text(strip=True) if button is not None else "")
        if not name or not inputs.get("un"):
            continue
        careers.append(CareerLink(name=name, un=inputs["un"], se=inputs.get("se", "")))
    if not careers:
        raise ValueError("SIIAA careers page contains no program forms")
    return careers
