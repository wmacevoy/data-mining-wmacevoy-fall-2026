"""Stage 2 -- address normalization and the three-valued match decision.

The core idea
-------------
For *matching* two addresses, normalization only has to be CONSISTENT,
not canonical. We never need to know that "RD" is the correct USPS
abbreviation -- we only need "ROAD" and "RD" to collapse to the same
token on both sides. That is a much weaker requirement than real address
standardization, and it lets us avoid an entire class of failure.

Why not just use a parser
-------------------------
`usaddress` mis-parses Mesa County's lettered grid roads:

    "2879 B 1/2 RD"  ->  StreetNamePreDirectional='B', StreetName='1/2'

which is wrong -- the street name is "B 1/2". Numeric grid roads
("26 1/2 RD") parse correctly, lettered ones do not. So we compare
whole normalized *lines* and never ask a parser which token is the
street name. `usaddress` is still useful for classification (PO boxes,
unit designators); we do that with explicit regexes here so the rules
are visible and the pipeline has one dependency instead of three.
"""
import re

# --- canonicalization tables ---------------------------------------------
# Not exhaustive USPS Publication 28 -- just enough to make both sides of a
# comparison agree. Add entries when a spot-check turns up a miss.

STREET_SUFFIXES = {
    "STREET": "ST", "STR": "ST",
    "ROAD": "RD",
    "AVENUE": "AVE", "AV": "AVE",
    "DRIVE": "DR",
    "COURT": "CT",
    "LANE": "LN",
    "CIRCLE": "CIR",
    "PLACE": "PL",
    "BOULEVARD": "BLVD", "BLVD.": "BLVD",
    "PARKWAY": "PKWY", "PKY": "PKWY",
    "TRAIL": "TRL",
    "TERRACE": "TER",
    "HIGHWAY": "HWY",
    "LOOP": "LOOP",
    "POINT": "PT",
    "RIDGE": "RDG",
    "SQUARE": "SQ",
    "VILLAGE": "VLG",
}

DIRECTIONALS = {
    "NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W",
    "NORTHEAST": "NE", "NORTHWEST": "NW",
    "SOUTHEAST": "SE", "SOUTHWEST": "SW",
}

# Unit designators, mapped to a single spelling so "APT 2" == "# 2" == "UNIT 2".
UNIT_WORDS = {
    "APARTMENT": "UNIT", "APT": "UNIT", "UNIT": "UNIT",
    "SUITE": "UNIT", "STE": "UNIT",
    "#": "UNIT", "NO": "UNIT",
    "BUILDING": "BLDG", "BLDG": "BLDG",
    "SPACE": "SPC", "SPC": "SPC",
    "LOT": "LOT", "TRAILER": "TRLR", "TRLR": "TRLR",
    "ROOM": "RM", "RM": "RM", "FLOOR": "FL", "FL": "FL",
}

# Mailing addresses that cannot be compared to a physical location at all.
PO_BOX_RE = re.compile(
    r"\b(?:"
    r"P\.?\s*O\.?\s*BOX"          # PO BOX, P.O. BOX, POBOX
    r"|POST\s+OFFICE\s+BOX"
    r"|GENERAL\s+DELIVERY"
    r"|PMB"                        # private mailbox
    r"|(?:HC|RR|HCR)\s*\d+\s*BOX"  # rural / highway contract routes
    r")\b",
    re.IGNORECASE,
)

UNIT_TAIL_RE = re.compile(
    r"\s+(?P<word>UNIT|BLDG|SPC|LOT|TRLR|RM|FL)\s+(?P<id>[A-Z0-9][A-Z0-9\-]*)\s*$"
)


def is_po_box(text: str) -> bool:
    """True when a mailing address has no physical location to compare."""
    return bool(text) and bool(PO_BOX_RE.search(text))


def normalize_line(text: str) -> str:
    """Collapse an address line to a comparable canonical form.

    Uppercases, strips punctuation, and maps suffix/directional/unit
    synonyms. Deliberately preserves "/" so Grand Valley fractional roads
    ("B 1/2 RD", "26 1/2 RD") survive intact.
    """
    if not text:
        return ""

    text = text.upper()
    text = text.replace("#", " # ")             # "#2" -> "# 2"
    text = re.sub(r"[.,;:]", " ", text)          # drop sentence punctuation
    text = re.sub(r"[^A-Z0-9/#\- ]", " ", text)  # keep / for fractions
    text = re.sub(r"\s+", " ", text).strip()

    tokens = []
    for token in text.split(" "):
        # Order matters little here since the tables are disjoint.
        token = DIRECTIONALS.get(token, token)
        token = STREET_SUFFIXES.get(token, token)
        token = UNIT_WORDS.get(token, token)
        tokens.append(token)

    return " ".join(tokens).strip()


