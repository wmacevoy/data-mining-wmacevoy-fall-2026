"""Interactive view of the owner-occupancy proxy, split by property type.

    pixi run app

Reads out/parcels_match.parquet (run `pixi run all` first) and re-scores every
parcel a second way -- using LOCATION as the situs source instead of the
STRNUMBER..STRUNIT components -- so the two scorings can be compared side by
side. That comparison is the point of the page: the component path silently
drops the unit designator, and how much that costs depends almost entirely on
whether a property type has units.
"""
import io
import re

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from pipeline import config, fetch, geo
from pipeline.addresses import decide_match

TYPES = ["Residential", "Townhouse", "Condo"]
STATUSES = ["match", "no_match", "unknown"]
STATUS_LABEL = {
    "match": "Mails to property",
    "no_match": "Mails elsewhere",
    "unknown": "No answer",
}

# --- palette ---------------------------------------------------------------
# Two chromatic poles plus a recessive neutral for "the data cannot answer".
# Blue/orange rather than blue/red on purpose: absentee ownership is not a
# failure state, and a red segment would editorialize. Validated with the
# dataviz palette checker (all checks pass, both modes, all pairs).
LIGHT = {
    "surface": "#fcfcfb", "plane": "#f9f9f7",
    "ink": "#0b0b0b", "ink2": "#52514e", "muted": "#898781",
    "grid": "#e1e0d9", "axis": "#c3c2b7",
    "match": "#2a78d6", "no_match": "#eb6834", "unknown": "#898781",
    "series": ["#2a78d6", "#eb6834", "#1baf7a"],
    "context": "#898781",
    # Sequential: one hue, more-is-darker against a light surface.
    "seq": ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"],
    # Label ink flips where the fill crosses into the dark half of the ramp.
    "seq_flip": 0.62, "seq_hi_ink": "#ffffff", "seq_lo_ink": "#0b0b0b",
    "empty": "#eeede8",
}
DARK = {
    "surface": "#1a1a19", "plane": "#0d0d0d",
    "ink": "#ffffff", "ink2": "#c3c2b7", "muted": "#898781",
    "grid": "#2c2c2a", "axis": "#383835",
    "match": "#3987e5", "no_match": "#d95926", "unknown": "#898781",
    "series": ["#3987e5", "#d95926", "#199e70"],
    "context": "#898781",
    # Same hue, reversed: on a dark surface "more" has to mean brighter,
    # or the high end recedes into the background instead of standing out.
    "seq": ["#104281", "#184f95", "#256abf", "#3987e5", "#5598e7", "#86b6ef", "#cde2fb"],
    # Ramp runs the other way here, so the label ink does too: the high end
    # is the PALE end on a dark surface and needs near-black on it.
    "seq_flip": 0.45, "seq_hi_ink": "#0b0b0b", "seq_lo_ink": "#ffffff",
    "empty": "#242422",
}


def palette():
    try:
        return DARK if st.context.theme.type == "dark" else LIGHT
    except Exception:
        return LIGHT


def chart_theme(p):
    """Recessive chrome, text in ink tokens rather than series colors."""
    return {
        "config": {
            "background": p["surface"],
            "font": 'system-ui, -apple-system, "Segoe UI", sans-serif',
            "view": {"stroke": None},
            "axis": {
                "labelColor": p["muted"], "titleColor": p["ink2"],
                "labelFontSize": 12, "titleFontSize": 12, "titleFontWeight": 500,
                "gridColor": p["grid"], "gridWidth": 1,
                "domainColor": p["axis"], "tickColor": p["axis"],
                "labelFont": 'system-ui, -apple-system, sans-serif',
            },
            "legend": {
                "labelColor": p["ink2"], "titleColor": p["ink2"],
                "labelFontSize": 12, "titleFontSize": 12, "symbolType": "square",
                "symbolSize": 110, "orient": "top", "direction": "horizontal",
                "offset": 4,
            },
            "title": {
                "color": p["ink"], "subtitleColor": p["muted"],
                "fontSize": 15, "fontWeight": 600, "subtitleFontSize": 12,
                "anchor": "start", "offset": 12,
            },
        }
    }


# --- data ------------------------------------------------------------------

ENTITY_RE = r"\bLLC\b|\bINC\b|\bCORP|\bLP\b|\bLLLP\b|\bLTD\b|\bCOMPANY\b|\bPARTNERS"
TRUST_RE = r"\bTRUST\b|\bTRUSTEE|REVOCABLE"
GOV_RE = (r"\bCITY OF\b|COUNTY|STATE OF|DISTRICT|SCHOOL|FEDERAL|UNITED STATES"
          r"|DEPT|BUREAU|FOREST SERVICE|AUTHORITY")

SITUS_COMPONENTS = ["STRNUMBER", "STRDIR", "STRNAME", "STRMODE", "STRUNIT"]


@st.cache_data(show_spinner="Scoring parcels both ways…")
def load():
    path = config.OUT_DIR / "parcels_match.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)

    # Re-run the identical ladder with LOCATION as the situs source. Blanking
    # the components forces build_situs_line() onto its fallback, which keeps
    # the "#" that normalize_line maps to UNIT.
    blanked = {c: None for c in SITUS_COMPONENTS}
    alt_rows = pd.DataFrame(
        [decide_match({**row, **blanked}) for row in df.to_dict("records")],
        index=df.index,
    )
    df["alt_status"] = alt_rows["match_status"]
    df["alt_reason"] = alt_rows["match_reason"]
    df["alt_situs"] = alt_rows["situs_norm"]

    owner = df["OWNER"].fillna("").str.upper()
    df["owner_type"] = "person"
    df.loc[owner.str.contains(TRUST_RE, regex=True), "owner_type"] = "trust"
    df.loc[owner.str.contains(ENTITY_RE, regex=True), "owner_type"] = "company"
    df.loc[owner.str.contains(GOV_RE, regex=True), "owner_type"] = "government"
    df.loc[owner.eq(""), "owner_type"] = "missing"

    unit = df["STRUNIT"].astype(str).str.strip()
    df["has_unit"] = df["STRUNIT"].notna() & unit.ne("") & unit.ne("nan")

    # How many parcels share this parcel's mailing address? A proxy for
    # portfolio ownership that does not depend on parsing the owner name.
    key = df["mailing_norm"].fillna("") + "|" + \
        df["MAILING_ZIP"].fillna("").astype(str).str[:5]
    counts = key[df["mailing_norm"].fillna("").ne("")].value_counts()
    df["mail_portfolio"] = key.map(counts).fillna(0).astype(int)

    df["sale_year"] = pd.to_datetime(df["SDATE"], errors="coerce").dt.year

    # Coordinates are optional: without cache/points/ everything except the
    # map still works, so join what is there and let the map hide itself.
    points = fetch.load_points()
    if points:
        coords = pd.DataFrame.from_records(points)[
            ["ACCOUNTNO", "LATITUDE", "LONGITUDE", "UTM12_X", "UTM12_Y"]]
        df = df.merge(coords, on="ACCOUNTNO", how="left")
        df = geo.add_survey_grid(df)
    return df


