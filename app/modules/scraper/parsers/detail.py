import re
from dataclasses import dataclass, field

from app.modules.scraper.normalize import (
    as_bool,
    duration_months,
    interview_address,
    offer_kind,
    period_text,
    split_date,
)
from app.modules.scraper.parsers.htmlutil import page_lines

_COMPETENCIES_LABEL = re.compile(
    r"Describa las competencias a desarrollar en las actividades:[\s\S]{0,500}?profesi[oó]n\)",
    re.IGNORECASE,
)


@dataclass
class AreaBlock:
    name: str
    activities: str
    competencies: str


@dataclass
class FacultyRow:
    faculty: str
    perfil: str
    campus: str


@dataclass
class ParsedDetail:
    tipo: str = ""
    program_number: str = ""
    registered_at: str = ""
    registered_at_raw: str = ""
    company: str = ""
    sector: str = ""
    period: str = ""
    revalidated: bool = False
    status: str = ""
    name: str = ""
    program_type: str = ""
    department: str = ""
    start_date: str = ""
    start_date_raw: str = ""
    end_date: str = ""
    end_date_raw: str = ""
    duration_months: int = 0
    supervisor_name: str = ""
    supervisor_position: str = ""
    email: str = ""
    phone: str = ""
    interview_address: str = ""
    work_address: str = ""
    addressee: str = ""
    appointment_position: str = ""
    monthly_stipend: str = ""
    other_support: str = ""
    social_axes: list[str] = field(default_factory=list)
    promotes_entrepreneurship: bool = False
    blocks: list[AreaBlock] = field(default_factory=list)
    faculties: list[FacultyRow] = field(default_factory=list)


