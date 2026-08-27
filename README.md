# Data Mining — Fall 2026

Course projects for Data Mining at Colorado Mesa University.

**[`DATA-SCIENCE.md`](DATA-SCIENCE.md) is why this repository is shaped the way it is** — what the
course thinks the discipline is, and what makes a claim worth acting on. This file is the mechanics:
how to install and run things.

Everything in this repository is run through **[pixi](https://pixi.prefix.dev)**.
There is one command to set up and one command to run. There is no `conda
activate`, no `.venv` to source, no `setup.sh`, and **no WSL requirement** —
Windows students run this natively in PowerShell.

---

## 1. One-time setup

### Install pixi

**macOS**

```bash
brew install pixi
```

or, without Homebrew:

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

**Windows** — run in PowerShell. This is native Windows; you do not need WSL,
Ubuntu, or Docker for the projects in this repo.

```powershell
winget install prefix-dev.pixi
```

or, if you do not have winget:

```powershell
powershell -ExecutionPolicy Bypass -c "irm -useb https://pixi.sh/install.ps1 | iex"
```

**Linux / WSL**

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Close and reopen your terminal, then check it:

```bash
pixi --version
```

### Get the code

```bash
git clone git@github.com:wmacevoy/data-mining-wmacevoy-fall-2026
cd data-mining-wmacevoy-fall-2026
pixi install
```

That last command solves `pixi.toml` and builds an environment under `.pixi/`.
It installs about 200 packages and occupies roughly 775 MB. On a warm cache it
finishes in seconds; a cold first run took about 12 seconds on an M-series Mac.
You never activate this environment and you never edit it.

> The broader laptop setup — disk encryption, GitHub SSH keys, GPG, 1Password —
> is unchanged, and still lives in
> [`devops-wmacevoy/macos.md`](https://github.com/wmacevoy/devops-wmacevoy/blob/main/macos.md)
> and
> [`windows.md`](https://github.com/wmacevoy/devops-wmacevoy/blob/main/windows.md).
> Follow those first. For **this** repo you can skip the WSL and Docker steps.

---

## 2. Everyday use

Every task runs from the repository root, regardless of which folder you are in:

```bash
pixi run app      # launch the Colorado River dashboard
pixi run test     # run the test suite
pixi run lint     # check code style
pixi run meta     # list available USGS gauges
pixi run px       # Parquet explorer (CLI)
pixi run clean    # delete cached data and debug snapshots
```

To see everything available:

```bash
pixi task list
```

Arguments pass straight through:

```bash
pixi run app --server.port 8502
pixi run px data/*.parquet --columns
```

If you want a shell with the environment already on your `PATH`:

```bash
pixi shell
```

---

## 3. Why pixi, and what it replaced

The previous course repo configured each project with a hand-written
`setup.sh` + `context.sh` pair wrapping conda. The idea was right — a
project-local environment with no global activation — but it drifted: seven
projects ended up with five different `setup.sh` files, and because
`environment.yml` was almost entirely unpinned, no two students ever solved the
same environment.

Pixi is the same idea with the drift designed out:

| Old scaffolding | Now |
| --- | --- |
| `./setup.sh` | `pixi install` |
| `./run.sh`, `./python.sh`, `./px.sh`, `./meta.sh` | `pixi run <task>` |
| `context.sh` conda-prefix helpers | built in |
| `.venv/` via `conda create -p` | `.pixi/envs/` |
| `environment.yml` + `requirements.txt` (which disagreed) | one `[dependencies]` table |
| `jq` required to read `config.json` | not required |
| bash required → WSL on Windows | native PowerShell |

Two things are worth calling out:

**One dependency table is the actual fix.** The old setup had
`environment.yml` and `requirements.txt` disagreeing with each other, and
neither was pinned meaningfully. Now there is one `[dependencies]` table with
real version constraints, and `pixi install` solves it for your platform.

**On `pixi.lock`.** Pixi writes one, and this repo does **not** commit it. That
is deliberate. A committed lock pins exact builds, which is the right call for
a deployed service and the wrong one for a course: it solves per-platform, it
goes stale over a fifteen-week semester, and a build yanked from the channel in
October breaks every student at once with no way forward. Instead everyone
solves fresh from `pixi.toml`, and the constraints there are what keep you in
range. The tradeoff is real and worth naming: two students may end up on
slightly different patch versions. If a result ever depends on which, that is a
finding about the result — see [`DATA-SCIENCE.md`](DATA-SCIENCE.md) on
provenance.

Your local `pixi.lock` is untracked, not ignored. Leave it alone; it is yours.

**No bash means no WSL.** The old wrappers were shell scripts, which is what
forced Windows students onto WSL for what is otherwise a pure-Python project.
Pixi tasks are declared in `pixi.toml` and executed by pixi's own cross-platform
shell, so `pixi run app` behaves identically in PowerShell, Terminal, and bash.
CI proves this on every push — see below.

---

## 4. How `pixi.toml` is organized

Open it; it is short and commented. The structure answers "shared baseline,
per-project differences":

```toml
[dependencies]              # the baseline EVERY project inherits
python, pandas, numpy, pyarrow, ...

[feature.dev.dependencies]  # tooling shared by every project
pytest, ruff

[feature.colorado-river.dependencies]   # just this project's extras
streamlit, altair, httpx, matplotlib

[feature.colorado-river.tasks]          # just this project's commands
app, px, meta, test, lint, clean

[environments]
default = ["colorado-river", "dev"]
```

Adding a project is a feature block plus one line under `[environments]`.
Nothing is copied between projects, so nothing can drift out of sync.

### Adding a project

```toml
[feature.houses.dependencies]
scikit-learn = ">=1.5"
seaborn = ">=0.13"

[feature.houses.tasks]
train = { cmd = "python train.py", cwd = "houses" }

[environments]
houses = ["houses", "dev"]
```

Then `pixi install` and `pixi run -e houses train`.

### Changing dependencies

Edit `pixi.toml` (or use `pixi add <package>`) and commit `pixi.toml`. Do not
commit `pixi.lock`.

Because there is no lock, **the constraints in `pixi.toml` are the only pinning
this repo has**, so write real ones. The baseline already bounds both ends
(`pandas = ">=2.2,<3"`, `numpy = ">=1.26,<3"`, `python = "3.12.*"`); the
per-project extras are lower-bound only, which is where a major release
upstream could break a build mid-semester. If that happens, the fix is an upper
bound in `pixi.toml`, not a lockfile. CI will tell you on all three platforms
whether your change still solves.

---

## 5. Continuous integration

`.github/workflows/ci.yaml` runs lint and tests on **Ubuntu, macOS, and
Windows** for every push. It passes no `locked:` and no `cache:` — both of those
require a committed `pixi.lock`, and `cache: true` is a hard error without one
because it builds its cache key by hashing that file. So every run solves
`pixi.toml` from scratch, which is exactly what happens on a student's first
`pixi install`. CI tests the experience you actually have.

The Windows leg is not decoration. It is how we find out that a dependency
lacks a `win-64` build in week one rather than the night before an assignment
is due.

---

## 6. Troubleshooting

**`pixi: command not found` right after installing**
Close and reopen your terminal. The installer adds pixi to your `PATH` in your
shell profile, which only takes effect in new shells.

**"lockfile is out of date"**
Your local `pixi.lock` no longer matches `pixi.toml`. Run `pixi install` to
re-solve. Nothing needs committing — the lock is not tracked.

**The dashboard does not open a browser tab by itself**
That is intentional — see `colorado_river/.streamlit/config.toml`. Click the
`Local URL:` that Streamlit prints.

**Stale or corrupt environment**
```bash
pixi clean          # remove .pixi/ for this workspace
pixi install
```

**Start completely over**
```bash
pixi clean
pixi clean cache    # also clears the shared package cache
pixi install
```

---

## License

MIT — see [`LICENSE`](LICENSE).
