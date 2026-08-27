"""Stage 1 -- pull parcel records from the ArcGIS REST service, cached to disk.

Design notes
------------
The cache is *per page*, not per pull. That means:

  * an interrupted pull resumes instead of restarting
  * downstream stages never touch the county's server
  * the raw bytes are kept exactly as received, so you can re-derive
    everything later without re-fetching (the assessor table changes
    under you on the reassessment cycle -- a snapshot is the only way to
    make an analysis reproducible)

A manifest records what was asked for and when, because "which pull is
this?" becomes unanswerable about a week after you stop caring.
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from . import config

USER_AGENT = "mesa-primary-residence-pipeline/1.0 (research; contact: local)"


def _request(url: str, params: dict, timeout: int = 90) -> dict:
    """GET a JSON payload from an ArcGIS REST endpoint."""
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}?{query}", headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    # ArcGIS reports failures inside a 200 response, so check explicitly.
    if isinstance(payload, dict) and "error" in payload:
        raise RuntimeError(f"ArcGIS error: {payload['error']}")
    return payload


def record_count(where: str = None) -> int:
    """How many records match, without downloading any of them."""
    payload = _request(
        f"{config.SERVICE_URL}/query",
        {"where": where or config.WHERE, "returnCountOnly": "true", "f": "json"},
    )
    return payload["count"]


def _page_path(offset: int):
    return config.RAW_DIR / f"page_{offset:07d}.json"


def fetch_all(where: str = None, page_size: int = None,
              refresh: bool = False, limit: int = None) -> dict:
    """Page through the layer, writing one JSON file per page.

    Returns the manifest dict.
    """
    where = where or config.WHERE
    page_size = page_size or config.PAGE_SIZE
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)

    total = record_count(where)
    if limit:
        total = min(total, limit)
    print(f"[fetch] {total} records matching {where!r}")

    manifest = {
        "service_url": config.SERVICE_URL,
        "where": where,
        "fields": config.FIELDS,
        "page_size": page_size,
        "total_records": total,
        "pulled_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "pages": [],
    }

    offset = 0
    while offset < total:
        path = _page_path(offset)

        if path.exists() and not refresh:
            # Cache hit. Read only enough to record the row count.
            features = json.loads(path.read_text())["features"]
            print(f"[fetch] offset {offset:>7}  cached  ({len(features)} rows)")
        else:
            payload = _request(
                f"{config.SERVICE_URL}/query",
                {
                    "where": where,
                    "outFields": ",".join(config.FIELDS),
                    "orderByFields": config.ORDER_BY,
                    "resultOffset": offset,
                    "resultRecordCount": page_size,
                    "returnGeometry": "false",  # geometry triples the payload
                    "f": "json",
                },
            )
            features = payload.get("features", [])
            path.write_text(json.dumps(payload))
            print(f"[fetch] offset {offset:>7}  fetched ({len(features)} rows)")
            time.sleep(0.25)  # be a polite guest on a county server

        manifest["pages"].append({"offset": offset, "rows": len(features)})

        if not features:
            print("[fetch] empty page -- stopping early")
            break
        offset += page_size

    (config.CACHE_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def load_records() -> list:
    """Read every cached page back into a flat list of attribute dicts."""
    if not config.RAW_DIR.exists():
        raise FileNotFoundError(
            f"No cache at {config.RAW_DIR}. Run the fetch stage first."
        )

    records = []
    for path in sorted(config.RAW_DIR.glob("page_*.json")):
        payload = json.loads(path.read_text())
        for feature in payload.get("features", []):
            records.append(feature["attributes"])

    if not records:
        raise ValueError("Cache exists but contains no records.")
    return records
