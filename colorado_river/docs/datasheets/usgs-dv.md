# Datasheet — USGS daily values (DV)

Where this data came from and what it means, so it can be checked later without asking anyone
([DM1/D13](https://github.com/wmacevoy/data-mining/blob/main/guide/05-design.md#d13)). One per
source. After Gebru et al., *Datasheets for Datasets*, cut to what the guide's principles ask for.

## Origin

- **Source:** USGS Water Services, `https://waterservices.usgs.gov/nwis/dv/`, JSON, no key; the same
  three gauges as the [IV datasheet](usgs-iv.md) · **License / terms:** U.S. Government work,
  public domain *(inferred: not checked against the service's terms)*
- **Collected by, of whom, for what purpose:** the USGS, of rivers, for public water monitoring;
  each value is USGS's daily statistic computed from its own instantaneous record.
- **Pulled:** by `load_or_fetch_dv` in `usgs.py`, when the app opens a gauge with no cache file: one
  request per parameter (`00060`, `00010`, `00480`), statistic `00003` (mean), the last *N* years
  (sidebar, default 5) as dates. Never again until `pixi run clean`. No raw copy is kept: only the
  values are written to `colorado_river/data/<site>_dv_<parameter>_00003_<N>y.parquet`.
- **Revisions:** yes. In each series, every value after one date is `P`, provisional, and every
  value before it is `A`, approved *(measured 2026-10-29)*:

  | Series | Last approved day | Provisional days |
  | ------ | ----------------- | ---------------- |
  | 09095500 discharge | 2026-03-26 | 216 |
  | 09152500 discharge | 2025-11-12 | 350 |
  | 09163500 discharge | 2026-03-03 | 239 |
  | 09163500 water temperature | 2026-06-02 | 146 |

- **Excluded before it reached us:** salinity (`00480`) at all three gauges, and daily water
  temperature at 09095500 and 09152500: requested, not served *(measured 2026-10-29)*.
- **Excluded by the pipeline:** the `qualifiers`, the `noDataValue`, and the site's time-zone
  block. Only date and value are kept.
- **Service end:** as in the [IV datasheet](usgs-iv.md): retired in the first quarter of 2027.
- **This sheet:** written by Claude Opus 5.5 on 2026-10-29 from a raw pull of all three gauges,
  saved outside the repository; lines marked *(measured)* are from that pull, the rest from
  `usgs.py` or *(inferred)*. **What would show it wrong:** a profile of a raw pull — per series, the
  qualifiers and where `P` begins, the `noDataValue`, missing days, and the newest day's lag:
  `pixi run profile`, which pulls afresh and keeps the raw JSON in `debug/raw/`. Rerun later on
  2026-10-29, it agreed with every *(measured)* line here.

## People

- **Is any row about a person, or linkable to one?** No.
- **Consent and permitted uses:** public data · **Retention:** the cache is kept until
  `pixi run clean`.
  ([DM1/R9](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r9))

## Columns

*Knowable at* is when the value became available to someone who could act on it — the column that
prevents leakage ([DM1/R6](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r6)).

| Column | Meaning | Units / clock | Sentinels and defaults | Knowable at | Absent / late / wrong / lying |
| ------ | ------- | ------------- | ---------------------- | ----------- | ----------------------------- |
| date | the day (`dateTime`, midnight with no offset), the index | a local calendar day at the gauge *(inferred: USGS computes daily values in local standard time; not checked)*; stored as a date with no time zone | none | the next day, provisional *(measured 2026-10-29: the newest day was 2026-10-28)* | 1,825 days per discharge series, none missing; temperature at 09163500 has 1,823, missing 2026-08-04 and 2026-08-05 *(measured)* |
| discharge_cfs | daily mean streamflow, parameter `00060`, statistic `00003` | ft³/s | `noDataValue` −999999.0, kept as a number if served; none seen | the next day, provisional; approved 7 to 12 months later in this pull | estimated (`e`) on 62 to 93 of 1,825 days per gauge, mostly December to February *(measured; ice, inferred)* |
| water_temp_c | daily mean water temperature, parameter `00010` | °C | as above | as above | served only at 09163500 *(measured 2026-10-29)*; the app omits the section elsewhere |
| salinity_ppt | daily mean salinity, parameter `00480` | ppt | — | never: not served | absent at all three gauges *(measured 2026-10-29)* |
| qualifiers | `A` approved, `P` provisional, `e` estimated, per day | — | — | with the value; `P` becomes `A` at review | dropped by the pipeline: a cached day does not say which it is |

## Labels

Not applicable: this source supplies no target, and nothing is predicted (`Q1/OUT-1`).

## Known problems

- 2026-10-29 — the most recent 5 to 12 months of every series are provisional, and the cache keeps
  them as first served; the qualifier is dropped. Left in place: the *Late data, pinned* and
  *Provenance removed* lessons in `DATA-SCIENCE.md`.
- 2026-10-29 — the daily means are USGS's local days, while `daily_features` in the app builds its
  own days from IV in UTC: two definitions of "day", one of the listed lessons.
- 2026-10-29 — estimated winter values are on screen with nothing to mark them.
