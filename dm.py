#!/usr/bin/env python3
"""dm: the data-mining guide's command-line companion, beside se.py in a repository that follows both.

  dm --doctor   Is the data project sound? Runs SE1's doctor (se.py, found beside this file, or by
                SE_PY, SE_GUIDE, .se1/, or ../software-engineering/) and adds the rows DM1 asks to be
                mechanical rather than told: both working agreements loaded and the SE1 release the data
                one extends against the SE1 copy present, the question and its
                one-way doors, the plan, where the holdout lives and whether it is in reach, a
                datasheet per source with every column's knowable-at, raw read-only, the one command
                from raw to report, the ledger and who writes it, the model card and its bias audit,
                the recorded environment, and citations of the question. Read-only.
                "none yet" is a true answer: a guide, or a project on day one, has none of these.

Standard library only, Python 3.9 or later. This copy is from the guide release named in RELEASE.
Every threshold and heuristic here is invented and has not yet met a real project (GAPS.md, 7).
"""
import argparse
import csv
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

RELEASE = "v1.0"
GUIDE_REPO = "wmacevoy/data-mining"
SE_REPO = "wmacevoy/software-engineering"

Finding = namedtuple("Finding", "name ids state text fix")  # state: pass | warn | none yet | fail
PASS, WARN, NONE, FAIL = "pass", "warn", "none yet", "fail"
WORST = {PASS: 0, NONE: 1, WARN: 2, FAIL: 3}
LABEL_RE = re.compile(r"This copy is\s+from\s+\*\*(v\d+\.\d+)\*\*")
# The SE1 release a DM1 copy was written against: the link to SE1's AGENTS.md its header carries.
EXTENDS_RE = re.compile(r"software-engineering/blob/(v\d+\.\d+(?:\.\d+)?)/AGENTS\.md")
DM_NAME, SE_NAME = "AGENTS-DM.md", "AGENTS.md"  # the guide's names for the two copies; any name is accepted
ID_RE = re.compile(r"\*\*([A-Z]{2,}-\d+)\*\*\s*\*\(since v(\d+)\)\*")
PLACEHOLDER_RE = re.compile(r"_(…|\.\.\.|path|command|name|date|yyyy-mm-dd|who|whom|what)[^_\n]{0,40}_|^_[^_\n]+_$|^\s*$")
CODE_SUFFIXES = {".py", ".r", ".jl", ".js", ".ts", ".sh", ".sql", ".ipynb", ".mk", ".ps1", ""}
LOCKS = ("pixi.lock", "conda-lock.yml", "environment.yml", "environment.yaml", "requirements.txt",
         "requirements.lock", "poetry.lock", "uv.lock", "Pipfile.lock", "renv.lock", "package-lock.json")


# ---------------------------------------------------------------- small helpers (no se.py needed)

def read(path):
    try:
        return Path(path).read_text(encoding="utf8", errors="replace")
    except OSError:
        return ""


def run(cmd, cwd=None, timeout=20):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout.decode("utf8", errors="replace")
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


def tracked_files(repo):
    rc, out = run(["git", "ls-files", "-z"], cwd=repo)
    if rc != 0:
        return [p for p in Path(repo).rglob("*") if p.is_file() and ".git" not in p.parts]
    return [Path(repo) / f for f in out.split("\0") if f]


def is_text(path):
    return path.suffix.lower() in {".md", ".txt", ".py", ".r", ".jl", ".js", ".ts", ".sh", ".yml", ".yaml", ".toml",
                                   ".json", ".sql", ".cfg", ".ini", ".ps1", ".ipynb", ""}


def placeholder(value):
    """True for a template field nobody filled in: `_…_`, `_path_`, `_command_`, or nothing at all."""
    return bool(PLACEHOLDER_RE.search(value.strip()))


def parse_tables(text):
    """Every Markdown table in the text, as a list of row dicts with lowercased headers."""
    tables, rows, header = [], [], None
    for line in text.splitlines() + [""]:
        if not line.strip().startswith("|"):
            if header is not None:
                tables.append(rows)
            rows, header = [], None
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        rows.append(dict(zip(header, cells)))
    return tables