def share(df, group, value_col, order):
    """Long-form share table: one row per (group, category)."""
    out = (df.groupby([group, value_col]).size().rename("n").reset_index())
    total = out.groupby(group)["n"].transform("sum")
    out["share"] = out["n"] / total
    out[value_col] = pd.Categorical(out[value_col], order, ordered=True)
    return out.dropna(subset=[value_col])


# Every table the page draws, in the shape it draws it, keyed by the name the
# export picker offers. Populated as the page runs, so the picker cannot fall
# out of step with what is actually on screen.
EXPORTS: dict[str, pd.DataFrame] = {}


def table_view(frame, name, label="Show the numbers"):
    """The relief rule: every chart has a readable table behind it."""
    EXPORTS[name] = frame
    with st.expander(label):
        st.dataframe(frame, width="stretch", hide_index=True)


# --- export ----------------------------------------------------------------

EXCEL_MIME = ("application/vnd.openxmlformats-officedocument"
              ".spreadsheetml.sheet")
FORMATS = {
    "CSV": ("csv", "text/csv"),
    "Excel": ("xlsx", EXCEL_MIME),
    "Parquet": ("parquet", "application/vnd.apache.parquet"),
}


def excel_engine():
    """Whichever .xlsx writer is installed, or None. xlsxwriter is the
    declared dependency; openpyxl is accepted so an environment built from an
    older requirements.txt still gets the Excel option."""
    for engine in ("xlsxwriter", "openpyxl"):
        try:
            __import__(engine)
            return engine
        except ImportError:
            continue
    return None


def sheet_name(name):
    """Excel rejects []:*?/\\ in sheet names and truncates past 31 chars."""
    return re.sub(r"[\[\]:*?/\\]", " ", name)[:31].strip() or "Sheet1"


@st.cache_data(show_spinner="Writing the file…", max_entries=4)
def build_file(frame, fmt, name):
    """Serialize one table. Cached on the frame itself, so re-picking a format
    after a filter change costs one write, not one per rerun."""
    if fmt == "CSV":
        return frame.to_csv(index=False).encode("utf-8")

    buf = io.BytesIO()
    if fmt == "Parquet":
        # Categoricals are display scaffolding (they exist to order bars);
        # a reader opening the file should get plain strings back.
        flat = frame.copy()
        for col in flat.columns:
            if isinstance(flat[col].dtype, pd.CategoricalDtype):
                flat[col] = flat[col].astype("string")
        flat.to_parquet(buf, index=False)
        return buf.getvalue()

    with pd.ExcelWriter(buf, engine=excel_engine(), datetime_format="yyyy-mm-dd",
                        date_format="yyyy-mm-dd") as writer:
        sheet = sheet_name(name)
        frame.to_excel(writer, sheet_name=sheet, index=False)
        if writer.engine == "xlsxwriter":
            # Header row frozen and filterable, columns wide enough to read:
            # the difference between a file someone uses and one they re-format
            # by hand before they can.
            ws = writer.sheets[sheet]
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, len(frame), max(len(frame.columns) - 1, 0))
            for i, col in enumerate(frame.columns):
                body = frame[col].astype("string").str.len().max()
                width = max(len(str(col)), 0 if pd.isna(body) else int(body))
                ws.set_column(i, i, min(max(width + 2, 9), 46))
    return buf.getvalue()


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# --- value bins ------------------------------------------------------------

NICE_STEPS = [1, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10]


def nice_number(x, up):
    """Round x out to a 1-2-5-ish multiple of a power of ten, so the axis
    reads $1,500 .. $1,500,000 rather than $1,820 .. $1,420,702."""
    if not np.isfinite(x) or x <= 0:
        return 0.0
    exp = np.floor(np.log10(x))
    mant = x / 10.0 ** exp
    if up:
        step = next((s for s in NICE_STEPS if s >= mant - 1e-9), 10)
    else:
        step = next((s for s in reversed(NICE_STEPS) if s <= mant + 1e-9), 1)
    return float(step * 10.0 ** exp)


def si_ticks(prefix):
    """Vega expression for one SI-formatted tick, with a plain zero."""
    return (f"datum.value === 0 ? '{prefix}0' "
            f": '{prefix}' + format(datum.value, '~s')")


def value_edges(values, n, log):
    """Bin edges spanning the middle 99% of the priced parcels.

    The full range is $10 to $21.7M -- six and a third decades, of which the
    housing stock occupies about one. Binning across all of it spends most of
    the axis on a few dozen parcels and leaves four bins for the bulk, so the
    domain stops at the half-percentiles. What falls outside is clipped into
    the end bins rather than dropped: the caption says how many, and every
    parcel stays counted somewhere.
    """
    lo = nice_number(values.quantile(0.005), up=False) if log else 0.0
    hi = nice_number(values.quantile(0.995), up=True)
    if log:
        lo = max(lo, 1.0)
        hi = max(hi, lo * 10)
        return np.logspace(np.log10(lo), np.log10(hi), n + 1)
    hi = max(hi, 1.0)
    # Rounding the width out (rather than the count) is what keeps linear bins
    # landing on $50,000 instead of $46,875.
    width = nice_number((hi - lo) / n, up=True) or 1.0
    return np.arange(lo, hi + width * 0.5, width)


# --- page ------------------------------------------------------------------

st.set_page_config(page_title="Owner occupancy by property type",
                   layout="wide", initial_sidebar_state="expanded")

P = palette()
alt.theme.register("mesa", enable=True)(lambda: chart_theme(P))

