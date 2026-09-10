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

## The app

`app.py` is a Streamlit view of the built table, split by property type.
It reads `out/parcels_match.parquet` and re-scores every parcel a second
time with `LOCATION` as the situs source instead of the
`STRNUMBER`..`STRUNIT` components, so the two scorings sit side by side.
That comparison is the whole point of the page: the component path drops
the unit designator, and how much that costs depends almost entirely on
whether a property type carries units (Residential 7%, Townhouse 52%,
Condo 93%). See "A known defect" below.

### Running it

The app is a *reader*, not a stage — it will not fetch or build anything.
Produce the table first, once:

```bash
pixi run all          # fetch + build -> out/parcels_match.parquet
```

Then, whichever of these you prefer:

```bash
pixi run app                          # the task; equivalent to the next line
pixi run streamlit run app.py         # direct, and takes streamlit's flags
```

Or step into the environment first and drop pixi from the command
entirely:

```bash
pixi shell
streamlit run app.py
```

Without pixi at all:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Any of these opens a browser at <http://localhost:8501>. `Ctrl-C` in the
terminal stops the server.

The flags worth knowing. All three forms take them — pixi appends
whatever you add onto the end of the task's command line:

```bash
streamlit run app.py --server.port 8600        # 8501 already taken
streamlit run app.py --server.headless true    # don't open a browser
streamlit run app.py --server.address 0.0.0.0  # reachable off-machine; see below

pixi run app --server.port 8600                # same thing through the task
```

`streamlit run` puts the script's own directory on `sys.path`, so the
`from pipeline import ...` at the top of `app.py` resolves no matter
which directory you launch from — an absolute path works fine:

```bash
streamlit run ~/projects/.../primary-residence-mesa-county/app.py
```

The first load takes a few seconds: it re-scores all 79,660 parcels the
second way. That result is cached (`@st.cache_data`), so the filters and
the scoring toggle are instant afterwards. Edit `app.py` while it runs and
the page offers to re-run.

`pixi.toml` pins `streamlit >= 1.63` for a reason worth knowing about.
streamlit 1.59.1 together with pyarrow 25.0.0 **segfaults** inside
`pyarrow.pandas_compat.convert_column`, in the step where Streamlit
re-serialises a chart's data to Arrow. It is non-deterministic and takes a
handful of reruns to show up, which is exactly what makes it nasty: the
server dies outright, with no traceback and nothing on the page. It
reproduces on pandas 2.3.3 and 3.0.5 alike, so pandas is not the variable;
moving *either* streamlit to 1.63 or pyarrow to 25.0.1 clears it. Don't
loosen that bound without re-running the app through a dozen reruns.

**Do not bind it to `0.0.0.0` on an untrusted network.** The parcel table
shows `OWNER` and `MAILING` — see the privacy note at the bottom of this
file. Streamlit has no authentication; the default binding is localhost
for a reason.

### The value distribution

The **What the properties are worth** section bins `TOTVALCUR` — the
assessor's total actual value — into a frequency distribution, one panel
per outcome. `TOTVALCUR` is a *valuation*, not a sale price; the parcel
record carries no price, so this is the only money in it.

Three things about that section are decisions rather than defaults:

- **Linear by default, log available.** Values run from \$10 to \$21.7M but
  the housing stock sits in about one decade around \$350k. A log axis
  spends two of its three decades on ~2% of the parcels; a linear one puts
  the hump where it can be read. Log is worth a look for the bottom of the
  range, where the vacant lots and the odd records live.
- **Count panels are scaled independently; share panels are not.** The
  categories differ up to sevenfold in size, so a shared count axis leaves
  the two smaller ones flat against the largest one's peak. Each count
  panel therefore gets its own y domain — a real hazard in small
  multiples, so every panel's subtitle carries its n and the caption says
  outright that the heights do not compare. Switching to *share within
  category* puts all three on one axis, which is the honest way to compare
  shapes.
- **\$0 parcels are off the chart, and said so loudly.** About 1,046
  parcels carry no value at all, and they are not spread evenly: roughly
  one in six *No answer* parcels is one of them. A \$0 assessment and a
  cheap house are different facts, and a log axis has no room for zero
  either, so they are counted in a callout instead of being folded into
  the first bin.

The domain stops at the half-percentiles of the priced parcels and what
falls outside is folded into the end bins rather than dropped, so every
parcel is still counted somewhere; the caption gives both counts.

### Exporting

The **Export** section at the bottom of the page writes any table on the
page — the parcel rows, or any of the aggregates behind the charts — as
**CSV**, **Excel** or **Parquet**. Whatever the filters, the scoring
toggle and the outcome/search boxes currently select is what comes out,
which is the reason it is there: the on-screen parcel table is truncated
to 500 rows, and the export is not.

