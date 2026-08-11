param(
    [string]$SimHubInstallPath = "C:\Program Files (x86)\SimHub",
    [string]$PackagePath = (Join-Path $PSScriptRoot "dist\AuthenticControls"),
    [switch]$ReplaceOverlayLayouts
)

$ErrorActionPreference = "Stop"
$packageRoot = [System.IO.Path]::GetFullPath($PackagePath)
$simHubRoot = [System.IO.Path]::GetFullPath($SimHubInstallPath)

if (-not (Test-Path -LiteralPath (Join-Path $packageRoot "AuthenticControls.Plugin.dll"))) {
    throw "The built Authentic Controls package was not found: $packageRoot"
}
if (-not (Test-Path -LiteralPath (Join-Path $simHubRoot "SimHubWPF.exe"))) {
    throw "The SimHub installation could not be verified: $simHubRoot"
}
if (Get-Process -Name "SimHubWPF" -ErrorAction SilentlyContinue) {
    throw "Close SimHub before installing Authentic Controls."
}

$backupRoot = Join-Path $env:TEMP ("AuthenticControls-SimHub-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

function Backup-RelativePath {
    param([string]$RelativePath)

    $source = Join-Path $simHubRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        return
    }
    $target = Join-Path $backupRoot $RelativePath
    New-Item -ItemType Directory -Path (Split-Path $target -Parent) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $target -Recurse -Force
}

foreach ($relativePath in @(
    "AuthenticControls.Plugin.dll",
    "AuthenticControls.Plugin.pdb",
    "AuthenticControls.Core.dll",
    "AuthenticControls.Core.pdb",
    "PluginsData\AuthenticControls",
    "DashTemplates\Authentic Controls Preflight Overlay",
    "DashTemplates\Authentic Controls Preflight Compact",
    "DashTemplates\Authentic Controls Preflight Glance",
    "DashTemplates\Authentic Controls Preflight Display"
)) {
    Backup-RelativePath $relativePath
}

$installedLayoutDirectory = Join-Path $simHubRoot "OverlayLayouts"
if (Test-Path -LiteralPath $installedLayoutDirectory) {
    foreach ($layout in Get-ChildItem -LiteralPath $installedLayoutDirectory -Filter "Authentic Controls*.olayout") {
        Backup-RelativePath ("OverlayLayouts\" + $layout.Name)
    }
}

foreach ($fileName in @(
    "AuthenticControls.Plugin.dll",
    "AuthenticControls.Plugin.pdb",
    "AuthenticControls.Core.dll",
    "AuthenticControls.Core.pdb"
)) {
    Copy-Item -LiteralPath (Join-Path $packageRoot $fileName) -Destination $simHubRoot -Force
}
Copy-Item -LiteralPath (Join-Path $packageRoot "PluginsData") -Destination $simHubRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $packageRoot "DashTemplates") -Destination $simHubRoot -Recurse -Force

New-Item -ItemType Directory -Path $installedLayoutDirectory -Force | Out-Null
$preservedLayouts = @()
$resizedLayouts = @()
foreach ($sourceLayout in Get-ChildItem -LiteralPath (Join-Path $packageRoot "OverlayLayouts") -Filter "*.olayout") {
    $installedLayout = Join-Path $installedLayoutDirectory $sourceLayout.Name
    if ((Test-Path -LiteralPath $installedLayout) -and -not $ReplaceOverlayLayouts) {
        $preservedLayouts += $sourceLayout.Name
        continue
    }
    Copy-Item -LiteralPath $sourceLayout.FullName -Destination $installedLayout -Force
}

# Version 0.9.6 narrowed the Detailed surface. Version 0.10.3 adds technique
# guidance to Compact and raises its height from 260 to 300. Preserve customized
# positions by keeping each migrated part centered, and leave any already-custom-
# sized part untouched. The pre-install backup makes this migration reversible.
if (-not $ReplaceOverlayLayouts) {
    foreach ($layout in Get-ChildItem -LiteralPath $installedLayoutDirectory -Filter "Authentic Controls*.olayout") {
        $payload = Get-Content -LiteralPath $layout.FullName -Raw | ConvertFrom-Json
        $changed = $false
        foreach ($part in $payload.OverlayLayoutParts) {
            if ($part.DashboardName -like "*Authentic Controls Preflight Overlay.djson" -and
                [double]$part.Width -eq 900.0) {
                $center = [double]$part.Left + ([double]$part.Width / 2.0)
                $part.Width = 840.0
                $part.Left = $center - 420.0
                $changed = $true
            }
            if ($part.DashboardName -like "*Authentic Controls Preflight Compact.djson" -and
                [double]$part.Height -eq 260.0) {
                $center = [double]$part.Top + ([double]$part.Height / 2.0)
                $part.Height = 300.0
                $part.Top = $center - 150.0
                $changed = $true
            }
        }
        if ($changed) {
            $json = $payload | ConvertTo-Json -Depth 20
            [System.IO.File]::WriteAllText(
                $layout.FullName,
                $json,
                (New-Object System.Text.UTF8Encoding($false)))
            $resizedLayouts += $layout.Name
        }
    }
}

Write-Host "Installed Authentic Controls from: $packageRoot"
Write-Host "Rollback backup: $backupRoot"
if ($preservedLayouts.Count -gt 0) {
    Write-Host ("Preserved customized overlay layouts: " + ($preservedLayouts -join ", "))
}
if ($resizedLayouts.Count -gt 0) {
    Write-Host ("Centered and resized updated overlay surfaces in: " + ($resizedLayouts -join ", "))
}
