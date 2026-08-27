"""Tests for normalization and the match decision.

These are fixtures, not live data -- the point is that the *logic* is
pinned down before anyone looks at 60,000 real parcels. Several cases
encode Grand Valley specifics that generic address libraries get wrong.
"""
import pytest

from pipeline.addresses import (
    build_situs_line, decide_match, is_po_box, normalize_line, split_unit,
)


# --- normalization --------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("123 North Seventh Street", "123 N SEVENTH ST"),
    ("123 N 7th St.", "123 N 7TH ST"),
    ("2879 B 1/2 Road", "2879 B 1/2 RD"),        # lettered grid road
    ("641 26 1/2 Rd", "641 26 1/2 RD"),          # numeric grid road
    ("3090 F Rd", "3090 F RD"),
    ("755 Horizon Drive", "755 HORIZON DR"),
    ("  1250   E   RD  ", "1250 E RD"),
    ("", ""),
])
def test_normalize_line(raw, expected):
    assert normalize_line(raw) == expected


def test_fraction_survives_normalization():
    """The '/' must not be stripped -- 'B 1/2 RD' and 'B RD' are different
    streets, and Mesa County has both."""
    assert normalize_line("2879 B 1/2 RD") != normalize_line("2879 B RD")


def test_synonyms_collapse_to_the_same_token():
    """Consistency, not canonical correctness, is what matching needs."""
    assert normalize_line("100 Elm Street") == normalize_line("100 ELM ST")
    assert normalize_line("100 North Elm St") == normalize_line("100 N ELM ST")


# --- unit handling --------------------------------------------------------

@pytest.mark.parametrize("raw,street,unit", [
    ("123 N 7TH ST UNIT A", "123 N 7TH ST", "UNIT A"),
    ("123 N 7TH ST APT 2", "123 N 7TH ST", "UNIT 2"),
    ("123 N 7TH ST # 2", "123 N 7TH ST", "UNIT 2"),
    ("123 N 7TH ST", "123 N 7TH ST", ""),
])
def test_split_unit(raw, street, unit):
    assert split_unit(normalize_line(raw)) == (street, unit)


# --- PO boxes -------------------------------------------------------------

@pytest.mark.parametrize("raw", [
    "PO BOX 1234", "P.O. Box 99", "POST OFFICE BOX 5",
    "HC 62 BOX 12", "RR 2 BOX 40", "PMB 300",
])
def test_po_box_detected(raw):
    assert is_po_box(raw)


@pytest.mark.parametrize("raw", ["123 BOXWOOD LN", "500 POST RD", "2879 B 1/2 RD"])
def test_po_box_false_positives(raw):
    assert not is_po_box(raw)


# --- situs assembly -------------------------------------------------------

def test_build_situs_from_components():
    row = {"STRNUMBER": "2879", "STRDIR": "", "STRNAME": "B 1/2",
           "STRMODE": "RD", "STRUNIT": "", "LOCATION": "IGNORED"}
    assert build_situs_line(row) == "2879 B 1/2 RD"


def test_build_situs_falls_back_to_location():
    row = {"STRNUMBER": None, "STRNAME": None, "LOCATION": "755 HORIZON DR"}
    assert build_situs_line(row) == "755 HORIZON DR"


# --- the decision ladder --------------------------------------------------

def parcel(**overrides):
    """A minimal owner-occupied parcel, overridable per test."""
    base = {
        "STRNUMBER": "755", "STRDIR": "", "STRNAME": "HORIZON",
        "STRMODE": "DR", "STRUNIT": "", "LOCATION": "755 HORIZON DR",
        "SITUS_CITY": "GRAND JUNCTION", "SITUS_STATE": "CO", "SITUS_ZIP": "81506",
        "MAILING": "755 HORIZON DR", "MAILING_CITY": "GRAND JUNCTION",
        "MAILING_ST": "CO", "MAILING_ZIP": "81506",
    }
    base.update(overrides)
    return base


def test_exact_match_is_true():
    result = decide_match(parcel())
    assert result["match"] is True
    assert result["match_status"] == "match"
    assert result["mailing_scope"] == "same_property"


def test_match_survives_formatting_differences():
    result = decide_match(parcel(MAILING="755 Horizon Drive."))
    assert result["match"] is True