STATUS_SCALE = alt.Scale(
    domain=[STATUS_LABEL[s] for s in STATUSES],
    range=[P["match"], P["no_match"], P["unknown"]],
)
TYPE_SCALE = alt.Scale(domain=TYPES, range=P["series"])

st.title("Primary residence by address — Mesa County")
st.caption(
    "Does the tax bill go to the property itself? The proxy behaves very "
    "differently on Residential, Townhouse and Condo parcels — and most of "
    "the difference turns out to be an artifact of how the situs address is "
    "assembled, not a fact about tenure."
)

data = load()
if data is None:
    st.error("No `out/parcels_match.parquet`. Run `pixi run all` first.")
    st.stop()

# --- filters: one row above the charts ------------------------------------
with st.sidebar:
    st.header("Filters")
    scoring = st.radio(
        "Situs address source",
        ["Corrected (LOCATION)", "As built (components)"],
        help="The pipeline assembles situs from STRNUMBER..STRUNIT, which "
             "appends the unit as a bare token so split_unit() never fires. "
             "LOCATION keeps the '#', which normalize_line maps to UNIT.",
    )
    types = st.multiselect("Property type", TYPES, default=TYPES)
    cities = sorted(data["SITUS_CITY"].dropna().unique())
    picked_cities = st.multiselect("Situs city", cities, default=[])
    owner_types = st.multiselect(
        "Owner type", ["person", "trust", "company", "government"],
        default=["person", "trust", "company", "government"])
    vmin, vmax = int(data["TOTVALCUR"].min()), int(data["TOTVALCUR"].max())
    val_lo, val_hi = st.select_slider(
        "Total value", options=[0, 50_000, 100_000, 200_000, 350_000, 500_000,
                                1_000_000, 5_000_000, vmax],
        value=(0, vmax), format_func=lambda v: f"${v:,.0f}")

STATUS_COL = "alt_status" if scoring.startswith("Corrected") else "match_status"
REASON_COL = "alt_reason" if scoring.startswith("Corrected") else "match_reason"

df = data[data["PROPTYPE"].isin(types or TYPES)]
if picked_cities:
    df = df[df["SITUS_CITY"].isin(picked_cities)]
df = df[df["owner_type"].isin(owner_types or ["person"])]
df = df[df["TOTVALCUR"].between(val_lo, val_hi) | df["TOTVALCUR"].isna()]
df = df.copy()
df["status_label"] = df[STATUS_COL].map(STATUS_LABEL)

if df.empty:
    st.warning("No parcels match those filters.")
    st.stop()

# --- KPI row ---------------------------------------------------------------
occ = (df[STATUS_COL] == "match").mean()
occ_alt = (df["match_status" if STATUS_COL == "alt_status" else "alt_status"]
           == "match").mean()
flips = int(((df["match_status"] == "no_match") & (df["alt_status"] == "match")).sum())

k = st.columns(4)
k[0].metric("Parcels in scope", f"{len(df):,}")
k[1].metric("Mails to property", f"{occ:.1%}",
            delta=f"{occ - occ_alt:+.1f} pp vs other scoring" if len(types) else None,
            delta_color="off")
k[2].metric("Carry a unit number", f"{df['has_unit'].mean():.1%}")
k[3].metric("Re-scored by the fix", f"{flips:,}",
            help="Parcels the component path calls absentee that the LOCATION "
                 "path calls owner-occupied.")

st.divider()

# --- 1. status composition by type ----------------------------------------
st.subheader("Where the tax bill goes, by property type")
st.caption(
    "Part-to-whole. Blue and orange are the two poles; grey is the honest "
    "third answer — the record cannot settle it."
)

STATUS_ORDER = [STATUS_LABEL[s] for s in STATUSES]
comp = share(df, "PROPTYPE", "status_label", STATUS_ORDER)
comp["PROPTYPE"] = pd.Categorical(comp["PROPTYPE"], TYPES, ordered=True)
comp["rank"] = comp["status_label"].map(
    {s: i for i, s in enumerate(STATUS_ORDER)}).astype(int)
comp = comp.sort_values(["PROPTYPE", "rank"])
# Stack by hand so the segments run match -> no_match -> unknown and the
# direct labels sit at segment midpoints rather than at the stack's edge.
comp["x1"] = comp.groupby("PROPTYPE", observed=True)["share"].cumsum()
comp["x0"] = comp["x1"] - comp["share"]
comp["mid"] = (comp["x0"] + comp["x1"]) / 2

Y = alt.Y("PROPTYPE:N", title=None, sort=TYPES,
          axis=alt.Axis(labelFontSize=13, labelPadding=8))
bars = alt.Chart(comp).mark_bar(
    height=30, stroke=P["surface"], strokeWidth=2).encode(
    y=Y,
    x=alt.X("x0:Q", title=None, scale=alt.Scale(domain=[0, 1], nice=False),
            axis=alt.Axis(format="%", grid=True)),
    x2="x1:Q",
    color=alt.Color("status_label:N", scale=STATUS_SCALE, title=None,
                    sort=STATUS_ORDER, legend=alt.Legend(orient="top")),
    tooltip=[alt.Tooltip("PROPTYPE:N", title="Type"),
             alt.Tooltip("status_label:N", title="Outcome"),
             alt.Tooltip("n:Q", title="Parcels", format=","),
             alt.Tooltip("share:Q", title="Share", format=".1%")],
)
# Direct labels -- required, since one series sits under 3:1 on the light surface.
labels = alt.Chart(comp).mark_text(
    fontSize=12, fontWeight=600, color="#ffffff", baseline="middle").encode(
    y=Y, x=alt.X("mid:Q", scale=alt.Scale(domain=[0, 1], nice=False)),
    text=alt.Text("share:Q", format=".0%"),
    opacity=alt.condition(alt.datum.share > 0.06, alt.value(1), alt.value(0)),
)
st.altair_chart((bars + labels).properties(height=48 * max(len(types), 1) + 40),
                width="stretch")
table_view(comp.assign(share=(comp["share"] * 100).round(1))
           .rename(columns={"PROPTYPE": "Property type",
                            "status_label": "Outcome",
                            "n": "Parcels", "share": "Share %"}),
           "Status by property type")