def real_rows(rows):
    """Table rows that are not the template's italic example row."""
    return [r for r in rows if not all(placeholder(v) or (v.startswith("_") and v.endswith("_")) for v in r.values() if v)]


def section(text, heading):
    """The text under `## heading` (any level), to the next heading of the same or higher level."""
    m = re.search(rf"^(#+)\s*{re.escape(heading)}\b.*$", text, re.I | re.M)
    if not m:
        return None
    level = len(m.group(1))
    rest = text[m.end():]
    n = re.search(rf"^#{{1,{level}}}\s", rest, re.M)
    return rest[: n.start()] if n else rest


def field(text, name):
    """The value after `**Name:**` on its line (and continuation lines), or None."""
    m = re.search(rf"\*\*{re.escape(name)}:?\*\*:?\s*(.*)", text, re.I)
    if not m:
        return None
    value, lines = m.group(1), text[m.end():].splitlines()
    for line in lines:
        if line.startswith("  ") and not line.lstrip().startswith(("-", "*", "|")):
            value += " " + line.strip()
        else:
            break
    return value


def backtick_paths(value):
    return [p for p in re.findall(r"`([^`]+)`", value or "") if not placeholder(p)]


def claude_imports(claude_md):
    out = []
    for line in read(claude_md).splitlines():
        m = re.match(r"^@(\S+)", line.strip())
        if m:
            p = Path(os.path.expanduser(m.group(1)))
            out.append(p if p.is_absolute() else Path(claude_md).parent / p)
    return out


def latest_doc(repo, stem):
    """(path, version) of the highest docs/STEM_vN.md (or at the root), or (None, 0)."""
    found = []
    for d in (Path(repo) / "docs", Path(repo)):
        for p in d.glob(f"{stem}_v*.md"):
            m = re.search(r"_v(\d+)\.md$", p.name)
            if m:
                found.append((int(m.group(1)), p))
    if not found:
        return None, 0
    v, p = max(found)
    return p, v


SKIP_DIRS = {"templates", "node_modules", "site-packages"}  # the guide's own templates; other people's files


def find_docs(repo, patterns):
    """Project documents matching the glob patterns. Dot-directories (.pixi, .venv, .git) and installed
    packages are not the project: the first real repository offered a library's model_card_template.md."""
    repo = Path(repo)
    out = []
    for pat in patterns:
        for p in sorted(repo.glob(pat)):
            parts = p.relative_to(repo).parts[:-1]
            if p.is_file() and p not in out and not any(d.startswith(".") or d in SKIP_DIRS for d in parts):
                out.append(p)
    return out


def rel(repo, path):
    """A path as the report prints it: relative to the repository, forward slashes on every platform."""
    try:
        return Path(path).resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def worst(states):
    return max(states, key=lambda s: WORST[s]) if states else PASS


# ---------------------------------------------------------------- finding se.py

def find_se(repo):
    """SE1's se.py: beside this file, then SE_PY, SE_GUIDE/se.py, the repository, .se1/, ../software-engineering/.
    Returns (module, path) or (None, None)."""
    here = Path(__file__).resolve().parent
    cands = [here / "se.py"]
    if os.environ.get("SE_PY"):
        cands.append(Path(os.environ["SE_PY"]))
    if os.environ.get("SE_GUIDE"):
        cands.append(Path(os.environ["SE_GUIDE"]) / "se.py")
    cands += [Path(repo) / "se.py", Path(repo) / ".se1" / "se.py", here.parent / "software-engineering" / "se.py"]
    for c in cands:
        if c.is_file():
            try:
                spec = importlib.util.spec_from_file_location("se", c)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "doctor"):
                    return mod, c
            except Exception:  # a stub copy, or a broken one: the row below says so
                continue
    return None, None


# ---------------------------------------------------------------- the rows

