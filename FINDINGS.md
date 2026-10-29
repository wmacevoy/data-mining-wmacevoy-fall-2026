# Findings

What we learned the expensive way: surprises, dead ends, measurements, the attack that worked. The
only document reality writes
([SE1/W10](https://github.com/wmacevoy/software-engineering/blob/v1.3/guide/08-work.md#w10)).
Blameless: say what would have found it, not who should have asked
([SE1/H12](https://github.com/wmacevoy/software-engineering/blob/v1.3/guide/09-people.md#h12)).

This file is at the root, not in `docs/`, because `docs/` is the published GitHub Pages site.
It is also the field report on the DM1 migration (`HANDOFF-migrate-to-DM1.md`, step 5): each entry
names the rule or doctor row it concerns, so it can be sent back to SE1 and DM1 by ID.

## 2026-10-29 — Step 1 baseline: four doctor failures, not the three the handoff recorded

- **What happened:** `se --doctor --offline` gave 11 checks, 4 failed. The handoff note, written
  twelve minutes earlier, recorded 3. The fourth was the handoff hook: an untracked
  `.claude/settings.json`, created after the note, runs `python3 se.py --post` at every session
  start, and `se.py` was not yet in the repository. Copying `se.py` fixed it. Before any change,
  `pixi run lint` and `pixi run test` passed in `default` (2 tests), `occupancy` (8), `ml` (18) and
  `llm` (19), the `llm` run with the uncommitted edits to `llm/tests/test_zen.py` and
  `llm/zen/coder.py` in place. The parcels project was not run: it has its own `pixi.toml`, no lint
  task, and no feature block in the root manifest.
- **Kind:** K2
- **Cost:** none; found by running the baseline before trusting the note
  ([SE1/A11](https://github.com/wmacevoy/software-engineering/blob/v1.3/guide/10-agents.md#a11)).
- **Findable by:** the handoff's own instruction: run the baseline, and the repository wins.
- **Changed:** the hook is now tracked, so a clone gets it and `se.py` beside it.

## 2026-10-29 — Step 1: SE1 and DM1 adopted; the phrase test passed

- **What happened:** copied `AGENTS.md`, `se`, `se.ps1`, `se.py` from SE1 at tag v1.3.1, and
  `AGENTS-DM.md`, `dm`, `dm.ps1`, `dm.py` from DM1 at commit `f5ccfea` (untagged; the copy says
  v1.0). Each is byte-identical to its source. `CLAUDE.md` imports both by name. Both doctors: 0
  failed (SE1 11 checks, DM1 23). Phrase test (SE1 ADOPT.md step 2): a fresh `claude -p` session,
  Claude Code 2.1.312, with Read, Bash, Grep, Glob, Edit, Write, WebFetch, WebSearch, Agent and
  NotebookEdit denied, quoted verbatim the first sentence under *After a gap* in `AGENTS.md` and
  the *Load both files at every start* sentence in `AGENTS-DM.md`.
- **Kind:** K2
- **Cost:** one failed attempt: `claude -p --disallowedTools a,b "prompt"` reads every word of the
  prompt as another tool name, because the flag takes a variable number of arguments, then stops
  with *Input must be provided*. Giving the prompt on stdin works.
- **Findable by:** ADOPT.md step 2 giving the command, not only the idea.
- **Changed:** none yet; for SE1: the phrase test in ADOPT.md could show a working `-p` command.

## 2026-10-29 — SE1 doctor: the repository-guide row changes source when CLAUDE.md appears

- **What happened:** before `CLAUDE.md` existed, the *repository guide* row read README.md and
  passed on a false reading (`.github/workflows/ci.yaml`, the first backtick on a line with
  "tests"), so the *CI* row failed. With `CLAUDE.md` present, the same row reads `CLAUDE.md`,
  reports *none yet*, and *CI* drops to a warn. The false reading disappeared without the doctor
  saying why; README.md did not change.
- **Kind:** K3 for the first reading (the row said pass, on the wrong command)
- **Cost:** a reader comparing the two runs would think something was fixed.
- **Findable by:** a fixture: README.md naming no *The full check* line, run with and without a
  `CLAUDE.md`.
- **Changed:** none yet; for SE1 (`se.py`): a README with no *The full check* line gives *none yet*,
  and the row names the file it read.

## 2026-10-29 — DM1 doctor: the data-working-agreement row claims a test it did not run

- **What happened:** the row passes with "observed loading: a fresh session can quote a line of
  each". The doctor did not observe that; it read the imports. SE1's *loads at every start* row on
  the same run says it correctly: configured, and the phrase test is how loading is observed.
- **Kind:** K3 factory
  ([SE1/U7](https://github.com/wmacevoy/software-engineering/blob/v1.3/guide/02-unknowing.md#u7)):
  a pass that reads as observed when it is configured.
- **Cost:** none here, because the phrase test was run anyway.
- **Findable by:** reading the row's text against what the check does.
- **Changed:** none yet; for DM1 (`dm.py`): word the row as SE1's is, *configured*, with the phrase
  test as the observation.

## 2026-10-29 — DM1 adds nothing at session start

- **What happened:** `dm.py` has no `--post` or `--hook`. The SessionStart hook runs SE1's self test
  only; nothing DM1-specific (raw read-only, the holdout, data about people) is checked or said at
  start.
- **Kind:** K2
- **Cost:** unknown; possibly a null, if `AGENTS-DM.md` loaded at start is enough.
- **Findable by:** asking what `./se --post` is for and whether data work needs the same.
- **Changed:** none yet; a question for DM1 (`GAPS.md`).

## 2026-10-29 — CI checks one project of five

- **What happened:** `.github/workflows/ci.yaml` runs `pixi run lint` and `pixi run test` in the
  default environment only, which is `colorado_river`. `occupancy`, `ml` and `llm` are never linted
  or tested in CI, and the parcels project is outside the root manifest.
- **Kind:** K2
- **Cost:** none yet; it shapes step 2, where *the full check* is either narrower than the repository
  or CI grows to match it
  ([SE1/O3](https://github.com/wmacevoy/software-engineering/blob/v1.3/guide/07-operating.md#o3)).
- **Findable by:** reading CI against `[environments]` in `pixi.toml`.
- **Changed:** none yet; Warren's call in step 2.

## 2026-10-29 — The working set's default home is the published site

- **What happened:** SE1 puts the working set in `docs/` (`docs/FINDINGS.md`, `docs/QUEUE.md`), and
  DM1's doctor reads `QUESTION_vN` and `PLAN_vN` at the root or in `docs/` only. Here `docs/` is
  deployed as GitHub Pages, so every working-set file there would be published. Decided: each
  project's working set goes in `<project>/docs/`, and this file is at the root.
- **Kind:** K2
- **Cost:** none, caught before writing anything there.
- **Findable by:** `docs/_config.yml`.
- **Changed:** the decision above. For DM1: its templates and doctor assume one project per
  repository and a private `docs/`; the doctor will not find `<project>/docs/QUESTION_v1.md` yet.

## 2026-10-29 — Step 2: CONTRIBUTING.md written; the doctors went from 0 failed to 1, wrongly

- **What happened:** with `CONTRIBUTING.md` from DM1's template, SE1's *repository guide* and *CI*
  rows pass (`pixi run lint && pixi run test`, both run by the workflow), and DM1's *raw to report*
  passes. DM1's *holdout* row fails: "ml: tracked by git, so in every clone and every agent's reach;
  llm: …". The line it read says there is no holdout, and names `ml` and `llm` in backticks as the
  projects whose test sets are not holdouts; the doctor took every backtick on the line as a path
  to the holdout, and the project directories are tracked.
- **Kind:** K3 (the doctor was sure, and wrong)
- **Cost:** a false failure in every session from here on, until the doctor or the line changes;
  the line was left true rather than reworded to satisfy it.
- **Findable by:** a fixture: `**The holdout:** none, in any project. \`ml\` scores every run on its
  test split.` should give *none yet*, not a failure.
- **Changed:** fixed in DM1 (`b6532cb` on its branch `field-report-1`, with a test): a plan or
  CONTRIBUTING holdout line that starts with *none* gives *none yet*, unless a tracked file is named
  holdout. `dm.py` re-copied; the row now reads "CONTRIBUTING.md says there is none". Still open:
  a backtick that is a command (`make split`) on a line that does name a path is read as a path.

## 2026-10-29 — DM1 doctor: `field()` never reads a wrapped line

- **What happened:** the *raw is read-only* row said "CONTRIBUTING.md's *Raw data* line names no
  path", but the path is on the line's second, indented row. `field()` splits the text after the
  match, and the first piece is the empty rest of the matched line, so the loop stops before any
  continuation: `field('**A:** x\n  y\n', 'A')` returns `'x'`. Every field the doctor reads (raw,
  holdout, raw to report, the datasheet's *This sheet*, the plan's fields) is cut at its first
  line. Read correctly, the row would fail, and rightly: all 80 files under
  `primary-residence-mesa-county/cache/raw/` are writable.
- **Kind:** K3
- **Cost:** a row that says *none yet* where the truth is a failure; found only because the row
  disagreed with the file.
- **Findable by:** that one-line fixture, as a test in DM1.
- **Changed:** fixed in DM1 (`d0cd786` on its branch `field-report-1`, with a test that wraps the
  fixture's raw line). `dm.py` re-copied, unedited; the row now fails, truly: "80 of 80 files under
  `primary-residence-mesa-county/cache/raw/` are writable". Making them read-only waits for that
  project's migration, since `fetch` writes there.

## 2026-10-29 — DM1's CONTRIBUTING template assumes one project, one command, one line

- **What happened:** the template has one *Raw to report*, one *Raw data*, one *Success prints*.
  Here five projects each have their own, and the full check prints two lines (`All checks passed!`
  from ruff, `2 passed` from pytest). The answer was a *Projects* table, with the bold lines about
  `colorado_river`, the one CI checks. The template also has no way to say *none yet* where the
  doctor parses a command: a *Raw to report* line with no backtick fails as an unfilled
  placeholder (`check_raw_to_report`), read from the code, not run.
- **Kind:** K2
- **Cost:** a table the doctor cannot read, so for four of the five projects it checks nothing.
- **Findable by:** the course shape itself: one root, several projects (the handoff's
  *Found while surveying*).
- **Changed:** none yet; for DM1: say what a multi-project repository does, and teach the doctor
  `<project>/docs/` and a projects table, or say it reads one project.

## 2026-10-29 — Raw is not read-only in the one project that keeps raw

- **What happened:** `primary-residence-mesa-county/cache/raw/` is the only raw data in the
  repository (80 JSON pages from the county's ArcGIS service), and every file is writable;
  `fetch` writes there
  ([DM1/D6](https://github.com/wmacevoy/data-mining/blob/main/guide/05-design.md#d6)). The three
  other data projects keep caches that `clean` deletes and that are not raw: the remote service is
  the authority, and USGS revises its provisional values. `colorado_river`'s cache records no
  provenance, which is one of its lessons.
- **Kind:** K2
- **Cost:** none yet.
- **Findable by:** `find primary-residence-mesa-county/cache/raw -type f -perm -u+w`.
- **Changed:** recorded in `CONTRIBUTING.md`; whether to make it read-only is Warren's call, with
  that project's migration (step 4).

## 2026-10-29 — CI has not passed since 2026-08-18; the full check written in step 2 did not run

- **What happened:** `pixi run lint` and `pixi run test` stop with "the task 'lint' is ambiguous":
  every project defines `lint`, `test`, `app`, and `clean`, and pixi 0.76.2 will not pick the
  default environment for a name more than one environment has. CI runs exactly those commands, and
  has failed on all three platforms on every push since 2026-10-15 (three runs); the run before,
  2026-08-20, failed on a cache-key error; the last success was 2026-08-18. Step 2 wrote the
  same bare commands into `CONTRIBUTING.md` as the full check, and both doctors passed it, because
  they compare text and do not run it. The baseline had run them with `-e default`, so it never saw
  the failure. The README's everyday commands (`pixi run app`, `test`, `lint`, `clean`) fail the
  same way for a student; `px` and `meta`, defined once, still work.
- **Kind:** K3 (a check passed in the doctor and in this file, and could not run)
- **Cost:** two and a half months of red CI that read, in the handoff and here, as "CI runs lint and
  tests on three platforms"; one commit of `CONTRIBUTING.md` that was false.
- **Findable by:** running the full check exactly as written, bare, before writing it down
  ([SE1/A2](https://github.com/wmacevoy/software-engineering/blob/v1.3/guide/10-agents.md#a2)); `gh
  run list --workflow CI`. For SE1 and DM1: a doctor that passes a check command it never ran says
  *configured*, not *pass*, as its hook row already does.
- **Changed:** CI and `CONTRIBUTING.md` name the environment: `pixi run -e colorado-river lint &&
  pixi run -e colorado-river test`, which passes here (ruff clean, 2 passed). The README and
  `colorado_river/README.md` still give the bare commands: Warren's call, since students read them.

## 2026-10-29 — Step 3: colorado_river's QUESTION, PLAN, and datasheets; what the templates cost

- **What happened:** wrote `colorado_river/docs/QUESTION_v1.md`, `PLAN_v1.md`, and
  `datasheets/usgs-iv.md` and `usgs-dv.md`, from Warren's account (the question was "explore an
  ingress data set with local interest and demonstrate the beginning of a data pipeline") and a raw
  pull of all three gauges, kept outside the repository. The project is descriptive and teaches;
  DM1's question and plan are shaped for a prediction. Not applicable, and said so: PRED-1's
  prediction point, the price of errors as false positive and negative (kept: it fit the lessons
  well), the split, the holdout, the baseline, the interval, the search budget, labels, the ledger.
  BIAS-1 is *none*, because no row is about a person — but the bias table's *Measurement* row is
  where the provisional and estimated values surfaced, so it earned its place.
- **Kind:** K2
- **Cost:** about half the question and plan say *not applicable*. That is cheap to write and cheap
  to read, and it is now on record why.
- **Findable by:** the handoff's step 4 question for `ml`, asked here too: does DM1's QUESTION fit a
  teaching pipeline? It fits with a *Decision* about the course, not the data.
- **Changed:** none yet; for DM1: a descriptive or teaching project is a named case in the
  templates (the decision is who uses the result; PRED-1 becomes "what is knowable at a fetch").

## 2026-10-29 — The datasheet's *Knowable at* found what the lesson table does not list

- **What happened:** looking at the raw data before writing columns (DM1 AGENTS.md, *Before you
  start*) found, on 2026-10-29: none of the three gauges serves salinity, and only the state-line
  gauge serves daily water temperature, and the app omits both sections without saying why; every
  IV reading in a 7-day pull is provisional, and every DV series is provisional after one date
  (2025-11-12 to 2026-06-02 by series); 62 to 93 days per gauge in 5 years are estimated, mostly
  winter; the pipeline drops the qualifier that says which, and does not handle USGS's
  `noDataValue` (−999999.0), none of which appeared; and USGS retires WaterServices in the first
  quarter of 2027, with degradation possible from August 2026 (USGS water data blog, updated
  2026-10-17), so the reference project's source ends during the spring semester.
- **Kind:** K2, and for the source's end, a K3 waiting to happen
- **Cost:** none yet. Nothing was fixed: the qualifier and cache problems are the listed lessons,
  and the `noDataValue`, the silent omissions, and the migration are Warren's to decide.
- **Findable by:** DM1/R6's column, filled from a profile of raw data, not from the code.
- **Changed:** recorded in the datasheets' *Known problems* and the question's *Not for* and *Not
  yet answered*.

## 2026-10-29 — DM1 doctor: a project's working set in `<project>/docs/` is invisible

- **What happened:** from the root, the doctor reports *none yet* for question, plan, and
  datasheets. It reads `docs/QUESTION_vN` and `docs/PLAN_vN` only, and finds datasheets only as
  `docs/datasheets/*.md` at the root or a file named `datasheet*`. Run on the project as the
  repository (`./dm --doctor --repo colorado_river`): the question passes (5 IDs, bias measure set,
  *Not for* present, every citation versioned), the datasheets pass (2 sheets, 11 columns, each
  with *Knowable at*), the holdout reads *none yet*, the plan warns "baseline not yet scored on a
  date", which is wrong for a plan that says nothing is scored, and the agreement row fails, rightly
  for that root.
- **Kind:** K2 (expected: the handoff predicted it)
- **Cost:** the doctor checks the root, where there is nothing, and not the project, where there is.
- **Findable by:** the fixture: this repository, with `colorado_river/docs/` and the agreements at
  the root.
- **Changed:** none yet; for DM1: either the doctor learns `<project>/docs/` (one row per project),
  or the guide says one project per doctor run with `--repo`, and the agreement rows look upward;
  and the plan row takes *not applicable* for a baseline.
