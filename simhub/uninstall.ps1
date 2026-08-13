param(
    [string]$SimHubInstallPath = "C:\Program Files (x86)\SimHub",
    [string]$BackupDirectory = "",
    [switch]$RemovePackagedLayouts
)

$ErrorActionPreference = "Stop"
$simHubRoot = [System.IO.Path]::GetFullPath($SimHubInstallPath)
if (-not (Test-Path -LiteralPath (Join-Path $simHubRoot "SimHubWPF.exe"))) {
    throw "The SimHub installation could not be verified: $simHubRoot"
}
$targetExecutable = [System.IO.Path]::GetFullPath((Join-Path $simHubRoot "SimHubWPF.exe"))
foreach ($process in @(Get-Process -Name "SimHubWPF" -ErrorAction SilentlyContinue)) {
    try {
        $runningExecutable = [System.IO.Path]::GetFullPath($process.MainModule.FileName)
        if ($runningExecutable.Equals($targetExecutable, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Close SimHub before removing As Driven."
        }
    }
    catch [System.Management.Automation.RuntimeException] {
        throw
    }
    catch {
        if ($simHubRoot.Equals(
            [System.IO.Path]::GetFullPath("C:\Program Files (x86)\SimHub"),
            [StringComparison]::OrdinalIgnoreCase)) {
            throw "Close SimHub before removing As Driven."
        }
    }
}

if ([string]::IsNullOrWhiteSpace($BackupDirectory)) {
    $BackupDirectory = Join-Path $env:TEMP (
        "AsDriven-SimHub-uninstall-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
}
$backupRoot = [System.IO.Path]::GetFullPath($BackupDirectory)
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

function Backup-And-Remove {
    param([string]$RelativePath)

    $source = Join-Path $simHubRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        return
    }
    $target = Join-Path $backupRoot $RelativePath
    New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
    Remove-Item -LiteralPath $source -Recurse -Force
}

foreach ($relativePath in @(
    "AsDriven.Plugin.dll",
    "AsDriven.Plugin.pdb",
    "AsDriven.Core.dll",
    "AsDriven.Core.pdb",
    "DashTemplates\As Driven Preflight Overlay",
    "DashTemplates\As Driven Preflight Compact",
    "DashTemplates\As Driven Preflight Glance",
    "DashTemplates\As Driven Preflight Display",
    "DashTemplates\As Driven Verification Drive"
)) {
    Backup-And-Remove $relativePath
}

if ($RemovePackagedLayouts) {
    $layoutDirectory = Join-Path $simHubRoot "OverlayLayouts"
    if (Test-Path -LiteralPath $layoutDirectory) {
        foreach ($layout in Get-ChildItem -LiteralPath $layoutDirectory -File -Filter "As Driven*.olayout") {
            Backup-And-Remove ("OverlayLayouts\" + $layout.Name)
        }
    }
}

Write-Host "Removed As Driven plugin binaries and packaged dashboards."
Write-Host "Backup: $backupRoot"
Write-Host "Preserved PluginsData, settings, diagnostics, contribution drafts, and customized overlay layouts."
if ($RemovePackagedLayouts) {
    Write-Host "As Driven overlay layout files were removed because -RemovePackagedLayouts was supplied."
}
