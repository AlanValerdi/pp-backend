import logging

from app.modules.catalog.schemas import ProgramLevel, Section
from app.modules.scraper.normalize import fold

logger = logging.getLogger(__name__)

SECTIONS: list[Section] = [
    Section(id="ingenierias", name="Ingenierías", order=1),
    Section(id="licenciaturas", name="Licenciaturas", order=2),
    Section(id="salud", name="Área de la salud", order=3),
    Section(id="economia", name="Economía y administración", order=4),
]

SALUD = {
    "biomedicina",
    "ciencia forense",
    "estomatologia",
    "farmacia",
    "medicina",
    "medicina veterinaria y zootecnia",
    "nutricion",
    "nutricion clinica",
    "enfermeria",
    "quimico farmacobiologo",
    "readaptacion y activacion fisica",
}

ECONOMIA = {
    "administracion de empresas",
    "administracion publica y ciencias politicas",
    "administracion publica y gestion para el desarrollo",
    "administracion turistica",
    "administracion y direccion de pymes",
    "comercio internacional",
    "contaduria publica",
    "contaduria y finanzas publicas",
    "direccion financiera",
    "economia",
    "finanzas",
    "gastronomia",
    "innovacion emprendedora",
    "mercadotecnia y medios digitales",
    "negocios internacionales",
}

KNOWN_LICENCIATURAS = {
    "actuaria",
    "antropologia",
    "arquitectura",
    "arte digital",
    "arte dramatico",
    "artes plasticas",
    "biologia",
    "ciencias politicas",
    "cinematografia",
    "comunicacion",
    "consultoria juridica",
    "criminologia",
    "cultura fisica",
    "danza moderna y clasica",
    "derecho",
    "diseno grafico",
    "electronica",
    "ensenanza del frances",
    "ensenanza del ingles",
    "etnocoreologia",
    "fauna silvestre",
    "filosofia",
    "fisica y fisica aplicada",
    "gestion de ciudades inteligentes",
    "gestion de la informacion",
    "gestion territorial e identidad biocultural",
    "historia",
    "humanidades",
    "linguistica y literatura hispanica",
    "matematicas y matematicas aplicadas",
    "musica",
    "periodismo",
    "procesos educativos",
    "psicologia",
    "quimica",
    "relaciones internacionales",
    "sociologia",
    "urbanismo",
    "ciencias de la computacion",
}

_FACULTIES: list[tuple[str, str, tuple[str, ...]]] = [
    ("fcfm", "Facultad de Ciencias Físico Matemáticas", ("fisico matem", "cs fisico")),
    ("fcc", "Facultad de Ciencias de la Computación", ("ciencias de la computacion", "cs de la computacion")),
    ("fiq", "Facultad de Ingeniería Química", ("ingenieria quimica",)),
    ("fmed", "Facultad de Medicina", ("facultad de medicina",)),
    ("fenf", "Facultad de Enfermería", ("enfermeria",)),
    ("fce", "Facultad de Economía", ("facultad de economia",)),
    ("fca", "Facultad de Contaduría Pública", ("contaduria",)),
]

UNKNOWN_FACULTY_ID = "sin-facultad"
UNKNOWN_FACULTY_NAME = "Sin facultad"


def section_for(level: ProgramLevel, name: str) -> str:
    key = fold(name)
    if key in SALUD:
        return "salud"
    if level == "Ing":
        return "ingenierias"
    if key in ECONOMIA:
        return "economia"
    if key not in KNOWN_LICENCIATURAS and level == "Lic":
        logger.warning("carrera sin mapa de seccion, se usa licenciaturas: %s", name)
    return "licenciaturas"


def known_unprefixed(name: str) -> bool:
    key = fold(name)
    return key in SALUD or key in ECONOMIA or key in KNOWN_LICENCIATURAS


def faculty_identity(raw: str) -> tuple[str, str]:
    key = fold(raw)
    for faculty_id, canonical, needles in _FACULTIES:
        if any(needle in key for needle in needles):
            return faculty_id, canonical
    faculty_id = slugify_faculty(key)
    return faculty_id, title_faculty(raw)


def looks_official(raw: str) -> bool:
    key = fold(raw)
    return "facultad" in key or "escuela" in key


def slugify_faculty(key: str) -> str:
    from app.modules.scraper.normalize import slugify

    return slugify(key)[:48] or UNKNOWN_FACULTY_ID


def title_faculty(raw: str) -> str:
    from app.modules.scraper.normalize import title_es

    return title_es(raw)