def find_copies(repo):
    """(dm_path, dm_label, se_path, se_label): the DM1 and SE1 working agreements, wherever they are and whatever
    they are called, told apart by which guide they link to (the guide's names: AGENTS.md for SE1's, AGENTS-DM.md)."""
    repo = Path(repo)
    cands = [p for pat in ("AGENTS*.md", "docs/AGENTS*.md", ".claude/AGENTS*.md") for p in sorted(repo.glob(pat))]
    cands += claude_imports(repo / "CLAUDE.md")
    dm, se, seen = (None, None), (None, None), set()
    for c in cands:
        try:
            r = c.resolve()
        except OSError:
            continue
        if r in seen or not c.is_file():
            continue
        seen.add(r)
        t = read(c)
        m = LABEL_RE.search(t)
        label = m.group(1) if m else None
        if GUIDE_REPO in t and dm[0] is None:
            dm = (c, label)
        elif SE_REPO in t and dm[0] != c and se[0] is None:
            se = (c, label)
    return dm + se


def check_agreements(repo):
    repo = Path(repo).resolve()
    dm, dm_label, se, se_label = find_copies(repo)
    name, ids = "data working agreement", "DM1/A1, SE1/A11"
    if not dm:
        return Finding(name, ids, FAIL, "no copy of the data-mining AGENTS.md: none at the root, in docs/, or imported by CLAUDE.md",
                       f"copy it from the guide ({GUIDE_REPO}) as {DM_NAME} beside SE1's {SE_NAME}, and import both from CLAUDE.md")
    if not dm_label:
        return Finding(name, ids, FAIL, f"{rel(repo, dm)} carries no release label",
                       "re-copy it from a release: a copy that cannot say which release it is cannot say it is behind")
    if not se:
        return Finding(name, ids, FAIL, f"{rel(repo, dm)} is {dm_label}, but the SE1 AGENTS.md it extends is not here",
                       "copy SE1's AGENTS.md beside it (SE1's ADOPT.md, step 1); every SE1 rule it leans on is in that file")
    claude = repo / "CLAUDE.md"
    if claude.is_file():
        imports = [p.resolve() for p in claude_imports(claude) if p.exists()]
        missing = [rel(repo, p) for p in (dm, se) if p.resolve() not in imports]
        if missing:
            return Finding(name, ids, FAIL, f"CLAUDE.md does not import {', '.join(missing)}",
                           "a CLAUDE.md switches off Claude Code's own AGENTS.md read; import both copies from inside the working directory")
        names = "" if (dm.name, se.name) == (DM_NAME, SE_NAME) else f" (the guide's names are {SE_NAME} for SE1's and {DM_NAME} for this one)"
        return Finding(name, ids, PASS, f"[Claude Code configuration] {rel(repo, dm)} ({dm_label}) and {rel(repo, se)} "
                       f"({se_label or 'no label'}), both imported by CLAUDE.md from inside the working directory; observed "
                       f"loading: a fresh session can quote a line of each{names}", "")
    loaded = [p for p in (dm, se) if p.resolve() == (repo / "AGENTS.md").resolve()]
    other = [rel(repo, p) for p in (dm, se) if p not in loaded]
    return Finding(name, ids, FAIL, f"[Claude Code configuration] no CLAUDE.md: AGENTS.md is read by itself and nothing loads {', '.join(other)}",
                   "add a CLAUDE.md that imports both copies by name")


def check_extends(repo):
    """The DM1 copy says which SE1 release it was written against; the SE1 copy here says which it is."""
    repo = Path(repo).resolve()
    dm, dm_label, se, se_label = find_copies(repo)
    name, ids = "extends", "SE1/U7, SE1/U9"
    if not dm or not se:
        return Finding(name, ids, NONE, "needs both copies to compare", "")
    m = EXTENDS_RE.search(read(dm))
    if not m:
        return Finding(name, ids, WARN, f"{rel(repo, dm)} does not say which SE1 release it extends", "re-copy it from a release whose header links SE1's AGENTS.md at a tag")
    pin = m.group(1)
    if not se_label:
        return Finding(name, ids, WARN, f"{rel(repo, dm)} extends SE1 {pin}; {rel(repo, se)} carries no label to compare", "re-copy SE1's AGENTS.md from a release")
    minor = lambda v: tuple(int(x) for x in v[1:].split(".")[:2])
    if minor(se_label) > minor(pin):
        return Finding(name, ids, WARN, f"{rel(repo, dm)} ({dm_label}) extends SE1 {pin}; the SE1 copy here is {se_label}: what changed between them, this guide has not reviewed",
                       f"read SE1's CHANGELOG from {pin}; the guide's next release says what it reframed, declined, or confirmed")
    if minor(se_label) < minor(pin):
        return Finding(name, ids, FAIL, f"{rel(repo, se)} is SE1 {se_label}, older than the {pin} this guide's copy extends: rules it leans on are missing",
                       f"re-copy SE1's AGENTS.md at {pin} or newer")
    return Finding(name, ids, PASS, f"{rel(repo, dm)} ({dm_label}) extends SE1 {pin}; the SE1 copy here is {se_label}", "")


