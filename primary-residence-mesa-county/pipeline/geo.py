"""Put parcels on the survey grid.

Mesa County's parcel number is a spatial address. `2435-223-00-007` reads

    2435  township/range      6 mi x 6 mi
    22    section 01-36       1 mi x 1 mi
    3     quarter section     160 acres  (1=NE 2=NW 3=SW 4=SE)
    00    block
    007   parcel

all of which checks out against the coordinates in layer 2: the 4-digit
prefixes bound to a median 5.84 x 5.86 mi box, sections to 0.96 x 0.96,
and section numbers follow the PLSS serpentine (1 in the NE corner, 6 in
the NW, 7 directly below 6, 36 in the SE).

Why the map does not simply group by that prefix
------------------------------------------------
Mesa County is surveyed under **two** principal meridians -- the 6th
(`SEC 22 8S 102W 6TH PM`) over most of the county and the Ute over the
Grand Valley (`T1N R2W`). Their township lines do not share a lattice, and
near the join the county's township codes cover partial, irregular ground:
of 61 well-sampled prefixes, 24 pairs have footprints that overlap once you
place each at its own measured origin. Grouping by prefix therefore
produces bins that are neither equal-area nor non-overlapping.

So the map bins on a **regular 6-mile grid** instead -- township-sized
cells, anchored to where the survey's township lines actually fall. Whole,
well-sampled townships land within a median 0.29 mi of a cell boundary, so
over the Grand Valley the cells and the real townships are the same thing;
near the meridian join they are honestly just a grid.

The anchor is derived, not hardcoded, so it stays correct if the county
re-numbers or extends the layer.
"""
import numpy as np
import pandas as pd

MILE = 1609.344          # metres; UTM zone 12N is metric
CELL = 6 * MILE          # a township is six miles square


def section_cell(sec):
    """Section number 1-36 -> (column, row) within its township, 0-indexed.

    Columns run west (0) to east (5), rows south (0) to north (5). PLSS
    numbering snakes: 1-6 east-to-west across the north row, 7-12
    west-to-east on the row below it, and so on.
    """
    sec = np.asarray(sec, dtype="float64")
    band = np.floor((sec - 1) / 6)          # 0 = north row .. 5 = south row
    within = (sec - 1) % 6
    row = 5 - band
    col = np.where(band % 2 == 0, 5 - within, within)
    return col, row


def _township_origins(df):
    """Estimate each township's south-west corner, in UTM metres.

    Subtracting the section offset from every parcel removes the parcel
    clustering that would otherwise bias a plain centroid: what is left
    is the township corner plus a within-section offset that averages out.
    """
    col, row = section_cell(df["sec"])
    ox = df["UTM12_X"] - col * MILE
    oy = df["UTM12_Y"] - row * MILE
    return (df.assign(_ox=ox, _oy=oy)
            .groupby("twnrng")
            .agg(n=("ACCOUNTNO", "size"), ox=("_ox", "mean"), oy=("_oy", "mean"),
                 w=("UTM12_X", lambda s: (s.max() - s.min()) / MILE),
                 h=("UTM12_Y", lambda s: (s.max() - s.min()) / MILE)))


def _circular_anchor(values, weights):
    """Weighted circular mean of `values` modulo one cell.

    Circular because the quantity is a phase: origins at 0.1 mi and 5.9 mi
    into a cell are 0.2 mi apart, not 5.8, and a plain mean would land the
    grid lines in the middle of the townships.
    """
    theta = 2 * np.pi * (np.asarray(values) % CELL) / CELL
    mean = np.arctan2((weights * np.sin(theta)).sum(),
                      (weights * np.cos(theta)).sum())
    return (mean % (2 * np.pi)) / (2 * np.pi) * CELL


def add_survey_grid(df):
    """Add survey-grid cell indices at two resolutions, plus the PLSS columns.

    `cx` / `cy` are 6-mile township cells; `sx` / `sy` are 1-mile section
    cells. Both are floored against the *same* anchor, so the section grid
    nests exactly six-by-six inside the township grid rather than being a
    second, independently-fitted lattice.

    Needs `PARCELNUM` and the layer-2 `UTM12_X` / `UTM12_Y`. Parcels
    without coordinates get <NA> cells; parcels without a PLSS-coded
    parcel number (manufactured homes, which own no land) still get a
    cell, because the cell comes from the coordinates, not the number.
    """
    out = df.copy()
    num = out["PARCELNUM"].fillna("").astype(str)
    out["twnrng"] = num.str[:4]
    out["sec"] = pd.to_numeric(num.str[4:6], errors="coerce")
    out["qtr"] = pd.to_numeric(num.str[6:7], errors="coerce")
    # 7xxx accounts are manufactured homes: no land parcel, so no survey code.
    out.loc[num.str.len().ne(12) | out["twnrng"].str.startswith("7")
            | ~out["sec"].between(1, 36), ["sec", "qtr"]] = np.nan

    plss = out[out["sec"].notna() & out["UTM12_X"].notna()]
    if plss.empty:
        for col in ("cx", "cy", "sx", "sy"):
            out[col] = pd.NA
        return out

    origins = _township_origins(plss)
    # Anchor only on townships that are both well sampled and fully spanned;
    # a partial township's corner cannot be estimated from its parcels.
    whole = origins[(origins.n >= 200) & (origins.w > 5.5) & (origins.h > 5.5)]
    if len(whole) < 3:
        whole = origins[origins.n >= 50]
    ax = _circular_anchor(whole.ox.values - 0.5 * MILE, whole.n.values)
    ay = _circular_anchor(whole.oy.values - 0.5 * MILE, whole.n.values)

    out["cx"] = np.floor((out["UTM12_X"] - ax) / CELL)
    out["cy"] = np.floor((out["UTM12_Y"] - ay) / CELL)
    out["sx"] = np.floor((out["UTM12_X"] - ax) / MILE)
    out["sy"] = np.floor((out["UTM12_Y"] - ay) / MILE)
    out.loc[out["UTM12_X"].isna(), ["cx", "cy", "sx", "sy"]] = np.nan
    return out
