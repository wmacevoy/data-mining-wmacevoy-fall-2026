# Contributing

How to work on this repository — for a new teammate and for an agent, who both arrive knowing
nothing ([SE1/A3](https://github.com/wmacevoy/software-engineering/blob/v1.3/guide/10-agents.md#a3)).
Keep it short and true: a change that makes a line here untrue updates it in the same change.

Five course projects share one root. `colorado_river` is the reference project, and the only one CI
checks; the others are listed under [Projects](#projects). Installing pixi and the everyday
commands are in [README.md](README.md).

## Run it

- **Prerequisites:** [pixi](https://pixi.prefix.dev) (README section 1); `pixi install` at the
  root. Every root task runs from the root, whatever the current directory. Name the environment
  (`-e`) for any task more than one project has (`app`, `test`, `lint`, `clean`): pixi refuses the
  bare name as ambiguous.
- **Raw to report:** `pixi run -e colorado-river clean && pixi run -e colorado-river app` — for
  `colorado_river`, the dashboard is the
  report: `clean` empties the cache, so every number on screen comes from a new USGS pull. It is
  interactive; no command writes a report. Not timed at full size. USGS revises provisional values,
  so a later rerun can show different numbers, and nothing records which pull a number came from.
  The other projects are under [Projects](#projects).
- **Fetch / refresh raw data:** `colorado_river` has no fetch task. The app fetches on a cache miss
  (`load_or_fetch_*` in `usgs.py`) and then keeps the cache forever; to refresh, reset. It records
  nothing about the pull: no URL, no fetch time, no revision status.
- **Reset derived data:** `pixi run -e colorado-river clean` — deletes `colorado_river/data/` and
  `colorado_river/debug/`. Each project's `clean` is under [Projects](#projects).

## Check it

- **The full check:** `pixi run -e colorado-river lint && pixi run -e colorado-river test` — for
  `colorado_river` only: ruff, then the
  unit tests in `colorado_river/tests/`. There is no fixture through every stage, no property test,
  and no golden output: none yet. The same commands CI runs, on Ubuntu, macOS and Windows, when
  `colorado_river/`, `pixi.toml`, or the workflow changes
  ([DM1/O2](https://github.com/wmacevoy/data-mining/blob/main/guide/07-operating.md#o2)).
- **Success prints:** `All checks passed!` from ruff, then `4 passed` from pytest.
- **The doctor:** `./dm --doctor` — SE1's rows and this guide's: both agreements loaded, the
  question's one-way doors, the holdout's reach, every column's knowable-at, raw read-only, the
  ledger's writer; *none yet* is a true answer
  ([DM1/A2](https://github.com/wmacevoy/data-mining/blob/main/guide/10-agents.md#a2)). It reads
  this repository as one project; it does not yet look in `<project>/docs/`.
- **Golden output:** none yet
  ([DM1/T7](https://github.com/wmacevoy/data-mining/blob/main/guide/06-testing.md#t7)).
- **Lessons left in place:** `colorado_river` keeps known defects on purpose: silent excepts, the
  DST gap, two definitions of "day", a check that cannot fail, an anomaly score that cannot exceed
  5.295, a cache with no expiry, no provenance in the Parquet. They are listed in
  [DATA-SCIENCE.md](DATA-SCIENCE.md#where-this-shows-up-in-colorado_river) and in
  `colorado_river/README.md`. They are curriculum, not bugs: do not fix one, or add a check that
  catches one, without asking Warren.

## Projects

| Project                         | Run with                         | Raw, and from where                                                                                                 | Raw to report                                     | Check, not in CI                                 | Reset                        |
| ------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------------------ | ---------------------------- |
| `colorado_river`                | `pixi run -e colorado-river <task>` | none kept: USGS Water Services is the authority; `data/` is a cache                                                 | `clean`, then `app`                               | (CI runs it)                                     | `clean`                      |
| `occupancy_explorer`            | `pixi run -e occupancy <task>`   | none kept: the occupancy GraphQL API is the authority; `data/events.parquet` is a cache that fetches only new rows | `sync`, then `app`                                | `lint`, `test`                                   | `clean`                      |
| `primary-residence-mesa-county` | `pixi run <task>` in its folder  | `cache/raw/*.json`, a snapshot of Mesa County's ArcGIS parcel service, git-ignored                                 | `all` (fetch, then build to `out/`), then `app`   | `test` (no lint task)                            | none: no `clean` task        |
| `ml`                            | `pixi run -e ml <task>`          | MNIST, downloaded by `data` into `data/`                                                                            | `data`, `train`, then `app`; `export` for ONNX    | `lint`, `test`                                   | `clean` (`data/`, `runs/`)   |
| `llm`                           | `pixi run -e llm <task>`         | the SE1 guide, vendored and tracked in `llm/vendor/`; the lab's 40 questions in `llm/questions.jsonl`               | `index`, then `compare`; `zen-run` needs an API key | `lint`, `test`                                   | `clean`                      |

`primary-residence-mesa-county` has its own `pixi.toml` from before the root manifest; its tasks run
from inside its folder, and the root `pixi run` does not reach it.

## Data rules for this repository

- **Raw data:** only the parcels project keeps raw data, in
  `primary-residence-mesa-county/cache/raw/`. It is not read-only: its files are writable, and
  `fetch` writes there. `colorado_river`, `occupancy_explorer`, and `ml` keep caches, deleted by
  `clean`, not raw; the remote service is the authority, and it can change.
- **The holdout:** none, in any project. `ml` scores every run on MNIST's test split, and `llm`
  scores every setup on its 40 questions; both are test sets read on every run, not holdouts kept
  from the people building the model
  ([DM1/F5](https://github.com/wmacevoy/data-mining/blob/main/guide/03-feedback.md#f5)).
- **Data about people:** `colorado_river`, `ml`, and `llm` have none. `occupancy_explorer` counts
  people through doorways (location, time, delta), with no one identified. The parcels rows name
  owners and their mailing addresses. Agents may read the parcels data (Warren, 2026-10-29); what
  else may leave this machine, and what may be published, is not stated yet
  ([DM1/A8](https://github.com/wmacevoy/data-mining/blob/main/guide/10-agents.md#a8)).
- **Clock:** no rule for the repository yet
  ([DM1/D5](https://github.com/wmacevoy/data-mining/blob/main/guide/05-design.md#d5)). In
  `colorado_river`, instantaneous values arrive in UTC, are shown in `America/Denver`, and are made
  tz-naive before display; daily values are dates with no time zone. A "day" there has two
  definitions on screen at once, which is one of the lessons above.

## Where things are

- **Working set:** each project's own `docs/` folder, `<project>/docs/`, for `QUESTION_vN`,
  `PLAN_vN`, datasheets, model cards, and the ledger: none yet. `FINDINGS.md` for the whole
  repository is at the root. The root `docs/` is the published GitHub Pages site; nothing from the
  working set goes there
  ([DM1/W6](https://github.com/wmacevoy/data-mining/blob/main/guide/08-work.md#w6)).
- **Agents:** read `AGENTS-DM.md` (copied from the [data mining guide](https://github.com/wmacevoy/data-mining/blob/main/AGENTS.md))
  and the SE1 `AGENTS.md` it extends, both imported from `CLAUDE.md`, and this file, before acting.
  `dm`, `dm.ps1`, and `dm.py` sit beside SE1's `se.py`.

| AGENTS.md says                 | In this repository                                                        |
| ------------------------------ | ------------------------------------------------------------------------- |
| the repository guide           | `CONTRIBUTING.md`                                                         |
| the queue                      | `QUEUE.md`, at the root                                                   |
| findings                       | `FINDINGS.md`, at the root                                                |
| the check command              | `pixi run -e colorado-river lint && pixi run -e colorado-river test`; success prints `4 passed` |
| the handoff check              | `.claude/settings.json`: `python3 se.py --post` at start, resume, compact |
| `Non-goals`, `Scope decisions` | none yet                                                                  |