Which format:

| | keeps dtypes and NA | opens in | note |
|---|---|---|---|
| Parquet | yes, exactly | pandas, DuckDB, Spark | the one to re-open in code |
| CSV | no — everything is text | anything | biggest file of the three |
| Excel | approximately | Excel, Sheets, LibreOffice | header frozen and filterable |

Excel is the slow one: about nine seconds for all 62k parcels with every
column, because `.xlsx` is an XML format and every cell is an element.
The result is cached per (table, format), so it is paid once. Sheets are
capped at 1,048,576 rows — over that the app says so and points at the
other two formats rather than writing a truncated file.

Excel export needs a writer engine; `xlsxwriter` is in `pixi.toml` and
`requirements.txt`. Without one (or with only `openpyxl`, which also
works) the Excel option explains itself and CSV and Parquet still work.

## Where things are, on the ground

The parcel number is a spatial address, and it checks out against layer 2's
coordinates:

```
2435-223-00-007
2435   township / range     6 mi x 6 mi   (measured: 5.84 x 5.86 median)
22     section 01-36        1 mi x 1 mi   (measured: 0.96 x 0.96)
3      quarter section      160 acres     (1=NE 2=NW 3=SW 4=SE)
00     block
007    parcel
```

Section numbers follow the PLSS serpentine — 1 in the north-east corner, 6
in the north-west, 7 directly below 6, 36 in the south-east. The Grand
Valley road grid *is* this grid: numbered roads run north-south at 1.002 mi
per road-number step, lettered roads east-west at 0.981 mi per letter. So
`2879 B 1/2 RD` is already a coordinate to within half a mile, and the
fractional roads that break `usaddress` are load-bearing rather than noise.

**Layer 2 of the same service** carries `LATITUDE`, `LONGITUDE`, `UTM12_X`
and `UTM12_Y` as ordinary attribute fields — location with no geometry
parsing and no reprojection, populated for all 79,660 records. `pixi run
fetch` pulls it into `cache/points/`; `--no-points` skips it.

### Why the map is a grid and not a group-by

Mesa County is surveyed under **two** principal meridians: the 6th over most
of the county (`SEC 22 8S 102W 6TH PM`) and the Ute over the Grand Valley
(`T1N R2W`). Their township lines do not share a lattice, and near the join
the county's township codes cover partial, irregular ground — of 61
well-sampled prefixes, 24 pairs overlap once each is placed at its own
measured origin. Grouping by the prefix gives bins that are neither
equal-area nor disjoint.

`pipeline/geo.py` therefore bins on a regular 6-mile grid anchored to where
the survey's township lines actually fall (derived from the section offsets,
not hardcoded). Whole, well-sampled townships land within a median 0.29 mi
of a cell boundary, so over the valley the cells and the real townships are
the same thing; near the meridian join they are honestly just a grid.

The map colours `match / (match + no_match)`, so unknowns are out of the
ratio. Cells where unknowns are most of the record are drawn in neutral grey
instead: they hold the lowest ratios on the map, and that ordering is not a
coincidence — PO-box and missing-address parcels cluster in the rural east
and south, so dropping unknowns does not remove that bias, it concentrates
it.

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

## A known defect

`build_situs_line()` joins the situs components with spaces, so `STRUNIT`
lands as a bare trailing token -- `516 31 1/2 RD 50` against a mailing
line of `516 31 1/2 RD UNIT 50`. `split_unit()` needs a keyword, so it
never fires: it recovers the unit from the components 0.1% of the time
and from `LOCATION` 98.1% of the time, because `LOCATION` keeps the `#`
that `normalize_line()` already maps to `UNIT`. The documented fallback
field is strictly better than the primary path.

The cost is 4,276 parcels (5.4% of the county) scored `no_match` that
should be `match`, and it is not spread evenly -- it lands on whatever
has units. Manufactured homes are the extreme: of the 2,660 `M`-prefix
accounts, the pipeline currently calls 2,548 absentee and 3 owner-occupied.

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
pipeline/config.py        service URLs, field lists, paths
pipeline/fetch.py         stage 1 — cached paged pull (layers 1 and 2)
pipeline/addresses.py     stage 2 — normalization + match decision
pipeline/build.py         stage 3 — assemble table, write outputs
pipeline/geo.py           parcel number → township grid, for the map
app.py                    streamlit view, split by property type
tools/crosscheck.py       optional: compare against usaddress-scourgify
tests/test_addresses.py   40 fixture tests, no network
cache/raw/                parcel snapshot + manifest.json  (gitignored)
cache/points/             parcel coordinates, layer 2      (gitignored)
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
