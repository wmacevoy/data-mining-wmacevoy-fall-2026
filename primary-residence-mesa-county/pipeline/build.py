"""Stage 3 -- turn the cached pages into a table with the match column."""
import json

import pandas as pd

from . import addresses, config, fetch


def build(residential_only: bool = False) -> pd.DataFrame:
    """Load the cache, apply the match decision, return the table."""
    records = fetch.load_records()
    df = pd.DataFrame.from_records(records)
    print(f"[build] {len(df)} parcels loaded from cache")

    if residential_only and "PROPTYPE" in df.columns:
        before = len(df)
        mask = df["PROPTYPE"].astype(str).str.upper().str.contains("RESID", na=False)
        df = df[mask].copy()
        print(f"[build] residential filter: {before} -> {len(df)}")

    # ArcGIS returns dates as epoch milliseconds.
    if "SDATE" in df.columns:
        df["SDATE"] = pd.to_datetime(df["SDATE"], unit="ms", errors="coerce")

    decisions = pd.DataFrame.from_records(
        [addresses.decide_match(row) for row in df.to_dict("records")],
        index=df.index,
    )
    df = pd.concat([df, decisions], axis=1)

    # `boolean` (not `bool`) so True / False / <NA> all survive round-trips.
    df["match"] = df["match"].astype("boolean")
    df["unit_agrees"] = df["unit_agrees"].astype("boolean")
    return df


def summarize(df: pd.DataFrame) -> str:
    """A short report -- the thing you actually read after a run."""
    total = len(df)
    lines = [f"parcels: {total}", ""]

    counts = df["match_status"].value_counts()
    lines.append("match_status")
    for status in ("match", "no_match", "unknown"):
        n = int(counts.get(status, 0))
        lines.append(f"  {status:<10} {n:>8}  {n / total:6.1%}")

    lines += ["", "match_reason"]
    for reason, n in df["match_reason"].value_counts().items():
        lines.append(f"  {reason:<20} {n:>8}  {n / total:6.1%}")

    lines += ["", "mailing_scope"]
    for scope, n in df["mailing_scope"].value_counts().items():
        lines.append(f"  {scope:<20} {n:>8}  {n / total:6.1%}")

    # Unknown rate is the honest quality metric: how often the data simply
    # cannot answer the question. Watch it per neighborhood, not just overall.
    if "NBDESC" in df.columns:
        by_nbhd = (
            df.assign(unknown=df["match_status"].eq("unknown"))
            .groupby("NBDESC")["unknown"].mean()
            .sort_values(ascending=False).head(5)
        )
        lines += ["", "highest unknown rate by neighborhood"]
        for name, rate in by_nbhd.items():
            lines.append(f"  {str(name)[:28]:<30} {rate:6.1%}")

    return "\n".join(lines)


def write_outputs(df: pd.DataFrame) -> None:
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = config.OUT_DIR / "parcels_match.csv"
    df.to_csv(csv_path, index=False)
    print(f"[build] wrote {csv_path}")

    try:
        pq_path = config.OUT_DIR / "parcels_match.parquet"
        df.to_parquet(pq_path, index=False)
        print(f"[build] wrote {pq_path}")
    except Exception as exc:  # pyarrow not installed -- CSV is enough
        print(f"[build] parquet skipped ({exc.__class__.__name__})")

    report = summarize(df)
    (config.OUT_DIR / "summary.txt").write_text(report)
    print("\n" + report)
