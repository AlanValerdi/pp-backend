from pathlib import Path

import pytest

from app.modules.scraper.parsers import parse_careers, parse_detail, parse_listing
from app.modules.scraper.parsers.listing import ListingRow
from app.modules.scraper.service import ScraperService

FIXTURES = Path(__file__).parent / "fixtures"


def test_careers_page_lists_every_program() -> None:
    careers = parse_careers((FIXTURES / "careers.html").read_text(encoding="utf-8"))
    assert len(careers) == 86
    assert careers[0].name == "ACTUARÍA"
    assert careers[0].un == "0FB43CD29E3E98C8"
    computing = next(item for item in careers if "COMPUTACIÓN" in item.name)
    assert computing.name == "LIC./ING. EN CIENCIAS DE LA COMPUTACIÓN"


def test_listing_page_reads_offer_rows() -> None:
    rows = parse_listing((FIXTURES / "listing.html").read_text(encoding="utf-8"))
    assert len(rows) == 117
    first = rows[0]
    assert first.folio == "246834"
    assert first.tipo == "Servicio Social"
    assert first.perfil_educativo == "Lic. en Actuaría"
    assert first.curso_induccion == "Curso(s)"
    assert first.empresa == "DIRECCION DE SERVICIO SOCIAL"
    assert first.v_01


def test_detail_page_matches_the_catalog_contract() -> None:
    detail = parse_detail((FIXTURES / "detail.html").read_text(encoding="utf-8"))
    assert detail.tipo == "practica_profesional"
    assert detail.program_number == "246965"
    assert detail.registered_at == "2026-09-01"
    assert detail.registered_at_raw == "01/09/26"
    assert detail.company.startswith("J.V. ABASTECEDORA")
    assert detail.sector == "PRIVADO"
    assert detail.period == "1, 2027"
    assert detail.revalidated is False
    assert detail.status == "ACEPTADO"
    assert detail.name == "PRACTICANTE DE COMPRAS"
    assert detail.program_type == "MULTIDISCIPLINARIO"
    assert detail.department == "FINANZAS"
    assert detail.start_date == "2027-01-05"
    assert detail.end_date == "2027-04-05"
    assert detail.duration_months == 3
    assert detail.supervisor_name == "GERARDO CUAUTLE MONTES"
    assert detail.email == "gerardo.c@jvmontacargas.com.mx"
    assert detail.monthly_stipend == "$1,200.00"
    assert detail.other_support == "Cursos de SAP"
    assert detail.social_axes == ["Empleo justo y bien remunerado", "Innovación"]
    assert detail.promotes_entrepreneurship is True
    assert detail.blocks[0].name == "ACTUARÍA"
    assert "SAP" in detail.blocks[0].activities
    assert "Trabajo en Equipo" in detail.blocks[0].competencies
    assert detail.faculties[0].faculty == "Facultad Cs Fisico Matematicas"


def test_same_folio_is_stored_once_and_linked_to_both_levels() -> None:
    row = ListingRow(
        folio="24018",
        programa="Desarrollo",
        tipo="Práctica Profesional",
        area="Lic. / Ing.",
        perfil_educativo="Lic. en Ciencias de la Computación",
        coordinador="Coordinación",
        curso_induccion="Curso(s)",
        empresa="FCC",
        v_01="abc",
        ca="def",
    )
    ing = ListingRow(
        folio="24018",
        programa="Desarrollo",
        tipo="Práctica Profesional",
        area="Lic. / Ing.",
        perfil_educativo="Ing. en Ciencias de la Computación",
        coordinador="Coordinación",
        curso_induccion="Curso(s)",
        empresa="FCC",
        v_01="xyz",
        ca="def",
    )
    service = ScraperService(client=None)  # type: ignore[arg-type]
    areas: dict = {}
    offers: dict = {}
    service._absorb_career("LIC./ING. EN CIENCIAS DE LA COMPUTACIÓN", [row, ing], areas, offers)
    assert len(areas) == 2
    assert len(offers) == 1
    assert len(offers["24018"].fetches) == 2
    assert offers["24018"].listing.area == "Lic. / Ing."
    assert offers["24018"].listing.tipo == "practica_profesional"


@pytest.mark.parametrize("parser", [parse_careers, parse_listing, parse_detail])
def test_unexpected_source_page_is_rejected(parser) -> None:
    with pytest.raises(ValueError):
        parser("<html><body>Please log in</body></html>")


def test_legitimate_empty_listing() -> None:
    html = "<table><thead><tr><th>Folio</th><th>Perfil educativo</th><th>Empresa</th></tr></thead>"
    assert parse_listing(html + "<tbody></tbody></table>") == []


def test_offer_row_missing_detail_form_is_rejected() -> None:
    html = "<table><thead><tr><th>Folio</th><th>Perfil educativo</th><th>Empresa</th></tr></thead>"
    html += "<tbody><tr><td>123</td>" + "<td>x</td>" * 7 + "</tr></tbody></table>"
    with pytest.raises(ValueError):
        parse_listing(html)