def split_unit(normalized: str):
    """Separate a trailing unit designator from the street portion.

    Returns (street_without_unit, unit_or_empty). Multi-unit parcels often
    have a unit on one side and not the other, so the caller decides how
    much that matters instead of having it baked in.
    """
    match = UNIT_TAIL_RE.search(normalized)
    if not match:
        return normalized, ""
    street = normalized[: match.start()].strip()
    return street, f"{match.group('word')} {match.group('id')}"


def build_situs_line(row: dict) -> str:
    """Assemble the property address from the county's own components.

    The situs side is already parsed, so this is assembly rather than
    parsing. Falls back to the pre-assembled LOCATION field when the
    components are empty.
    """
    parts = [
        row.get("STRNUMBER"), row.get("STRDIR"),
        row.get("STRNAME"), row.get("STRMODE"), row.get("STRUNIT"),
    ]
    line = " ".join(str(p).strip() for p in parts if not _is_missing(p))
    return line if line.strip() else _clean(row.get("LOCATION"))


def zip5(value) -> str:
    """First five digits of a ZIP, or '' if there aren't five."""
    if value is None:
        return ""
    digits = re.sub(r"\D", "", str(value))
    return digits[:5] if len(digits) >= 5 else ""


#: Values that mean "no data" once a JSON null has been through pandas.
#: This bites hard: pandas turns JSON null into float NaN, which is
#: *truthy*, so a naive `if value:` check lets the string "NAN" through and
#: it gets compared as if it were an address.
_MISSING_TOKENS = {"", "NAN", "NONE", "NULL", "<NA>", "NAT"}


def _is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:  # NaN is not equal to itself
        return True
    return str(value).strip().upper() in _MISSING_TOKENS


def _clean(value) -> str:
    return "" if _is_missing(value) else str(value).strip().upper()


# --- the decision ---------------------------------------------------------

# Reason codes. Kept as strings so the output CSV is readable without a
# lookup table, and so new codes don't require a schema migration.
MISSING_MAILING = "missing_mailing"
MISSING_SITUS = "missing_situs"
PO_BOX = "po_box"
STATE_DIFFERS = "state_differs"
ZIP_DIFFERS = "zip_differs"
CITY_DIFFERS = "city_differs"
STREET_DIFFERS = "street_differs"
STREET_MATCH = "street_match"


def decide_match(row: dict) -> dict:
    """Three-valued decision: does the tax bill go to the property itself?

    Returns a dict of new columns. `match` is True / False / None, where
    None means "the data does not support an answer" -- distinct from a
    confident False.

    The ladder checks geography before street text on purpose. Street
    names repeat across towns ("123 MAIN ST" exists everywhere), so a
    street match between different cities is a coincidence, not evidence.
    """
    situs_raw = build_situs_line(row)
    mail_raw = _clean(row.get("MAILING"))

    situs_city, mail_city = _clean(row.get("SITUS_CITY")), _clean(row.get("MAILING_CITY"))
    situs_state = _clean(row.get("SITUS_STATE")) or config_home_state()
    mail_state = _clean(row.get("MAILING_ST"))
    situs_zip, mail_zip = zip5(row.get("SITUS_ZIP")), zip5(row.get("MAILING_ZIP"))

    situs_norm = normalize_line(situs_raw)
    mail_norm = normalize_line(mail_raw)

    out = {
        "situs_norm": situs_norm,
        "mailing_norm": mail_norm,
        "match": None,
        "match_status": "unknown",
        "match_reason": "",
        "unit_agrees": None,
        "mailing_scope": "unknown",
    }

    def finish(match, reason, scope=None):
        out["match"] = match
        out["match_status"] = {True: "match", False: "no_match", None: "unknown"}[match]
        out["match_reason"] = reason
        if scope:
            out["mailing_scope"] = scope
        return out

    # --- unknowns: absence of evidence, not evidence of absence -----------
    if not mail_norm:
        return finish(None, MISSING_MAILING)
    if not situs_norm:
        return finish(None, MISSING_SITUS)
    if is_po_box(mail_raw):
        # A PO box owner may well live at the property. Common in rural
        # Mesa County, so calling these "not primary" would bias the map.
        return finish(None, PO_BOX, "po_box")

    # --- geography prefilter: cheap, and settles most rows ----------------
    if mail_state and mail_state != situs_state:
        return finish(False, STATE_DIFFERS, "out_of_state")
    if mail_zip and situs_zip and mail_zip != situs_zip:
        return finish(False, ZIP_DIFFERS, "elsewhere_in_state")
    if mail_city and situs_city and mail_city != situs_city:
        return finish(False, CITY_DIFFERS, "elsewhere_in_state")

    # --- same locality: now the street text actually means something -----
    situs_street, situs_unit = split_unit(situs_norm)
    mail_street, mail_unit = split_unit(mail_norm)

    if situs_street == mail_street:
        out["unit_agrees"] = (situs_unit == mail_unit)
        return finish(True, STREET_MATCH, "same_property")

    return finish(False, STREET_DIFFERS, "same_city")


def config_home_state() -> str:
    """Indirection so tests can run without importing config side effects."""
    from . import config
    return config.HOME_STATE