def check_question(repo):
    q, v = latest_doc(repo, "QUESTION")
    name = "question"
    if not q:
        return Finding(name, "DM1/R1, DM1/R2, DM1/W6", NONE, "no docs/QUESTION_vN.md",
                       "treat the task's text as the question, marked (inferred); the decision, the unit, the outcome, and the prediction point come first"), None, 0, {}
    text = read(q)
    ids = {m.group(1): int(m.group(2)) for m in ID_RE.finditer(text)}
    doors = {"UNIT": "the unit", "OUT": "the outcome", "PRED": "the prediction point"}
    unset = [f"{p}-n ({what})" for p, what in doors.items() if not any(i.startswith(p + "-") for i in ids)]
    blank = []
    for m in ID_RE.finditer(text):
        line = text[m.start(): text.find("\n", m.end()) if text.find("\n", m.end()) != -1 else len(text)]
        if placeholder(line.split("*", 4)[-1] if "*" in line else line):
            blank.append(m.group(1))
    if unset:
        return Finding(name, "DM1/R2", FAIL, f"QUESTION_v{v} leaves a one-way door unset: {', '.join(unset)}",
                       "fix the unit, the outcome, and the prediction point before anything else"), q, v, ids
    if blank:
        return Finding(name, "DM1/R2, DM1/R3", FAIL, f"QUESTION_v{v}: {', '.join(blank[:4])} still carry the template's placeholder",
                       "a definition that is not written is decided privately by whoever writes the first join"), q, v, ids
    if not any(i.startswith("BAR-") for i in ids):
        return Finding(name, "DM1/R3", FAIL, f"QUESTION_v{v} sets no bar (BAR-n) before results are seen",
                       "write the metric, the split, and the number that would count as failure, now"), q, v, ids
    if not any(i.startswith("BIAS-") for i in ids):
        return Finding(name, "DM1/R10", FAIL, f"QUESTION_v{v} names no bias measure (BIAS-n)",
                       "bias is always a requirement; choosing the measure belongs to people"), q, v, ids
    if section(text, "Not for") is None:
        return Finding(name, "DM1/R11", WARN, f"QUESTION_v{v} has no *Not for* section",
                       "say what the model is not for; it will still answer there"), q, v, ids
    return Finding(name, "DM1/R2, DM1/R3, DM1/R10", PASS,
                   f"QUESTION_v{v}: {len(ids)} IDs; unit, outcome, prediction point, bar, and bias measure set; Not for present", ""), q, v, ids


def check_plan(repo, have_question):
    p, v = latest_doc(repo, "PLAN")
    name = "plan"
    if not p:
        if have_question:
            return Finding(name, "DM1/F6, DM1/R3", WARN, "no docs/PLAN_vN.md: the split, metric, baseline, and slices are being chosen as results arrive",
                           "write it before the outcome is examined; departing from it later is normal, departing silently is the problem")
        return Finding(name, "DM1/F6", NONE, "no docs/PLAN_vN.md", "")
    text = read(p)
    m = re.search(r"Outcome examined yet\??\s*:?\s*\**\s*([^·\n]*)", text, re.I)
    examined = m.group(1).strip(" _*") if m else "?"
    holdout = field(text, "Holdout")
    if holdout is None or placeholder(holdout):
        return Finding(name, "DM1/F5", FAIL, f"PLAN_v{v}: the holdout has no stated home, reader, or spending rule",
                       "say where it is kept, who may read it, and when it will be spent")
    baseline = field(text, "Baseline")
    notes = []
    if baseline is None or placeholder(baseline) or not re.search(r"\d{4}-\d{2}-\d{2}", baseline):
        notes.append("baseline not yet scored on a date")
    slices = section(text, "Slices") or ""
    n_slices = sum(len(real_rows(t)) for t in parse_tables(slices))
    if n_slices == 0:
        notes.append("no slices chosen before results")
    if notes:
        return Finding(name, "DM1/T1, DM1/T9", WARN, f"PLAN_v{v}: " + "; ".join(notes) + f"; outcome examined: {examined.strip()}",
                       "the baseline and the slices are chosen now so they are not chosen to flatter")
    return Finding(name, "DM1/F5, DM1/T1, DM1/T9", PASS,
                   f"PLAN_v{v}: holdout named, baseline scored, {n_slices} slice(s); outcome examined: {examined.strip()}", "")


