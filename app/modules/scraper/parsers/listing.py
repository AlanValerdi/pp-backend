from dataclasses import dataclass

from selectolax.lexbor import LexborHTMLParser

from app.modules.scraper.parsers.htmlutil import cell_text


@dataclass(frozen=True)
class ListingRow:
    folio: str
    programa: str
    tipo: str
    area: str
    perfil_educativo: str
    coordinador: str
    curso_induccion: str
    empresa: str
    v_01: str
    ca: str


def parse_listing(html: str) -> list[ListingRow]:
    tree = LexborHTMLParser(html)
    headers = " ".join(cell_text(node.text(strip=True)).casefold() for node in tree.css("th"))
    if not all(label in headers for label in ("folio", "perfil", "empresa")):
        raise ValueError("Unexpected SIIAA listing page")
    rows: list[ListingRow] = []
    for tr in tree.css("table tbody tr"):
        cells = tr.css("td")
        if len(cells) < 8:
            if cells and cell_text(cells[0].text(strip=True)).isdigit():
                raise ValueError("Offer row has missing columns")
            continue
        form = _perfil_form(tr)
        if form is None:
            if cells and cell_text(cells[0].text(strip=True)).isdigit():
                raise ValueError("Offer row has no detail form")
            continue
        inputs = {
            (node.attributes.get("name") or ""): node.attributes.get("value") or ""
            for node in form.css("input")
        }
        texts = [cell_text(cell.text(strip=True)) for cell in cells]
        folio = texts[0]
        if not folio or not inputs.get("v_01"):
            raise ValueError("Offer row is missing its identifier")
        rows.append(
            ListingRow(
                folio=folio,
                programa=texts[1],
                tipo=texts[2],
                area=texts[3],
                perfil_educativo=texts[4],
                coordinador=texts[5],
                curso_induccion=texts[6],
                empresa=texts[7],
                v_01=inputs.get("v_01", ""),
                ca=inputs.get("ca", ""),
            )
        )
    return rows


def _perfil_form(tr):
    for form in tr.css("form"):
        action = (form.attributes.get("action") or "").upper()
        if "CAR_PROG" in action:
            return form
    return None
