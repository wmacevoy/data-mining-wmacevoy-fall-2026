# Colorado & Gunnison River Flow

A Streamlit dashboard over live USGS river-gauge data for the Colorado and
Gunnison Rivers near Grand Junction. It fetches instantaneous and daily
measurements, caches them as Parquet, derives daily features, and flags unusual
days with a rolling z-score.

This is the reference project for the course: a small, real, end-to-end pipeline
— remote API → local cache → feature engineering → dashboard — that a person
other than the author can actually run.

## Running it

From the **repository root** (not this folder):

```bash
pixi run app
```

Then click the `Local URL:` that Streamlit prints. See the
[root README](../README.md) if you have not installed pixi yet.

| Task | What it does |
| --- | --- |
| `pixi run app` | Launch the dashboard |
| `pixi run meta` | List USGS gauges (`--mode config` for just the configured ones) |
| `pixi run px` | Parquet explorer — inspect the cache from the CLI |
| `pixi run profile` | Pull raw USGS JSON into `debug/raw/` and print what the app drops: qualifiers, sentinels, gaps |
| `pixi run test` | Run the tests |
| `pixi run lint` | Check code style |
| `pixi run clean` | Delete `data/` and `debug/` |

Extra arguments pass through:

```bash
pixi run app --server.port 8502
pixi run px data/09163500_dv_00060_00003_5y.parquet --info --head 10
pixi run px data/09095500_iv_all_7d.parquet --select time,discharge_cfs --where "discharge_cfs > 1000"
pixi run meta --format json --state CO --state UT
```

## Layout

| File | Purpose |
| --- | --- |
| `app.py` | Streamlit UI, charts, debug snapshot controls |
| `usgs.py` | USGS Water Services client; caches to `data/*.parquet` |
| `eda.py` | Timezone handling, resampling, daily features, rolling anomalies |
| `px.py` | Parquet explorer (CLI) |
| `meta.py` | Lists USGS sources |
| `profile_raw.py` | Profiles a raw USGS pull; backs the datasheets in `docs/datasheets/` |
| `config.json` | Gauge catalog and the `debug` flag |
| `.streamlit/config.toml` | Streamlit settings — **tracked on purpose**, see below |
| `pytest.ini` | Puts this folder on the import path for tests |
| `tests/` | Unit tests for `eda` and Parquet round-tripping |

`data/` and `debug/` are generated and git-ignored.

## Data source

[USGS Water Services](https://waterservices.usgs.gov/) — no API key required.

- **IV** (instantaneous): ~15-minute samples, UTC.
- **DV** (daily): daily aggregates, date-indexed, no timezone.

Parameter codes: `00060` discharge (cfs), `00065` gage height (ft),
`00010` water temperature (°C), `00480` salinity (ppt).

Add gauges by editing `usgs_sources` in `config.json`; `usgs.py` falls back to a
built-in catalog if the file is missing or malformed.

## About that Streamlit first-run prompt

On a machine that has never run Streamlit, `streamlit run` interrupts with:

```
👋 Welcome to Streamlit!
If you'd like to receive helpful onboarding emails, news, offers, promotions,
and the occasional swag, please enter your email address below.
Email:
```

It then blocks on stdin. The server does not start until someone types
something. It is per-user state written to `~/.streamlit/credentials.toml`, so
it reappears on every fresh laptop, every lab machine, and every CI runner.

**Pixi does not handle this** — nothing in pixi knows what Streamlit is. The
fix is the committed `.streamlit/config.toml` in this folder, specifically
`server.headless = true`, which skips onboarding entirely.

Two details worth knowing:

- The old repo generated this file from `config.json` with `jq` inside
  `setup.sh`, and only when the file did not already exist. That is why its
  `gatherUsageStats` ended up as `true` while `config.json` said `false` —
  the generated copy silently drifted from its source, and because
  `.gitignore` contained `.streamlit/`, nobody could see it. Committing the
  file directly removes the generator, the `jq` dependency, and the drift.
- `headless = true` also means Streamlit no longer auto-opens a browser tab.
  Click the printed URL instead. This is the same tradeoff every Streamlit
  container image makes.

Verified both ways with a throwaway `HOME`: with this file the server starts
clean and writes nothing to `~/.streamlit`; without it, the prompt appears and
the health check never comes up.

## Timezones and Arrow

The two things that actually break this app:

- **Timezones.** IV data are fetched in UTC, converted to `America/Denver` for
  display, then made timezone-*naive* before rendering. DV data are date-indexed
  with no timezone at all.
- **Arrow serialization.** Streamlit converts every DataFrame to an Arrow table.
  Mixed-type object columns — floats next to timestamps — raise `ArrowInvalid`.
  `arrow_safe_df()` in `app.py` normalizes frames before display, and the IV gap
  summary is rendered as JSON for the same reason.

If you hit an Arrow error: enable **Save debug snapshots** in the sidebar and
read the `*_dtypes.txt` files written to `debug/` to find the offending column.
Deleting stale `data/*.parquet` also helps when a schema has changed.

## Known rough edges

These are real and left in place deliberately — they are the next lessons, not
oversights.

1. **Silent failure.** There are 17 `except Exception:` blocks that swallow
   errors, several of them `except: pass`. A USGS outage currently looks
   identical to a quiet day. Reliability means catching a problem *and
   reporting it*.
2. **No retry.** `_nwis_request` makes one HTTP call. A single transient 503
   loses the whole fetch. Real pipelines retry with backoff.
3. **Naive `datetime.now()`.** `usgs.py` is careful — it uses
   `datetime.now(timezone.utc)` throughout. But `app.py` stamps its debug
   snapshot filenames with a bare `datetime.now()` (lines 86 and 97), so
   snapshot names are in local wall-clock time while the data inside them are
   UTC. Comparing two snapshots across a DST boundary will mislead you. Ruff's
   `DTZ` rules catch this; they are documented as off in `../ruff.toml`.
4. **Cache never expires.** `load_or_fetch_*` returns a cached Parquet file
   forever, so "instantaneous values" can be arbitrarily stale. There is no TTL
   and no way to force a refresh from the UI.

## License

MIT — see [`../LICENSE`](../LICENSE).