def holdout_sources(repo):
    """Lines that say where the holdout lives: the plan's Holdout field and CONTRIBUTING's."""
    out = []
    p, _ = latest_doc(repo, "PLAN")
    if p:
        h = field(read(p), "Holdout")
        if h is not None:
            out.append((rel(repo, p), h))
    for guide in ("CONTRIBUTING.md", "CLAUDE.md"):
        h = field(read(Path(repo) / guide), "The holdout") or field(read(Path(repo) / guide), "Holdout")
        if h is not None:
            out.append((guide, h))
    return out


def check_holdout(repo):
    repo = Path(repo).resolve()
    name, ids = "holdout", "DM1/F5, DM1/A4"
    sources = holdout_sources(repo)
    tracked = tracked_files(repo)
    named = [rel(repo, f) for f in tracked if "holdout" in f.name.lower() and f.suffix.lower() not in (".md", ".py", ".txt")]
    states, texts = [], []
    if named:
        states.append(FAIL)
        texts.append(f"a tracked file is named holdout ({named[0]}): in every clone, and in every agent's reach")
    if not sources:
        if not named:
            return Finding(name, ids, NONE, "no plan or CONTRIBUTING line says where the holdout lives", "")
    paths = [(src, p) for src, line in sources for p in backtick_paths(line)]
    if sources and not paths and not any(placeholder(line) for _, line in sources):
        states.append(WARN)
        texts.append(f"{sources[0][0]} names the holdout without a path: {sources[0][1][:60]!r}")
    for src, p in paths:
        path = Path(os.path.expanduser(p))
        path = path if path.is_absolute() else repo / path
        try:
            inside = str(path.resolve()).startswith(str(repo) + os.sep) or path.resolve() == repo
        except OSError:
            inside = False
        if not inside:
            states.append(PASS)
            texts.append(f"{p}: outside the working directory")
            continue
        rc, _ = run(["git", "ls-files", "--error-unmatch", "--", str(path)], cwd=repo)
        if path.exists() and rc == 0:
            states.append(FAIL)
            texts.append(f"{p}: tracked by git, so in every clone and every agent's reach")
        elif path.exists() and os.access(path, os.R_OK):
            states.append(FAIL)
            texts.append(f"{p}: present and readable from the working directory")
        elif path.exists():
            states.append(PASS)
            texts.append(f"{p}: present, not readable by this user")
        else:
            # a pattern like `data/holdout/` matches only a directory; an absent path is one if it was written with a slash
            rc, _ = run(["git", "check-ignore", "-q", "--", str(path) + ("/" if p.rstrip().endswith("/") else "")], cwd=repo)
            if rc == 0:
                states.append(PASS)
                texts.append(f"{p}: not here, and git-ignored")
            else:
                states.append(WARN)
                texts.append(f"{p}: not here, and not git-ignored: if it appears it will be tracked")
    state = worst(states)
    fix = "" if state == PASS else "keep it outside the working directory, or behind a permission the agent lacks; spend it yourself, at a decision"
    return Finding(name, ids, state, "; ".join(texts), fix)


