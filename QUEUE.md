# Queue

The migration to SE1 and DM1 that `HANDOFF-migrate-to-DM1.md` sets out, on branch `adopt-se1-dm1`
(not pushed). Steps 0 to 3 are done; what is left is below. An agent may move an item to *review*;
only Warren marks one *done*. Written 2026-10-29, when the session was closed for later.

## Before resuming

- **Torn work, not this migration's:** `llm/tests/test_zen.py` and `llm/zen/coder.py` (modified),
  `llm/#README.md#`, `primary-residence-mesa-county/#app.py#`, the two
  `mesa-parcels-the-columns-shown-above.*` files, `.vikiignore`, both `pixi.lock`. Do not commit,
  stash, move, or delete any of it.
- **The ten `colorado_river` defects are curriculum** (`DATA-SCIENCE.md`): ask before fixing one or
  adding a check that would catch one.
- **Doctors at close:** `./se --doctor` 0 failed. `./dm --doctor` 1 failed, truly: raw is not
  read-only (parcels `cache/raw/`, item W10). Run both first; a different result means something
  moved.
- **The full check:** `pixi run -e colorado-river lint && pixi run -e colorado-river test`, which
  prints `2 passed`.

## Waiting on Warren

| ID  | Decision | Where | Status |
| --- | -------- | ----- | ------ |
| W1  | Read back `Q1`'s three *(inferred)* assumptions and `Q1/BAR-1` *(invented)*: confirm or correct | `colorado_river/docs/QUESTION_v1.md` | blocked |
| W2  | `README.md` and `colorado_river/README.md` tell students `pixi run app`, `test`, `clean`, which pixi refuses as ambiguous. Change them to `-e colorado-river`? | FINDINGS, "CI has not passed since 2026-08-18" | blocked |
| W3  | USGS retires WaterServices in the first quarter of 2027 (one source says 2027-02-22). Move `usgs.py` to `api.waterdata.usgs.gov` before the spring semester? A source change: stop-and-ask | datasheets; [USGS blog](https://waterdata.usgs.gov/blog/api-waterservices-decom/) | blocked |
| W4  | USGS's `noDataValue` (−999999.0) would be kept as a reading. Handle it, or make it an eleventh lesson? | `colorado_river/docs/PLAN_v1.md`, *Missing data* | blocked |
| W5  | The raw-pull profile behind the datasheets' *(measured)* lines is only in the session scratchpad, under `/private/tmp`, and will not survive a reboot. Add it to `colorado_river/` (e.g. a `profile` task)? | datasheets, *What would show it wrong* | blocked |
| W6  | `DATA-SCIENCE.md`: stays as the course's text, or becomes a pointer at DM1 | handoff step 0 | blocked |
| W7  | Merge `../data-mining` branch `field-report-1` (`d0cd786`, `b6532cb`: the doctor's wrapped-line and holdout-none fixes, with tests; `dm.py` here is already the copy) | `../data-mining` | review |
| W8  | Should DM1's doctor look in `<project>/docs/`? A design decision for DM1 | FINDINGS, last entry | blocked |
| W9  | Push `adopt-se1-dm1` and open a PR; CI runs the fixed commands only then | this branch | blocked |
| W10 | Parcels `cache/raw/` is writable and `fetch` writes there: make it read-only after a fetch, or record why not | `CONTRIBUTING.md`, *Data rules* | blocked |
| W11 | Parcels rows name owners and mailing addresses: what may leave this machine, and what may be published | `CONTRIBUTING.md`, *Data rules* | blocked |

## Next for an agent

| ID  | Task | Status |
| --- | ---- | ------ |
| N1  | Step 4, `primary-residence-mesa-county`: QUESTION, PLAN, datasheet for the ArcGIS parcel service. The bias section is the hard part: draft the questions, do not fill it in for the client (DM1/R10). Needs W11 for anything beyond reading | next |
| N2  | Step 4, `llm`: DM1/A9's case, a language model in the pipeline (version, sample, contamination). `questions.jsonl` is the lab's data, not a `QUESTION_vN`. Leave the torn `llm` files alone | next |
| N3  | Step 4, `ml`: say whether DM1's QUESTION fits a teaching pipeline with no decision behind it; MNIST's test split is read every run, not a holdout | next |
| N4  | Step 4, `occupancy_explorer`: people in the rows (doorway counts, no one identified) | next |
| N5  | DM1 doctor, open: a holdout line whose backticks name a command is read as a path | next, in `../data-mining` |
| N6  | Step 5: the field report, by DM1 ID, from `FINDINGS.md`, as a `GAPS.md` entry in `../data-mining` and the first *For copies* note under its v1.0. Nulls go in too | after N1 to N4 |

Each step-4 project is its own commit, with both doctors before and after.

## Done on this branch

`6aba63a` SE1 and DM1 adopted, phrase test passed · `8e29d26` CI only on `colorado_river` changes ·
`6ab0d7c` `CONTRIBUTING.md` · `b71e86f` `dm.py` re-copied with two doctor fixes · `878c511` `-e
colorado-river` in CI and the full check · `bf07d04` `colorado_river/docs/`: QUESTION_v1, PLAN_v1,
two datasheets. What each found is in `FINDINGS.md`.
