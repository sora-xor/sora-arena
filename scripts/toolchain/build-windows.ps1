# Build the native practice kernel and UE editor with project-scoped Windows pins.
[CmdletBinding()]
param(
    [ValidateSet('Development', 'DebugGame')][string]$Configuration = 'Development',
    [string]$EngineRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$doctor = Join-Path $PSScriptRoot 'doctor-windows.ps1'
$pins = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'versions.json') | ConvertFrom-Json
$reportText = & $doctor -Json -EngineRoot $EngineRoot
if ($LASTEXITCODE -ne 0) {
    Write-Error 'Pinned Windows prerequisites are unavailable. Run scripts/toolchain/doctor-windows.ps1 for details.'
    exit 1
}
$report = $reportText | ConvertFrom-Json
if (-not $report.build_ready) { throw 'The Windows doctor did not certify build prerequisites.' }

$sourceConfig = Join-Path $root 'Config\UnrealBuildTool\BuildConfiguration.xml'
$localConfig = Join-Path $root 'Saved\UnrealBuildTool\BuildConfiguration.xml'
if (-not (Test-Path -LiteralPath $localConfig -PathType Leaf)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $localConfig) -Force | Out-Null
    Copy-Item -LiteralPath $sourceConfig -Destination $localConfig
}

Push-Location $root
try {
    & cargo build --locked --release -p arena-ffi
    if ($LASTEXITCODE -ne 0) { throw "Rust native kernel build failed with exit code $LASTEXITCODE." }
    & py -3 scripts/unreal/stage_kernel.py --platform Win64
    if ($LASTEXITCODE -ne 0) { throw "Native kernel staging failed with exit code $LASTEXITCODE." }
    & py -3 scripts/unreal/verify_parity.py
    if ($LASTEXITCODE -ne 0) { throw "Windows native parity failed with exit code $LASTEXITCODE." }
    & py -3 scripts/unreal/test_parity_guards.py
    if ($LASTEXITCODE -ne 0) { throw "Parity guard tests failed with exit code $LASTEXITCODE." }

    $buildBat = Join-Path ([string]$report.engine_root) 'Engine\Build\BatchFiles\Build.bat'
    & $buildBat SoraArenaEditor Win64 $Configuration "-Project=$($report.project)" -WaitMutex `
        '-Compiler=VisualStudio2022' "-CompilerVersion=$($pins.windows.msvc)"
    if ($LASTEXITCODE -ne 0) { throw "Unreal editor build failed with exit code $LASTEXITCODE." }
    Write-Output 'Windows native parity and SoraArenaEditor compilation completed. Cooking, packaging, visual quality, and runtime remain separate gates.'
} finally {
    Pop-Location
}