def parse_detail(html: str) -> ParsedDetail:
    lines = page_lines(html)
    text = "\n".join(lines)
    detail = ParsedDetail()
    head, marker, rest = _partition(text, r"No\.\s*de\s*programa\s*:")
    kind = _last_kind(head)
    detail.tipo = offer_kind(kind) if kind else ""
    detail.program_number = _field(rest, r"Fecha\s+de\s+registro\s*:")
    rest = _after(rest, r"Fecha\s+de\s+registro\s*:")
    registered_raw = _field(rest, r"Empresa\s+que\s+oferta\s*:")
    detail.registered_at, detail.registered_at_raw = split_date(registered_raw)
    rest = _after(rest, r"Empresa\s+que\s+oferta\s*:")
    detail.company = _one(rest, r"Sector\s+al\s+que\s+pertenece\s*:")
    rest = _after(rest, r"Sector\s+al\s+que\s+pertenece\s*:")
    detail.sector = _one(rest, r"Periodo\s+del\s+programa\s*:")
    rest = _after(rest, r"Periodo\s+del\s+programa\s*:")
    detail.period = period_text(_one(rest, r"Revalidado\s*:"))
    rest = _after(rest, r"Revalidado\s*:")
    detail.revalidated = as_bool(_one(rest, r"Estatus\s*:"))
    rest = _after(rest, r"Estatus\s*:")
    detail.status = _one(rest, r"Datos\s+generales")
    rest = _after(rest, r"Datos\s+generales")
    rest = _after(rest, r"Nombre\s+del\s+Programa\s*:")
    detail.name = _one(rest, r"Tipo\s+de\s+programa\s*:")
    rest = _after(rest, r"Tipo\s+de\s+programa\s*:")
    detail.program_type = _one(rest, r"Área\s+o\s+departamento\s+donde\s+el\s+alumno\s+realizar[aá]")
    rest = _after(rest, r"Área\s+o\s+departamento\s+donde\s+el\s+alumno\s+realizar[aá][^\n]*")
    detail.department = _one(rest, r"Fecha\s+de\s+inicio\s*:")
    rest = _after(rest, r"Fecha\s+de\s+inicio\s*:")
    start_raw = _one(rest, r"Fecha\s+de\s+t[eé]rmino\s*:")
    detail.start_date, detail.start_date_raw = split_date(start_raw)
    rest = _after(rest, r"Fecha\s+de\s+t[eé]rmino\s*:")
    end_raw = _one(rest, r"Duraci[oó]n\s+en\s+meses\s*:")
    detail.end_date, detail.end_date_raw = split_date(end_raw)
    rest = _after(rest, r"Duraci[oó]n\s+en\s+meses\s*:")
    detail.duration_months = duration_months(_one(rest, r"Responsable\s+de\s+los\s+alumnos"))
    rest = _after(rest, r"Nombre\s+del\s+responsable\s+de\s+supervisar[\s\S]{0,240}?dependencia\s*:")
    detail.supervisor_name = _one(rest, r"Puesto\s+o\s+cargo\s+del\s+responsable\s*:")
    rest = _after(rest, r"Puesto\s+o\s+cargo\s+del\s+responsable\s*:")
    detail.supervisor_position = _one(rest, r"Correo\s+electr[oó]nico\s*:")
    rest = _after(rest, r"Correo\s+electr[oó]nico\s*:")
    detail.email = _one(rest, r"Tel[eé]fono\s*:")
    rest = _after(rest, r"Tel[eé]fono\s*:")
    detail.phone = _one(rest, r"Direcci[oó]n\s+donde\s+se\s+presenta\s+el\s+alumno\s+a\s+entrevista\s*:")
    rest = _after(rest, r"Direcci[oó]n\s+donde\s+se\s+presenta\s+el\s+alumno\s+a\s+entrevista\s*:")
    detail.interview_address = interview_address(
        _one(rest, r"Direcci[oó]n\s+donde\s+el\s+alumno\s+estar[aá]\s+f[ií]sicamente\s*:")
    )
    rest = _after(rest, r"Direcci[oó]n\s+donde\s+el\s+alumno\s+estar[aá]\s+f[ií]sicamente\s*:")
    detail.work_address = _one(rest, r"Informaci[oó]n\s+para\s+generar\s+nombramiento")
    rest = _after(
        rest,
        r"Nombre\s+de\s+la\s+persona\s+a\s+qui[eé]n\s+se\s+dirigir[aá]\s+el\s+nombramiento[\s\S]{0,80}?:",
    )
    detail.addressee = _one(rest, r"Cargo\s*:")
    rest = _after(rest, r"Cargo\s*:")
    detail.appointment_position = _one(rest, r"Informaci[oó]n\s+del\s+programa")
    rest = _after(rest, r"Apoyo\s+econ[oó]mico\s+mesual\s*:")
    detail.monthly_stipend = _one(rest, r"Otros\s+apoyos\s*:")
    rest = _after(rest, r"Otros\s+apoyos\s*:")
    detail.other_support = _one(rest, r"Ejes\s+rectores\s+de\s+pertinencia\s+social")
    rest = _after(rest, r"Ejes\s+rectores\s+de\s+pertinencia\s+social[^\n]*")
    axes = _until(rest, r"(?:¿\s*)?el\s+programa\s+promueve\s+la\s+capacidad\s+de\s+emprendimiento")
    detail.social_axes = [
        line
        for line in _lines(axes)
        if line and not re.match(r"¿?\s*el programa\b", line, flags=re.IGNORECASE)
    ]
    rest = _after(rest, r"promueve\s+la\s+capacidad\s+de\s+emprendimiento\??[:.\s]*")
    detail.blocks = _area_blocks(rest)
    if detail.blocks:
        first_line = _lines(rest.split("Actividades a realizar")[0])[0:1]
        if first_line:
            detail.promotes_entrepreneurship = as_bool(first_line[0])
    else:
        detail.promotes_entrepreneurship = as_bool(_one(rest, r"Facultad\s*/\s*Escuela"))
    detail.faculties = _faculties(text)
    if not marker or not detail.program_number.isdigit() or not detail.name or not detail.tipo:
        raise ValueError("Unexpected or incomplete SIIAA detail page")
    return detail


