# Analysis plan — v1

What we will do, and how we will judge it, written **before the outcome is examined**. Not because
it will be right, but as a dated record of how many choices were open
([DM1/F6](https://github.com/wmacevoy/data-mining/blob/main/guide/03-feedback.md#f6)). Departing from
it is normal; departing silently is the problem — add a dated line under *Departures*. A substantial
change is a new version.

Question: `QUESTION_v1` · Written: 2026-10-29 · Outcome examined yet? _no outcome: nothing is
predicted (`Q1/OUT-1`); the data were looked at, in a raw pull on 2026-10-29_

Written after the project was built, from the code and Warren's account
([SE1/W12](https://github.com/wmacevoy/software-engineering/blob/v1.3/guide/08-work.md#w12)): it
records the plan the project carries out, *(inferred)*, not one made before it.

## What the pipeline does

The ingress and basic filtering that `Q1/BAR-1` judges, in the order the data meet them.

1. **Fetch** one gauge's IV for the last *N* days and DV for the last *M* years from USGS Water
   Services (`usgs.py`); see the [IV](datasheets/usgs-iv.md) and [DV](datasheets/usgs-dv.md)
   datasheets.
2. **Parse** the JSON into one frame per service: time (UTC) or date as the index, one column per
   parameter, empty values as null.
3. **Cache** each frame as Parquet in `colorado_river/data/`, keyed by gauge, service, and window.
4. **Filter** by gauge and window in the sidebar; by column and row predicate with
   `pixi run px --select … --where …`.
5. **Derive** IV gap summaries, daily features from IV, weekly averages from DV, and a rolling
   z-score per day (`eda.py`).
6. **Show** the frames and charts in Streamlit (`app.py`).

## Split

How rows are divided, and why that matches how the model will be used
([DM1/F7](https://github.com/wmacevoy/data-mining/blob/main/guide/03-feedback.md#f7)).

- **Grouping:** not applicable: no model is fitted.
- **Time:** not applicable.
- **Holdout:** none — nothing is fitted or scored, so there is nothing to hold out
  ([DM1/F5](https://github.com/wmacevoy/data-mining/blob/main/guide/03-feedback.md#f5)). The
  rolling z-score is fitted to the window that includes the day it scores; that is one of the
  lessons, not a split.

## Metric and baseline

([DM1/T1](https://github.com/wmacevoy/data-mining/blob/main/guide/06-testing.md#t1))

- **Primary metric:** `Q1/BAR-1`, pass or fail: a fresh clone runs and shows the three gauges,
  filtered, on three platforms, because the decision is whether this teaches ingress.
- **Second metric**, the one the search is not told about
  ([DM1/F9](https://github.com/wmacevoy/data-mining/blob/main/guide/03-feedback.md#f9)): whether
  every number on screen can be traced to the USGS value and qualifier it came from. It fails
  today, by design (the provenance lesson).
- **Baseline:** not applicable: nothing is scored.
- **Interval:** not applicable.

## Slices

Chosen now, so they are not chosen to flatter
([DM1/T9](https://github.com/wmacevoy/data-mining/blob/main/guide/06-testing.md#t9)). For this
project, a slice is where `Q1/BAR-1` could pass on one gauge and fail on another.

| Slice | Why it matters | Expected *n* |
| ----- | -------------- | ------------ |
| each gauge | the sidebar's first filter; the three serve different parameters | 3 gauges |
| provisional vs. approved days | what is on screen changes after review | 146 to 350 provisional days per DV series *(measured 2026-10-29)* |
| estimated (winter) days | measured differently, not marked | 62 to 93 days per gauge in 5 years *(measured)* |
| windows across a DST change | the DST and "day" lessons appear only here | 2 per year |

## Search budget

What will be tried, and roughly how many configurations
([DM1/F4](https://github.com/wmacevoy/data-mining/blob/main/guide/03-feedback.md#f4)). The ledger
records the actual count.

- Model families: none.
- Features: the daily features and rolling z-score already in `eda.py`; no search.
- Tuning: none; the z-score window is 30, fixed in `app.py`.
- No pattern search, so no ledger.

## Missing data

For each input with gaps: why it is missing, and what we will do — drop, impute, or model the
indicator ([DM1/R5](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r5)).
The treatment is what the code does today.

| Input | Why missing | Treatment |
| ----- | ----------- | --------- |
| salinity, all gauges | not served by these gauges | requested anyway; the section is omitted without a message |
| DV water temperature at 09095500 and 09152500 | not served as a daily mean | omitted without a message |
| DV water temperature at 09163500, 2026-08-04 and 05 | not stated by USGS | the days are absent; the chart draws across them |
| IV readings between 15-minute steps | late upload, equipment *(inferred)* | `summarize_gaps` reports them; shifted by DST (a lesson) |
| a value served as `noDataValue` (−999999.0) | USGS's sentinel | not handled: it would be kept as a reading; none seen |
| a whole fetch, when USGS is down or retired | outage; retirement in the first quarter of 2027 | swallowed by a silent except: shown as no data (a lesson) |

## Departures

- 2026-10-29 — written after the fact, from the code (above); nothing in the pipeline was changed.