def check_datasheets(repo):
    name, ids = "datasheets", "DM1/R5, DM1/R6, DM1/D13"
    sheets = find_docs(repo, ("docs/datasheets/*.md", "docs/DATASHEET*.md", "**/DATASHEET*.md", "**/datasheet*.md"))
    if not sheets:
        return Finding(name, ids, NONE, "no datasheet", "one per source, drafted as a proposal rather than guessed (AGENTS.md: Before you start)")
    bad, unsigned, cols = [], [], 0
    for s in sheets:
        text = read(s)
        tables = [t for t in parse_tables(text) if t and any("knowable" in k for k in t[0])]
        if not tables:
            bad.append(f"{rel(repo, s)}: no Columns table with a *Knowable at* column")
            continue
        for row in real_rows(tables[0]):
            cols += 1
            col = next((v for k, v in row.items() if k == "column"), "?")
            know = next((v for k, v in row.items() if "knowable" in k), "")
            if placeholder(know):
                bad.append(f"{rel(repo, s)}: column {col} does not say when it becomes knowable")
        if field(text, "This sheet") is None:
            unsigned.append(rel(repo, s))
    if bad:
        return Finding(name, ids, FAIL, f"{len(sheets)} datasheet(s); " + "; ".join(bad[:3]) + (" ..." if len(bad) > 3 else ""),
                       "the knowable-at column is the leakage check that runs before any model exists")
    if unsigned:
        return Finding(name, "SE1/U9", WARN, f"{len(sheets)} datasheet(s), {cols} columns, every one says when it becomes knowable; "
                       f"{unsigned[0]} does not say who wrote it or what would show it wrong", "the template's *This sheet* line")
    return Finding(name, ids, PASS, f"{len(sheets)} datasheet(s), {cols} columns, every one says when it becomes knowable", "")


def check_raw(repo):
    repo = Path(repo).resolve()
    name, ids = "raw is read-only", "DM1/D6"
    line = field(read(repo / "CONTRIBUTING.md"), "Raw data")
    if line is None:
        return Finding(name, ids, NONE, "CONTRIBUTING.md has no *Raw data* line saying where raw lives", "templates/CONTRIBUTING.md, Data rules")
    paths = backtick_paths(line)
    if not paths:
        return Finding(name, ids, NONE, "CONTRIBUTING.md's *Raw data* line names no path", "fill in the template's placeholder")
    p = paths[0]
    path = Path(os.path.expanduser(p))
    path = path if path.is_absolute() else repo / path
    if not path.exists():
        return Finding(name, ids, NONE, f"raw ({p}) is not present here", "fetched on demand? then the fetch records when and from where (DM1/D2)")
    files = [f for f in (path.rglob("*") if path.is_dir() else [path]) if f.is_file()]
    if not files:
        return Finding(name, ids, NONE, f"raw ({p}) is empty", "")
    writable = [f for f in files if os.access(f, os.W_OK)]
    if writable:
        return Finding(name, ids, FAIL, f"{len(writable)} of {len(files)} files under {p} are writable ({rel(repo, writable[0])} ...)",
                       f"chmod -R a-w {p}, or keep raw in a store the pipeline cannot write; derived data is rebuilt, never hand-edited")
    return Finding(name, ids, PASS, f"{len(files)} files under {p}, none writable", "")


def check_raw_to_report(repo):
    name, ids = "raw to report", "DM1/D6, DM1/W7"
    text = read(Path(repo) / "CONTRIBUTING.md")
    if not text:
        return Finding(name, ids, NONE, "no CONTRIBUTING.md", "write one from templates/CONTRIBUTING.md")
    line = field(text, "Raw to report")
    if line is None:
        return Finding(name, ids, NONE, "CONTRIBUTING.md names no command from raw to report", "you cannot check a number you cannot regenerate")
    cmds = backtick_paths(line)
    if not cmds:
        return Finding(name, ids, FAIL, "CONTRIBUTING.md's *Raw to report* line still holds the template's placeholder",
                       "name the one command, and about how long it takes at full size")
    return Finding(name, ids, PASS, f"`{cmds[0]}`", "")


def ledger_rows(path):
    text = read(path)
    if path.suffix.lower() == ".jsonl":
        rows = []
        for line in text.splitlines():
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    rows.append({"_unparsed": line})
        return rows
    if path.suffix.lower() == ".csv":
        return list(csv.DictReader(io.StringIO(text)))
    return [r for t in parse_tables(text) for r in real_rows(t)]


def spent(row):
    for k, v in row.items():
        v = str(v).strip().lower()
        if "holdout" in str(k).lower() and v and v not in ("no", "false", "0", "n", "—", "-", ""):
            return True
        if str(k).lower() == "split" and "holdout" in v:
            return True
    return False


