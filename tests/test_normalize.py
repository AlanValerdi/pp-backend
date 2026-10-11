from app.modules.scraper.classification import faculty_identity, section_for
from app.modules.scraper.normalize import (
    area_uuid,
    as_bool,
    duration_months,
    interview_address,
    offer_uuid,
    parse_career_name,
    period_text,
    split_date,
)
from app.modules.scraper.service import _target_levels


def test_dual_career_splits_into_two_areas() -> None:
    parsed = parse_career_name("LIC./ING. EN CIENCIAS DE LA COMPUTACIÓN")
    assert [(item.level, item.name, item.slug) for item in parsed] == [
        ("Lic", "Ciencias de la Computación", "ciencias-de-la-computacion"),
        ("Ing", "Ciencias de la Computación", "ingenieria-en-ciencias-de-la-computacion"),
    ]
    assert parsed[0].raw_name == "Lic. en Ciencias de la Computación"
    assert parsed[1].raw_name == "Ing. en Ciencias de la Computación"


def test_engineering_without_en_expands_the_name() -> None:
    parsed = parse_career_name("ING. INDUSTRIAL")
    assert parsed[0].level == "Ing"
    assert parsed[0].name == "Ingeniería Industrial"
    assert parsed[0].slug == "ingenieria-industrial"
    assert parsed[0].raw_name == "Ing. Industrial"


def test_unprefixed_career_is_not_parsed_as_a_level() -> None:
    assert parse_career_name("ACTUARÍA") == []


def test_dates_bools_period_and_duration() -> None:
    assert split_date("01/09/26") == ("2026-09-01", "01/09/26")
    assert split_date("05/01/27") == ("2027-01-05", "05/01/27")
    assert as_bool("si") is True
    assert as_bool("Sí") is True
    assert as_bool("") is False
    assert period_text("1 , 2027") == "1, 2027"
    assert duration_months("3 Meses") == 3
    assert interview_address("vía correo") == "via correo"
    assert interview_address("PROLONGACIÓN VICTORIA 93") == "PROLONGACIÓN VICTORIA 93"


def test_ids_are_stable() -> None:
    assert area_uuid("Lic", "Actuaría") == area_uuid("Lic", "actuaría")
    assert area_uuid("Lic", "Actuaría") != area_uuid("Ing", "Actuaría")
    assert offer_uuid("246965") == offer_uuid("246965")


def test_section_and_faculty_maps() -> None:
    assert section_for("Ing", "Ingeniería Industrial") == "ingenierias"
    assert section_for("Lic", "Actuaría") == "licenciaturas"
    assert section_for("Lic", "Nutrición Clínica") == "salud"
    assert section_for("Lic", "Administración de Empresas") == "economia"
    faculty_id, name = faculty_identity("Facultad Cs Fisico Matematicas")
    assert faculty_id == "fcfm"
    assert name == "Facultad de Ciencias Físico Matemáticas"


def test_perfil_picks_level_on_a_dual_career() -> None:
    assert _target_levels("Ing Ciencias Computación", ["Lic", "Ing"]) == ["Ing"]
    assert _target_levels("Ciencias de la Computación", ["Lic", "Ing"]) == ["Lic"]
    assert _target_levels("Lic. / Ing. en Ciencias de la Computación", ["Lic", "Ing"]) == [
        "Lic",
        "Ing",
    ]
