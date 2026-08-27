#!/usr/bin/env python3
"""Command line entry point.

    python run.py count                  # how many parcels match --where
    python run.py fetch                  # cached pull (safe to re-run)
    python run.py fetch --limit 2000     # small pull while developing
    python run.py build                  # cache -> out/parcels_match.csv
    python run.py all                    # fetch then build

The stages are separate on purpose. `fetch` is the only one that touches
the network; everything after it works offline from the cache, so you can
iterate on the matching logic without hammering a county server.
"""
import argparse

from pipeline import build as build_stage
from pipeline import config, fetch


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=["count", "fetch", "build", "all"])
    parser.add_argument("--where", default=config.WHERE,
                        help="ArcGIS SQL filter (default: 1=1)")
    parser.add_argument("--limit", type=int,
                        help="stop after roughly N records (development)")
    parser.add_argument("--page-size", type=int, default=config.PAGE_SIZE)
    parser.add_argument("--refresh", action="store_true",
                        help="re-fetch pages already in the cache")
    parser.add_argument("--residential-only", action="store_true",
                        help="keep only PROPTYPE containing RESID")
    args = parser.parse_args()

    if args.stage == "count":
        print(fetch.record_count(args.where))
        return

    if args.stage in ("fetch", "all"):
        fetch.fetch_all(where=args.where, page_size=args.page_size,
                        refresh=args.refresh, limit=args.limit)

    if args.stage in ("build", "all"):
        df = build_stage.build(residential_only=args.residential_only)
        build_stage.write_outputs(df)


if __name__ == "__main__":
    main()