def check_ledger(repo):
    name, ids = "ledger", "DM1/F6, DM1/A3"
    files = find_docs(repo, ("docs/ledger.*", "docs/LEDGER*", "ledger.*", "LEDGER*", "**/ledger.jsonl", "**/ledger.csv"))
    if not files:
        return Finding(name, ids, NONE, "no ledger", "one line appended by the code each time anything is scored; the count is part of every result")
    machine = [f for f in files if f.suffix.lower() in (".jsonl", ".csv")]
    ledger = machine[0] if machine else files[0]
    rows = ledger_rows(ledger)
    writers = [rel(repo, f) for f in tracked_files(repo)
               if f.suffix.lower() in CODE_SUFFIXES and f.resolve() != ledger.resolve() and ledger.name in read(f)]
    n_spent = sum(1 for r in rows if spent(r))
    where = rel(repo, ledger)
    if not rows:
        return Finding(name, ids, NONE, f"{where}: empty" + (f"; written by {writers[0]}" if writers else ""), "")
    if not writers:
        return Finding(name, ids, WARN, f"{where}: {len(rows)} rows, holdout spent {n_spent} time(s); no code references it: appended from memory?",
                       "the code that scores appends the line; a summary's count is a claim")
    return Finding(name, ids, PASS, f"{where}: {len(rows)} rows, holdout spent {n_spent} time(s); written by {writers[0]}", "")


def check_model_cards(repo, question_text):
    name, ids = "model card", "DM1/D10, DM1/R10, DM1/O9"
    cards = find_docs(repo, ("docs/model_cards/*.md", "docs/MODEL_CARD*.md", "**/MODEL_CARD*.md", "**/model_card*.md"))
    if not cards:
        return Finding(name, ids, NONE, "no model card", "before a model decides anything: what it was trained on, how well by slice, how it fails")
    groups = field(question_text or "", "Groups that matter")
    names_groups = groups is not None and not placeholder(groups)
    bad, unsigned = [], []
    for c in cards:
        text = read(c)
        for f in ("Data version", "Code commit", "Seed(s)"):
            v = field(text, f)
            if v is None or placeholder(v.split("·")[0]):
                bad.append(f"{rel(repo, c)}: {f} not recorded")
                break
        audit = section(text, "Bias audit") or ""
        if names_groups and not any(real_rows(t) for t in parse_tables(audit)):
            bad.append(f"{rel(repo, c)}: bias audit empty while the question names groups ({groups.strip()[:40]})")
        if field(text, "This card") is None:
            unsigned.append(rel(repo, c))
    if bad:
        return Finding(name, ids, FAIL, f"{len(cards)} card(s); " + "; ".join(bad[:3]), "a model that scores people ships with its audit, or does not ship")
    if unsigned:
        return Finding(name, "SE1/U9", WARN, f"{len(cards)} card(s), identity and audit present; {unsigned[0]} does not say who wrote it or what would retire it",
                       "the template's *This card* line")
    return Finding(name, ids, PASS, f"{len(cards)} card(s), identity recorded" + (", bias audit filled" if names_groups else ", no groups named in the question"), "")


def check_environment(repo):
    repo = Path(repo).resolve()
    name, ids = "environment", "DM1/O1, DM1/D6"
    tracked = {rel(repo, f) for f in tracked_files(repo)}
    present = [n for n in LOCKS if (repo / n).is_file()]
    if not present:
        return Finding(name, ids, NONE, "no lock or environment file at the root", "a result records the environment it ran in, resolved")
    kept = [n for n in present if n in tracked]
    if kept:
        return Finding(name, ids, PASS, f"{kept[0]} tracked", "")
    return Finding(name, ids, WARN, f"{present[0]} present but not tracked (the guide's GAPS 6)",
                   "then each result must record its resolved environment some other way, and the model card says where")


