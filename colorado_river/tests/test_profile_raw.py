from datetime import datetime, timezone

from profile_raw import profile_series


def _series(values):
    return {
        "variable": {
            "variableCode": [{"value": "00060"}],
            "variableName": "Streamflow, ft&#179;/s",
            "unit": {"unitCode": "ft3/s"},
            "noDataValue": -999999.0,
        },
        "values": [{"value": values}],
    }


def test_dv_profile_counts_what_the_app_drops():
    # The datasheets' *(measured)* lines come from these fields.
    values = [
        {"value": "100", "qualifiers": ["A"], "dateTime": "2026-01-01T00:00:00.000"},
        {"value": "90", "qualifiers": ["A", "e"], "dateTime": "2026-01-02T00:00:00.000"},
        {"value": "-999999.0", "qualifiers": ["P"], "dateTime": "2026-01-04T00:00:00.000"},
        {"value": "80", "qualifiers": ["P", "e"], "dateTime": "2026-02-05T00:00:00.000"},
    ]
    fetched = datetime(2026, 2, 7, tzinfo=timezone.utc)
    p = profile_series(_series(values), "dv", fetched)

    assert p["n"] == 4
    assert p["sentinels"] == 1
    assert (p["min"], p["max"]) == (80.0, 100.0)
    assert p["qualifiers"] == {"A": 2, "e": 2, "P": 2}
    assert p["last_approved"] == "2026-01-02T00:00:00.000"
    assert p["missing_days"][0] == "2026-01-03"
    assert len(p["missing_days"]) == 1 + 31  # 01-03, and 01-05 through 02-04
    assert p["estimated_by_month"] == {1: 1, 2: 1}
    assert p["newest_lag_days"] == 2


def test_iv_profile_reports_steps_offsets_and_lag():
    values = [
        {"value": "10", "qualifiers": ["P"], "dateTime": "2026-11-01T01:00:00.000-06:00"},
        {"value": "11", "qualifiers": ["P"], "dateTime": "2026-11-01T01:15:00.000-06:00"},
        {"value": "12", "qualifiers": ["P"], "dateTime": "2026-11-01T01:00:00.000-07:00"},
    ]
    fetched = datetime(2026, 11, 1, 8, 30, tzinfo=timezone.utc)
    p = profile_series(_series(values), "iv", fetched)

    assert p["steps_seconds"] == {900: 1, 2700: 1}
    assert p["offsets"] == {"-06:00": 2, "-07:00": 1}
    assert p["newest_lag_minutes"] == 30.0
    assert p["last_approved"] is None