def test_grid_road_match():
    result = decide_match(parcel(
        STRNAME="B 1/2", STRMODE="RD", STRNUMBER="2879",
        LOCATION="2879 B 1/2 RD", SITUS_ZIP="81503",
        MAILING="2879 B 1/2 Road", MAILING_ZIP="81503",
    ))
    assert result["match"] is True, result


def test_out_of_state_is_false():
    result = decide_match(parcel(
        MAILING="1 WALL ST", MAILING_CITY="NEW YORK",
        MAILING_ST="NY", MAILING_ZIP="10005",
    ))
    assert result["match"] is False
    assert result["mailing_scope"] == "out_of_state"


def test_different_zip_same_state_is_false():
    result = decide_match(parcel(
        MAILING="100 MAIN ST", MAILING_CITY="DENVER",
        MAILING_ST="CO", MAILING_ZIP="80202",
    ))
    assert result["match"] is False
    assert result["match_reason"] == "zip_differs"


def test_same_city_different_street_is_false():
    result = decide_match(parcel(MAILING="2879 B 1/2 RD"))
    assert result["match"] is False
    assert result["match_reason"] == "street_differs"


def test_street_coincidence_across_cities_is_not_a_match():
    """'123 MAIN ST' exists in many towns. Geography is checked first so a
    name collision never reads as owner occupancy."""
    row = parcel(
        STRNUMBER="123", STRNAME="MAIN", STRMODE="ST", LOCATION="123 MAIN ST",
        SITUS_CITY="FRUITA", SITUS_ZIP="81521",
        MAILING="123 MAIN ST", MAILING_CITY="DENVER", MAILING_ZIP="80202",
    )
    assert decide_match(row)["match"] is False


def test_po_box_is_unknown_not_false():
    """Rural owners often use a PO box while living on the property.
    Calling these 'not primary' would bias the map."""
    result = decide_match(parcel(MAILING="PO BOX 1234", MAILING_ZIP="81502"))
    assert result["match"] is None
    assert result["match_status"] == "unknown"
    assert result["match_reason"] == "po_box"


def test_missing_mailing_is_unknown():
    result = decide_match(parcel(MAILING=None))
    assert result["match"] is None
    assert result["match_reason"] == "missing_mailing"


def test_missing_situs_is_unknown():
    result = decide_match(parcel(
        STRNUMBER=None, STRNAME=None, STRMODE=None, LOCATION=None,
    ))
    assert result["match"] is None
    assert result["match_reason"] == "missing_situs"


def test_unit_agreement_reported_separately():
    """Same building, different unit text -- still a street match, but the
    caller can see the units disagree and decide what that means."""
    result = decide_match(parcel(
        STRUNIT="UNIT A", LOCATION="755 HORIZON DR UNIT A",
        MAILING="755 HORIZON DR UNIT B",
    ))
    assert result["match"] is True
    assert result["unit_agrees"] is False


def test_missing_mailing_state_does_not_block_a_match():
    """Absent geography should not manufacture a False."""
    result = decide_match(parcel(MAILING_ST=None, MAILING_CITY=None,
                                 MAILING_ZIP=None))
    assert result["match"] is True


# --- pandas NaN handling --------------------------------------------------
# JSON null survives ArcGIS as None, but pandas converts it to float NaN,
# which is truthy. Without an explicit check the literal string "NAN" gets
# compared as if it were an address. Found by an end-to-end smoke test.

def test_nan_mailing_is_unknown_not_a_bogus_address():
    result = decide_match(parcel(MAILING=float("nan")))
    assert result["match"] is None
    assert result["match_reason"] == "missing_mailing"
    assert "NAN" not in result["mailing_norm"]


def test_nan_situs_components_do_not_leak_into_the_line():
    row = {"STRNUMBER": "755", "STRDIR": float("nan"), "STRNAME": "HORIZON",
           "STRMODE": "DR", "STRUNIT": float("nan"), "LOCATION": None}
    assert build_situs_line(row) == "755 HORIZON DR"


def test_nan_geography_does_not_manufacture_a_mismatch():
    result = decide_match(parcel(MAILING_ST=float("nan"),
                                 MAILING_CITY=float("nan"),
                                 MAILING_ZIP=float("nan")))
    assert result["match"] is True
