#!/usr/bin/env python3
"""
profile_raw.py — Profile a raw USGS pull

Usage:
  python profile_raw.py [--days 7] [--years 5]

Makes the same requests the app makes for every configured gauge, saves each raw
JSON payload in debug/raw/ beside the time it was fetched, and prints what the
datasheets in docs/datasheets/ say about it: per series, the count, the
noDataValue and how often it appears, the qualifiers (A approved, P provisional,
e estimated), the last approved value, missing days, and how far behind the
newest value is.

The app's parser keeps only the time and the value; this script keeps
everything else, so it shows what the app throws away.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List

from dateutil import parser as dtp

from usgs import (
    DISCHARGE_CFS,
    SALINITY_PPT,
    SITE_CATALOG,
    STAGE_FT,
    WATER_TEMP_C,
    fetch_dv_json,
    fetch_iv_json,
)

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug", "raw")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pull raw USGS JSON and profile it")
    parser.add_argument("--days", type=int, default=7, help="IV window in days (the app's default: 7)")
    parser.add_argument("--years", type=int, default=5, help="DV window in years (the app's default: 5)")
    return parser.parse_args()


def profile_series(ts: Dict, kind: str, fetched: datetime) -> Dict:
    """Summarize one USGS timeSeries entry, from IV (kind "iv") or DV ("dv").

    Pure: takes the parsed JSON and the fetch time, returns a dict, does no I/O.
    """
    var = ts["variable"]
    values = ts["values"][0]["value"]
    no_data = var.get("noDataValue")

    numbers = [float(v["value"]) for v in values if v["value"] not in ("", None)]
    real = [x for x in numbers if x != no_data]

    # A value can carry more than one qualifier (["P", "e"]), so count each one.
    qualifiers: Counter = Counter()
    for v in values:
        for q in v.get("qualifiers", []):
            qualifiers[q] += 1
    approved = [v["dateTime"] for v in values if "A" in v.get("qualifiers", [])]

    out = {
        "parameter": var["variableCode"][0]["value"],
        "name": var["variableName"],
        "unit": var["unit"]["unitCode"],
        "n": len(values),
        "no_data_value": no_data,
        "sentinels": len(numbers) - len(real),
        "min": min(real) if real else None,
        "max": max(real) if real else None,
        "qualifiers": dict(qualifiers),
        "last_approved": max(approved) if approved else None,
        "first": values[0]["dateTime"] if values else None,
        "last": values[-1]["dateTime"] if values else None,
    }
    if not values:
        return out

    if kind == "iv":
        times = [dtp.isoparse(v["dateTime"]) for v in values]
        steps = Counter(int((b - a).total_seconds()) for a, b in zip(times, times[1:]))
        lag = fetched - times[-1].astimezone(timezone.utc)
        out["steps_seconds"] = dict(steps)
        # The offset each timestamp was served with, e.g. "-06:00" or "-07:00".
        out["offsets"] = dict(Counter(v["dateTime"][-6:] for v in values))
        out["newest_lag_minutes"] = round(lag.total_seconds() / 60, 1)
    else:
        days = [dtp.isoparse(v["dateTime"]).date() for v in values]
        present = set(days)
        missing: List[date] = []
        d = days[0]
        while d < days[-1]:
            if d not in present:
                missing.append(d)
            d += timedelta(days=1)
        estimated = [day for v, day in zip(values, days) if "e" in v.get("qualifiers", [])]
        out["missing_days"] = [m.isoformat() for m in missing]
        out["estimated_by_month"] = dict(sorted(Counter(day.month for day in estimated).items()))
        out["newest_lag_days"] = (fetched.date() - days[-1]).days
    return out


def print_profile(name: str, requested: List[str], prof: List[Dict]) -> None:
    print(f"== {name}")
    served = {p["parameter"] for p in prof}
    for code in requested:
        if code not in served:
            print(f"   {code}: requested, not served")
    for p in prof:
        print(f"   {p['parameter']} {p['name']!r} unit={p['unit']} n={p['n']} min={p['min']} max={p['max']}")
        print(f"     noDataValue={p['no_data_value']} sentinels={p['sentinels']} qualifiers={p['qualifiers']}")
        print(f"     first={p['first']} last={p['last']} last_approved={p['last_approved']}")
        if "steps_seconds" in p:
            print(f"     steps_seconds={p['steps_seconds']} offsets={p['offsets']}")
            print(f"     newest_lag_minutes={p['newest_lag_minutes']}")
        if "missing_days" in p:
            print(f"     missing_days={p['missing_days']}")
            print(f"     estimated_by_month={p['estimated_by_month']}")
            print(f"     newest_lag_days={p['newest_lag_days']}")


def save_and_print(name: str, kind: str, requested: List[str], body: Dict) -> None:
    fetched = datetime.now(timezone.utc)
    with open(os.path.join(RAW_DIR, f"{name}.json"), "w", encoding="utf-8") as f:
        json.dump({"fetched_utc": fetched.isoformat(), "body": body}, f)
    series = body.get("value", {}).get("timeSeries", [])
    print_profile(name, requested, [profile_series(ts, kind, fetched) for ts in series])


def main() -> None:
    args = parse_args()
    os.makedirs(RAW_DIR, exist_ok=True)
    end = datetime.now(timezone.utc)
    iv_start = end - timedelta(days=args.days)
    dv_start = end - timedelta(days=365 * args.years)
    iv_parameters = (DISCHARGE_CFS, STAGE_FT, WATER_TEMP_C, SALINITY_PPT)

    # The same requests as load_or_fetch_iv and load_or_fetch_dv in usgs.py.
    for site in SITE_CATALOG.values():
        body = fetch_iv_json(site, iv_start, end, parameters=iv_parameters)
        save_and_print(f"{site}_iv_{args.days}d", "iv", list(iv_parameters), body)
        for code in (DISCHARGE_CFS, WATER_TEMP_C, SALINITY_PPT):
            body = fetch_dv_json(site, dv_start, end, parameter=code)
            save_and_print(f"{site}_dv_{code}_{args.years}y", "dv", [code], body)

    print(f"raw payloads in {RAW_DIR}")


if __name__ == "__main__":
    main()
