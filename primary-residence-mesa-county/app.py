"""Interactive view of the owner-occupancy proxy, split by property type.

    pixi run app

Reads out/parcels_match.parquet (run `pixi run all` first) and re-scores every
parcel a second way -- using LOCATION as the situs source instead of the
STRNUMBER..STRUNIT components -- so the two scorings can be compared side by
side. That comparison is the point of the page: the component path silently
drops the unit designator, and how much that costs depends almost entirely on
whether a property type has units.
"""
import re

import altair as alt
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


def table_view(frame, label="Show the numbers"):
    """The relief rule: every chart has a readable table behind it."""
    with st.expander(label):
        st.dataframe(frame, width="stretch", hide_index=True)


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
                            "n": "Parcels", "share": "Share %"}))

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
                            "has_unit": "Carry a unit no. %", "n": "Parcels"}))

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
                                    "unknown_share": "Unknown %"}))

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
                            "n": "Parcels", "share": "Share %"}))

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
                            "value": "Share %"}))

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
                            "rate": "Mails to property %", "n": "Parcels"}))

# --- 6. the rows -----------------------------------------------------------
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
st.caption(f"{len(rows):,} parcels")
st.dataframe(rows[cols].head(500), width="stretch", hide_index=True,
             column_config={
                 "alt_situs": st.column_config.TextColumn("situs_norm (LOCATION)"),
                 "TOTVALCUR": st.column_config.NumberColumn("Value", format="$%d"),
                 "mail_portfolio": st.column_config.NumberColumn("Parcels at mailing addr"),
             })

st.caption(
    "Source: Mesa County Assessor tax parcels (ArcGIS ParcelPointQuery layer 1), "
    f"snapshot in `cache/manifest.json`. OWNER and MAILING are public record but "
    "identify households — aggregate before redistributing."
)