def _area_blocks(tail: str) -> list[AreaBlock]:
    parts = re.split(
        r"Actividades\s+a\s+realizar\s+por\s+el\s+prestador\s*:?",
        tail,
        flags=re.IGNORECASE,
    )
    if len(parts) < 2:
        return []
    blocks: list[AreaBlock] = []
    previous = parts[0]
    body_parts = parts[1:]
    for index, part in enumerate(body_parts):
        name = _area_name(previous)
        is_last = index == len(body_parts) - 1
        competencies_match = _COMPETENCIES_LABEL.search(part)
        if competencies_match is None:
            activities = _until(part, r"Facultad\s*/\s*Escuela")
            competencies = ""
            previous = ""
        else:
            activities = part[: competencies_match.start()]
            after = part[competencies_match.end() :]
            competencies = _until(after, r"Facultad\s*/\s*Escuela")
            previous = "" if is_last else _trailing_area_name(competencies)
            if previous:
                competencies = competencies[: competencies.rfind(previous)].rstrip()
        faculty_cut = re.search(r"Facultad\s*/\s*Escuela", activities, flags=re.IGNORECASE)
        if faculty_cut:
            activities = activities[: faculty_cut.start()]
        blocks.append(
            AreaBlock(
                name=name,
                activities=_block_text(activities),
                competencies=_block_text(competencies),
            )
        )
    return [block for block in blocks if block.name or block.activities]


def _area_name(chunk: str) -> str:
    lines = _lines(chunk)
    content = [line for line in lines if not _is_bool_line(line)]
    return content[-1] if content else ""


def _trailing_area_name(competencies: str) -> str:
    lines = _lines(competencies)
    if len(lines) < 2:
        return ""
    candidate = lines[-1]
    if len(candidate) > 80:
        return ""
    return candidate


def _faculties(text: str) -> list[FacultyRow]:
    marker = re.search(r"Prestadores\s+solicitados", text, flags=re.IGNORECASE)
    if marker is None:
        return []
    tail = text[marker.end() :]
    tail = re.split(r"Diseño y desarrollo|Copyright|DCYTIC", tail, maxsplit=1, flags=re.IGNORECASE)[0]
    lines = _lines(tail)
    rows: list[FacultyRow] = []
    index = 0
    while index + 4 < len(lines):
        faculty, perfil, cve, campus, count = lines[index : index + 5]
        if re.fullmatch(r"\d+", cve) and re.fullmatch(r"\d+", count):
            rows.append(FacultyRow(faculty=faculty, perfil=perfil, campus=campus))
            index += 5
        else:
            index += 1
    return rows


def _last_kind(head: str) -> str:
    matches = list(re.finditer(r"servicio social|pr[aá]ctica profesional", head, flags=re.IGNORECASE))
    return matches[-1].group(0) if matches else ""


def _partition(text: str, pattern: str) -> tuple[str, str, str]:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        return text, "", ""
    return text[: match.start()], match.group(0), text[match.end() :]


def _after(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        return ""
    return text[match.end() :]


def _until(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        return text
    return text[: match.start()]


def _field(text: str, end_pattern: str) -> str:
    return _one(text, end_pattern)


def _one(text: str, end_pattern: str) -> str:
    return _inline(_until(text, end_pattern))


def _inline(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" \n:-")


def _lines(value: str) -> list[str]:
    return [re.sub(r"\s+", " ", line).strip() for line in value.splitlines() if line.strip()]


def _block_text(value: str) -> str:
    return "\n".join(_lines(_until(value, r"Facultad\s*/\s*Escuela")))


def _is_bool_line(value: str) -> bool:
    return re.fullmatch(r"s[ií]|no", value.strip(), flags=re.IGNORECASE) is not None
