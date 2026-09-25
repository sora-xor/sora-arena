# Read-only Windows prerequisite report for the pinned Unreal Engine build (scripts/toolchain/versions.json).
[CmdletBinding()]
param(
    [string]$EngineRoot,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$pins = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'versions.json') | ConvertFrom-Json
$checks = [Collections.Generic.List[object]]::new()

function Add-Check {
    param([string]$Name, [object]$Actual, [object]$Expected, [bool]$Ok, [string]$Detail = '')
    $checks.Add([pscustomobject]@{
        name = $Name
        actual = $Actual
        expected = $Expected
        ok = $Ok
        detail = $Detail
    })
}

function Test-UbtPinXml {
    param([string]$Path, [object]$Pins)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    try {
        [xml]$config = Get-Content -Raw -LiteralPath $Path
        $node = $config.SelectSingleNode("//*[local-name()='WindowsPlatform']")
        if ($null -eq $node) { return $false }
        $compiler = $node.SelectSingleNode("*[local-name()='Compiler']")
        $msvc = $node.SelectSingleNode("*[local-name()='CompilerVersion']")
        $sdk = $node.SelectSingleNode("*[local-name()='WindowsSdkVersion']")
        return $null -ne $compiler -and $compiler.InnerText -eq 'VisualStudio2022' -and
            $null -ne $msvc -and $msvc.InnerText -eq [string]$Pins.windows.msvc -and
            $null -ne $sdk -and $sdk.InnerText -eq [string]$Pins.windows.sdk
    } catch { return $false }
}

$isWindows = [Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT
Add-Check 'host' ([Environment]::OSVersion.ToString()) '64-bit Windows' ($isWindows -and [Environment]::Is64BitOperatingSystem)

if ([string]::IsNullOrWhiteSpace($EngineRoot)) { $EngineRoot = $env:UE_ROOT }
if ([string]::IsNullOrWhiteSpace($EngineRoot)) { $EngineRoot = [string]$pins.unreal.default_windows_root }
$engine = [IO.Path]::GetFullPath($EngineRoot)
$buildVersionPath = Join-Path $engine 'Engine\Build\Build.version'
$buildVersion = $null
$actualEngineVersion = $null
if (Test-Path -LiteralPath $buildVersionPath -PathType Leaf) {
    try {
        $buildVersion = Get-Content -Raw -LiteralPath $buildVersionPath | ConvertFrom-Json
        $actualEngineVersion = @($buildVersion.MajorVersion, $buildVersion.MinorVersion, $buildVersion.PatchVersion) -join '.'
    } catch {
        $buildVersion = $null
        $actualEngineVersion = "invalid Build.version: $($_.Exception.Message)"
    }
}
# Same identity as scripts/unreal/sora_engine_pin.py: exact version, changelists,
# branch, promoted/licensee flags, Launcher installed build and the project's
# engine plugin descriptors.
Add-Check 'unreal' $actualEngineVersion ([string]$pins.unreal.version) ($actualEngineVersion -eq [string]$pins.unreal.version) $engine
foreach ($field in @(
        @('unreal_changelist', 'Changelist', 'changelist'),
        @('unreal_compatible_changelist', 'CompatibleChangelist', 'compatible_changelist'),
        @('unreal_branch', 'BranchName', 'branch'),
        @('unreal_promoted_build', 'IsPromotedBuild', 'is_promoted_build'),
        @('unreal_licensee_version', 'IsLicenseeVersion', 'is_licensee_version'))) {
    $actualField = $null
    if ($null -ne $buildVersion -and @($buildVersion.PSObject.Properties.Name) -contains $field[1]) {
        $actualField = $buildVersion.($field[1])
    }
    $expectedField = $pins.unreal.($field[2])
    Add-Check $field[0] $actualField $expectedField ($null -ne $actualField -and [string]$actualField -ceq [string]$expectedField)
}
$installedBuild = Test-Path -LiteralPath (Join-Path $engine 'Engine\Build\InstalledBuild.txt') -PathType Leaf
$installedLabel = 'installed build (Engine/Build/InstalledBuild.txt)'
Add-Check 'unreal_distribution' $(if ($installedBuild) { $installedLabel } else { 'not an installed build' }) $installedLabel $installedBuild ([string]$pins.unreal.distribution)
$pluginActual = [ordered]@{}
$pluginExpected = [ordered]@{}
$pluginsOk = $true
foreach ($plugin in $pins.unreal.plugins.PSObject.Properties) {
    $pluginExpected[$plugin.Name] = "$($plugin.Value.version_name) (version $($plugin.Value.version))"
    $pluginActual[$plugin.Name] = $null
    $descriptor = Join-Path $engine ([string]$plugin.Value.descriptor)
    if (Test-Path -LiteralPath $descriptor -PathType Leaf) {
        try {
            $pluginData = Get-Content -Raw -LiteralPath $descriptor | ConvertFrom-Json
            $pluginActual[$plugin.Name] = "$($pluginData.VersionName) (version $($pluginData.Version))"
        } catch {}
    }
    if ($pluginActual[$plugin.Name] -cne $pluginExpected[$plugin.Name]) { $pluginsOk = $false }
}
Add-Check 'unreal_plugins' ([pscustomobject]$pluginActual) ([pscustomobject]$pluginExpected) $pluginsOk
$batchFile = Join-Path $engine 'Engine\Build\BatchFiles\Build.bat'
Add-Check 'unreal_build_script' $batchFile 'Engine\Build\BatchFiles\Build.bat' (Test-Path -LiteralPath $batchFile -PathType Leaf)

$vswhere = $null
if ($isWindows -and -not [string]::IsNullOrWhiteSpace(${env:ProgramFiles(x86)})) {
    $candidate = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $vswhere = $candidate }
}
if ($null -eq $vswhere) {
    $command = Get-Command vswhere.exe -ErrorAction SilentlyContinue
    if ($null -ne $command) { $vswhere = $command.Source }
}
$vs = $null
if ($null -ne $vswhere) {
    try {
        $instances = @((& $vswhere -products '*' -all -format json -utf8 | Out-String | ConvertFrom-Json))
        $vs = $instances | Where-Object {
            $_.installationVersion -match '^17\.14(?:\.|$)' -and $_.isComplete -and $_.isLaunchable -and -not $_.isPrerelease
        } | Sort-Object installationVersion -Descending | Select-Object -First 1
    } catch { $vs = $null }
}
$vsVersion = if ($null -ne $vs) { [string]$vs.installationVersion } else { $null }
Add-Check 'visual_studio' $vsVersion ([string]$pins.windows.visual_studio) ($null -ne $vs) 'Stable, complete VS 2022 17.14 installation via vswhere.'