def check_citations(repo, q, version, ids):
    name = "question citations"
    if not ids:
        return Finding(name, "DM1/R2, SE1/R10", NONE, "no question IDs to cite", "")
    bare, stale, ahead = [], [], []
    pat = re.compile(r"(?:(Q(\d+))/)?\b(" + "|".join(map(re.escape, ids)) + r")\b")
    for f in tracked_files(repo):
        r = rel(repo, f)
        if f.resolve() == q.resolve() or not is_text(f) or f.name.startswith(("QUESTION_v", "AGENTS")) or f.name in ("dm.py", "se.py"):
            continue
        if "templates" in Path(r).parts:
            continue
        for i, line in enumerate(read(f).splitlines(), 1):
            for m in pat.finditer(line):
                where = f"{r}:{i}"
                if not m.group(1):
                    bare.append(where)
                elif int(m.group(2)) < ids[m.group(3)]:
                    stale.append(f"{where} Q{m.group(2)}/{m.group(3)} (since v{ids[m.group(3)]})")
                elif int(m.group(2)) > version:
                    ahead.append(where)
    if bare or stale or ahead:
        parts = []
        if stale:
            parts.append(f"{len(stale)} stale (the definition moved): {stale[0]}")
        if bare:
            parts.append(f"{len(bare)} unversioned: {bare[0]}")
        if ahead:
            parts.append(f"{len(ahead)} ahead of v{version}: {ahead[0]}")
        return Finding(name, "DM1/R2, SE1/R10", FAIL, "; ".join(parts), "cite the question version that last changed the definition: Qn/ID, never a bare ID")
    return Finding(name, "DM1/R2, SE1/R10", PASS, f"every citation of the {len(ids)} question IDs is versioned and current", "")


def dm_rows(repo):
    repo = Path(repo).resolve()
    out = [check_agreements(repo), check_extends(repo)]
    qf, q, version, ids = check_question(repo)
    out.append(qf)
    out.append(check_plan(repo, q is not None))
    out.append(check_holdout(repo))
    out.append(check_datasheets(repo))
    out.append(check_raw(repo))
    out.append(check_raw_to_report(repo))
    out.append(check_ledger(repo))
    out.append(check_model_cards(repo, read(q) if q else ""))
    out.append(check_environment(repo))
    out.append(check_citations(repo, q, version, ids) if q else Finding("question citations", "DM1/R2, SE1/R10", NONE, "no question", ""))
    return out


def doctor(repo, online=True, cache_dir=None, se=None, today=None):
    """SE1's rows first, when se.py is at hand, then DM1's."""
    repo = Path(repo).resolve()
    out = []
    if se is not None:
        out += se.doctor(repo, online=online, cache_dir=cache_dir, today=today)
    else:
        out.append(Finding("SE1 doctor", "SE1/U7", NONE, "se.py not found: SE1's rows did not run",
                           "copy se.py from the SE1 guide beside dm.py, or set SE_GUIDE to a checkout of it"))
    return out + dm_rows(repo)


def python_kind():
    exe = sys.executable or ""
    kind = "pixi" if ".pixi" in exe else "conda" if ("conda" in exe or "miniforge" in exe or "mamba" in exe) else "system"
    return f"python {sys.version.split()[0]} ({kind}: {exe})"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="dm", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--doctor", action="store_true", help="check the data project (the default)")
    ap.add_argument("--repo", default=".", help="the repository to check (default: here)")
    ap.add_argument("--offline", action="store_true", help="do not try the network for SE1's release check")
    ap.add_argument("--dm-only", action="store_true", help="only DM1's rows, even if se.py is at hand")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    se, se_path = (None, None) if a.dm_only else find_se(repo)
    if a.version:
        print(f"dm {RELEASE} · se {se.RELEASE + ' at ' + str(se_path) if se else 'not found'} · {python_kind()}")
        return 0
    findings = doctor(repo, online=not a.offline, se=se)
    if a.json:
        print(json.dumps([f._asdict() for f in findings], indent=2))
    else:
        print(f"dm --doctor · {repo} · dm {RELEASE} · se {se.RELEASE if se else 'not found'} · {python_kind()}")
        for f in findings:
            fix = f"  → {f.fix}" if f.fix and f.state != PASS else ""
            print(f"[{f.state:>8}] {f.name:<22} ({f.ids})  {f.text}{fix}")
        bad = sum(1 for f in findings if f.state == FAIL)
        print(f"{len(findings)} checks, {bad} failed" + ("" if bad else "; none yet is a true answer"))
    return 1 if any(f.state == FAIL for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
