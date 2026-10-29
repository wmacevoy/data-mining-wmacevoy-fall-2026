# Datasheet — USGS instantaneous values (IV)

Where this data came from and what it means, so it can be checked later without asking anyone
([DM1/D13](https://github.com/wmacevoy/data-mining/blob/main/guide/05-design.md#d13)). One per
source. After Gebru et al., *Datasheets for Datasets*, cut to what the guide's principles ask for.

## Origin

- **Source:** USGS Water Services, `https://waterservices.usgs.gov/nwis/iv/`, JSON, no key; gauges
  09095500 (Colorado River near Cameo), 09152500 (Gunnison River near Grand Junction), 09163500
  (Colorado River at the CO–UT state line), from `config.json` · **License / terms:** U.S.
  Government work, public domain *(inferred: not checked against the service's terms)*
- **Collected by, of whom, for what purpose:** the USGS, of rivers, for public water monitoring.
- **Pulled:** by `load_or_fetch_iv` in `usgs.py`, when the app opens a gauge with no cache file: one
  request for parameters `00060,00065,00010,00480`, the last *N* days (sidebar, default 7), in UTC,
  `siteStatus=all`. Never again until `pixi run clean`. No raw copy is kept: the JSON is parsed and
  only the values are written to `colorado_river/data/<site>_iv_all_<N>d.parquet`.
- **Revisions:** yes. Every reading in a 7-day pull is qualified `P`, provisional *(measured
  2026-10-29: 6,022 of 6,022 discharge, stage, and temperature readings across the three gauges)*;
  USGS reviews and may revise them, and the cache keeps the first version forever.
- **Excluded before it reached us:** salinity (`00480`): requested, and served by none of the three
  gauges *(measured 2026-10-29)*. What USGS withholds or deletes before serving (equipment
  failures, ice) is not stated in the response.
- **Excluded by the pipeline:** the `qualifiers` of every reading (`P`, `A`, `e`, and others), the
  series' `noDataValue`, the method, and the site's time-zone block. Only time and value are kept.
- **Service end:** USGS will retire WaterServices in the first quarter of 2027, and may degrade it
  from August 2026; the replacement is `https://api.waterdata.usgs.gov/ogcapi/` (USGS water data
  blog, *WaterServices decommission*, updated 2026-10-17).
- **This sheet:** written by Claude Opus 5.5 on 2026-10-29 from a raw pull of all three gauges,
  saved outside the repository; lines marked *(measured)* are from that pull, the rest from
  `usgs.py` or *(inferred)*. **What would show it wrong:** a profile of a raw pull — per series, the
  qualifiers, `noDataValue`, the step between readings, the UTC offset, and the newest reading's
  lag. It last ran 2026-10-29; it is not in the repository yet.

## People

- **Is any row about a person, or linkable to one?** No.
- **Consent and permitted uses:** public data · **Retention:** the cache is kept until
  `pixi run clean`.
  ([DM1/R9](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r9))

## Columns

*Knowable at* is when the value became available to someone who could act on it — the column that
prevents leakage ([DM1/R6](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r6)).
The column names are the cache's; the raw field is in *Meaning*.

| Column | Meaning | Units / clock | Sentinels and defaults | Knowable at | Absent / late / wrong / lying |
| ------ | ------- | ------------- | ---------------------- | ----------- | ----------------------------- |
| time | the reading's time (`dateTime`), the index | served as local time with offset (`-06:00` in this pull); parsed and stored as UTC | none seen | the reading itself: time + 21 to 66 minutes for the newest reading *(measured 2026-10-29)* | every 15 minutes; one 45-minute step, in 09095500's temperature *(measured)*; after `to_local` in the app it is naive Denver time, where DST makes gaps that did not happen (a lesson) |
| discharge_cfs | streamflow, parameter `00060` | ft³/s | `noDataValue` −999999.0, kept as a number if served; none seen | provisional at time + under an hour; approved months later, possibly changed | all three gauges serve it; empty string becomes null |
| stage_ft | gage height, parameter `00065` | ft | as above | as above | all three gauges serve it |
| water_temp_c | water temperature, parameter `00010` | °C | as above | as above | all three gauges serve it as IV; at 09095500, 2 fewer readings than discharge in this pull *(measured)* |
| salinity_ppt | salinity, parameter `00480` | ppt | — | never: not served | absent at all three gauges; the column does not appear *(measured 2026-10-29)* |
| qualifiers | `P` provisional, `A` approved, `e` estimated, and others, per reading | — | — | with the reading; changes when USGS reviews it | dropped by the pipeline: no cached row says whether it is provisional |

## Labels

Not applicable: this source supplies no target, and nothing is predicted (`Q1/OUT-1`).

## Known problems

- 2026-10-29 — every reading in a 7-day window is provisional, and the cache drops the qualifier
  that says so; a revision is never seen. Left in place: the *Late data, pinned* and *Provenance
  removed* lessons in `DATA-SCIENCE.md`.
- 2026-10-29 — a `noDataValue` of −999999.0 would be stored as a discharge; no filter removes it.
  None appeared in this pull. Not one of the listed lessons; raised with Warren before anything
  changes.
- 2026-10-29 — the service is retired in the first quarter of 2027 (above); every pull after that
  fails, and the app's silent excepts would show it as no data.
