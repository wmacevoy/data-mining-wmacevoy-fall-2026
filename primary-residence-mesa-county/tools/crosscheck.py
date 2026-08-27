#!/usr/bin/env python3
"""Cross-check the hand-rolled normalizer against usaddress-scourgify.

Run in the optional environment:

    pixi run -e crosscheck python tools/crosscheck.py

Agreement is reassuring but not proof; the interesting output is the
DISAGREEMENTS list, which is where either our abbreviation table has a
gap or scourgify has a parse failure on a local address form.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.addresses import normalize_line  # noqa: E402

try:
    import usaddress
    from scourgify import normalize_address_record
    from scourgify.exceptions import UnParseableAddressError
except ImportError:
    sys.exit("Run this in the crosscheck environment: pixi run -e crosscheck ...")


SAMPLES = [
    "755 Horizon Drive, Grand Junction, CO 81506",
    "755 HORIZON DR, GRAND JUNCTION, CO 81506",
    "2879 B 1/2 Road, Grand Junction, CO 81503",
    "2879 B 1/2 RD, GRAND JUNCTION, CO 81503",
    "641 26 1/2 Rd, Grand Junction, CO 81506",
    "3090 F Rd, Clifton, CO 81520",
    "1250 E Rd, Palisade, CO 81526",
    "123 North Seventh Street, Apt A, Grand Junction, CO 81501",
    "123 N 7TH ST UNIT A, GRAND JUNCTION, CO 81501",
    "PO BOX 1234, Grand Junction, CO 81502",
]


def main():
    print(f"{'input':<52} {'ours':<26} {'scourgify':<26}")
    print("-" * 106)
    disagreements = []

    for raw in SAMPLES:
        ours = normalize_line(raw.split(",")[0])
        try:
            theirs = normalize_address_record(raw)["address_line_1"]
        except UnParseableAddressError:
            theirs = "<unparseable>"
        except Exception as exc:
            theirs = f"<{exc.__class__.__name__}>"

        flag = "" if ours == theirs else "  <-- differs"
        print(f"{raw[:50]:<52} {ours:<26} {theirs:<26}{flag}")
        if ours != theirs:
            disagreements.append((raw, ours, theirs))

    # The known-bad component parse, shown explicitly so it stays visible.
    print("\nusaddress component parse on a lettered grid road:")
    print(" ", dict(usaddress.tag("2879 B 1/2 RD, GRAND JUNCTION, CO 81503")[0]))
    print("  ^ StreetName should be 'B 1/2'. This is why we compare lines.")

    print(f"\n{len(disagreements)} disagreement(s) of {len(SAMPLES)} samples.")


if __name__ == "__main__":
    main()