$msvcRoot = if ($null -ne $vs) { Join-Path ([string]$vs.installationPath) ("VC\Tools\MSVC\" + $pins.windows.msvc) } else { $null }
$msvcFiles = @('bin\Hostx64\x64\cl.exe', 'bin\Hostx64\x64\link.exe', 'include\yvals_core.h', 'lib\x64\vcruntime.lib')
$msvcOk = $null -ne $msvcRoot
if ($msvcOk) {
    foreach ($relative in $msvcFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $msvcRoot $relative) -PathType Leaf)) { $msvcOk = $false }
    }
}
Add-Check 'msvc' $(if ($msvcOk) { [string]$pins.windows.msvc } else { $null }) ([string]$pins.windows.msvc) $msvcOk $msvcRoot

$sdkRoot = $null
if ($isWindows) {
    try { $sdkRoot = Get-ItemPropertyValue -Path 'HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots' -Name 'KitsRoot10' -ErrorAction Stop } catch {}
    if ([string]::IsNullOrWhiteSpace($sdkRoot) -and -not [string]::IsNullOrWhiteSpace(${env:ProgramFiles(x86)})) {
        $sdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits\10'
    }
}
$sdkFiles = @(
    "Include\$($pins.windows.sdk)\um\Windows.h",
    "Lib\$($pins.windows.sdk)\um\x64\kernel32.lib",
    "bin\$($pins.windows.sdk)\x64\rc.exe"
)
$sdkOk = -not [string]::IsNullOrWhiteSpace($sdkRoot)
if ($sdkOk) {
    foreach ($relative in $sdkFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $sdkRoot $relative) -PathType Leaf)) { $sdkOk = $false }
    }
}
Add-Check 'windows_sdk' $(if ($sdkOk) { [string]$pins.windows.sdk } else { $null }) ([string]$pins.windows.sdk) $sdkOk $sdkRoot

