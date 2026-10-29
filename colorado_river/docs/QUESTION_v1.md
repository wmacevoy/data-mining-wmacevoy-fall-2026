# Question — v1

The decision this work serves, and exactly what is being predicted, described, or found. The data
equivalent of requirements: changes only with the client, and a change is a new version
(`QUESTION_v2.md`), never an edit to this one. See
[DM1/R1–R10](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md).

Client (the one voice who can decide): Warren MacEvoy, for the course · Date sent: 2026-10-29 ·
*Tell us what is wrong with it.*

Written by Claude Opus 5.5 from Warren's account of 2026-10-29, after the project existed
([SE1/W12](https://github.com/wmacevoy/software-engineering/blob/v1.3/guide/08-work.md#w12)). In his
words: the question was "explore an ingress data set with local interest and demonstrate the
beginning of a data pipeline"; the plan was "to have a conversation and see what was available, then
create an ingress around it"; it "was resolved to the colorado river data with a plan to demonstrate
ingress and basic filtering". Everything else here is *(inferred)* until Warren reads it back.

## The decision

Who decides what, when, with what in front of them today — and what it costs when they get it wrong
([DM1/R1](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r1)).

- **Decision:** whether `colorado_river` is fit to be the course's first example of ingress and
  basic filtering: the project students read and run before they build their own. Warren decides,
  before it is taught. *(inferred)* No decision about the river is served: this is a teaching
  pipeline, and it describes; it predicts nothing.
- **What we would do if the answer came out the other way:** fix what makes it unfit, or pick a
  different source; the shape (remote API → local cache → features → dashboard) stays.
  *(inferred)* Already in view: the USGS service it reads is being retired in the first quarter of
  2027 (see *Not yet answered*).

## People in the data

Whose rows these are, what they were collected for, and whether this use is that
([DM1/P3](https://github.com/wmacevoy/data-mining/blob/main/guide/01-purpose.md#p3),
[DM1/R9](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r9)).

None. Every row is a gauge reading: discharge, stage, water temperature. The data were collected by
the USGS for public water monitoring, and public use is that use.

## Bias

A requirement like any other, decided with the client
([DM1/R10](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r10)).

- **Who asks about one case, and which reference class will the answer describe:** a student or a
  local asking "is today's flow unusual?" gets an answer about one gauge against the last 30 days
  at that gauge, in a window that includes today
  ([DM1/U8](https://github.com/wmacevoy/data-mining/blob/main/guide/02-unknowing.md#u8)). Not this
  date in other years, not other gauges. *(inferred)*
- **Groups that matter:** no groups of people. The rows do fall into groups that are measured
  differently: approved and provisional values, and estimated values, mostly in winter — measured
  2026-10-29, see the datasheets. *(inferred)*
- **BIAS-1** *(since v1)* None: no rows are about people, so no per-group measure is required. The
  measurement groups above are shown, not hidden: they are a requirement of the datasheets, not of
  this bar. *(inferred)*

| Source | Present here? How we will check |
| ------ | ------------------------------- |
| Historical | No people; not applicable. |
| Selection, representation | Three gauges near Grand Junction, chosen for local interest; they describe these three reaches and no others. |
| Measurement | Yes: recent values are provisional and get revised; winter values are often estimated (ice, *inferred*). The pipeline drops the qualifier that says which, so a reader cannot tell. Checked by the raw profile in the datasheets. |
| Aggregation | Yes: a "day" in the daily features is a UTC day, while the chart shows Denver time (a lesson, `DATA-SCIENCE.md`). |
| Evaluation | Nothing is evaluated. |
| Deployment | A local dashboard, run by students; no one acts on it. |

## Definitions

One-way doors: each costs a re-analysis to change
([DM1/R2](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r2)). Prefix
by area (`OUT-1`, `UNIT-1`, …), mark each with the version that last changed it, and cite them as
`Q1/OUT-1`.

- **UNIT-1** *(since v1)* One row is: one reading at one gauge — for instantaneous values, one
  timestamp (every 15 minutes) with discharge, stage, and water temperature where the gauge serves
  them; for daily values, one date's mean of one parameter. *(inferred, from `usgs.py`)*
- **OUT-1** *(since v1)* The outcome, written so it could be a query: none is predicted. What is
  shown: for the gauge and the two windows chosen in the sidebar, the values USGS served at
  the moment of the first fetch, and the daily features and anomaly flags computed from them.
  *(inferred)*
- **PRED-1** *(since v1)* The prediction point: none, since nothing is predicted. What a reader
  can know at a fetch: instantaneous readings up to about an hour old, daily means up to yesterday,
  and approved values only up to a date some months back; everything after it is provisional.
  *(measured 2026-10-29: 21–66 minutes; yesterday; approval boundaries 2025-11-12 to 2026-06-02,
  by series)*

## The bar

Specific enough to be rejected, written before results are seen
([DM1/R3](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r3)). Mark
guesses *(invented)*.

- **BAR-1** *(since v1)* A student with a fresh clone and pixi installed runs `pixi run app`, and
  sees each of the three gauges' last 7 days of instantaneous values and 5 years of daily means,
  filtered by the sidebar's gauge and window, with no step the README does not name. Pass or fail,
  on Ubuntu, macOS, and Windows; no baseline, because nothing is scored. *(invented)*

## The price of each error

([DM1/R4](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r4))

| Error | What it looks like here | Who pays | Relative cost |
| ----- | ----------------------- | -------- | ------------- |
| False positive | A day flagged unusual that is not; a 75-minute "outage" that did not happen (the DST lesson) | the student who believes the screen | low: no one acts on it *(inferred)* |
| False negative | A USGS outage shown as a quiet day (the silent-except lesson); a revised value never seen (the cache lesson) | the student, and the course, if it teaches that the screen is the river | higher: the lesson is that the pipeline lies quietly *(inferred)* |

## Envelope

([DM1/R8](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r8))

- **Data:** three gauges. Per gauge, about 670 instantaneous readings per parameter in 7 days, and
  1,825 daily means per parameter in 5 years. The binding number is events: 5 spring runoffs in a
  5-year window. *(measured 2026-10-29)*
- **Labels:** none.
- **Compute:** a fetch took 0.05–0.3 seconds per request, 12 requests. *(measured 2026-10-29)*
- **Expert time:** Warren's, to read this back.
- **Inference:** not applicable.
- **Freshness:** the cache never refreshes (a lesson); `pixi run clean` is the only refresh.

## Assumptions (K4s), read back to the client

In their words, not ours ([DM1/H2](https://github.com/wmacevoy/data-mining/blob/main/guide/09-people.md#h2)).

- "We're assuming the decision is whether this project is fit to teach ingress and filtering from,
  and that nothing about the river itself is being decided. True?" — _not yet asked_
- "We're assuming 'basic filtering' means choosing a gauge, a time window, and columns or rows
  (the sidebar, and `pixi run px --select/--where`), not removing bad readings. True?" — _not yet
  asked_
- "We're assuming the ten defects listed in `DATA-SCIENCE.md` stay as they are, and this question
  does not ask for them to be fixed. True?" — _not yet asked_

## Not for

Populations, conditions, and uses this work will still produce an answer for, and that we will not
stand behind ([DM1/R11](https://github.com/wmacevoy/data-mining/blob/main/guide/04-requirements.md#r11)).

- Safety on the river, flood warning, boating, or water rights — use USGS and the National Weather
  Service directly; this cache can be any age, and its anomaly score cannot exceed 5.295 (a lesson).
- Salinity — the code requests it, but none of the three gauges serves parameter `00480`
  *(measured 2026-10-29)*, and the app then omits the section without saying why.
- Daily water temperature at Cameo or on the Gunnison — only the state-line gauge serves it as a
  daily mean *(measured 2026-10-29)*; elsewhere that section is omitted the same way.
- Any gauge other than the three in `config.json`, without its own datasheet.

## Not yet answered

- Whether the project moves to USGS's new Water Data APIs (`api.waterdata.usgs.gov`) before
  WaterServices is retired in the first quarter of 2027, with degradation possible from August
  2026 (USGS water data blog, updated 2026-10-17); a search reports 2027-02-22 as the date — Warren,
  before the spring semester.
- The three assumptions above — Warren.
- Whether BAR-1 is the bar, or what is — Warren.