# --- 2. the defect ---------------------------------------------------------
st.subheader("How much of that gap is the unit-number defect?")
st.caption(
    "Owner-occupancy rate under each scoring. Grey is the pipeline as it "
    "stands; blue is the same ladder reading situs from LOCATION. The gap "
    "tracks how often a property type carries a unit number."
)

rows = []
for t in TYPES:
    s = data[data["PROPTYPE"] == t]
    if s.empty:
        continue
    rows.append({"PROPTYPE": t, "scoring": "As built (components)",
                 "rate": (s["match_status"] == "match").mean(),
                 "has_unit": s["has_unit"].mean(), "n": len(s)})
    rows.append({"PROPTYPE": t, "scoring": "Corrected (LOCATION)",
                 "rate": (s["alt_status"] == "match").mean(),
                 "has_unit": s["has_unit"].mean(), "n": len(s)})
db = pd.DataFrame(rows)

# Emphasis: the corrected value is the point, as-built is context.
EMPH = alt.Scale(domain=["As built (components)", "Corrected (LOCATION)"],
                 range=[P["context"], P["match"]])
link = alt.Chart(db).mark_rule(strokeWidth=2, color=P["axis"]).encode(
    y=alt.Y("PROPTYPE:N", title=None, sort=TYPES,
            axis=alt.Axis(labelFontSize=13, labelPadding=8)),
    x=alt.X("min(rate):Q", title="Mails to property",
            scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")),
    x2="max(rate):Q",
)
dots = alt.Chart(db).mark_point(filled=True, size=190, stroke=P["surface"],
                                strokeWidth=2).encode(
    y=alt.Y("PROPTYPE:N", sort=TYPES, title=None),
    x=alt.X("rate:Q", scale=alt.Scale(domain=[0, 1])),
    color=alt.Color("scoring:N", scale=EMPH, title=None,
                    legend=alt.Legend(orient="top")),
    tooltip=[alt.Tooltip("PROPTYPE:N", title="Type"),
             alt.Tooltip("scoring:N", title="Scoring"),
             alt.Tooltip("rate:Q", title="Mails to property", format=".1%"),
             alt.Tooltip("has_unit:Q", title="Carry a unit no.", format=".1%"),
             alt.Tooltip("n:Q", title="Parcels", format=",")],
)
# The high end is labelled beside its dot; the low end is raised above the
# rule instead of pushed left, because Condo's low end sits at 1% and a
# left-pushed label would land on top of the axis text.
db["is_high"] = db["rate"] == db.groupby("PROPTYPE")["rate"].transform("max")


def end_label(frame, dy):
    return alt.Chart(frame).mark_text(
        align="left", dx=12, dy=dy, fontSize=12, fontWeight=600,
        color=P["ink2"], baseline="middle").encode(
        y=alt.Y("PROPTYPE:N", sort=TYPES, title=None),
        x=alt.X("rate:Q", scale=alt.Scale(domain=[0, 1])),
        text=alt.Text("rate:Q", format=".0%"))


dot_labels = end_label(db[db["is_high"]], 0) + end_label(db[~db["is_high"]], -16)
st.altair_chart((link + dots + dot_labels).properties(height=200),
                width="stretch")
table_view(db.assign(rate=(db["rate"] * 100).round(1),
                     has_unit=(db["has_unit"] * 100).round(1))
           .rename(columns={"PROPTYPE": "Property type", "scoring": "Scoring",
                            "rate": "Mails to property %",
                            "has_unit": "Carry a unit no. %", "n": "Parcels"}),
           "Occupancy under each scoring")

st.info(
    "**Condo 1.1% → 33.2%.** 93% of condo parcels carry a `STRUNIT`, so almost "
    "every one was mis-scored; 52% of townhouses and 7% of houses do. The "
    "as-built ranking was measuring unit prevalence, not tenure."
)

# --- 2b. the county map ----------------------------------------------------
st.subheader("Owner occupancy across the county")

if "cx" not in df.columns or df["cx"].isna().all():
    st.info(
        "No coordinates cached. Run `pixi run fetch` (or `python run.py fetch`) "
        "to pull layer 2 — the map needs `cache/points/`."
    )
else:
    mc0, mc1, mc2 = st.columns([2, 2, 2])
    level = mc0.radio(
        "Cell size", ["Township (6 mi)", "Section (1 mi)"], horizontal=True,
        help="Township gives about 25 usable cells for the whole county — "
             "coarse. Section is the same grid divided six ways in each "
             "direction, so the valley resolves and the back country thins out.")
    min_res = mc1.slider(
        "Minimum resolved parcels per cell", 10, 200, 30, step=10,
        help="Cells below this are drawn blank. A rate on 8 parcels is noise, "
             "and a heat map makes noise look like a finding.")
    unk_max = mc2.slider(
        "Grey out cells above this unknown share", 0.10, 1.0, 0.30, step=0.05,
        format="%.0f%%",
        help="Unknowns are excluded from the ratio, so in a cell that is "
             "mostly unknown the ratio is computed from a small, "
             "self-selected minority. Those cells get a neutral fill "
             "instead of a place on the colour ramp.")

    section_level = level.startswith("Section")
    KX, KY = ("sx", "sy") if section_level else ("cx", "cy")
    st.caption(
        f"Each cell is {'1 mile' if section_level else '6 miles'} square — a "
        f"survey {'section, 640 acres' if section_level else 'township'} — on a "
        "grid anchored to where the county's real township lines fall; the "
        "section grid nests exactly inside the township one. Colour is "
        "`match / (match + no_match)`; unknowns are out of the ratio, as asked. "
        "Grey cells hold data but too much of it is unanswerable to put on "
        "the same scale."
    )

    cells = (df.dropna(subset=[KX, KY])
             .assign(m=df["alt_status"].eq("match"),
                     nm=df["alt_status"].eq("no_match"),
                     uk=df["alt_status"].eq("unknown"))
             .groupby([KX, KY], as_index=False)
             .agg(n=("ACCOUNTNO", "size"), m=("m", "sum"),
                  nm=("nm", "sum"), uk=("uk", "sum")))
    cells = cells.rename(columns={KX: "cx", KY: "cy"})
    cells["resolved"] = cells["m"] + cells["nm"]
    # `.where` keeps this float64-with-NaN; masking with pd.NA would make it
    # an *object* column of floats and NAs. Streamlit re-serialises every
    # chart's data to Arrow on each rerun, and object columns are the slow,
    # inference-driven path through that -- chart data stays plain numeric.
    cells["rate"] = cells["m"] / cells["resolved"].where(cells["resolved"] > 0)
    cells["unknown_share"] = cells["uk"] / cells["n"]
    cells["cx"] = cells["cx"].astype(int)
    cells["cy"] = cells["cy"].astype(int)
    shown = cells[cells["resolved"] >= min_res].copy()

    trusted = shown[shown["unknown_share"] <= unk_max]
    flagged = shown[shown["unknown_share"] > unk_max]

    if trusted.empty:
        st.warning("No cell clears both thresholds. Loosen one of them.")
    else:
        # Square cells, north up. The indices themselves are arbitrary, so the
        # axes carry a compass rather than numbers nobody can use.
        xs = range(int(cells.cx.min()), int(cells.cx.max()) + 1)
        ys = range(int(cells.cy.min()), int(cells.cy.max()) + 1)
        # Keep cells square and the whole county inside a readable width.
        px = max(6, min(40, 900 // max(len(list(xs)), 1)))
        label_cells = px >= 26
        # The ramp spans only the comparable cells. Letting a 0%-on-mostly-
        # unknown cell set the low end would compress every real difference
        # into the top third of the scale.
        lo, hi = float(trusted.rate.min()), float(trusted.rate.max())
        seq = alt.Scale(range=P["seq"], domain=[lo, hi], clamp=True)

        axis_x = alt.X("cx:O", title="west  →  east", sort=list(xs),
                       axis=alt.Axis(labels=False, ticks=False, grid=False,
                                     domain=False, titleColor=P["muted"]))
        axis_y = alt.Y("cy:O", title="south  →  north", sort=list(reversed(list(ys))),
                       axis=alt.Axis(labels=False, ticks=False, grid=False,
                                     domain=False, titleColor=P["muted"]))

        # Every cell that holds any parcel at all, so the county keeps its
        # shape instead of dissolving wherever data is thin.
        backdrop = alt.Chart(cells).mark_rect(
            stroke=P["surface"], strokeWidth=2).encode(
            x=axis_x, y=axis_y, color=alt.value(P["empty"]),
            tooltip=[alt.Tooltip("n:Q", title="Parcels", format=","),
                     alt.Tooltip("resolved:Q", title="Resolved", format=","),
                     alt.Tooltip("unknown_share:Q", title="Unknown", format=".0%")],
        )
        heat = alt.Chart(trusted).mark_rect(
            stroke=P["surface"], strokeWidth=2).encode(
            x=axis_x, y=axis_y,
            color=alt.Color("rate:Q", scale=seq,
                            title="Mails to property",
                            legend=alt.Legend(format=".0%", orient="top",
                                              gradientLength=190, direction="horizontal")),
            tooltip=[alt.Tooltip("rate:Q", title="Mails to property", format=".1%"),
                     alt.Tooltip("n:Q", title="Parcels", format=","),
                     alt.Tooltip("resolved:Q", title="Resolved", format=","),
                     alt.Tooltip("m:Q", title="Mails to property", format=","),
                     alt.Tooltip("nm:Q", title="Mails elsewhere", format=","),
                     alt.Tooltip("unknown_share:Q", title="Unknown", format=".0%")],
        )
        # Cells whose ratio rests on too little answerable data: present,
        # labelled, but deliberately off the colour scale.
        grey = alt.Chart(flagged).mark_rect(
            stroke=P["surface"], strokeWidth=2).encode(
            x=axis_x, y=axis_y, color=alt.value(P["context"]),
            tooltip=[alt.Tooltip("rate:Q", title="Mails to property", format=".1%"),
                     alt.Tooltip("n:Q", title="Parcels", format=","),
                     alt.Tooltip("resolved:Q", title="Resolved", format=","),
                     alt.Tooltip("unknown_share:Q", title="Unknown", format=".0%")],
        )
        # Direct labels: the light end of a sequential ramp is under 3:1, so
        # the number has to be readable without the colour.
        mid = lo + P["seq_flip"] * (hi - lo)
        layers = [backdrop, heat, grey]
        if label_cells:
            layers.append(
                alt.Chart(trusted).mark_text(fontSize=11, fontWeight=600).encode(
                    x=axis_x, y=axis_y, text=alt.Text("rate:Q", format=".0%"),
                    color=alt.condition(alt.datum.rate > mid,
                                        alt.value(P["seq_hi_ink"]),
                                        alt.value(P["seq_lo_ink"]))))
            # The grey fill is mode-invariant, so its label is too: white on
            # #898781 is only 2.7:1, near-black is 7.9:1 in both themes.
            layers.append(
                alt.Chart(flagged).mark_text(
                    fontSize=11, fontWeight=600, color="#0b0b0b").encode(
                    x=axis_x, y=axis_y, text=alt.Text("rate:Q", format=".0%")))
        st.altair_chart(
            alt.layer(*layers).properties(
                width=px * len(list(xs)), height=px * len(list(ys))),
            width="content")
        if not label_cells:
            st.caption(
                "Cells are too small at this resolution to carry their number. "
                "Hover for the exact rate and counts, or open the table below — "
                "the pale end of the ramp is under 3:1 against the surface, so "
                "the colour alone is not the reading."
            )

        st.caption(
            f"{len(trusted)} cells on the scale, covering "
            f"{trusted.n.sum() / cells.n.sum():.0%} of the parcels in view · "
            f"{len(flagged)} greyed for unknowns · "
            f"{len(cells) - len(shown)} too thin to draw."
        )
        tbl = shown.sort_values("rate", ascending=False)
        unit = "section" if section_level else "township"
        table_view(tbl.assign(rate=(tbl.rate * 100).round(1),
                              unknown_share=(tbl.unknown_share * 100).round(1))
                   [["cx", "cy", "n", "resolved", "m", "nm", "rate", "unknown_share"]]
                   .rename(columns={"cx": f"{unit} X", "cy": f"{unit} Y", "n": "Parcels",
                                    "resolved": "Resolved", "m": "To property",
                                    "nm": "Elsewhere", "rate": "Mails to property %",
                                    "unknown_share": "Unknown %"}),
                   "Map grid cells")

        if len(flagged):
            st.warning(
                f"The {len(flagged)} grey cells run "
                f"{flagged.unknown_share.min():.0%}–{flagged.unknown_share.max():.0%} "
                "unknown, and they hold the lowest printed rates on the map. "
                "That ordering is not a coincidence: PO-box and missing-address "
                "parcels cluster in the rural east and south, so excluding "
                "them does not remove the bias, it concentrates it. Colouring "
                "these on the same ramp would draw a rental band around the "
                "county's edge that the underlying records do not support."
            )

st.divider()

# --- 3. reason mix ---------------------------------------------------------
st.subheader("Which rung of the ladder decided it")
st.caption("Share of each property type settled by each reason code.")

rm = share(df, "PROPTYPE", REASON_COL,
           sorted(df[REASON_COL].dropna().unique()))
rm["PROPTYPE"] = pd.Categorical(rm["PROPTYPE"], TYPES, ordered=True)
reason_chart = alt.Chart(rm).mark_bar(height=11, cornerRadiusEnd=4).encode(
    y=alt.Y(f"{REASON_COL}:N", title=None, sort="-x",
            axis=alt.Axis(labelFontSize=12, labelPadding=6)),
    x=alt.X("share:Q", title="Share of that property type",
            axis=alt.Axis(format="%")),
    yOffset=alt.YOffset("PROPTYPE:N", sort=TYPES),
    color=alt.Color("PROPTYPE:N", scale=TYPE_SCALE, title=None, sort=TYPES,
                    legend=alt.Legend(orient="top")),
    tooltip=[alt.Tooltip("PROPTYPE:N", title="Type"),
             alt.Tooltip(f"{REASON_COL}:N", title="Reason"),
             alt.Tooltip("n:Q", title="Parcels", format=","),
             alt.Tooltip("share:Q", title="Share", format=".1%")],
).properties(height=alt.Step(14))
st.altair_chart(reason_chart, width="stretch")
table_view(rm.assign(share=(rm["share"] * 100).round(1))
           .rename(columns={"PROPTYPE": "Property type", REASON_COL: "Reason",
                            "n": "Parcels", "share": "Share %"}),
           "Reason mix by property type")

# --- 4. independent absentee signals --------------------------------------
st.subheader("Signals that do not depend on the address match")
st.caption(
    "Three independent absentee indicators. They order the property types the "
    "same way the corrected match does, which is the reason to believe the "
    "residual Residential → Townhouse → Condo gradient is real."
)

sig_rows = []
for t in TYPES:
    s = df[df["PROPTYPE"] == t]
    if s.empty:
        continue
    sig_rows += [
        {"PROPTYPE": t, "signal": "Owner is a company",
         "value": s["owner_type"].eq("company").mean()},
        {"PROPTYPE": t, "signal": "Mail goes out of state",
         "value": s["mailing_scope"].eq("out_of_state").mean()},
        {"PROPTYPE": t, "signal": "Mailing address covers ≥5 parcels",
         "value": s["mail_portfolio"].ge(5).mean()},
    ]
SIGNAL_ORDER = ["Owner is a company", "Mailing address covers ≥5 parcels",
                "Mail goes out of state"]
sig = pd.DataFrame(sig_rows)
sig_chart = alt.Chart(sig).mark_bar(height=16, cornerRadiusEnd=4).encode(
    y=alt.Y("signal:N", title=None, sort=SIGNAL_ORDER,
            axis=alt.Axis(labelLimit=260, labelPadding=6)),
    x=alt.X("value:Q", title="Share of parcels", axis=alt.Axis(format="%")),
    yOffset=alt.YOffset("PROPTYPE:N", sort=TYPES),
    color=alt.Color("PROPTYPE:N", scale=TYPE_SCALE, title=None, sort=TYPES,
                    legend=alt.Legend(orient="top")),
    tooltip=[alt.Tooltip("PROPTYPE:N", title="Type"),
             alt.Tooltip("signal:N", title="Signal"),
             alt.Tooltip("value:Q", title="Share", format=".1%")],
).properties(height=alt.Step(20))
sig_labels = alt.Chart(sig).mark_text(
    align="left", dx=5, fontSize=11, color=P["ink2"], baseline="middle").encode(
    y=alt.Y("signal:N", title=None, sort=SIGNAL_ORDER),
    x=alt.X("value:Q"),
    yOffset=alt.YOffset("PROPTYPE:N", sort=TYPES),
    text=alt.Text("value:Q", format=".1%"),
)
st.altair_chart(sig_chart + sig_labels, width="stretch")
table_view(sig.assign(value=(sig["value"] * 100).round(1))
           .rename(columns={"PROPTYPE": "Property type", "signal": "Signal",
                            "value": "Share %"}),
           "Independent absentee signals")

# --- 5. owner type ---------------------------------------------------------
st.subheader("Owner-occupancy within each owner type")
st.caption(
    "Trusts land between people and companies in every property type — the "
    "estate-planning confound, visible."
)
ot = (df[df["owner_type"].isin(["person", "trust", "company"])]
      .assign(m=df[STATUS_COL].eq("match"))
      .groupby(["PROPTYPE", "owner_type"])
      .agg(rate=("m", "mean"), n=("ACCOUNTNO", "size")).reset_index())
ot_chart = alt.Chart(ot).mark_bar(height=16, cornerRadiusEnd=4).encode(
    y=alt.Y("owner_type:N", title=None, sort=["person", "trust", "company"],
            axis=alt.Axis(labelPadding=6)),
    x=alt.X("rate:Q", title="Mails to property", axis=alt.Axis(format="%"),
            scale=alt.Scale(domain=[0, 1])),
    yOffset=alt.YOffset("PROPTYPE:N", sort=TYPES),
    color=alt.Color("PROPTYPE:N", scale=TYPE_SCALE, title=None, sort=TYPES,
                    legend=alt.Legend(orient="top")),
    tooltip=[alt.Tooltip("PROPTYPE:N", title="Type"),
             alt.Tooltip("owner_type:N", title="Owner"),
             alt.Tooltip("rate:Q", title="Mails to property", format=".1%"),
             alt.Tooltip("n:Q", title="Parcels", format=",")],
).properties(height=alt.Step(20))
ot_labels = alt.Chart(ot).mark_text(
    align="left", dx=5, fontSize=11, color=P["ink2"]).encode(
    y=alt.Y("owner_type:N", sort=["person", "trust", "company"], title=None),
    x=alt.X("rate:Q"), yOffset=alt.YOffset("PROPTYPE:N", sort=TYPES),
    text=alt.Text("rate:Q", format=".0%"),
)
st.altair_chart(ot_chart + ot_labels, width="stretch")
table_view(ot.assign(rate=(ot["rate"] * 100).round(1))
           .rename(columns={"PROPTYPE": "Property type", "owner_type": "Owner",
                            "rate": "Mails to property %", "n": "Parcels"}),
           "Occupancy by owner type")

# --- 6. value distribution -------------------------------------------------
st.subheader("What the properties are worth, by outcome")
st.caption(
    "Frequency distribution of the assessor's total actual value, split three "
    "ways. This is a valuation, not a sale price — nothing here is what "
    "anyone paid — but it is the only money the parcel record carries."
)

vc0, vc1, vc2 = st.columns([2, 3, 2])
val_log = vc0.radio(
    "Value axis", ["Linear", "Log"], horizontal=True,
    help="Linear is the ordinary reading of a price distribution and is "
         "what the hump is best seen on. Log stretches the bottom of the "
         "range instead, which is where the vacant lots and the odd "
         "records live — the tail is thin, and on a log axis you can see "
         "how thin.") == "Log"
hist_mode = vc1.radio(
    "Bar height", ["Count", "Share within category"], horizontal=True,
    help="The three categories differ by up to sevenfold in size, so on "
         "counts the smaller ones are short everywhere — that is a fact "
         "about how many parcels there are, not about where their values "
         "sit. Switch to share to compare the shapes.")
nbins = vc2.slider("Bins", 12, 60, 32, step=4)

priced = df[df["TOTVALCUR"] > 0]
unpriced = df[~(df["TOTVALCUR"] > 0)]      # catches NaN as well as 0

if priced.empty:
    st.info("No parcel in scope carries a value, so there is nothing to bin.")
else:
    edges = value_edges(priced["TOTVALCUR"], nbins, val_log)
    lo, hi = float(edges[0]), float(edges[-1])
    clipped = priced["TOTVALCUR"].clip(lo, hi)

    hist_rows = []
    for label in STATUS_ORDER:
        vals = clipped[priced["status_label"] == label]
        counts, _ = np.histogram(vals, bins=edges)
        total = counts.sum()
        hist_rows.append(pd.DataFrame({
            "status_label": label,
            "x0": edges[:-1], "x1": edges[1:], "n": counts,
            "share": counts / total if total else 0.0,
        }))
    hist = pd.concat(hist_rows, ignore_index=True)

    # Medians on the unclipped values: the number quoted should be the real
    # one even when the tail it sits in has been folded into an end bin.
    med = priced.groupby("status_label")["TOTVALCUR"].median()
    hist["med"] = hist["status_label"].map(med)
    hist["med_at"] = hist["med"].clip(lo, hi)

    counting = hist_mode == "Count"
    # Short axis titles on purpose: a long rotated y title overflows the left
    # of the plot under Vega's fit autosize, and takes the panel's own title
    # off the top with it.
    y_col, y_title = ("n", "Parcels") if counting else ("share", "Share")
    # Counts go through si_ticks() rather than an axis format because this
    # Vega build renders "," on a quantitative axis as "6e+3", and its own
    # "~s" picks ONE SI prefix for the whole axis -- which prints "0k" at the
    # origin, and "$0M" on the value axis below.
    y_axis = (alt.Axis(labelExpr=si_ticks(""), grid=True, tickCount=3)
              if counting else
              alt.Axis(format="%", grid=True, tickCount=3))
    x_scale = alt.Scale(type="log" if val_log else "linear",
                        domain=[lo, hi], nice=False, clamp=True)
    # Shares are comparable by construction, so those panels share one y
    # domain. Counts are not: the categories differ sevenfold in size, and a
    # shared count axis leaves the two smaller ones as flat lines against the
    # largest one's peak. Each count panel therefore gets its own domain --
    # which is a real hazard in small multiples, so the panel subtitles carry
    # the n and the caption says outright that the heights do not compare.
    shared_max = float(hist[y_col].max()) or 1.0

    # Three charts rather than one faceted chart: a facet cannot take its
    # width from the container, and a histogram pinned to a fixed pixel width
    # overflows the column the moment the window narrows.
    for i, label in enumerate(STATUS_ORDER):
        part = hist[hist["status_label"] == label]
        last = i == len(STATUS_ORDER) - 1
        n_here = int(part["n"].sum())
        top = float(part[y_col].max()) if counting else shared_max
        y_scale = alt.Scale(domain=[0, (top or 1.0) * 1.12], nice=False)
        bars = alt.Chart(part).mark_bar().encode(
            x=alt.X("x0:Q", scale=x_scale,
                    title="Assessor total actual value" if last else None,
                    axis=alt.Axis(labelExpr=si_ticks("$"), grid=False,
                                  labels=last, ticks=last)),
            x2="x1:Q",
            y=alt.Y(f"{y_col}:Q", title=y_title, stack=None, scale=y_scale,
                    axis=y_axis),
            color=alt.value(P[STATUSES[i]]),
            tooltip=[alt.Tooltip("x0:Q", title="From", format="$,.0f"),
                     alt.Tooltip("x1:Q", title="To", format="$,.0f"),
                     alt.Tooltip("n:Q", title="Parcels", format=","),
                     alt.Tooltip("share:Q", title="Share of category",
                                 format=".1%")],
        )
        # The medians are the comparison the eye cannot make reliably off the
        # bars, so they are drawn rather than left to the table.
        mark = part.head(1)[["med", "med_at"]]
        rule = alt.Chart(mark).mark_rule(
            color=P["ink2"], strokeWidth=1.5, strokeDash=[4, 3]).encode(
            x=alt.X("med_at:Q", scale=x_scale, title=None))
        rule_label = alt.Chart(mark).mark_text(
            align="left", dx=6, fontSize=11, fontWeight=600,
            color=P["ink2"], baseline="top").encode(
            x=alt.X("med_at:Q", scale=x_scale, title=None), y=alt.value(2),
            text=alt.Text("med:Q", format="$,.0f"))
        st.altair_chart(
            alt.layer(bars, rule, rule_label).properties(
                height=140 if not last else 162,
                title=alt.Title(label, subtitle=f"{n_here:,} priced parcels",
                                fontSize=13, subtitleFontSize=11)),
            width="stretch")

    # Dollar signs have to be escaped in anything Streamlit renders as
    # markdown: a bare pair of them opens LaTeX math mode and the rest of the
    # paragraph comes out in a serif italic.
    below = int((priced["TOTVALCUR"] < lo).sum())
    above = int((priced["TOTVALCUR"] > hi).sum())
    ends = ([f"{below:,} below \\${lo:,.0f}"] if below else []) + \
           ([f"{above:,} above \\${hi:,.0f}"] if above else [])
    st.caption(
        "Dashed rule is each category's median. "
        + ("Each panel is scaled to its own peak, so read the shapes and the "
           "medians across panels, not the bar heights — the counts are in "
           "the subtitles. Switch to share to put all three on one axis. "
           if counting else
           "All three panels share one axis, so the shapes compare directly. ")
        + f"Bins are {'log-spaced' if val_log else 'even'} across "
          f"\\${lo:,.0f}–\\${hi:,.0f}"
        + (f"; {' and '.join(ends)} are folded into the end bins, which is "
           "why those bars can stand proud of their neighbours." if ends
           else ".")
    )

    if len(unpriced):
        by_status = unpriced["status_label"].value_counts()
        worst = by_status.idxmax()
        in_worst = max(len(df[df["status_label"] == worst]), 1)
        st.warning(
            f"**{len(unpriced):,} parcels carry no value** (\\$0 or blank) "
            "and are off this chart entirely — a log axis has no room for "
            "zero, and a \\$0 assessment is a different kind of fact from a "
            "cheap house. They are not spread evenly: "
            f"{by_status[worst]:,} of them "
            f"({by_status[worst] / in_worst:.0%} of that category) sit in "
            f"*{worst}*. A parcel with no value on record is "
            "disproportionately one the address match could not settle "
            "either — both usually mean a thin or unusual record, so read "
            "the low end of the distribution with that in mind."
        )

    wide = (hist.pivot_table(index=["x0", "x1"], columns="status_label",
                             values="n", fill_value=0)
            .reindex(columns=STATUS_ORDER, fill_value=0).reset_index())
    wide.columns.name = None
    table_view(wide.assign(**{"Value from": wide["x0"].map("${:,.0f}".format),
                              "Value to": wide["x1"].map("${:,.0f}".format)})
               [["Value from", "Value to", *STATUS_ORDER]],
               "Value distribution")

st.divider()

# --- 7. the rows -----------------------------------------------------------
st.subheader("The parcels")
st.caption(
    "Always read the two normalized strings that were actually compared — "
    "they are how a surprising row gets explained."
)
c1, c2 = st.columns([2, 3])
outcome = c1.selectbox("Outcome", ["all"] + [STATUS_LABEL[s] for s in STATUSES])
q = c2.text_input("Search address or owner", "")

rows = df
if outcome != "all":
    rows = rows[rows["status_label"] == outcome]
if q:
    pat = re.escape(q.strip())
    rows = rows[rows["LOCATION"].fillna("").str.contains(pat, case=False)
                | rows["MAILING"].fillna("").str.contains(pat, case=False)
                | rows["OWNER"].fillna("").str.contains(pat, case=False)]

cols = ["ACCOUNTNO", "PROPTYPE", "LOCATION", "SITUS_CITY", "MAILING",
        "MAILING_CITY", "MAILING_ST", "OWNER", "owner_type", "alt_situs",
        "mailing_norm", "match_status", "alt_status", "match_reason",
        "alt_reason", "mail_portfolio", "TOTVALCUR"]
st.caption(f"{len(rows):,} parcels — the table shows the first 500; "
           "export below to get all of them.")
st.dataframe(rows[cols].head(500), width="stretch", hide_index=True,
             column_config={
                 "alt_situs": st.column_config.TextColumn("situs_norm (LOCATION)"),
                 "TOTVALCUR": st.column_config.NumberColumn("Value", format="$%d"),
                 "mail_portfolio": st.column_config.NumberColumn("Parcels at mailing addr"),
             })
# The parcel rows first: it is the table people come here to take away, and
# the only one the screen truncates.
EXPORTS = {"Parcels — the columns shown above": rows[cols],
           "Parcels — every column": rows,
           **EXPORTS}

# --- 8. export -------------------------------------------------------------
st.divider()
st.subheader("Export")
st.caption(
    "Every table on this page, as it currently stands — the sidebar filters, "
    "the scoring choice, and the outcome and search boxes above all carry "
    "through. Parquet round-trips dtypes and missing values exactly and is "
    "the one to re-open in pandas; CSV flattens both but opens anywhere; "
    "Excel is for handing to someone who will double-click it."
)

x1, x2 = st.columns([3, 2])
# The map's table only registers when the map draws, so this list can shrink
# under a remembered selection; Streamlit falls back to the first option.
table_name = x1.selectbox("Table", list(EXPORTS))
fmt = x2.radio("Format", list(FORMATS), horizontal=True)
export = EXPORTS[table_name]
ext, mime = FORMATS[fmt]

if fmt == "Excel" and excel_engine() is None:
    st.warning(
        "No .xlsx writer installed. `pixi install` (or "
        "`pip install xlsxwriter`) adds one; CSV and Parquet work regardless."
    )
elif fmt == "Excel" and len(export) > 1_048_575:
    st.error(
        f"{len(export):,} rows will not fit on an Excel sheet (the limit is "
        "1,048,576 including the header). Use Parquet or CSV, or narrow the "
        "filters."
    )
else:
    if fmt == "Excel" and len(export) > 20_000:
        st.caption(f"{len(export):,} rows — the .xlsx takes a few seconds to "
                   "write the first time, then it is cached.")
    blob = build_file(export, fmt, table_name)
    st.download_button(
        f"Download {fmt}",
        data=blob,
        file_name=f"mesa-{slug(table_name)}.{ext}",
        mime=mime,
        type="primary",
        icon=":material/download:",
    )
    st.caption(f"{len(export):,} rows × {len(export.columns)} columns · "
               f"{len(blob) / 1e6:.1f} MB")

st.caption(
    "Source: Mesa County Assessor tax parcels (ArcGIS ParcelPointQuery layer 1), "
    f"snapshot in `cache/manifest.json`. OWNER and MAILING are public record but "
    "identify households — aggregate before redistributing."
)
