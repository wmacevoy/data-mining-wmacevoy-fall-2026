# dm.ps1: runs dm.py with the repository's own Python when it has one (see `dm` for the order).
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dmPy = Join-Path $here "dm.py"
$candidates = @()
if ($env:CONDA_PREFIX) { $candidates += (Join-Path $env:CONDA_PREFIX "python.exe"); $candidates += (Join-Path $env:CONDA_PREFIX "bin/python") }
$candidates += (Join-Path $here ".pixi/envs/default/python.exe")
$candidates += (Join-Path $here ".pixi/envs/default/bin/python")
foreach ($c in $candidates) { if (Test-Path $c) { & $c $dmPy @args; exit $LASTEXITCODE } }
if ((Test-Path (Join-Path $here "pixi.toml")) -and (Get-Command pixi -ErrorAction SilentlyContinue)) {
  pixi run --manifest-path (Join-Path $here "pixi.toml") python $dmPy @args; exit $LASTEXITCODE
}
foreach ($name in @("python3", "python")) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if ($cmd) { & $cmd.Source $dmPy @args; exit $LASTEXITCODE }
}
Write-Error "dm: no python found; install Python 3.9 or later"
exit 2
