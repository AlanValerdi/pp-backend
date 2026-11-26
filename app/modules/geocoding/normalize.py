import re
import unicodedata

DEFAULT_REGION = "Puebla, México"
_VIRTUAL_MARKERS = ("virtual", "en linea", "remoto")
_REGION_MARKERS = ("puebla", "mexico", "cdmx", "tlaxcala", "veracruz", "oaxaca", "hidalgo", "morelos")


def _strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_address(value: str) -> str:
    """Canonical cache key: lowercase, no accents, tidy spacing around commas."""
    text = _strip_accents(value).lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    return text.strip(" ,.;")


def is_virtual(value: str) -> bool:
    key = normalize_address(value)
    return not key or any(marker in key for marker in _VIRTUAL_MARKERS)


def geocoding_query(raw_address: str) -> str:
    """Query sent to the geocoder; adds the default region when no state is mentioned."""
    key = normalize_address(raw_address)
    if any(re.search(rf"\b{marker}\b", key) for marker in _REGION_MARKERS):
        return raw_address.strip()
    return f"{raw_address.strip()}, {DEFAULT_REGION}"


_POSTAL_WITH_MARKER = re.compile(r"\bc\.?\s*p\.?\s*:?\s*(\d{5})(?!\d)")
_POSTAL_BARE = re.compile(r"(?<!\d)(\d{5})(?!\d)")
_CDMX_MARKERS = ("cdmx", "ciudad de mexico", "distrito federal", "d.f.")


def extract_postal_code(raw_address: str) -> str | None:
    """Return a 5-digit Mexican postal code, preferring one introduced by CP / C.P."""
    key = normalize_address(raw_address)
    match = _POSTAL_WITH_MARKER.search(key) or _POSTAL_BARE.search(key)
    return match.group(1) if match else None


def infer_state(raw_address: str) -> str:
    key = normalize_address(raw_address)
    if any(marker in key for marker in _CDMX_MARKERS):
        return "Ciudad de México"
    return "Puebla"
