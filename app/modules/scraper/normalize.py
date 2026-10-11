import re
import unicodedata
import uuid
from datetime import date

from app.modules.catalog.schemas import OfferKind, ProgramLevel

NAMESPACE = uuid.UUID("6f0c2a1e-9b4d-4e3a-8c1f-5d7a9b2e4c60")

_SMALL_WORDS = {"de", "del", "la", "las", "los", "y", "e", "en", "para", "por", "a", "o", "u"}
_CAREER_RE = re.compile(
    r"""^
    (?:
        (?P<dual>LIC\.?\s*/\s*ING(?:ENIER[IÍ]A)?)
        |
        (?P<level>LIC(?:ENCIATURA)?|ING(?:ENIER[IÍ]A)?)
    )
    \.?
    \s*
    (?P<en>EN\s+)?
    (?P<rest>.+?)
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)
_DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{2,4})")


def fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"\s+", " ", stripped).strip().lower()


def slugify(value: str) -> str:
    folded = fold(value)
    slug = re.sub(r"[^a-z0-9]+", "-", folded).strip("-")
    return slug or "carrera"


def title_es(value: str) -> str:
    words = re.sub(r"\s+", " ", value).strip().split(" ")
    titled: list[str] = []
    for index, word in enumerate(words):
        lower = word.lower()
        if index > 0 and lower in _SMALL_WORDS:
            titled.append(lower)
        else:
            titled.append(lower.capitalize())
    return " ".join(titled)


def area_uuid(level: str, name: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"area:{level}:{fold(name)}"))


def offer_uuid(folio: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"offer:{folio.strip()}"))


def offer_kind(value: str) -> OfferKind:
    key = fold(value)
    if "practic" in key:
        return "practica_profesional"
    return "servicio_social"


def as_bool(value: str) -> bool:
    key = fold(value).strip(" .:;")
    return key in {"si", "yes", "true", "1", "s"}


def period_text(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    return re.sub(r"\s*,\s*", ", ", compact)


def duration_months(value: str) -> int:
    match = re.search(r"\d+", value)
    return int(match.group()) if match else 0


def split_date(value: str) -> tuple[str, str]:
    raw = re.sub(r"\s+", " ", value).strip()
    match = _DATE_RE.search(raw)
    if match is None:
        return "", raw
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    shown = match.group(0)
    if year < 100:
        year += 2000 if year < 70 else 1900
    try:
        iso = date(year, month, day).isoformat()
    except ValueError:
        return "", shown
    return iso, shown


def interview_address(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    key = fold(cleaned)
    if "correo" in key and len(cleaned) < 48:
        return "via correo"
    return cleaned


def levels_in_text(value: str) -> list[ProgramLevel]:
    key = fold(value)
    has_ing = bool(re.search(r"\bing\b|ingenier", key))
    has_lic = bool(re.search(r"\blic\b|licenciatura", key))
    levels: list[ProgramLevel] = []
    if has_lic:
        levels.append("Lic")
    if has_ing:
        levels.append("Ing")
    return levels


class ParsedArea:
    def __init__(self, level: ProgramLevel, name: str, raw_name: str, has_en: bool) -> None:
        self.level = level
        self.name = name
        self.raw_name = raw_name
        self.has_en = has_en

    @property
    def slug(self) -> str:
        if self.level == "Ing":
            if self.has_en:
                return f"ingenieria-en-{slugify(self.name)}"
            return slugify(self.raw_name.replace("Ing.", "Ingeniería"))
        return slugify(self.name)


def parse_career_name(raw: str) -> list[ParsedArea]:
    match = _CAREER_RE.match(re.sub(r"\s+", " ", raw).strip())
    if match is None:
        return []
    rest = title_es(match.group("rest"))
    has_en = bool(match.group("en"))
    if match.group("dual"):
        return [_area("Lic", rest, has_en), _area("Ing", rest, has_en)]
    level: ProgramLevel = "Ing" if fold(match.group("level")).startswith("ing") else "Lic"
    return [_area(level, rest, has_en)]


def unprefixed_area(level: ProgramLevel, career_name: str) -> ParsedArea:
    name = title_es(career_name)
    return _area(level, name, has_en=True)


def _area(level: ProgramLevel, name: str, has_en: bool) -> ParsedArea:
    prefix = "Ing." if level == "Ing" else "Lic."
    if has_en:
        raw_name = f"{prefix} en {name}"
        display = name
    elif level == "Ing":
        raw_name = f"{prefix} {name}"
        display = f"Ingeniería {name}"
    else:
        raw_name = f"{prefix} {name}"
        display = name
    return ParsedArea(level=level, name=display, raw_name=raw_name, has_en=has_en)