$rustup = Get-Command rustup.exe -ErrorAction SilentlyContinue
$rustc = Get-Command rustc.exe -ErrorAction SilentlyContinue
$cargo = Get-Command cargo.exe -ErrorAction SilentlyContinue
$target = 'x86_64-pc-windows-msvc'
$installedTargets = @()
$rustHost = $null
if ($null -ne $rustup -and $null -ne $rustc -and $null -ne $cargo) {
    try {
        $installedTargets = @(& $rustup.Source target list --installed)
        $rustHost = (& $rustc.Source -vV | Where-Object { $_ -match '^host: ' } | Select-Object -First 1) -replace '^host: ', ''
    } catch {}
}
Add-Check 'rust_msvc_target' $installedTargets $target ($installedTargets -contains $target -and $rustHost -eq $target) "rustc host: $rustHost"
Add-Check 'cargo' $(if ($null -ne $cargo) { $cargo.Source } else { $null }) 'cargo.exe available' ($null -ne $cargo)

$python = Get-Command py.exe -ErrorAction SilentlyContinue
$pythonVersion = $null
if ($null -ne $python) {
    try { $pythonVersion = (& $python.Source -3 --version 2>&1 | Out-String).Trim() } catch {}
}
Add-Check 'python3' $pythonVersion 'Python 3 via py -3' ($pythonVersion -match '^Python 3\.')

$projectFiles = @(Get-ChildItem -LiteralPath $root -Filter '*.uproject' -File)
$projectOk = $projectFiles.Count -eq 1 -and $projectFiles[0].Name -eq 'SoraArena.uproject'
if ($projectOk) {
    try {
        $projectData = Get-Content -Raw -LiteralPath $projectFiles[0].FullName | ConvertFrom-Json
        $projectOk = $projectData.EngineAssociation -eq '5.8' -and @($projectData.Modules.Name) -contains 'SoraArena'
    } catch { $projectOk = $false }
}
$sourceFiles = @(
    'Source\SoraArena.Target.cs', 'Source\SoraArenaEditor.Target.cs',
    'Source\SoraArena\SoraArena.Build.cs', 'Source\SoraArena\Private\SoraArena.cpp',
    'crates\arena-ffi\Cargo.toml', 'crates\arena-ffi\include\arena.h',
    'scripts\unreal\stage_kernel.py', 'scripts\unreal\verify_parity.py'
)
foreach ($relative in $sourceFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $relative) -PathType Leaf)) { $projectOk = $false }
}
Add-Check 'project_source' @($projectFiles.Name) 'SoraArena 5.8 C++/Rust source' $projectOk $root

$ubtConfig = Join-Path $root 'Config\UnrealBuildTool\BuildConfiguration.xml'
$configOk = Test-UbtPinXml $ubtConfig $pins
Add-Check 'project_ubt_pins' $(if ($configOk) { $ubtConfig } else { $null }) 'VS 2022 / pinned MSVC / pinned SDK' $configOk
$localConfig = Join-Path $root 'Saved\UnrealBuildTool\BuildConfiguration.xml'
if (Test-Path -LiteralPath $localConfig -PathType Leaf) {
    Add-Check 'existing_local_ubt_config' $localConfig 'same Windows pins as project config' (Test-UbtPinXml $localConfig $pins)
}

$ready = @($checks | Where-Object { -not $_.ok }).Count -eq 0
$report = [pscustomobject]@{
    build_ready = $ready
    engine_root = $engine
    project = (Join-Path $root 'SoraArena.uproject')
    checks = $checks.ToArray()
    note = 'Presence/version checks only. Native parity, Unreal compilation, cooking, packaging, rendering, and gameplay still require separate runs.'
}
if ($Json) {
    $report | ConvertTo-Json -Depth 8
} else {
    foreach ($check in $checks) {
        $mark = if ($check.ok) { 'OK' } else { 'MISSING/MISMATCH' }
        Write-Output "$mark  $($check.name): $($check.actual) (expected $($check.expected))"
        if ($check.detail) { Write-Output "    $($check.detail)" }
    }
    Write-Output "Pinned Windows build prerequisites: $(if ($ready) { 'READY' } else { 'NOT READY' })"
    Write-Output $report.note
}
if ($ready) { exit 0 } else { exit 1 }
