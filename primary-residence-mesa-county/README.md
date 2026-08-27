# Primary Residence vs. Rental — Mesa County

Builds a parcel-level dataset flagging whether a property's **tax bill is
mailed to the property itself**, as a surrogate for owner occupancy.

```
ArcGIS REST  ──fetch──▶  cache/raw/*.json  ──build──▶  out/parcels_match.csv
 (network)               (immutable snapshot)          (+ .parquet, summary.txt)
```

## Quick start

Dependencies are per-project via [pixi](https://pixi.sh) — nothing is
installed globally. Like the rest of this repository, the lockfile is not
committed (see README section 3 at the root): the version bounds in
`pixi.toml` are the pinning, and every install re-solves them.

```bash
pixi install          # creates ./.pixi/ for this project only

pixi run count        # how many parcels are there?
pixi run dev-fetch    # small cached pull (2000 rows) while developing
pixi run fetch        # full cached pull
pixi run build        # cache -> out/
pixi run all          # fetch then build
pixi run test         # 40 tests, no network needed
```

`pixi shell` drops you into the environment if you'd rather run
`python run.py …` directly.

An optional second environment cross-checks the hand-rolled normalizer
against `usaddress-scourgify`:

```bash
pixi run -e crosscheck python tools/crosscheck.py
```

`requirements.txt` is kept only as a fallback for anyone without pixi.

## Why the stages are separate

`fetch` is the only stage that touches the network. Everything after it
runs from the cache. That matters for three reasons:

1. **Iteration.** Matching logic changes constantly early on. You should
   never re-download 60,000 rows to test a regex.
2. **Reproducibility.** The assessor table is mutable — valuations shift
   on the reassessment cycle, sales get appended, owners change. A cached
   snapshot with a timestamped manifest is the only way an analysis stays
   re-runnable.
3. **Courtesy.** It's a county server, not a CDN.

The cache is keyed *per page*, so an interrupted pull resumes rather than
restarting, and `--refresh` is the explicit opt-in to re-fetch.

## The match column

Three-valued, because "we don't know" is a real answer and collapsing it
into `False` would silently inflate the rental estimate.

| `match` | `match_status` | meaning |
|---|---|---|
| `True`  | `match`    | tax bill goes to the property |
| `False` | `no_match` | tax bill goes somewhere else |
| `<NA>`  | `unknown`  | the data can't answer |

Companion columns: `match_reason` (why), `situs_norm` / `mailing_norm`
(exactly what was compared — always keep these, they are how you debug a
surprising result), `unit_agrees`, and `mailing_scope`
(`same_property` / `same_city` / `elsewhere_in_state` / `out_of_state` /
`po_box` / `unknown`).

### The decision ladder

```
mailing missing?  ──▶ unknown (missing_mailing)
situs missing?    ──▶ unknown (missing_situs)
mailing is PO box?──▶ unknown (po_box)
state differs?    ──▶ False   (state_differs)
ZIP differs?      ──▶ False   (zip_differs)
city differs?     ──▶ False   (city_differs)
street matches?   ──▶ True    (street_match)  else False (street_differs)
```

Two choices worth defending:

**Geography is checked before street text.** Street names repeat across
towns — "123 MAIN ST" exists in Fruita and in Denver. A street match
between different cities is a coincidence, not evidence.

**PO boxes are `unknown`, not `False`.** Rural Mesa County owners
routinely use a PO box while living on the property. Scoring them as
"not primary" would put a false rental band around the county's edges —
exactly where the map would be most misread.

## Normalization

For *matching*, normalization only has to be **consistent**, not
canonical. We never need to know that `RD` is the correct USPS
abbreviation — only that `ROAD` and `RD` collapse to the same token on
both sides. That is a much weaker requirement than real address
standardization, and it avoids a whole class of failure.

Two things make this easier than it looks:

- **The situs side is already parsed.** The county stores `STRNUMBER`,
  `STRDIR`, `STRNAME`, `STRMODE`, `STRUNIT` as separate columns. Only
  `MAILING` is free text, so there is one side to normalize, not two.
- **Most rows never need string comparison.** State/ZIP/city settle the
  majority before any street text is examined.

### Why not `usaddress` or `libpostal`

`usaddress` mis-parses Mesa County's lettered grid roads:

```
"2879 B 1/2 RD"  ->  StreetNamePreDirectional='B', StreetName='1/2'
```

The street name is `B 1/2`. Numeric grid roads (`26 1/2 RD`) parse
correctly; lettered ones do not. And single-letter roads that collide
with directionals (`E RD`, `N RD`) are structurally ambiguous even when
they come out right.

So this pipeline compares whole normalized **lines** and never asks a
parser which token is the street name. The abbreviation tables in
`pipeline/addresses.py` are ~40 lines and fully visible; extend them when
a spot-check turns up a miss.

`usaddress-scourgify` is a reasonable independent cross-check — it applies
USPS Pub 28 at the line level and would agree with this code on the grid
roads. Worth running on a sample to see where the two disagree.

## What this measures, and what it doesn't

The proxy detects **absentee ownership**, which is *not* the same as
rental. An absentee-owned parcel could be a second home, a vacant
inheritance, or land banking.

Known error sources:

- PO box mailing addresses (handled as `unknown`)
- Owner lives next door or elsewhere in the same complex → false absentee
- Trusts and LLCs used by owner-occupants for estate planning
- Property managers receiving mail for owner-occupants (rare, but real)

### Validating it

The proxy has *measurable* accuracy, which is the best reason to build it
this way. **ACS table B25003** gives owner- vs. renter-occupied counts per
block group. Aggregate `match` to block group, regress against ACS renter
share, and report R². That turns a heuristic into an estimator with a
known error bar.

Also useful: **B25004** (vacancy, separates vacant from rented) and the
**City of Grand Junction short-term rental permits** (separates STR from
long-term).

## Layout

```
pixi.toml                 per-project environment + task definitions
run.py                    CLI entry point
pipeline/config.py        service URL, field list, paths
pipeline/fetch.py         stage 1 — cached paged pull
pipeline/addresses.py     stage 2 — normalization + match decision
pipeline/build.py         stage 3 — assemble table, write outputs
tools/crosscheck.py       optional: compare against usaddress-scourgify
tests/test_addresses.py   40 fixture tests, no network
cache/                    raw snapshot + manifest.json  (gitignored)
out/                      parcels_match.csv/.parquet, summary.txt
```

## Privacy note

`OWNER` and `MAILING` are real names and addresses. They are public
record, but an aggregated, redistributable file is a different artifact
from a record you look up one at a time. Aggregate to `NBHD` or block
group before publishing or sharing anything.

## Provenance

This project was built with Claude Code, in
[this session](https://claude.ai/code/session_01QAdPs5TMCK4kGYg3bmB6iv)
(`cse_01QAdPs5TMCK4kGYg3bmB6iv`). The transcript is the design record:
what was tried, what was rejected, and why the decision ladder under
"The match column" ended up in that order. `DATA-SCIENCE.md` argues that
a result is only as good as its provenance; this is that, for the code.
